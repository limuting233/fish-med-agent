from typing import Any, ClassVar

from tavily import AsyncTavilyClient

from fish_med_agent.agents.tools.base import Tool
from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_MAX_RESULTS = 5
_DEFAULT_SEARCH_DEPTH = "advanced"


class WebSearchTool(Tool):
    """基于 Tavily 的联网搜索工具。

    暴露给 LLM 的参数只有 query。max_results / search_depth 是 agent 级配置，
    避免 LLM 自由调节导致返回过长或费用失控。
    """

    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = (
        "联网搜索，用于获取知识库中未覆盖的信息，例如最新的药品法规、"
        "新出现的鱼病信息、特定品牌饲料/药品的资料等。"
        "调用前请尽量使用中文、包含具体的鱼种和症状关键词，以提升召回质量。"
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询语句，建议使用中文并包含鱼种、症状等关键词",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        search_depth: str = _DEFAULT_SEARCH_DEPTH,
    ) -> None:
        self._client = AsyncTavilyClient(api_key=settings.TAILY_API_KEY)
        self._max_results = max_results
        self._search_depth = search_depth

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"error": "query 不能为空"}

        query = query.strip()
        logger.info(f"web_search query={query!r} max_results={self._max_results}")

        try:
            response = await self._client.search(
                query=query,
                search_depth=self._search_depth,
                max_results=self._max_results,
            )
        except Exception:
            logger.exception("web_search failed")
            return {"error": "联网搜索失败，请稍后重试或换一种问法"}

        raw_results = response.get("results", []) if isinstance(response, dict) else []
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            }
            for item in raw_results
        ]
        logger.info(f"web_search returned {len(results)} results")
        return {"query": query, "results": results}
