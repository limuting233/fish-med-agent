from fastapi import APIRouter

from fish_med_agent.api.v1.endpoints import chat, healthz

api_v1_router = APIRouter()

api_v1_router.include_router(healthz.router, tags=["healthz"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
