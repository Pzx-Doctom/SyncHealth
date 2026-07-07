"""Fallback 辅助函数

DeepSeek（主 provider）调用失败时，自动降级到 Ollama（备用 provider）。

设计原则（原路径零破坏）：
- get_provider() 完全不变，继续返回原始 DeepSeek provider
- DeepSeek 成功时，辅助函数等价于直接调用 + re-raise，无额外开销
- AI_FALLBACK_ENABLED=false 时，辅助函数仅 re-raise，不引入 Ollama
- 仅捕获连接级异常（ConnectError/Timeout/HTTPStatusError），不捕获业务异常

流式 fallback 边界：
- 第一个 token 到达前失败 → 切换到 Ollama 重试
- 第一个 token 到达后失败 → 直接抛出（部分内容已返回前端，无法切换）
"""
import logging
from typing import AsyncIterator

import httpx

from app.config import settings
from app.services.ai.base import ChatMessage, GenerationConfig
from app.services.ai.factory import get_provider, get_ollama_provider

logger = logging.getLogger(__name__)

# 触发 fallback 的异常类型：连接错误、超时、HTTP 状态错误（5xx/401/403 等）
_FALLBACK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.HTTPStatusError,
)


async def chat_with_fallback(
    messages: list[ChatMessage], config: GenerationConfig | None = None
) -> str:
    """同步对话，主 provider 失败时自动降级到 Ollama"""
    provider = get_provider()
    try:
        return await provider.chat(messages, config)
    except _FALLBACK_EXCEPTIONS as e:
        if not settings.AI_FALLBACK_ENABLED:
            raise
        logger.warning(
            f"Primary provider ({type(provider).__name__}) failed: {e}, "
            f"falling back to Ollama"
        )
        ollama = get_ollama_provider()
        return await ollama.chat(messages, config)


async def stream_chat_with_fallback(
    messages: list[ChatMessage], config: GenerationConfig | None = None
) -> AsyncIterator[str]:
    """流式对话，主 provider 首个 token 前失败时自动降级到 Ollama"""
    provider = get_provider()
    first_token_received = False
    try:
        async for chunk in provider.stream_chat(messages, config):
            first_token_received = True
            yield chunk
        return  # 主 provider 成功完成，不 fallback
    except _FALLBACK_EXCEPTIONS as e:
        if first_token_received:
            # 已输出部分内容，无法切换，直接抛出
            raise
        if not settings.AI_FALLBACK_ENABLED:
            raise
        logger.warning(
            f"Primary provider ({type(provider).__name__}) stream failed "
            f"before first token: {e}, falling back to Ollama"
        )
        ollama = get_ollama_provider()
        async for chunk in ollama.stream_chat(messages, config):
            yield chunk
