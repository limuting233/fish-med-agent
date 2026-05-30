from abc import ABC, abstractmethod
from typing import Any, ClassVar


class Tool(ABC):
    """工具抽象基类。

    每个工具实现需要声明 name / description / parameters（JSON Schema），
    并实现异步 execute。Agent 主循环通过 to_openai_schema() 拼装传给 LLM 的 tools 参数。
    """

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """执行工具，返回结构化结果。

        失败应返回 {"error": "..."} 而非抛异常，让 LLM 看到错误自行决定下一步。
        """
        ...

    @classmethod
    def to_openai_schema(cls) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": cls.parameters,
            },
        }
