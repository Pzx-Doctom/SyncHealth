from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class ChatMessage:
    role: str  # system, user, assistant
    content: str


@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class ModelInfo:
    name: str
    max_context_window: int
    provider: str


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> str:
        """Single-turn completion. Returns full text."""

    @abstractmethod
    async def stream_chat(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> AsyncIterator[str]:
        """Streaming completion. Yields token chunks."""

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Returns model metadata."""
