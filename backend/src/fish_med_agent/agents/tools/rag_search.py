import asyncio
from typing import ClassVar, Any

import httpx

from fish_med_agent.agents.tools.base import Tool
from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_MODE = "mix"
_VALID_MODES = {"naive", "local", "global", "hybrid", "mix"}

# 重试配置：3 次尝试（1 初始 + 2 重试），退避 0.5s → 1.0s
_MAX_ATTEMPTS = 3
_BASE_BACKOFF_S = 0.5


class RAGSearchTool(Tool):
    """基于 LightRAG 的鱼病专业知识库检索工具。

    调用 LightRAG 的 /query/data 接口获取**原始检索结果**（chunks + references），
    不让 LightRAG 内部 LLM 生成答案——最终诊断由主 agent (DeepSeek) 综合输出。
    """

    name: ClassVar[str] = "rag_search"
    description: ClassVar[str] = (
        "查询鱼病专业知识库（基于水产养殖文献、病害图谱和诊疗资料构建）。"
        "在已收集到鱼种、症状等关键诊断信息后，应**优先**调用此工具检索病因、"
        "诊断依据和处置方案——这是最权威的领域知识来源，优先级高于 web_search。"
        "调用前请将用户描述提炼成简洁的中文查询，包含鱼种和核心症状关键词。"
        "例如：'草鱼 烂鳃 体表溃烂 治疗'。"
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "中文查询语句，建议包含鱼种 + 症状关键词，长度不少于 3 个字符",
                "minLength": 3,
            },
            "mode": {
                "type": "string",
                "enum": ["naive", "local", "global", "hybrid", "mix"],
                "description": (
                    "检索模式，根据问题特点选择：\n"
                    "- naive：纯向量检索，最快最省，适合关键词明确的简单查询\n"
                    "- local：实体邻域检索，适合查询特定病害名/药品名/鱼种\n"
                    "- global：关系图检索，适合查询病因关联、并发症、传播链等抽象关系\n"
                    "- hybrid：local + global 组合，适合涉及多个实体和关系的复杂问题\n"
                    "- mix：hybrid + 全文 chunks，最全面但最慢，适合疑难病例或需要详细证据的诊断\n"
                    "不确定时选 mix"
                ),
                "default": "mix",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_mode: str = _DEFAULT_MODE,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.LIGHTRAG_BASE_URL).rstrip("/")
        self._api_key = api_key or settings.LIGHTRAG_API_KEY
        self._default_mode = default_mode
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-API-Key": self._api_key},
            timeout=timeout or settings.LIGHTRAG_TIMEOUT,
            # LightRAG 永远是 localhost / 内网，禁用环境变量里的代理设置
            # 避免 HTTP_PROXY / ALL_PROXY / 系统代理（ClashX 等）劫持本地请求
            trust_env=False,
        )

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query")
        if not isinstance(query, str) or len(query.strip()) < 3:
            return {"error": "query 至少需要 3 个字符"}

        # mode 来自 LLM；非法值退回默认
        mode = kwargs.get("mode") or self._default_mode
        if mode not in _VALID_MODES:
            logger.warning(f"invalid mode {mode!r} from LLM, fallback to {self._default_mode}")
            mode = self._default_mode

        # conversation_history 由 agent 注入，供 LightRAG 内部 LLM 作上下文
        # 已经在 chat_service 层过滤为 [{role, content}]，且只含 user/assistant
        conversation_history = kwargs.get("conversation_history") or []

        query = query.strip()
        logger.info(
            f"rag_search query={query!r} mode={mode} "
            f"history_turns={len(conversation_history)}"
        )

        body: dict[str, Any] = {"query": query, "mode": mode}
        if conversation_history:
            body["conversation_history"] = conversation_history

        payload_or_error = await self._post_with_retry("/query/data", body)
        if "error" in payload_or_error:
            return payload_or_error
        payload = payload_or_error

        if not isinstance(payload, dict) or payload.get("status") != "success":
            msg = payload.get("message", "未知错误") if isinstance(payload, dict) else "响应格式异常"
            logger.warning(f"rag_search non-success status: {msg}")
            return {"error": f"知识库返回非成功状态：{msg}"}

        data = payload.get("data") or {}
        chunks = [
            {
                "content": item.get("content", ""),
                "source": item.get("file_path") or item.get("source") or "",
            }
            for item in (data.get("chunks") or [])
            if item.get("content")
        ]
        references = [
            {
                "file": item.get("file_path") or item.get("reference_id") or "",
                "title": item.get("title", ""),
            }
            for item in (data.get("references") or [])
        ]

        logger.info(f"rag_search returned {len(chunks)} chunks, {len(references)} refs")
        return {"query": query, "chunks": chunks, "references": references}

    async def _post_with_retry(
        self, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """带退避重试的 POST：

        - 5xx / 网络错误 / 超时 → 重试
        - 4xx → 立即失败，不重试
        - 失败时返回 {"error": "..."}；成功时返回响应 JSON dict

        失败时把完整错误信息打到日志（response body 全文 + headers + 请求体），
        方便定位上游问题。
        """
        full_url = f"{self._base_url}{path}"
        last_reason = "unknown"

        for attempt in range(_MAX_ATTEMPTS):
            attempt_tag = f"attempt {attempt + 1}/{_MAX_ATTEMPTS}"
            try:
                resp = await self._client.post(path, json=body)
            except httpx.RequestError as e:
                # 网络错误 / 超时 / 协议错误 都属于 RequestError
                last_reason = type(e).__name__
                # logger.exception 自带 traceback；再补一条结构化信息
                logger.exception(
                    f"rag_search request error ({attempt_tag})\n"
                    f"  exception_type: {type(e).__name__}\n"
                    f"  exception_repr: {e!r}\n"
                    f"  url: POST {full_url}\n"
                    f"  request_body: {body}"
                )
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                return {"error": "知识库响应超时或网络异常，请稍后重试"}

            if resp.status_code >= 500:
                last_reason = f"HTTP {resp.status_code}"
                logger.warning(
                    f"rag_search 5xx ({attempt_tag}) — full dump:\n"
                    f"  url: POST {full_url}\n"
                    f"  request_body: {body}\n"
                    f"  status: {resp.status_code} {resp.reason_phrase}\n"
                    f"  elapsed: {resp.elapsed.total_seconds():.3f}s\n"
                    f"  response_headers: {dict(resp.headers)}\n"
                    f"  response_body (len={len(resp.text)}): {resp.text!r}"
                )
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                return {"error": f"知识库服务暂时不可用（{last_reason}）"}

            if resp.status_code >= 400:
                # 4xx 是请求本身的问题，重试也没用
                logger.warning(
                    f"rag_search 4xx — full dump:\n"
                    f"  url: POST {full_url}\n"
                    f"  request_body: {body}\n"
                    f"  status: {resp.status_code} {resp.reason_phrase}\n"
                    f"  elapsed: {resp.elapsed.total_seconds():.3f}s\n"
                    f"  response_headers: {dict(resp.headers)}\n"
                    f"  response_body (len={len(resp.text)}): {resp.text!r}"
                )
                return {"error": f"知识库查询参数错误（HTTP {resp.status_code}）"}

            try:
                return resp.json()
            except ValueError:
                logger.exception(
                    f"rag_search response not json — full dump:\n"
                    f"  url: POST {full_url}\n"
                    f"  request_body: {body}\n"
                    f"  status: {resp.status_code}\n"
                    f"  response_headers: {dict(resp.headers)}\n"
                    f"  response_body (len={len(resp.text)}): {resp.text!r}"
                )
                return {"error": "知识库响应格式异常"}

        # 理论上走不到这里
        return {"error": f"知识库查询失败（{last_reason}）"}

    async def aclose(self) -> None:
        await self._client.aclose()