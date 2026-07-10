"""A/B comparison experiments for the Backend RAG pipeline.

Two comparisons:
  1. With RAG context vs Without RAG context (same provider)
  2. DeepSeek (primary) vs Ollama (local) – both with RAG context

Usage (standalone):
    cd backend
    python -m pytest tests/test_rag_compare.py -v -s -m rag_compare
"""

import json
import time
from typing import Any

import pytest

from app.config import settings
from app.services.ai.dify_retriever import retrieve_from_dify, format_dify_context
from app.services.ai.base import ChatMessage

DEFAULT_SYSTEM_PROMPT = (
    "You are SyncHealth AI, a knowledgeable and friendly health assistant. "
    "You analyze the user's Apple Watch health data to provide insights, "
    "answer health-related questions, and suggest improvements. "
    "When medical knowledge references are provided, use them to give more "
    "accurate and professional answers, but always clearly distinguish between "
    "general medical knowledge and personalized health advice. "
    "Always be supportive and remind users to consult healthcare professionals "
    "for medical advice. Respond in the same language the user uses."
)


# ─── Shared helpers ────────────────────────────────────────────────────────

async def _generate_answer(
    provider,
    query: str,
    dify_context: str,
) -> str:
    """Build messages with optional RAG context and call LLM."""
    messages = [ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)]
    if dify_context:
        messages.append(
            ChatMessage(
                role="system",
                content=f"Medical Knowledge Reference:\n\n{dify_context}",
            )
        )
    messages.append(ChatMessage(role="user", content=query))
    return await provider.chat(messages)


# ─── Test: RAG vs No RAG ───────────────────────────────────────────────────

