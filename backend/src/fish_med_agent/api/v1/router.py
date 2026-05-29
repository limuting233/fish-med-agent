from fastapi import APIRouter

from fish_med_agent.api.v1.endpoints import chat, healthz, conversation, auth, upload

api_v1_router = APIRouter()

api_v1_router.include_router(healthz.router, tags=["healthz"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])

api_v1_router.include_router(conversation.router, prefix="/conversation", tags=["conversation"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(upload.router, prefix="/upload", tags=["upload"])
