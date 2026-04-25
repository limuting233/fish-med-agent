from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fish_med_agent.api.v1.router import api_v1_router
from fish_med_agent.core.config import settings
from fish_med_agent.core.handlers import register_exception_handlers
from fish_med_agent.core.logging import configure_logging
from fish_med_agent.core.middleware import RequestIdMiddleware


def create_app():
    """
    创建FastAPI应用
    Returns:
        FastAPI应用对象

    """
    configure_logging()  # 配置日志

    app = FastAPI(
        title="Fish Med Agent Service",
        version=settings.SERVICE_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_prefix)

    return app


app = create_app()  # 创建FastAPI应用
