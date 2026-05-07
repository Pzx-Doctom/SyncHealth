"""Test script for Dify RAG retrieval.

Usage:
    cd backend
    python test_dify_rag.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `app` package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.ai.dify_retriever import retrieve_from_dify, format_dify_context
from app.config import settings


def print_separator(title: str = ""):
    width = 70
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print(f"{'=' * width}")


async def test_single_query(query: str):
    print_separator(f"Query: {query}")

    records = await retrieve_from_dify(query)

    if not records:
        print("\n  ⚠ No results returned.")
        if not settings.DIFY_RETRIEVE_ENABLED:
            print("  Reason: DIFY_RETRIEVE_ENABLED is False")
        return

    print(f"\n  Returned {len(records)} result(s):\n")

    for i, record in enumerate(records, 1):
        segment = record.get("segment", {})
        score = record.get("score")
        doc_name = segment.get("document", {}).get("name", "Unknown")
        content = segment.get("content", "")
        keywords = segment.get("keywords", [])

        print(f"  --- Result {i} ---")
        print(f"  Document : {doc_name}")
        print(f"  Score    : {score}")
        print(f"  Keywords : {keywords}")
        print(f"  Content  : {content[:300]}{'...' if len(content) > 300 else ''}")
        print()

    # Show formatted context (what will be injected into LLM)
    context = format_dify_context(records)
    if context:
        print_separator("Formatted Context (injected into LLM)")
        print(context)
        print()


async def main():
    print_separator("Dify RAG Test")
    print(f"  DIFY_RETRIEVE_ENABLED : {settings.DIFY_RETRIEVE_ENABLED}")
    print(f"  DIFY_API_BASE         : {settings.DIFY_API_BASE}")
    print(f"  DIFY_DATASET_ID       : {settings.DIFY_DATASET_ID}")
    print(f"  DIFY_SEARCH_METHOD    : {settings.DIFY_SEARCH_METHOD}")
    print(f"  DIFY_RETRIEVE_TOP_K   : {settings.DIFY_RETRIEVE_TOP_K}")
    print(f"  DIFY_SCORE_THRESHOLD  : {settings.DIFY_SCORE_THRESHOLD} (enabled={settings.DIFY_SCORE_THRESHOLD_ENABLED})")

    if not settings.DIFY_RETRIEVE_ENABLED:
        print("\n  ⚠ DIFY_RETRIEVE_ENABLED is False. Set it to true in .env first.")
        return

    queries = [
        "高血压的日常护理注意事项",
        "糖尿病患者饮食建议",
        "心率过快怎么办",
        "Apple Watch 心电图怎么看",
    ]

    for q in queries:
        await test_single_query(q)

    print_separator("Test Complete")


if __name__ == "__main__":
    asyncio.run(main())
