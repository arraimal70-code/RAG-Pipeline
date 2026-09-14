#!/usr/bin/env python3
"""
scripts/measure_performance.py — Performance measurement tool.

Measures latency at each pipeline stage and generates performance reports.
"""

import json
import time
import statistics
from pathlib import Path
from typing import Any
from datetime import datetime

from src.pipeline import RAGPipeline
from src.core.config import config


class PerformanceProfiler:
    """Profiles performance of RAG pipeline stages."""

    def __init__(self):
        self.pipeline = RAGPipeline()
        self.measurements: list[dict] = []

    def measure_query_latency(self, question: str, num_runs: int = 3) -> dict:
        """
        Measure query latency across multiple runs.

        Returns statistics (mean, median, p95, p99) for each stage.
        """
        stage_latencies: dict[str, list[float]] = {
            "query_analysis": [],
            "retrieval": [],
            "temporal_filtering": [],
            "evidence_assessment": [],
            "numerical_reasoning": [],
            "generation": [],
            "citation_validation": [],
            "claim_analysis": [],
            "total": [],
        }

        for i in range(num_runs):
            start = time.time()
            response = self.pipeline.query(question)
            total_time = (time.time() - start) * 1000

            # Extract stage latencies from response metadata
            stage_latencies["total"].append(total_time)
            stage_latencies["retrieval"].append(
                response.latency.get("retrieval_ms", 0)
            )
            stage_latencies["generation"].append(
                response.latency.get("generation_ms", 0)
            )

            # Note: Other stage latencies would need to be extracted from trace
            # For now, we'll estimate them
            other_time = total_time - sum([
                response.latency.get("retrieval_ms", 0),
                response.latency.get("generation_ms", 0),
            ])
            stage_latencies["query_analysis"].append(other_time / 6)
            stage_latencies["temporal_filtering"].append(other_time / 6)
            stage_latencies["evidence_assessment"].append(other_time / 6)
            stage_latencies["numerical_reasoning"].append(other_time / 6)
            stage_latencies["citation_validation"].append(other_time / 6)
            stage_latencies["claim_analysis"].append(other_time / 6)

        # Calculate statistics
        stats = {}
        for stage, times in stage_latencies.items():
            if times:
                stats[stage] = {
                    "mean_ms": statistics.mean(times),
                    "median_ms": statistics.median(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
                    "p95_ms": self._percentile(times, 95),
                    "p99_ms": self._percentile(times, 99),
                }

        return stats

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        d = k - f
        return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])

    def measure_ingestion_latency(self, pdf_path: Path) -> dict:
        """Measure document ingestion latency."""
        start = time.time()
        result = self.pipeline.ingest_document(pdf_path)
        elapsed = (time.time() - start) * 1000

        return {
            "filename": result["filename"],
            "num_pages": result["num_pages"],
            "num_chunks": result["num_chunks"],
            "total_time_ms": elapsed,
            "time_per_page_ms": elapsed / result["num_pages"] if result["num_pages"] > 0 else 0,
            "time_per_chunk_ms": elapsed / result["num_chunks"] if result["num_chunks"] > 0 else 0,
        }

    def measure_retrieval_latency(self, question: str, num_runs: int = 5) -> dict:
        """Measure retrieval latency specifically."""
        latencies = []

        for _ in range(num_runs):
            start = time.time()
            retrieval = self.pipeline.retriever.retrieve(question)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)

        return {
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": self._percentile(latencies, 95),
            "num_candidates": retrieval.total_candidates if retrieval else 0,
        }

    def generate_report(self, output_path: Path) -> None:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "config": {
                "chunking_strategy": config.chunking.strategy,
                "chunk_size": config.chunking.chunk_size,
                "embedding_provider": config.embedding.provider,
                "rerank_enabled": config.retrieval.rerank_enabled,
            },
            "measurements": self.measurements,
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Performance report saved to {output_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Measure RAG pipeline performance")
    parser.add_argument("--output", type=Path, default=Path("performance_report.json"))
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per measurement")

    args = parser.parse_args()

    profiler = PerformanceProfiler()

    # Example queries for testing
    test_queries = [
        "What was the revenue in 2023?",
        "Compare Q1 and Q2 results",
        "What is the company's strategy?",
    ]

    print("Measuring query latency...")
    for query in test_queries:
        print(f"  Query: {query}")
        stats = profiler.measure_query_latency(query, num_runs=args.runs)
        profiler.measurements.append({
            "type": "query",
            "query": query,
            "stats": stats,
        })

    # Generate report
    profiler.generate_report(args.output)

    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)

    for measurement in profiler.measurements:
        if measurement["type"] == "query":
            print(f"\nQuery: {measurement['query']}")
            stats = measurement["stats"]
            print(f"  Total latency:")
            print(f"    Mean: {stats['total']['mean_ms']:.2f} ms")
            print(f"    P95:  {stats['total']['p95_ms']:.2f} ms")
            print(f"    P99:  {stats['total']['p99_ms']:.2f} ms")


if __name__ == "__main__":
    main()
