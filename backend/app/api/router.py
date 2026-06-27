from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.ai import router as ai_router
from app.api.apple_health import router as apple_health_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.mcp import router as mcp_router
from app.api.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(sync_router)
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_router)
api_router.include_router(agents_router)
api_router.include_router(apple_health_router)
api_router.include_router(mcp_router)
