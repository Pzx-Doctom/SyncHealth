from datetime import datetime

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    message: str
    session_id: int | None = None
    agent_id: int | None = None


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: int
    agent_id: int | None = None
    title: str
    started_at: datetime
    last_message_at: datetime

    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str
    health_data_scope: list[str] | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    health_data_scope: list[str] | None = None
    is_active: bool | None = None


class AgentOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    system_prompt: str
    health_data_scope: list[str] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
