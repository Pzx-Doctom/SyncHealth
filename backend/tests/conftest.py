"""Shared pytest fixtures for RAG evaluation tests."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure backend/ is on sys.path so the `app` package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.ai.base import BaseLLMProvider
from app.services.ai.factory import get_ollama_provider, get_provider, reset_provider


@pytest.fixture(scope="session")
def eval_dataset() -> list[dict[str, Any]]:
    """Load the RAG evaluation dataset from eval_dataset.json."""
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) > 0, "eval_dataset.json is empty"
    return data


@pytest.fixture(scope="session")
def provider() -> BaseLLMProvider:
    """Get the primary LLM provider (e.g., DeepSeek)."""
    # Reset in case previous tests messed with the singleton
    reset_provider()
    return get_provider()


@pytest.fixture(scope="session")
def ollama_provider() -> BaseLLMProvider | None:
    """Get the Ollama provider. Returns None if Ollama is not configured."""
    if not settings.OLLAMA_BASE_URL or not settings.OLLAMA_MODEL:
        return None
    try:
        return get_ollama_provider()
    except Exception:
        return None


def pytest_configure(config):
    """Add custom markers for RAG evaluation tests."""
    config.addinivalue_line("markers", "rag_retrieval: tests for Dify retrieval quality")
    config.addinivalue_line("markers", "rag_generation: tests for RAG generation quality (RAGAS)")
    config.addinivalue_line("markers", "rag_compare: A/B comparison tests")
