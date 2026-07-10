"""Rich terminal report generator for RAG evaluation results.

Reads JSON result files produced by the individual test scripts and prints
a formatted summary using Rich tables.

Usage:
    cd backend
    python tests/eval_report.py [--input-dir tests/]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ─── Color scales ──────────────────────────────────────────────────────────

def _metric_color(value: float, high_is_good: bool = True) -> str:
    """Return a Rich-style color tag based on metric value."""
    if high_is_good:
        if value >= 0.7:
            return "green"
        elif value >= 0.4:
            return "yellow"
        else:
            return "red"
    else:
        if value <= 0.3:
            return "green"
        elif value <= 0.6:
            return "yellow"
        else:
            return "red"


# ─── Plain-text fallback ───────────────────────────────────────────────────

def _plain_report(results: dict[str, Any]) -> None:
    """Fallback when Rich is not installed."""
    print("\n" + "=" * 60)
    print("  RAG Evaluation Report")
    print("=" * 60)

    retrieval = results.get("retrieval")
    if retrieval:
        m = retrieval.get("macro_avg", {})
        print("\n  Retrieval Metrics:")
        for k in ("precision@3", "recall@3", "ndcg@3", "precision@5", "recall@5", "ndcg@5", "mrr"):
            if k in m:
                print(f"    {k:<20s}: {m[k]:.4f}")
        print(f"    {'queries':<20s}: {retrieval.get('num_queries', 'N/A')}")

    generation = results.get("generation")
    if generation:
        s = generation.get("scores", {})
        print("\n  Generation Metrics (RAGAS):")
        for k, v in s.items():
            if k != "error":
                print(f"    {k:<25s}: {v:.4f}")

    compare = results.get("compare")
    if compare:
        rag_vs = compare.get("rag_vs_no_rag", {}).get("summary", {})
        if rag_vs:
            print("\n  Comparison – RAG vs No RAG:")
            print(f"    avg_rag_length    : {rag_vs.get('avg_rag_length', 'N/A')}")
            print(f"    avg_no_rag_length : {rag_vs.get('avg_no_rag_length', 'N/A')}")
            print(f"    rag_longer_count  : {rag_vs.get('rag_longer_count', 'N/A')}")

        ds_vs = compare.get("deepseek_vs_ollama", {}).get("summary", {})
        if ds_vs:
            print("\n  Comparison – DeepSeek vs Ollama:")
            print(f"    avg_deepseek_length : {ds_vs.get('avg_deepseek_length', 'N/A')}")
            print(f"    avg_ollama_length   : {ds_vs.get('avg_ollama_length', 'N/A')}")
            print(f"    ollama_successes    : {ds_vs.get('ollama_success_count', 'N/A')}")


# ─── Rich report ───────────────────────────────────────────────────────────

def _rich_report(results: dict[str, Any]) -> None:
    """Rich-formatted evaluation report."""
    console = Console()

    # Title
    title = Text("RAG Evaluation Report", style="bold cyan")
    console.print(Panel(title, border_style="cyan"))
    console.print()

    # ── Retrieval ──
    retrieval = results.get("retrieval")
    if retrieval:
        m = retrieval.get("macro_avg", {})
        table = Table(
            title="Dify Retrieval Metrics (Macro Average)",
            box=box.ROUNDED,
            title_style="bold blue",
        )
        table.add_column("Metric", style="cyan")
        table.add_column("@3", justify="right")
        table.add_column("@5", justify="right")

        table.add_row(
            "Precision",
            f"[{_metric_color(m.get('precision@3', 0))}]{m.get('precision@3', 'N/A'):.4f}[/]",
            f"[{_metric_color(m.get('precision@5', 0))}]{m.get('precision@5', 'N/A'):.4f}[/]",
        )
        table.add_row(
            "Recall",
            f"[{_metric_color(m.get('recall@3', 0))}]{m.get('recall@3', 'N/A'):.4f}[/]",
            f"[{_metric_color(m.get('recall@5', 0))}]{m.get('recall@5', 'N/A'):.4f}[/]",
        )
        table.add_row(
            "NDCG",
            f"[{_metric_color(m.get('ndcg@3', 0))}]{m.get('ndcg@3', 'N/A'):.4f}[/]",
            f"[{_metric_color(m.get('ndcg@5', 0))}]{m.get('ndcg@5', 'N/A'):.4f}[/]",
        )

        mrr = m.get("mrr", "N/A")
        mrr_str = f"[{_metric_color(float(mrr))}]{mrr:.4f}[/]" if isinstance(mrr, (int, float)) else str(mrr)
        table.add_row("MRR", mrr_str, "")

        console.print(table)
        console.print(f"  [dim]Queries evaluated: {retrieval.get('num_queries', 'N/A')}[/dim]")
        console.print()

    # ── Generation ──
    generation = results.get("generation")
    if generation:
        s = generation.get("scores", {})
        if s:
            table = Table(
                title="Generation Metrics (RAGAS)",
                box=box.ROUNDED,
                title_style="bold green",
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Bar")

            for metric_name, value in s.items():
                if metric_name == "error":
                    continue
                color = _metric_color(float(value))
                bar = "█" * int(float(value) * 30)
                table.add_row(
                    metric_name.replace("_", " ").title(),
                    f"[{color}]{float(value):.4f}[/{color}]",
                    f"[{color}]{bar}[/{color}]",
                )

            console.print(table)
            console.print()

    # ── Comparison ──
    compare = results.get("compare")
    if compare:
        rag_vs_summary = compare.get("rag_vs_no_rag", {}).get("summary", {})
        if rag_vs_summary:
            table = Table(
                title="A/B Comparison – With RAG vs Without RAG",
                box=box.ROUNDED,
                title_style="bold magenta",
            )
            table.add_column("Metric", style="cyan")
            table.add_column("With RAG", justify="right")
            table.add_column("Without RAG", justify="right")

            table.add_row(
                "Avg Answer Length",
                str(rag_vs_summary.get("avg_rag_length", "N/A")),
                str(rag_vs_summary.get("avg_no_rag_length", "N/A")),
            )
            table.add_row(
                "Avg Generation Time",
                f"{rag_vs_summary.get('avg_rag_time', 'N/A')}s",
                f"{rag_vs_summary.get('avg_no_rag_time', 'N/A')}s",
            )
            table.add_row(
                "Longer Answer Count",
                str(rag_vs_summary.get("rag_longer_count", "N/A")),
                str(rag_vs_summary.get("no_rag_longer_count", "N/A")),
            )

            console.print(table)
            console.print()

        ds_vs_summary = compare.get("deepseek_vs_ollama", {}).get("summary", {})
        if ds_vs_summary:
            table = Table(
                title="A/B Comparison – DeepSeek vs Ollama (both with RAG)",
                box=box.ROUNDED,
                title_style="bold magenta",
            )
            table.add_column("Metric", style="cyan")
            table.add_column("DeepSeek", justify="right")
            table.add_column("Ollama", justify="right")

            table.add_row(
                "Avg Answer Length",
                str(ds_vs_summary.get("avg_deepseek_length", "N/A")),
                str(ds_vs_summary.get("avg_ollama_length", "N/A")),
            )
            table.add_row(
                "Avg Generation Time",
                f"{ds_vs_summary.get('avg_deepseek_time', 'N/A')}s",
                f"{ds_vs_summary.get('avg_ollama_time', 'N/A')}s",
            )
            table.add_row(
                "Success Rate",
                f"---",
                f"{ds_vs_summary.get('ollama_success_count', 'N/A')}/{ds_vs_summary.get('total_queries', 'N/A')}",
            )

            console.print(table)
            console.print()


# ─── Loader ────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict[str, Any] | None:
    """Try to load a JSON file, return None if missing/invalid."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ─── Main ──────────────────────────────────────────────────────────────────

