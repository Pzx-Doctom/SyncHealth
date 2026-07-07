from app.config import settings
from app.services.ai.base import BaseLLMProvider

_provider_instance: BaseLLMProvider | None = None
_ollama_instance: BaseLLMProvider | None = None


def get_provider() -> BaseLLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_type = settings.AI_PROVIDER

    if provider_type == "openai":
        from app.services.ai.provider_openai import OpenAIProvider
        _provider_instance = OpenAIProvider()
    elif provider_type == "local":
        # Local provider uses the same OpenAI-compatible API (e.g., Ollama)
        from app.services.ai.provider_openai import OpenAIProvider
        _provider_instance = OpenAIProvider()
    elif provider_type == "domestic":
        # Domestic LLMs often provide OpenAI-compatible endpoints
        from app.services.ai.provider_openai import OpenAIProvider
        _provider_instance = OpenAIProvider()
    else:
        from app.services.ai.provider_openai import OpenAIProvider
        _provider_instance = OpenAIProvider()

    return _provider_instance


def get_ollama_provider() -> BaseLLMProvider:
    """返回 Ollama provider 单例（作为备用 provider）。

    独立于 get_provider()，不影响主 provider 的单例缓存。
    """
    global _ollama_instance
    if _ollama_instance is not None:
        return _ollama_instance

    from app.services.ai.provider_ollama import OllamaProvider
    _ollama_instance = OllamaProvider()
    return _ollama_instance


def reset_provider():
    """重置所有 provider 单例"""
    global _provider_instance, _ollama_instance
    _provider_instance = None
    _ollama_instance = None
