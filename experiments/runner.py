"""
experiments/runner.py — Experiment framework.

Every experiment follows the scientific method:
1. Hypothesis: What do we expect?
2. Method: What are we changing?
3. Variables: What are the independent/dependent variables?
4. Metrics: What are we measuring?
5. Result: What actually happened?
6. Interpretation: Why might it have happened?
7. Limitation: What could explain a wrong result?
8. Next step: What should we investigate next?

Each experiment records its FULL configuration snapshot so that
any result can be reproduced exactly.
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from src.core.config import config, AppConfig
from src.core.models import (
    BenchmarkQuestion, ExperimentResult, EvaluationResult,
)
from src.evaluation.evaluator import Evaluator

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Experiment definitions
# ──────────────────────────────────────────────

EXPERIMENTS: dict[str, dict[str, Any]] = {
    # ── Retrieval strategy comparison ──
    "EXP-01_dense_baseline": {
        "hypothesis": "Dense retrieval alone provides reasonable baseline retrieval quality.",
        "method": "Run benchmark with dense retrieval only. Disable BM25 and reranking.",
        "overrides": {
            "retrieval": {
                "dense_top_k": 50,
                "bm25_top_k": 0,
                "rerank_enabled": False,
                "adaptive_enabled": False,
            }
        },
    },
    "EXP-02_bm25_baseline": {
        "hypothesis": "BM25 alone provides strong lexical retrieval but poor semantic matching.",
        "method": "Run benchmark with BM25 only. Disable dense retrieval and reranking.",
        "overrides": {
            "retrieval": {
                "dense_top_k": 0,
                "bm25_top_k": 50,
                "rerank_enabled": False,
                "adaptive_enabled": False,
            }
        },
    },
    "EXP-03_hybrid_rrf": {
        "hypothesis": "Hybrid retrieval (dense + BM25 with RRF) outperforms either alone.",
        "method": "Enable both dense and BM25 with RRF fusion. No reranking.",
        "overrides": {
            "retrieval": {
                "dense_top_k": 50,
                "bm25_top_k": 50,
                "fusion_method": "rrf",
                "rerank_enabled": False,
                "adaptive_enabled": False,
            }
        },
    },
    "EXP-04_hybrid_dense_heavy": {
        "hypothesis": "Dense-heavy weighting improves conceptual query retrieval.",
        "method": "Hybrid with dense_weight=0.8, bm25_weight=0.2.",
        "overrides": {
            "retrieval": {
                "dense_weight": 0.8,
                "bm25_weight": 0.2,
                "fusion_method": "weighted",
                "rerank_enabled": False,
                "adaptive_enabled": False,
            }
        },
    },
    "EXP-05_hybrid_lexical_heavy": {
        "hypothesis": "Lexical-heavy weighting improves exact-match query retrieval.",
        "method": "Hybrid with dense_weight=0.2, bm25_weight=0.8.",
        "overrides": {
            "retrieval": {
                "dense_weight": 0.2,
                "bm25_weight": 0.8,
                "fusion_method": "weighted",
                "rerank_enabled": False,
                "adaptive_enabled": False,
            }
        },
    },
    "EXP-06_adaptive_hybrid": {
        "hypothesis": "Adaptive hybrid retrieval (query-type-aware weights) outperforms fixed hybrid.",
        "method": "Enable adaptive retrieval with query classification.",
        "overrides": {
            "retrieval": {
                "adaptive_enabled": True,
                "adaptive_strategy": "query_type",
                "rerank_enabled": True,
            }
        },
    },

    # ── Chunking comparison ──
    "EXP-07_chunking_fixed": {
        "hypothesis": "Fixed-size chunking provides predictable but suboptimal retrieval.",
        "overrides": {"chunking": {"strategy": "fixed", "chunk_size": 512, "chunk_overlap": 64}},
    },
    "EXP-07_chunking_sentence": {
        "hypothesis": "Sentence-based chunking preserves semantic boundaries.",
        "overrides": {"chunking": {"strategy": "sentence", "chunk_size": 512, "chunk_overlap": 64}},
    },
    "EXP-07_chunking_recursive": {
        "hypothesis": "Recursive chunking balances structure preservation with flexibility.",
        "overrides": {"chunking": {"strategy": "recursive", "chunk_size": 512, "chunk_overlap": 64}},
    },
    "EXP-07_chunking_structure": {
        "hypothesis": "Structure-aware chunking produces topically coherent chunks.",
        "overrides": {"chunking": {"strategy": "structure", "chunk_size": 512, "chunk_overlap": 64}},
    },

    # ── Reranking ──
    "EXP-09_full_with_rerank": {
        "hypothesis": "Cross-encoder reranking significantly improves precision.",
        "overrides": {"retrieval": {"rerank_enabled": True, "rerank_top_k": 5}},
    },
    "EXP-09_full_no_rerank": {
        "hypothesis": "Without reranking, precision drops but latency improves.",
        "overrides": {"retrieval": {"rerank_enabled": False}},
    },

    # ── Top-K sensitivity ──
    "EXP-10_topk_3": {"overrides": {"retrieval": {"rerank_top_k": 3}}},
    "EXP-10_topk_5": {"overrides": {"retrieval": {"rerank_top_k": 5}}},
    "EXP-10_topk_10": {"overrides": {"retrieval": {"rerank_top_k": 10}}},

    # ── Ablation studies ──
    "EXP-ABL_no_bm25": {
        "hypothesis": "Removing BM25 from hybrid reduces lexical retrieval quality.",
        "overrides": {"retrieval": {"bm25_top_k": 0}},
    },
    "EXP-ABL_no_dense": {
        "hypothesis": "Removing dense from hybrid reduces semantic retrieval quality.",
        "overrides": {"retrieval": {"dense_top_k": 0}},
    },
    "EXP-ABL_no_adaptive": {
        "hypothesis": "Disabling adaptive retrieval makes all queries use the same strategy.",
        "overrides": {"retrieval": {"adaptive_enabled": False}},
    },
    "EXP-ABL_no_evidence_check": {
        "hypothesis": "Disabling evidence sufficiency check increases hallucination rate.",
        "overrides": {"evidence": {"sufficiency_enabled": False}},
    },

    # ── Full optimized pipeline ──
    "EXP-19_full_optimized": {
        "hypothesis": "Full pipeline with all components enabled produces best overall quality.",
        "overrides": {
            "retrieval": {
                "dense_top_k": 50,
                "bm25_top_k": 50,
                "fusion_method": "rrf",
                "rerank_enabled": True,
                "rerank_top_k": 5,
                "adaptive_enabled": True,
            },
            "evidence": {"sufficiency_enabled": True},
        },
    },
}


class ExperimentRunner:
    """
    Runs experiments systematically.

    For each experiment:
    1. Apply configuration overrides
    2. Load benchmark dataset
    3. Run evaluation on all questions
    4. Compute aggregate metrics
    5. Save results with full metadata
    """

    def __init__(self):
        self.evaluator = Evaluator()

    def load_benchmark(self) -> list[BenchmarkQuestion]:
        """Load the benchmark dataset."""
        dataset_path = config.evaluation.dataset_path
        if not dataset_path.exists():
            logger.error(f"Benchmark dataset not found: {dataset_path}")
            return []

        with open(dataset_path) as f:
            data = json.load(f)

        questions = [BenchmarkQuestion(**q) for q in data.get("questions", [])]
        logger.info(f"Loaded {len(questions)} benchmark questions")
        return questions

    def run_experiment(
        self,
        name: str,
        exp_def: dict[str, Any],
        questions: list[BenchmarkQuestion],
    ) -> ExperimentResult:
        """Run a single experiment."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Experiment: {name}")
        logger.info(f"Hypothesis: {exp_def.get('hypothesis', 'N/A')}")

        # Apply overrides
        overrides = exp_def.get("overrides", {})
        self._apply_overrides(overrides)

        # Run evaluation
        start_time = time.time()
        results = []
        errors = []

        for q in questions:
            try:
                result = self.evaluator.evaluate_question(q)
                results.append(result)
            except Exception as e:
                logger.error(f"Error on {q.question_id}: {e}")
                errors.append(f"{q.question_id}: {str(e)}")

        total_time = (time.time() - start_time) * 1000

        # Compute metrics
        metrics = self.evaluator.compute_aggregate_metrics(results)

        experiment = ExperimentResult(
            name=name,
            description=exp_def.get("method", ""),
            hypothesis=exp_def.get("hypothesis", ""),
            method=exp_def.get("method", ""),
            config_snapshot=self._snapshot_config(),
            dataset_version="v1.0",
            metrics=metrics,
            question_results=results,
            total_latency_ms=total_time,
            errors=errors,
            interpretation="RESULTS PENDING — requires analysis",
            limitations="Results depend on benchmark dataset quality",
            next_experiment="See experiment sequence in docs/RESEARCH_LOG.md",
        )

        # Save
        self._save_result(experiment)

        logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")
        return experiment

    def run_all(self) -> list[ExperimentResult]:
        """Run all defined experiments."""
        questions = self.load_benchmark()
        if not questions:
            logger.error("No benchmark questions. Aborting.")
            return []

        results = []
        for name, exp_def in EXPERIMENTS.items():
            result = self.run_experiment(name, exp_def, questions)
            results.append(result)

        # Generate comparison
        self._generate_comparison(results)
        return results

    def _apply_overrides(self, overrides: dict[str, Any]) -> None:
        """Apply configuration overrides."""
        for section, values in overrides.items():
            section_config = getattr(config, section, None)
            if section_config is None:
                logger.warning(f"Unknown config section: {section}")
                continue
            for key, value in values.items():
                if hasattr(section_config, key):
                    setattr(section_config, key, value)

    def _snapshot_config(self) -> dict:
        """Capture full configuration for reproducibility."""
        return {
            "chunking": {
                "strategy": config.chunking.strategy,
                "chunk_size": config.chunking.chunk_size,
                "chunk_overlap": config.chunking.chunk_overlap,
            },
            "embedding": {
                "provider": config.embedding.provider,
                "model_name": config.embedding.model_name,
            },
            "retrieval": {
                "dense_top_k": config.retrieval.dense_top_k,
                "bm25_top_k": config.retrieval.bm25_top_k,
                "fusion_method": config.retrieval.fusion_method,
                "dense_weight": config.retrieval.dense_weight,
                "bm25_weight": config.retrieval.bm25_weight,
                "rerank_enabled": config.retrieval.rerank_enabled,
                "rerank_top_k": config.retrieval.rerank_top_k,
                "adaptive_enabled": config.retrieval.adaptive_enabled,
            },
            "evidence": {
                "sufficiency_enabled": config.evidence.sufficiency_enabled,
                "min_evidence_score": config.evidence.min_evidence_score,
            },
            "generation": {
                "model": config.generation.model,
                "temperature": config.generation.temperature,
                "abstention_threshold": config.generation.abstention_threshold,
            },
        }

    def _save_result(self, experiment: ExperimentResult) -> None:
        """Save experiment result to disk."""
        output_dir = config.evaluation.results_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{experiment.name}_{experiment.timestamp[:10]}.json"
        with open(output_dir / filename, "w") as f:
            json.dump(experiment.model_dump(), f, indent=2, default=str)

    def _generate_comparison(self, results: list[ExperimentResult]) -> None:
        """Generate markdown comparison table."""
        metrics_keys = [
            "recall@5", "mrr", "factual_correctness",
            "groundedness", "citation_accuracy",
            "hallucination_rate", "latency_p50",
        ]

        lines = ["# Experiment Comparison\n"]
        lines.append("| Experiment | " + " | ".join(metrics_keys) + " |")
        lines.append("|" + "---|" * (len(metrics_keys) + 1))

        for exp in results:
            values = [f'{exp.metrics.get(m, 0):.3f}' for m in metrics_keys]
            lines.append(f"| {exp.name} | " + " | ".join(values) + " |")

        output_path = config.evaluation.results_dir / "COMPARISON.md"
        with open(output_path, "w") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = ExperimentRunner()
    runner.run_all()
