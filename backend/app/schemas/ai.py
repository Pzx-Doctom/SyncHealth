from datetime import datetime

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    message: str
    session_id: int | None = None
    agent_id: int | None = None
    model: str | None = None  # 运行时模型覆盖，None=用默认 provider


class OllamaModelOut(BaseModel):
    """Ollama 本地模型信息"""
    name: str
    size: int = 0
    digest: str = ""
    family: str = ""
    parameter_size: str = ""
    quantization: str = ""
    modified_at: str = ""


class ProviderStatusOut(BaseModel):
    """单个 provider 的健康状态"""
    status: str  # online | offline | error | unknown
    models_count: int = 0
    models: list[str] = []
    error: str | None = None


class AIHealthOut(BaseModel):
    """双 provider 健康状态汇总"""
    primary: ProviderStatusOut
    ollama: ProviderStatusOut
    fallback_enabled: bool = False


class DifyReference(BaseModel):
    """A single RAG knowledge reference."""
    document_name: str
    score: float | None = None
    keywords: list[str] = []
    content: str = ""


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime
    dify_references: list[DifyReference] | None = None

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
