"""聊天与 WebSocket 事件 schemas"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ===== WebSocket 事件类型 =====

WSEventType = Literal[
    "token",              # 流式文本 token
    "agent_switch",       # Agent 路由切换
    "tool_start",         # 工具调用开始
    "tool_result",        # 工具调用结果
    "memory_recall",      # 长期记忆召回
    "thinking",           # 思考链（可折叠）
    "done",               # 完成
    "error",              # 错误
]


class WSEvent(BaseModel):
    """WebSocket 事件统一格式"""
    type: WSEventType
    content: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None


# ===== 具体事件 payloads =====

class AgentSwitchData(BaseModel):
    """agent_switch 事件数据"""
    from_agent: str
    to_agent: str
    reason: str
    severity: str = "normal"


class ToolStartData(BaseModel):
    """tool_start 事件数据"""
    agent: str
    tool: str
    args: dict[str, Any]


class ToolResultData(BaseModel):
    """tool_result 事件数据"""
    agent: str
    tool: str
    result: str
    duration_ms: int
    status: Literal["success", "error", "timeout"]


class MemoryRecallData(BaseModel):
    """memory_recall 事件数据"""
    events: list[dict[str, Any]]
    similarity_score: float


class ErrorData(BaseModel):
    """error 事件数据"""
    message: str
    error_type: str = "generic"
    recoverable: bool = False


class DoneData(BaseModel):
    """done 事件数据"""
    session_id: int
    message_id: int
    agent_route: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    memory_recalls: list[dict[str, Any]] = Field(default_factory=list)


# ===== REST 请求/响应 =====

class ChatRequest(BaseModel):
    """WebSocket 初始请求"""
    message: str
    session_id: Optional[int] = None
    images: list[str] = Field(default_factory=list, description="Base64 编码的图片列表（用于 OCR）")
    enable_memory: bool = True
    enable_tools: bool = True


class ChatHistoryItem(BaseModel):
    """历史消息项"""
    id: int
    role: str
    content: str
    created_at: str
    agent_route: list[dict] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    current_agent: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """历史消息响应"""
    messages: list[ChatHistoryItem]
    total: int
