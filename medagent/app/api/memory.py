"""长期记忆管理 API - 画像读写、事件时间线、语义搜索"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.memory import (
    UserProfileData,
    UserProfileUpdate,
    HealthEventCreate,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    TimelineResponse,
    TimelineItem,
)
from app.memory.manager import memory_manager

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.get("/profile", response_model=UserProfileData)
async def get_user_profile():
    """获取用户健康画像"""
    profile = await memory_manager.get_profile(DEFAULT_USER_ID)
    if not profile:
        return UserProfileData()
    return UserProfileData(**profile)


@router.put("/profile", response_model=UserProfileData)
async def update_user_profile(update: UserProfileUpdate):
    """更新用户健康画像"""
    updated = await memory_manager.update_profile(
        DEFAULT_USER_ID,
        update.profile_data.model_dump(exclude_none=True),
    )
    return UserProfileData(**updated)


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    limit: int = Query(20, ge=1, le=100),
):
    """获取用户健康事件时间线"""
    events = await memory_manager.get_timeline(DEFAULT_USER_ID, limit=limit)
    return TimelineResponse(
        items=[
            TimelineItem(
                id=e.get("id", ""),
                summary=e.get("summary", ""),
                event_type=e.get("event_type", "event"),
                timestamp=e.get("timestamp", ""),
                details=e.get("details", {}),
            )
            for e in events
        ],
        total=len(events),
    )


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """语义搜索用户的长期记忆"""
    results = await memory_manager.recall(
        DEFAULT_USER_ID,
        request.query,
        top_k=request.top_k,
    )
    return MemorySearchResponse(
        results=[
            MemorySearchResult(
                summary=r.get("summary", ""),
                event_type=r.get("event_type", "event"),
                timestamp=r.get("timestamp", ""),
                similarity=r.get("similarity", 0),
                details=r.get("details", {}),
            )
            for r in results
        ],
        total=len(results),
    )


@router.post("/events")
async def add_health_event(event: HealthEventCreate):
    """手动添加健康事件到长期记忆"""
    event_id = await memory_manager.remember(
        user_id=DEFAULT_USER_ID,
        summary=event.summary,
        event_type=event.event_type,
        details=event.details,
        source_agent=event.source_agent,
    )
    if event_id:
        return {"message": "事件已添加", "event_id": event_id}
    raise HTTPException(status_code=500, detail="事件添加失败（向量存储可能不可用）")
