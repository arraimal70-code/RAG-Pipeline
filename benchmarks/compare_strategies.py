"""
benchmarks/compare_strategies.py — Multi-Strategy RAG Evaluation Harness.

Directly implements the comparative evaluation rule from Akber Shaikh's
"5 AI Engineer projects that will give you unfair advantage in 2026" (Project 4: RAG with Eval Harness):

"Try these four methods: Simple Chunking, Semantic Chunking, Hybrid Search, and Reranking.
Ask the same benchmark questions across all four and observe how accuracy evolves from
baseline (~61%) to production-grade (~85%+). Put that comparison table in your results."

Strategies Evaluated:
1. Baseline: Fixed-size Chunking (Dense Only, No BM25, No Rerank)
2. Semantic / Structure-Aware Chunking (Dense Only, No BM25, No Rerank)
3. Hybrid Retrieval: Structure Chunking + Dense + BM25 (RRF Fusion, No Rerank)
4. Production Pipeline: Structure Chunking + Hybrid Retrieval + Cross-Encoder Reranking
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import config
from benchmarks.run_benchmark import BenchmarkRunner


def run_strategy_comparison(dataset_path: Path, samples: int = 25) -> List[Dict[str, Any]]:
    """
    Run evaluation across the 4 key retrieval strategies and return comparison summary.
    """
    strategies = [
        {
            "name": "1. Simple Chunking (Fixed + Dense Only)",
            "config_overrides": {
                "chunking_strategy": "fixed",
                "chunk_size": 512,
                "chunk_overlap": 64,
                "dense_top_k": 20,
                "bm25_top_k": 0,
                "rerank_enabled": False,
                "adaptive_enabled": False,
            },
        },
        {
            "name": "2. Structure-Aware Chunking (Dense Only)",
            "config_overrides": {
                "chunking_strategy": "structure",
                "chunk_size": 512,
                "chunk_overlap": 64,
                "dense_top_k": 20,
                "bm25_top_k": 0,
                "rerank_enabled": False,
                "adaptive_enabled": False,
            },
        },
        {
            "name": "3. Hybrid Search (Dense + BM25 RRF)",
            "config_overrides": {
                "chunking_strategy": "structure",
                "chunk_size": 512,
                "chunk_overlap": 64,
                "dense_top_k": 50,
                "bm25_top_k": 50,
                "fusion_method": "rrf",
                "rerank_enabled": False,
                "adaptive_enabled": False,
            },
        },
        {
            "name": "4. Hybrid + Cross-Encoder Reranking",
            "config_overrides": {
                "chunking_strategy": "structure",
                "chunk_size": 512,
                "chunk_overlap": 64,
                "dense_top_k": 50,
                "bm25_top_k": 50,
                "fusion_method": "rrf",
                "rerank_enabled": True,
                "rerank_top_k": 5,
                "adaptive_enabled": True,
            },
        },
    ]

    results = []

    print("\n" + "=" * 78)
    print("      AKBER SHAIKH 2026 EVALUATION HARNESS: 4-STRATEGY RAG COMPARISON")
    print("=" * 78)
    print(f"Dataset: {dataset_path.name} | Evaluation Queries: {samples}\n")

    for strat in strategies:
        print(f"\n>>> Running Evaluation for Strategy: {strat['name']}...")
        cfg = strat["config_overrides"]

        # Apply configuration overrides
        config.chunking.strategy = cfg.get("chunking_strategy", "recursive")
        config.retrieval.dense_top_k = cfg.get("dense_top_k", 50)
        config.retrieval.bm25_top_k = cfg.get("bm25_top_k", 50)
        config.retrieval.fusion_method = cfg.get("fusion_method", "rrf")
        config.retrieval.rerank_enabled = cfg.get("rerank_enabled", True)
        if "rerank_top_k" in cfg:
            config.retrieval.rerank_top_k = cfg["rerank_top_k"]
        config.retrieval.adaptive_enabled = cfg.get("adaptive_enabled", True)

        runner = BenchmarkRunner(benchmark_file=dataset_path, max_samples=samples)
        summary = runner.run()

        results.append({
            "strategy": strat["name"],
            "Hit@1": summary["retrieval_metrics"]["Hit@1"],
            "Hit@3": summary["retrieval_metrics"]["Hit@3"],
            "Hit@5": summary["retrieval_metrics"]["Hit@5"],
            "MRR@5": summary["retrieval_metrics"]["MRR@5"],
            "NDCG@5": summary["retrieval_metrics"]["NDCG@5"],
            "Faithfulness": summary["generation_metrics"]["claim_level_faithfulness"],
            "P50_Latency_ms": summary["latency_ms"]["p50"],
        })

    # Print final Markdown Comparison Table
    print("\n\n" + "=" * 78)
    print("                     FINAL STRATEGY COMPARISON TABLE")
    print("=" * 78 + "\n")
    print("| Retrieval Strategy | Hit@1 | Hit@3 | Hit@5 | MRR@5 | NDCG@5 | Faithfulness | P50 Latency |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for r in results:
        print(
            f"| {r['strategy']:<40} | "
            f"{r['Hit@1']:6.1%} | "
            f"{r['Hit@3']:6.1%} | "
            f"{r['Hit@5']:6.1%} | "
            f"{r['MRR@5']:.4f} | "
            f"{r['NDCG@5']:.4f} | "
            f"{r['Faithfulness']:6.1%} | "
            f"{r['P50_Latency_ms']:5.1f} ms |"
        )
    print("\n" + "=" * 78 + "\n")

    # Save to json artifact
    out_file = PROJECT_ROOT / "benchmarks" / "results" / f"strategy_comparison_{int(time.time())}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[Artifact] Saved strategy comparison matrix to: {out_file}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="4-Strategy RAG Benchmark Comparison Harness")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(PROJECT_ROOT / "benchmarks" / "verified_benchmark.json"),
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=25,
        help="Number of query samples to evaluate",
    )
    args = parser.parse_args()
    run_strategy_comparison(dataset_path=Path(args.dataset), samples=args.samples)


if __name__ == "__main__":
    main()
