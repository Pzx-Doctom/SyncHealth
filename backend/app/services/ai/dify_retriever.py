"""Dify Knowledge Base Retriever

Retrieves medical knowledge segments from a Dify knowledge base using
the dedicated retrieve API:

    POST /datasets/{dataset_id}/retrieve

Request body:
    {
        "query": "<user message, max 250 chars>",
        "retrieval_model": {
            "search_method": "semantic_search",
            "reranking_enable": false,
            "top_k": 5,
            "score_threshold_enabled": true,
            "score_threshold": 0.5
        }
    }

Response body:
    {
        "query": {"content": "..."},
        "records": [
            {
                "segment": {
                    "id": "...", "content": "...", "keywords": [...],
                    "document": {"id": "...", "name": "..."}, ...
                },
                "score": 0.92,
                "child_chunks": [],
                "summary": null
            }
        ]
    }

Authentication: Bearer token in Authorization header.
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Maximum query length allowed by Dify API
DIFY_QUERY_MAX_LENGTH = 250


def _build_retrieval_model() -> dict[str, Any]:
    """Build the retrieval_model payload from settings.

    If DIFY_SEARCH_METHOD is empty, omit retrieval_model entirely
    so the dataset's own default config is used.
    """
    search_method = settings.DIFY_SEARCH_METHOD
    if not search_method:
        return {}

    model: dict[str, Any] = {
        "search_method": search_method,
        "reranking_enable": False,
        "top_k": settings.DIFY_RETRIEVE_TOP_K,
        "score_threshold_enabled": settings.DIFY_SCORE_THRESHOLD_ENABLED,
    }
    if settings.DIFY_SCORE_THRESHOLD_ENABLED:
        model["score_threshold"] = settings.DIFY_SCORE_THRESHOLD

    return model


async def retrieve_from_dify(query: str) -> list[dict[str, Any]]:
    """Retrieve knowledge segments from Dify using POST /retrieve API.

    Returns a list of record dicts, each containing:
      - segment: { id, content, keywords, document: { name, ... }, ... }
      - score: float (relevance score)
      - child_chunks: list
      - summary: str | null

    If Dify is disabled or any error occurs, returns an empty list (graceful degradation).
    """
    if not settings.DIFY_RETRIEVE_ENABLED:
        return []

    if not settings.DIFY_API_KEY or not settings.DIFY_DATASET_ID:
        logger.warning("Dify retrieve enabled but API_KEY or DATASET_ID is missing")
        return []

    # Truncate query to Dify's max length
    truncated_query = query[:DIFY_QUERY_MAX_LENGTH]

    # Build request body
    body: dict[str, Any] = {"query": truncated_query}
    retrieval_model = _build_retrieval_model()
    if retrieval_model:
        body["retrieval_model"] = retrieval_model

    url = f"{settings.DIFY_API_BASE.rstrip('/')}/datasets/{settings.DIFY_DATASET_ID}/retrieve"
    headers = {
        "Authorization": f"Bearer {settings.DIFY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Dify retrieve API returned %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except Exception as exc:
        logger.warning("Dify retrieve request failed: %s", exc)
        return []

    records = data.get("records", [])
    if not records:
        logger.info("Dify retrieve returned no results for query: %s", truncated_query[:50])

    return records


def parse_dify_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract structured reference info from Dify records for frontend display.

    Returns a list of dicts with: document_name, score, keywords, content.
    """
    refs: list[dict[str, Any]] = []
    for record in records:
        segment = record.get("segment", {})
        content = segment.get("content", "").strip()
        if not content:
            continue
        document = segment.get("document", {})
        refs.append({
            "document_name": document.get("name", "Unknown"),
            "score": record.get("score"),
            "keywords": segment.get("keywords", []),
            "content": content,
        })
    return refs


def format_dify_context(records: list[dict[str, Any]]) -> str:
    """Format retrieved records into a Markdown string for LLM injection.

    Produces:
        ## Medical Knowledge Reference
        ### [Doc Name] (score: 0.92)
        > Keywords: kw1, kw2
        segment content ...

        ### [Doc Name] (score: 0.85)
        ...
    """
    if not records:
        return ""

    parts = ["## Medical Knowledge Reference\n"]

    for record in records:
        segment = record.get("segment", {})
        content = segment.get("content", "").strip()
        if not content:
            continue

        # Document name
        document = segment.get("document", {})
        doc_name = document.get("name", "Unknown")

        # Relevance score
        score = record.get("score")
        score_str = f" (relevance: {score:.2f})" if score is not None else ""

        # Keywords
        keywords = segment.get("keywords", [])

        parts.append(f"### [{doc_name}]{score_str}")
        if keywords:
            parts.append(f"> Keywords: {', '.join(keywords)}")
        parts.append(content)
        parts.append("")  # blank line

    result = "\n".join(parts)
    return result if len(result) > 30 else ""
