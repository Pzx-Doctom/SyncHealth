"""Ollama 本地大模型 Provider

使用 Ollama 的 OpenAI 兼容端点 (/v1/chat/completions) 进行对话，
使用原生端点 (/api/tags) 进行模型管理和健康检查。

设计要点：
- 不发送 Authorization 头（Ollama 免认证）
- 同步超时 180s / 流式超时 300s（本地推理远慢于云端）
- 上下文窗口从配置读取（默认 4096），不硬编码 128000
- health_check / list_models 用 10s 短超时，避免阻塞
- 所有 httpx 客户端 trust_env=False，强制不走代理
  （本地连接不应被 HTTP_PROXY/ALL_PROXY 等环境变量拦截，避免 502）
"""
import json
import logging
from typing import AsyncIterator

import httpx

from app.config import settings
from app.services.ai.base import BaseLLMProvider, ChatMessage, GenerationConfig, ModelInfo

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        # 优先使用 OLLAMA_BASE_URL，回退到 AI_BASE_URL
        base = settings.OLLAMA_BASE_URL or settings.AI_BASE_URL
        self.base_url = base.rstrip("/")
        # OpenAI 兼容端点前缀
        self.v1_url = f"{self.base_url}/v1"
        self.model = settings.OLLAMA_MODEL or settings.AI_MODEL
        self.context_window = settings.OLLAMA_CONTEXT_WINDOW
        self.timeout = settings.OLLAMA_TIMEOUT
        self.stream_timeout = settings.OLLAMA_STREAM_TIMEOUT

    def _headers(self) -> dict:
        """Ollama 不需要认证，仅发送 Content-Type"""
        return {"Content-Type": "application/json"}

    def _build_body(
        self,
        messages: list[ChatMessage],
        config: GenerationConfig | None,
        stream: bool = False,
    ) -> dict:
        cfg = config or GenerationConfig(temperature=settings.AI_TEMPERATURE)
        # 如果 config 指定了 model，运行时覆盖
        model = cfg.model or self.model
        return {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "top_p": cfg.top_p,
            "stream": stream,
        }

    async def chat(
        self, messages: list[ChatMessage], config: GenerationConfig | None = None
    ) -> str:
        # trust_env=False：本地连接强制不走代理，避免 HTTP_PROXY 导致 502
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            response = await client.post(
                f"{self.v1_url}/chat/completions",
                headers=self._headers(),
                json=self._build_body(messages, config),
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream_chat(
        self, messages: list[ChatMessage], config: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        # trust_env=False：本地连接强制不走代理
        async with httpx.AsyncClient(timeout=self.stream_timeout, trust_env=False) as client:
            async with client.stream(
                "POST",
                f"{self.v1_url}/chat/completions",
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
        return ModelInfo(
            name=self.model,
            max_context_window=self.context_window,
            provider="ollama",
        )

    # ===== Ollama 专属方法 =====

    async def health_check(self) -> dict:
        """检查 Ollama 服务是否在线，返回状态和模型数"""
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = data.get("models", [])
                return {
                    "status": "online",
                    "models_count": len(models),
                    "models": [m.get("name", "") for m in models],
                }
        except httpx.ConnectError:
            return {"status": "offline", "models_count": 0, "models": []}
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "models_count": 0,
                "models": [],
            }

    async def list_models(self) -> list[dict]:
        """列出所有已拉取的本地模型，含详细信息"""
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    details = m.get("details", {})
                    models.append(
                        {
                            "name": m.get("name", ""),
                            "size": m.get("size", 0),
                            "digest": m.get("digest", "")[:12],
                            "family": details.get("family", ""),
                            "parameter_size": details.get("parameter_size", ""),
                            "quantization": details.get("quantization_level", ""),
                            "modified_at": m.get("modified_at", ""),
                        }
                    )
                return models
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []
