"""Retrieval-layer evaluation for the Backend Dify RAG pipeline.

Measures:
  - Precision@k  – fraction of top-k retrieved docs that are relevant
  - Recall@k    – fraction of all relevant docs that were retrieved in top-k
  - MRR         – Mean Reciprocal Rank (1 / rank of first relevant doc)
  - NDCG@k      – Normalized Discounted Cumulative Gain

Usage (standalone):
    cd backend
    python -m pytest tests/test_rag_retrieval.py -v -s -m rag_retrieval

Relies on:
    - eval_dataset.json  (ground-truth expected_doc_names per query)
    - app.services.ai.dify_retriever.retrieve_from_dify
"""

import math
from typing import Any
from collections import defaultdict

import pytest

from app.config import settings
from app.services.ai.dify_retriever import retrieve_from_dify

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_retrieval_metrics(
    queries: list[dict[str, Any]],
    ks: tuple[int, ...] = (3, 5),
) -> dict[str, Any]:
    """Run retrieval eval over all queries and aggregate metrics."""

    # per-query accumulators
    precision_sums: dict[int, float] = defaultdict(float)
    recall_sums: dict[int, float] = defaultdict(float)
    ndcg_sums: dict[int, float] = defaultdict(float)
    rr_scores: list[float] = []          # reciprocal rank per query
    query_details: list[dict] = []

    for item in queries:
        query = item["query"]
        expected = set(item["expected_doc_names"])

        # --- retrieve ---
        records = retrieve_from_dify(query)  # not awaited — will be wrapped
        doc_names = []
        doc_scores = []
        for r in records:
            name = r.get("segment", {}).get("document", {}).get("name", "")
            score = r.get("score", 0) or 0
            doc_names.append(name)
            doc_scores.append(score)

        relevant_at = [1 if name in expected else 0 for name in doc_names]

        # Reciprocal Rank
        rr = 0.0
        for rank, rel in enumerate(relevant_at, start=1):
            if rel == 1:
                rr = 1.0 / rank
                break
        rr_scores.append(rr)

        # Precision / Recall / NDCG @ k
        detail = {"query": query[:60], "expected": list(expected), "retrieved": doc_names, "scores": doc_scores}
        for k in ks:
            top_k_rel = relevant_at[:k]
            retrieved_k = min(k, len(doc_names))
            rel_count = sum(top_k_rel)

            precision = rel_count / retrieved_k if retrieved_k > 0 else 0.0
            recall = rel_count / len(expected) if len(expected) > 0 else 0.0

            # DCG
            dcg = 0.0
            for i, rel_val in enumerate(top_k_rel, start=1):
                dcg += rel_val / math.log2(i + 1) if rel_val else 0.0
            # IDCG – ideal: all expected docs ranked first
            ideal_rels = sorted([1] * min(len(expected), k) + [0] * max(0, k - len(expected)), reverse=True)[:k]
            idcg = 0.0
            for i, rel_val in enumerate(ideal_rels, start=1):
                idcg += rel_val / math.log2(i + 1) if rel_val else 0.0
            ndcg = dcg / idcg if idcg > 0 else 0.0

            precision_sums[k] += precision
            recall_sums[k] += recall
            ndcg_sums[k] += ndcg

            detail[f"precision@{k}"] = round(precision, 4)
            detail[f"recall@{k}"] = round(recall, 4)
            detail[f"ndcg@{k}"] = round(ndcg, 4)
        detail["reciprocal_rank"] = round(rr, 4)
        query_details.append(detail)

    n = len(queries)
    macro = {
        f"precision@{k}": round(precision_sums[k] / n, 4) for k in ks
    }
    macro.update({
        f"recall@{k}": round(recall_sums[k] / n, 4) for k in ks
    })
    macro.update({
        f"ndcg@{k}": round(ndcg_sums[k] / n, 4) for k in ks
    })
    macro["mrr"] = round(sum(rr_scores) / n, 4)

    return {"macro_avg": macro, "query_details": query_details, "num_queries": n}


# ---------------------------------------------------------------------------
# Async test helpers
# ---------------------------------------------------------------------------

@pytest.mark.rag_retrieval
@pytest.mark.asyncio
async def test_dify_retrieval_metrics(eval_dataset: list[dict[str, Any]]):
    """Run full retrieval evaluation and report all metrics."""
    if not settings.DIFY_RETRIEVE_ENABLED:
        pytest.skip("DIFY_RETRIEVE_ENABLED is False")

    metrics = _compute_retrieval_metrics(eval_dataset)

    print("\n" + "=" * 60)
    print("  Dify Retrieval Evaluation – Macro Averages")
    print("=" * 60)
    m = metrics["macro_avg"]
    print(f"  Precision@3 : {m.get('precision@3', 'N/A')}")
    print(f"  Recall@3    : {m.get('recall@3', 'N/A')}")
    print(f"  NDCG@3      : {m.get('ndcg@3', 'N/A')}")
    print(f"  Precision@5 : {m.get('precision@5', 'N/A')}")
    print(f"  Recall@5    : {m.get('recall@5', 'N/A')}")
    print(f"  NDCG@5      : {m.get('ndcg@5', 'N/A')}")
    print(f"  MRR         : {m.get('mrr', 'N/A')}")
    print(f"  Queries     : {metrics['num_queries']}")
    print("=" * 60 + "\n")

    # Per-query breakdown
    print("Per-query details:")
    for d in metrics["query_details"]:
        status = "✓" if d["reciprocal_rank"] > 0 else "✗"
        print(f"  {status} {d['query']}")
        print(f"     expected: {d['expected']}")
        print(f"     retrieved: {d['retrieved']}")
        print(f"     P@5={d['precision@5']} R@5={d['recall@5']} MRR={d['reciprocal_rank']}")

    # Persist to JSON for later consumption (e.g. by eval_report)
    import json
    out_path = __file__.rsplit(".", 1)[0] + "_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {out_path}")
