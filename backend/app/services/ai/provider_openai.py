import json
from typing import AsyncIterator

import httpx

from app.config import settings
from app.services.ai.base import BaseLLMProvider, ChatMessage, GenerationConfig, ModelInfo


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(self, messages: list[ChatMessage], config: GenerationConfig | None, stream: bool = False) -> dict:
        cfg = config or GenerationConfig(temperature=settings.AI_TEMPERATURE)
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "top_p": cfg.top_p,
            "stream": stream,
        }

    async def chat(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._build_body(messages, config),
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream_chat(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._build_body(messages, config, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(name=self.model, max_context_window=128000, provider="openai")
