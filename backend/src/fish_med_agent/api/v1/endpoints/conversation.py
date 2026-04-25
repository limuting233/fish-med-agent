from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.api.deps import get_db, get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.service.conversation_service import ConversationService

from fastapi import Request

logger = get_logger(__name__)

router = APIRouter()


@router.get("/list", response_model=ApiResponse[list[dict]])
async def list(
        http_request: Request,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),

):
    """
    获取用户的所有对话
    Args:
        db: 数据库会话, 用于执行数据库操作, 从依赖项中获取
        current_user_id: 当前用户ID, 从依赖项中获取

    Returns:
        对话列表
    """
    request_id = getattr(http_request.state, "request_id")  # 从请求状态中获取请求ID
    conversation_service = ConversationService(db)
    conversation_list = await conversation_service.get_list(current_user_id)
    return success_response(request_id=request_id, data=conversation_list)