def generate_report(input_dir: Path) -> dict[str, Any]:
    """Load all result files and output a report."""
    results: dict[str, Any] = {}

    # Load individual result files
    retrieval = _load_json(input_dir / "test_rag_retrieval_results.json")
    if retrieval:
        results["retrieval"] = retrieval

    generation = _load_json(input_dir / "test_rag_generation_results.json")
    if generation:
        results["generation"] = generation

    # Compare results – try two possible file names
    compare: dict[str, Any] = {}
    rag_vs = _load_json(input_dir / "test_rag_compare_results.json")
    ds_vs = _load_json(input_dir / "test_deepseek_vs_ollama_results.json")
    if rag_vs:
        compare["rag_vs_no_rag"] = rag_vs
    if ds_vs:
        compare["deepseek_vs_ollama"] = ds_vs
    if compare:
        results["compare"] = compare

    if not results:
        print("[!] No result files found. Run the evaluation tests first:")
        print("    python tests/eval_runner.py")
        return results

    # Print report
    if HAS_RICH:
        _rich_report(results)
    else:
        _plain_report(results)

    # Save combined report
    combined_path = input_dir / "rag_eval_report.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Combined report saved to: {combined_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Report Generator")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing *_results.json files (default: same dir as this script)",
    )
    args = parser.parse_args()

    generate_report(args.input_dir)


if __name__ == "__main__":
    main()
