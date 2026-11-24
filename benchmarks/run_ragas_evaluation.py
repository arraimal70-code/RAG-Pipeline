"""
benchmarks/run_ragas_evaluation.py — Frontier Automated RAGAS Benchmark Runner.

Executes automated RAGAS evaluation across Faithfulness, Answer Relevancy,
Context Precision, and Context Recall over the Frontier golden dataset.
"""

import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.evaluation.ragas_runner import RAGASDatasetItem, RAGASRunner


def main() -> None:
    dataset_path = root_dir / "benchmarks" / "golden_dataset.json"
    if not dataset_path.exists():
        print(f"Error: Golden dataset not found at {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dataset: list[RAGASDatasetItem] = [
        RAGASDatasetItem(
            question=item["question"],
            contexts=item["contexts"],
            answer=item["answer"],
            ground_truth=item["ground_truth"],
        )
        for item in data
    ]

    print("=" * 72)
    print("  FRONTIER TIER-1 RAGAS AUTOMATED BENCHMARK EVALUATION")
    print("=" * 72)
    print(f"Loaded {len(dataset)} verified golden benchmark queries.")
    print("Evaluating Faithfulness, Answer Relevancy, Context Precision, Context Recall...")

    runner = RAGASRunner()
    result = runner.evaluate_dataset(dataset)

    print("\n" + "=" * 72)
    print("  EVALUATION SCORECARD")
    print("=" * 72)
    print(f"  Total Samples Evaluated  : {result.total_samples}")
    print(f"  Mean Faithfulness        : {result.mean_faithfulness * 100:.2f}%")
    print(f"  Mean Answer Relevancy    : {result.mean_answer_relevancy * 100:.2f}%")
    print(f"  Mean Context Precision   : {result.mean_context_precision * 100:.2f}%")
    print(f"  Mean Context Recall      : {result.mean_context_recall * 100:.2f}%")
    print("-" * 72)
    print(f"  OVERALL RAGAS COMPOSITE  : {result.overall_score * 100:.2f}%")
    print("-" * 72)
    print(f"  P50 Evaluation Latency   : {result.p50_latency_ms:.2f} ms")
    print(f"  P95 Evaluation Latency   : {result.p95_latency_ms:.2f} ms")
    print(f"  P99 Evaluation Latency   : {result.p99_latency_ms:.2f} ms")
    print("=" * 72)

    # Save output results
    out_dir = root_dir / "benchmarks" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ragas_scorecard.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"Scorecard persisted to: {out_file.relative_to(root_dir)}")


if __name__ == "__main__":
    main()
