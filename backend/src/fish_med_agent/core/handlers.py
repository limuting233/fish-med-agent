from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from fish_med_agent.core.exception import BizException
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse

logger = get_logger(__name__)


async def biz_exception_handler(request: Request, exc: BizException) -> JSONResponse:
    """
    业务异常处理器。
    """
    request_id = getattr(request.state, "request_id")
    logger.warning(
        "Business exception: {code} {message}",
        code=exc.code,
        message=exc.message,
    )

    response = ApiResponse[None](
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        data=None,
    )

    return JSONResponse(
        status_code=int(exc.status_code),
        content=response.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册异常处理器。
    """
    app.add_exception_handler(BizException, biz_exception_handler)
