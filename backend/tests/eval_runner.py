"""One-click CLI runner for RAG evaluation.

Orchestrates all three evaluation phases:
  1. Retrieval quality  (Precision@k, Recall@k, MRR, NDCG)
  2. Generation quality  (RAGAS: Faithfulness, AnswerRelevancy, ContextRelevancy)
  3. A/B comparisons    (RAG vs No RAG, DeepSeek vs Ollama)

Usage:
    cd backend
    python tests/eval_runner.py                          # run all
    python tests/eval_runner.py --skip-generation        # skip generation phase
    python tests/eval_runner.py --skip-compare           # skip comparison phase
    python tests/eval_runner.py --quick                  # only 5 queries for fast check
    python tests/eval_runner.py --no-report              # don't print final report
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure backend/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Phase runners ─────────────────────────────────────────────────────────

async def _run_retrieval(queries: list[dict[str, Any]], k_values: tuple[int, ...] = (3, 5)) -> dict[str, Any]:
    """Run retrieval evaluation (same logic as test_rag_retrieval.py)."""
    import math
    from collections import defaultdict

    from app.config import settings
    from app.services.ai.dify_retriever import retrieve_from_dify

    if not settings.DIFY_RETRIEVE_ENABLED:
        return {"error": "DIFY_RETRIEVE_ENABLED is False", "macro_avg": {}, "query_details": [], "num_queries": 0}

    print(f"\n{'='*60}")
    print(f"  Phase 1: Retrieval Evaluation  ({len(queries)} queries)")
    print(f"{'='*60}")

    precision_sums: dict[int, float] = defaultdict(float)
    recall_sums: dict[int, float] = defaultdict(float)
    ndcg_sums: dict[int, float] = defaultdict(float)
    rr_scores: list[float] = []
    query_details: list[dict] = []

    for i, item in enumerate(queries):
        query = item["query"]
        expected = set(item["expected_doc_names"])

        records = await retrieve_from_dify(query)
        doc_names = []
        for r in records:
            name = r.get("segment", {}).get("document", {}).get("name", "")
            doc_names.append(name)

        relevant_at = [1 if name in expected else 0 for name in doc_names]

        rr = 0.0
        for rank, rel in enumerate(relevant_at, start=1):
            if rel == 1:
                rr = 1.0 / rank
                break
        rr_scores.append(rr)

        detail = {"query": query[:60], "expected": list(expected), "retrieved": doc_names}
        for k in k_values:
            top_k_rel = relevant_at[:k]
            retrieved_k = min(k, len(doc_names))
            rel_count = sum(top_k_rel)
            precision = rel_count / retrieved_k if retrieved_k > 0 else 0.0
            recall = rel_count / len(expected) if len(expected) > 0 else 0.0

            dcg = sum(rel / math.log2(idx + 1) for idx, rel in enumerate(top_k_rel, start=1) if rel)
            ideal_rels = sorted([1] * min(len(expected), k) + [0] * max(0, k - len(expected)), reverse=True)[:k]
            idcg = sum(rel / math.log2(idx + 1) for idx, rel in enumerate(ideal_rels, start=1) if rel)
            ndcg = dcg / idcg if idcg > 0 else 0.0

            precision_sums[k] += precision
            recall_sums[k] += recall
            ndcg_sums[k] += ndcg
            detail[f"precision@{k}"] = round(precision, 4)
            detail[f"recall@{k}"] = round(recall, 4)
            detail[f"ndcg@{k}"] = round(ndcg, 4)
        detail["reciprocal_rank"] = round(rr, 4)
        query_details.append(detail)

        status = "✓" if rr > 0 else "✗"
        print(f"  [{i+1:2d}] {status} {query[:55]}{'...' if len(query)>55 else ''}")

    n = len(queries)
    macro = {f"precision@{k}": round(precision_sums[k] / n, 4) for k in k_values}
    macro.update({f"recall@{k}": round(recall_sums[k] / n, 4) for k in k_values})
    macro.update({f"ndcg@{k}": round(ndcg_sums[k] / n, 4) for k in k_values})
    macro["mrr"] = round(sum(rr_scores) / n, 4)

    print(f"\n  Macro Averages:")
    for k, v in macro.items():
        print(f"    {k:<15s} : {v}")

    return {"macro_avg": macro, "query_details": query_details, "num_queries": n}


async def _run_generation(queries: list[dict[str, Any]], provider) -> dict[str, Any]:
    """Run RAGAS generation evaluation (same logic as test_rag_generation.py)."""
    from app.config import settings
    from app.services.ai.dify_retriever import retrieve_from_dify, format_dify_context
    from app.services.ai.base import ChatMessage

    if not settings.DIFY_RETRIEVE_ENABLED:
        return {"error": "DIFY_RETRIEVE_ENABLED is False", "scores": {}, "num_samples": 0}

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

    print(f"\n{'='*60}")
    print(f"  Phase 2: Generation Evaluation  ({len(queries)} queries)")
    print(f"{'='*60}")

    ragas_samples: list[dict[str, Any]] = []

    for i, item in enumerate(queries):
        query = item["query"]
        print(f"  [{i+1:2d}] Generating: {query[:55]}{'...' if len(query)>55 else ''}")

        records = await retrieve_from_dify(query)
        dify_context = format_dify_context(records)

        messages = [ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)]
        if dify_context:
            messages.append(ChatMessage(role="system", content=f"Medical Knowledge Reference:\n\n{dify_context}"))
        messages.append(ChatMessage(role="user", content=query))

        answer = await provider.chat(messages)
        ragas_samples.append({
            "question": query,
            "answer": answer,
            "contexts": [dify_context] if dify_context else [""],
            "ground_truth": item["ground_truth_answer"],
        })

    # RAGAS scoring
    print(f"\n  Computing RAGAS metrics...")
    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_relevancy

        dataset = Dataset.from_list(ragas_samples)
        result = ragas_evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_relevancy])
        scores = {k: round(float(v), 4) for k, v in result.items() if k != "ragas_score"}
        scores["ragas_score"] = round(float(result.get("ragas_score", 0)), 4)
    except ImportError:
        print("  [!] ragas not installed, skipping RAGAS scoring")
        scores = {"error": "ragas not installed"}
    except Exception as exc:
        print(f"  [!] RAGAS error: {exc}")
        scores = {"error": str(exc)}

    for k, v in scores.items():
        if k != "error":
            print(f"    {k:<25s} : {v}")

    return {"scores": scores, "samples": ragas_samples, "num_samples": len(ragas_samples)}


async def _run_compare(
    queries: list[dict[str, Any]],
    provider,
    ollama_provider,
) -> dict[str, Any]:
    """Run A/B comparisons (same logic as test_rag_compare.py)."""
    from app.config import settings
    from app.services.ai.dify_retriever import retrieve_from_dify, format_dify_context
    from app.services.ai.base import ChatMessage

    if not settings.DIFY_RETRIEVE_ENABLED:
        return {"error": "DIFY_RETRIEVE_ENABLED is False"}

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

    async def _generate(ctx: str, query: str, prov) -> tuple[str, float]:
        messages = [ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)]
        if ctx:
            messages.append(ChatMessage(role="system", content=f"Medical Knowledge Reference:\n\n{ctx}"))
        messages.append(ChatMessage(role="user", content=query))
        t0 = time.time()
        answer = await prov.chat(messages)
        return answer, time.time() - t0

    compare_result: dict[str, Any] = {}

    # ── RAG vs No RAG ──
    print(f"\n{'='*60}")
    print(f"  Phase 3a: RAG vs No RAG  ({len(queries)} queries)")
    print(f"{'='*60}")

    rag_details = []
    for i, item in enumerate(queries):
        query = item["query"]
        records = await retrieve_from_dify(query)
        dify_ctx = format_dify_context(records)

        rag_ans, rag_t = await _generate(dify_ctx, query, provider)
        no_ans, no_t = await _generate("", query, provider)

        rag_details.append({
            "query": query[:60],
            "rag_answer": rag_ans,
            "rag_time": round(rag_t, 2),
            "rag_length": len(rag_ans),
            "no_rag_answer": no_ans,
            "no_rag_time": round(no_t, 2),
            "no_rag_length": len(no_ans),
        })
        delta = len(rag_ans) - len(no_ans)
        sign = "+" if delta > 0 else ""
        print(f"  [{i+1:2d}] {sign}{delta:+d} chars  {query[:45]}{'...' if len(query)>45 else ''}")

    n = len(rag_details)
    compare_result["rag_vs_no_rag"] = {
        "summary": {
            "total_queries": n,
            "avg_rag_length": round(sum(d["rag_length"] for d in rag_details) / n, 1),
            "avg_no_rag_length": round(sum(d["no_rag_length"] for d in rag_details) / n, 1),
            "avg_rag_time": round(sum(d["rag_time"] for d in rag_details) / n, 2),
            "avg_no_rag_time": round(sum(d["no_rag_time"] for d in rag_details) / n, 2),
            "rag_longer_count": sum(1 for d in rag_details if d["rag_length"] > d["no_rag_length"]),
            "no_rag_longer_count": sum(1 for d in rag_details if d["rag_length"] < d["no_rag_length"]),
        },
        "details": rag_details,
    }

    # ── DeepSeek vs Ollama ──
    if ollama_provider is not None:
        print(f"\n{'='*60}")
        print(f"  Phase 3b: DeepSeek vs Ollama  ({len(queries)} queries)")
        print(f"{'='*60}")

        ds_details = []
        ollama_ok = 0
        for i, item in enumerate(queries):
            query = item["query"]
            records = await retrieve_from_dify(query)
            dify_ctx = format_dify_context(records)

            ds_ans, ds_t = await _generate(dify_ctx, query, provider)
            try:
                ol_ans, ol_t = await _generate(dify_ctx, query, ollama_provider)
                ol_ok = True
                ollama_ok += 1
            except Exception as exc:
                ol_ans = f"[Ollama error: {exc}]"
                ol_t = 0
                ol_ok = False

            ds_details.append({
                "query": query[:60],
                "deepseek_answer": ds_ans,
                "deepseek_time": round(ds_t, 2),
                "deepseek_length": len(ds_ans),
                "ollama_answer": ol_ans,
                "ollama_time": round(ol_t, 2),
                "ollama_length": len(ol_ans),
                "ollama_ok": ol_ok,
            })
            print(f"  [{i+1:2d}] DeepSeek:{len(ds_ans):4d}c  Ollama:{len(ol_ans):4d}c  {query[:35]}{'...' if len(query)>35 else ''}")

        compare_result["deepseek_vs_ollama"] = {
            "summary": {
                "total_queries": n,
                "ollama_success_count": ollama_ok,
                "avg_deepseek_length": round(sum(d["deepseek_length"] for d in ds_details) / n, 1),
                "avg_ollama_length": round(sum(d["ollama_length"] for d in ds_details) / n, 1) if ollama_ok else 0,
                "avg_deepseek_time": round(sum(d["deepseek_time"] for d in ds_details) / n, 2),
                "avg_ollama_time": round(sum(d["ollama_time"] for d in ds_details) / n, 2) if ollama_ok else 0,
            },
            "details": ds_details,
        }
    else:
        print("\n  [skip] Ollama provider not available, skipping DeepSeek vs Ollama comparison")

    return compare_result


# ─── Main ──────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument("--skip-retrieval", action="store_true", help="Skip retrieval evaluation")
    parser.add_argument("--skip-generation", action="store_true", help="Skip generation evaluation")
    parser.add_argument("--skip-compare", action="store_true", help="Skip A/B comparison")
    parser.add_argument("--quick", action="store_true", help="Only evaluate first 5 queries")
    parser.add_argument("--no-report", action="store_true", help="Skip final report generation")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for result JSON files")
    args = parser.parse_args()

    # Load dataset
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        full_dataset = json.load(f)

    queries = full_dataset[:5] if args.quick else full_dataset
    print(f"Loaded {len(queries)} evaluation queries (out of {len(full_dataset)} total)")

    # Output directory
    out_dir: Path = args.output_dir or Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Providers
    from app.services.ai.factory import get_provider, get_ollama_provider, reset_provider

    reset_provider()
    provider = get_provider()

    ollama_provider = None
    try:
        ollama_provider = get_ollama_provider()
    except Exception:
        pass

    overall: dict[str, Any] = {}

    # Phase 1: Retrieval
    if not args.skip_retrieval:
        retrieval = await _run_retrieval(queries)
        overall["retrieval"] = retrieval
        with open(out_dir / "test_rag_retrieval_results.json", "w", encoding="utf-8") as f:
            json.dump(retrieval, f, ensure_ascii=False, indent=2)
    else:
        print("\n[skip] Retrieval evaluation")

    # Phase 2: Generation
    if not args.skip_generation:
        generation = await _run_generation(queries, provider)
        overall["generation"] = generation
        with open(out_dir / "test_rag_generation_results.json", "w", encoding="utf-8") as f:
            json.dump(generation, f, ensure_ascii=False, indent=2)
    else:
        print("\n[skip] Generation evaluation")

    # Phase 3: A/B Compare
    if not args.skip_compare:
        compare = await _run_compare(queries, provider, ollama_provider)
        overall["compare"] = compare
        with open(out_dir / "test_rag_compare_results.json", "w", encoding="utf-8") as f:
            json.dump(compare, f, ensure_ascii=False, indent=2)
    else:
        print("\n[skip] A/B comparison")

    # Final report
    if not args.no_report:
        from eval_report import generate_report

        print(f"\n{'='*60}")
        print(f"  FINAL REPORT")
        print(f"{'='*60}")
        generate_report(out_dir)
    else:
        print(f"\nAll results saved to: {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
