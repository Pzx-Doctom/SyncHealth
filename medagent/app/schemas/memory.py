"""记忆系统 schemas"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserProfileData(BaseModel):
    """用户健康画像"""
    age: Optional[int] = None
    gender: Optional[str] = None
    bmi: Optional[float] = None
    chronic_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    health_goals: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    home_address: Optional[str] = None
    city: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """用户画像更新"""
    profile_data: UserProfileData


class HealthEvent(BaseModel):
    """健康事件（存储在 ChromaDB 向量库）"""
    id: Optional[str] = None
    summary: str
    event_type: Literal["health_event", "conversation", "preference", "diagnosis", "medication_change"]
    timestamp: str
    details: dict = Field(default_factory=dict)
    source_agent: Optional[str] = None


class HealthEventCreate(BaseModel):
    """创建健康事件"""
    summary: str
    event_type: str = "health_event"
    details: dict = Field(default_factory=dict)
    source_agent: Optional[str] = None


class MemorySearchRequest(BaseModel):
    """记忆语义搜索请求"""
    query: str
    top_k: int = 5


class MemorySearchResult(BaseModel):
    """记忆搜索结果"""
    summary: str
    event_type: str
    timestamp: str
    similarity: float
    details: dict = Field(default_factory=dict)


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]
    total: int


class TimelineItem(BaseModel):
    """时间线条目"""
    id: str
    summary: str
    event_type: str
    timestamp: str
    details: dict = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    items: list[TimelineItem]
    total: int
