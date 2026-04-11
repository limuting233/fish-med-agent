from fastapi import FastAPI

from fish_med_agent.api.v1.router import api_v1_router
from fish_med_agent.core.config import settings
from fish_med_agent.core.middleware import RequestIdMiddleware


def create_app():
    """
    创建FastAPI应用
    Returns:
        FastAPI应用对象

    """
    app = FastAPI(
        title="Fish Med Agent Service",
        version=settings.SERVICE_VERSION,
    )

    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_v1_router, prefix=settings.api_prefix)

    return app


app = create_app()  # 创建FastAPI应用
