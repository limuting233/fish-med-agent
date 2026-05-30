"""Agent 工具注册表。

工具在模块加载时创建为单例，整个 app 生命周期共享。这样可以复用底层 httpx
client 的连接池，避免每个请求都建立新连接。
"""
import json
from typing import Any

from fish_med_agent.agents.tools import RAGSearchTool, Tool, WebSearchTool
from fish_med_agent.core.logging import get_logger

logger = get_logger(__name__)

# 模块级单例：进程内复用
TOOLS: list[Tool] = [
    RAGSearchTool(),
    WebSearchTool(),
]

TOOLS_BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


def openai_tools_schema() -> list[dict[str, Any]]:
    """生成传给 OpenAI/DeepSeek 的 tools 参数。"""
    return [t.to_openai_schema() for t in TOOLS]


async def dispatch_tool_call(
    name: str,
    raw_arguments: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """根据 LLM 返回的 tool_call 调用对应工具。

    Args:
        name: 工具名（来自 tool_call.function.name）
        raw_arguments: LLM 提供的参数 JSON 字符串
        context: agent 注入的上下文参数（如 conversation_history），不暴露给 LLM
                 但会合并进 execute 的 kwargs。context 优先级高于 LLM 参数。

    工具内部已经把异常压成 {"error": ...}，这里只处理调度层的错误
    （未知工具名、参数 JSON 解析失败）。
    """
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        logger.warning(f"unknown tool requested: {name}")
        return {"error": f"未知工具：{name}"}

    try:
        arguments = json.loads(raw_arguments) if raw_arguments else {}
    except json.JSONDecodeError:
        logger.warning(f"invalid tool arguments JSON for {name}: {raw_arguments!r}")
        return {"error": "工具参数解析失败，请检查 JSON 格式"}

    # context 优先级高于 LLM 参数，防止 LLM 越权覆盖（如自己塞 conversation_history）
    merged = {**arguments, **(context or {})}
    return await tool.execute(**merged)
