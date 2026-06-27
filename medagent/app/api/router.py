"""API 路由聚合"""
from fastapi import APIRouter

api_router = APIRouter()

from app.api.chat import router as chat_router
from app.api.agents import router as agents_router
from app.api.sessions import router as sessions_router
from app.api.memory import router as memory_router

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(memory_router, prefix="/memory", tags=["memory"])