@pytest.mark.rag_compare
@pytest.mark.asyncio
async def test_rag_vs_no_rag(eval_dataset: list[dict[str, Any]], provider):
    """Compare answer quality with and without RAG context."""
    if not settings.DIFY_RETRIEVE_ENABLED:
        pytest.skip("DIFY_RETRIEVE_ENABLED is False")

    results: list[dict[str, Any]] = []
    rag_longer_count = 0
    no_rag_count = 0

    print("\n" + "=" * 60)
    print("  Comparison: With RAG vs Without RAG")
    print("=" * 60)

    for i, item in enumerate(eval_dataset):
        query = item["query"]
        print(f"  [{i+1}/{len(eval_dataset)}] {query[:60]}")

        records = await retrieve_from_dify(query)
        dify_context = format_dify_context(records)

        # With RAG
        t0 = time.time()
        rag_answer = await _generate_answer(provider, query, dify_context)
        rag_time = time.time() - t0

        # Without RAG
        t0 = time.time()
        no_rag_answer = await _generate_answer(provider, query, "")
        no_rag_time = time.time() - t0

        rag_len = len(rag_answer)
        no_rag_len = len(no_rag_answer)
        if rag_len > no_rag_len:
            rag_longer_count += 1
        elif no_rag_len > rag_len:
            no_rag_count += 1

        results.append({
            "query": query,
            "rag_answer": rag_answer,
            "rag_time": round(rag_time, 2),
            "rag_length": rag_len,
            "rag_context_length": len(dify_context),
            "no_rag_answer": no_rag_answer,
            "no_rag_time": round(no_rag_time, 2),
            "no_rag_length": no_rag_len,
        })

    # Summary
    total = len(results)
    avg_rag_len = sum(r["rag_length"] for r in results) / total
    avg_no_rag_len = sum(r["no_rag_length"] for r in results) / total
    avg_rag_time = sum(r["rag_time"] for r in results) / total
    avg_no_rag_time = sum(r["no_rag_time"] for r in results) / total

    print("\n  Summary:")
    print(f"  {'':<22s} │ {'With RAG':>12s} │ {'Without RAG':>12s}")
    print(f"  {'─'*22}─┼─{'─'*12}─┼─{'─'*12}")
    print(f"  {'Avg answer length':<22s} │ {avg_rag_len:>12.0f} │ {avg_no_rag_len:>12.0f}")
    print(f"  {'Avg generation time':<22s} │ {avg_rag_time:>11.2f}s │ {avg_no_rag_time:>11.2f}s")
    print(f"  {'Longer answers':<22s} │ {rag_longer_count:>12d} │ {no_rag_count:>12d}")
    print(f"  {'Total queries':<22s} │ {' ':>12s} │ {total:>12d}")
    print()

    # Persist
    out_path = __file__.rsplit(".", 1)[0] + "_results.json"
    summary = {
        "total_queries": total,
        "avg_rag_length": round(avg_rag_len, 1),
        "avg_no_rag_length": round(avg_no_rag_len, 1),
        "avg_rag_time": round(avg_rag_time, 2),
        "avg_no_rag_time": round(avg_no_rag_time, 2),
        "rag_longer_count": rag_longer_count,
        "no_rag_longer_count": no_rag_count,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": results}, f, ensure_ascii=False, indent=2)
    print(f"Results saved to: {out_path}")


# ─── Test: DeepSeek vs Ollama ──────────────────────────────────────────────

@pytest.mark.rag_compare
@pytest.mark.asyncio
async def test_deepseek_vs_ollama(eval_dataset: list[dict[str, Any]], provider, ollama_provider):
    """Compare answers from DeepSeek (primary) and Ollama (local), both with RAG."""
    if not settings.DIFY_RETRIEVE_ENABLED:
        pytest.skip("DIFY_RETRIEVE_ENABLED is False")
    if ollama_provider is None:
        pytest.skip("Ollama provider not available (check OLLAMA_BASE_URL/OLLAMA_MODEL)")

    results: list[dict[str, Any]] = []

    print("\n" + "=" * 60)
    print("  Comparison: DeepSeek vs Ollama (both with RAG context)")
    print("=" * 60)

    for i, item in enumerate(eval_dataset):
        query = item["query"]
        print(f"  [{i+1}/{len(eval_dataset)}] {query[:60]}")

        records = await retrieve_from_dify(query)
        dify_context = format_dify_context(records)

        # DeepSeek
        t0 = time.time()
        ds_answer = await _generate_answer(provider, query, dify_context)
        ds_time = time.time() - t0

        # Ollama
        t0 = time.time()
        try:
            ollama_answer = await _generate_answer(ollama_provider, query, dify_context)
            ollama_time = time.time() - t0
            ollama_ok = True
        except Exception as exc:
            ollama_answer = f"[Ollama error: {exc}]"
            ollama_time = 0
            ollama_ok = False

        results.append({
            "query": query,
            "deepseek_answer": ds_answer,
            "deepseek_time": round(ds_time, 2),
            "deepseek_length": len(ds_answer),
            "ollama_answer": ollama_answer,
            "ollama_time": round(ollama_time, 2),
            "ollama_length": len(ollama_answer),
            "ollama_ok": ollama_ok,
            "context_length": len(dify_context),
        })

    # Summary
    total = len(results)
    ok_count = sum(1 for r in results if r["ollama_ok"])
    avg_ds_len = sum(r["deepseek_length"] for r in results) / total
    avg_ds_time = sum(r["deepseek_time"] for r in results) / total
    if ok_count > 0:
        avg_ollama_len = sum(r["ollama_length"] for r in results if r["ollama_ok"]) / ok_count
        avg_ollama_time = sum(r["ollama_time"] for r in results if r["ollama_ok"]) / ok_count
    else:
        avg_ollama_len = 0
        avg_ollama_time = 0

    print("\n  Summary:")
    print(f"  {'':<22s} │ {'DeepSeek':>12s} │ {'Ollama':>12s}")
    print(f"  {'─'*22}─┼─{'─'*12}─┼─{'─'*12}")
    print(f"  {'Avg answer length':<22s} │ {avg_ds_len:>12.0f} │ {avg_ollama_len:>12.0f}")
    print(f"  {'Avg generation time':<22s} │ {avg_ds_time:>11.2f}s │ {avg_ollama_time:>11.2f}s")
    print(f"  {'Ollama successes':<22s} │ {' ':>12s} │ {ok_count:>12d}/{total}")
    print()

    out_path = __file__.rsplit(".", 1)[0] + "_results.json"
    summary = {
        "total_queries": total,
        "ollama_success_count": ok_count,
        "avg_deepseek_length": round(avg_ds_len, 1),
        "avg_ollama_length": round(avg_ollama_len, 1),
        "avg_deepseek_time": round(avg_ds_time, 2),
        "avg_ollama_time": round(avg_ollama_time, 2),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": results}, f, ensure_ascii=False, indent=2)
    print(f"Results saved to: {out_path}")
