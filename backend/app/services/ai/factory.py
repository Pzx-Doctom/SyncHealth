from app.config import settings
from app.services.ai.base import BaseLLMProvider

_provider_instance: BaseLLMProvider | None = None


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


def reset_provider():
    global _provider_instance
    _provider_instance = None
