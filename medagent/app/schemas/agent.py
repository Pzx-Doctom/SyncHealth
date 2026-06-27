"""Agent 配置 schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentConfigBase(BaseModel):
    agent_name: str = Field(..., description="triage | health_coach | report_interpreter | medication")
    display_name: str = ""
    description: str = ""
    system_prompt: str = ""
    enabled_tools: list[str] = Field(default_factory=list)
    is_active: bool = True


class AgentConfigCreate(AgentConfigBase):
    user_id: Optional[str] = None  # None=全局默认配置


class AgentConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    enabled_tools: Optional[list[str]] = None
    is_active: Optional[bool] = None


class AgentConfigOut(AgentConfigBase):
    id: int
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    agents: list[AgentConfigOut]
