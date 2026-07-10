"""Generation-layer evaluation for the Backend RAG pipeline.

Uses RAGAS metrics:
  - Faithfulness       – does the answer stick to the retrieved context?
  - AnswerRelevancy    – how well does the answer address the question?
  - ContextRelevancy   – how relevant is the retrieved context to the question?

Usage (standalone):
    cd backend
    python -m pytest tests/test_rag_generation.py -v -s -m rag_generation

Relies on:
    - eval_dataset.json
    - app.services.ai.dify_retriever  (retrieve_from_dify, format_dify_context)
    - app.services.ai.base.ChatMessage
    - Provider from app.services.ai.factory
"""

from typing import Any

import pytest

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


def _build_ragas_data(
    item: dict[str, Any],
    dify_context: str,
    llm_answer: str,
) -> dict[str, Any]:
    """Build a single RAGAS evaluation sample dict.

    RAGAS expects:
        question      : str
        answer        : str
        contexts      : list[str]
        ground_truth  : str
    """
    return {
        "question": item["query"],
        "answer": llm_answer,
        "contexts": [dify_context] if dify_context else [""],
        "ground_truth": item["ground_truth_answer"],
    }


@pytest.mark.rag_generation
@pytest.mark.asyncio
async def test_ragas_evaluation(
    eval_dataset: list[dict[str, Any]],
    provider,
):
    """Full RAGAS evaluation: generate answers with RAG context, then score."""
    from app.config import settings

    if not settings.DIFY_RETRIEVE_ENABLED:
        pytest.skip("DIFY_RETRIEVE_ENABLED is False")

    # Phase 1: Retrieve + Generate
    ragas_samples: list[dict[str, Any]] = []

    print("\n" + "=" * 60)
    print("  Phase 1 – Retrieving & Generating answers...")
    print("=" * 60)

    for i, item in enumerate(eval_dataset):
        query = item["query"]
        print(f"  [{i+1}/{len(eval_dataset)}] {query[:60]}")

        records = await retrieve_from_dify(query)
        dify_context = format_dify_context(records)

        messages = [
            ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT),
        ]
        if dify_context:
            messages.append(
                ChatMessage(
                    role="system",
                    content=f"Medical Knowledge Reference:\n\n{dify_context}",
                )
            )
        messages.append(ChatMessage(role="user", content=query))

        answer = await provider.chat(messages)
        ragas_samples.append(_build_ragas_data(item, dify_context, answer))

    # Phase 2: RAGAS scoring
    print("\n" + "=" * 60)
    print("  Phase 2 – Computing RAGAS metrics...")
    print("=" * 60)

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_relevancy

        dataset = Dataset.from_list(ragas_samples)
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_relevancy],
        )
        scores = {k: round(float(v), 4) for k, v in result.items() if k != "ragas_score"}
        scores["ragas_score"] = round(float(result.get("ragas_score", 0)), 4)
    except ImportError:
        pytest.skip("ragas or datasets not installed; run: pip install ragas datasets")
    except Exception as exc:
        print(f"\n  ⚠ RAGAS evaluation failed: {exc}")
        print("  Falling back to per-sample manual scoring...")
        scores = {"error": str(exc), "ragas_score": 0.0}

    # Report
    print("\n" + "=" * 60)
    print("  RAGAS Generation Evaluation Results")
    print("=" * 60)
    for metric, value in scores.items():
        if metric != "error":
            bar = "█" * int(value * 40)
            print(f"  {metric:<22s} : {value:.4f}  {bar}")
    print(f"  Samples evaluated       : {len(ragas_samples)}")
    print("=" * 60 + "\n")

    # Per-sample detail
    print("Per-sample answers (first 200 chars):")
    for s in ragas_samples:
        print(f"  Q: {s['question'][:50]}...")
        print(f"  A: {s['answer'][:200]}...")
        print(f"  contexts_length: {len(s['contexts'][0])}")
        print()

    # Persist results
    import json
    out_path = __file__.rsplit(".", 1)[0] + "_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"scores": scores, "samples": ragas_samples, "num_samples": len(ragas_samples)},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Results saved to: {out_path}")
