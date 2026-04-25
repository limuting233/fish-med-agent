from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from fish_med_agent.api.deps import get_db, get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.chat import ChatRequest
from fish_med_agent.service.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/stream")
async def chat_stream(
        chat_request: ChatRequest,
        http_request: Request,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
) -> StreamingResponse:
    """
    聊天流接口
    Args:
        chat_request: 聊天请求
        http_request: HTTP请求对象
        db: 异步数据库会话, 默认从依赖注入获取获取
        current_user_id: 当前用户ID, 默认从依赖注入获取当前用户ID
    Returns:
        SSE流式响应

    """

    logger.info(f"Received chat request: {chat_request}")

    chat_service = ChatService(db)
    res = chat_service.generate_stream_response(chat_request=chat_request, current_user_id=current_user_id)
    return StreamingResponse(res, media_type="text/event-stream")
