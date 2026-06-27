"""工具调用 schemas"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCallInfo(BaseModel):
    """工具调用信息（前端展示用）"""
    agent: str
    tool: str
    display_name: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    result: str = ""
    status: Literal["running", "success", "error", "timeout"] = "running"
    duration_ms: int = 0
    started_at: str


class ToolResult(BaseModel):
    """工具返回结果"""
    tool: str
    success: bool
    result: str
    error: str | None = None
    duration_ms: int = 0


class ToolListResponse(BaseModel):
    """工具列表"""
    tools: list[dict[str, Any]]
