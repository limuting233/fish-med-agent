from fastapi import APIRouter

from fish_med_agent.api.v1.endpoints import healthz

api_v1_router = APIRouter()

api_v1_router.include_router(healthz.router, tags=["healthz"])
