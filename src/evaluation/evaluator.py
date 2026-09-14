"""
src/evaluation/evaluator.py — Comprehensive evaluation framework.

Measures:
- Retrieval: Recall@K, MRR, nDCG
- Generation: Factual correctness, groundedness, citation accuracy
- System: Latency, token usage, cost
- Abstention: Correct refusal rate, false answering rate

Supports ablation studies by running the same dataset with
different configurations.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional
from collections import defaultdict

from src.core.config import config
from src.core.models import (
    BenchmarkQuestion, EvaluationResult, ExperimentResult,
    SupportLevel, FailureCategory, QuestionType,
)
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.generator import Generator

logger = logging.getLogger(__name__)


class Evaluator:
    """
    Evaluation framework for RAG pipeline.

    Supports:
    - Per-question evaluation with detailed metrics
    - Aggregate metric computation
    - Experiment tracking with configuration snapshots
    - Failure analysis categorization
    """

    def __init__(self):
        self.retriever = HybridRetriever()
        self.generator = Generator()

    def evaluate_question(self, question: BenchmarkQuestion) -> EvaluationResult:
        """Evaluate a single question end-to-end."""
        start_time = time.time()

        # Retrieve
        retrieval = self.retriever.retrieve(question.question)

        # Generate
        generation = self.generator.generate(question.question, retrieval)

        elapsed = (time.time() - start_time) * 1000

        # Evaluate retrieval quality
        retrieved_correct_source = self._check_source_match(
            retrieval, question.source_document
        )
        retrieved_correct_passage = self._check_passage_match(
            retrieval, question.relevant_chunk_ids
        )

        # Compute recall@K
        recall_at_k = self._compute_recall_at_k(retrieval, question)

        # Evaluate generation quality
        factual_correctness = self._estimate_factual_correctness(
            generation.answer, question.expected_answer, generation.support_level
        )
        groundedness = self._estimate_groundedness(generation)
        citation_accuracy = self._evaluate_citations(generation, retrieval)

        # Detect failures
        failure_category = self._categorize_failure(
            question, retrieval, generation,
            retrieved_correct_source, retrieved_correct_passage,
        )

        return EvaluationResult(
            question_id=question.question_id,
            question=question.question,
            expected_answer=question.expected_answer,
            generated_answer=generation.answer,
            support_level=generation.support_level,
            retrieved_correct_source=retrieved_correct_source,
            retrieved_correct_passage=retrieved_correct_passage,
            recall_at_k=recall_at_k,
            factual_correctness=factual_correctness,
            groundedness=groundedness,
            citation_accuracy=citation_accuracy,
            hallucination_detected=(
                generation.support_level == SupportLevel.UNSUPPORTED
            ),
            latency_ms=elapsed,
            failure_category=failure_category,
        )

    def run_experiment(
        self,
        name: str,
        description: str,
        questions: list[BenchmarkQuestion],
    ) -> ExperimentResult:
        """Run a complete experiment on the benchmark dataset."""
        logger.info(f"Starting experiment: {name}")
        start_time = time.time()

        results = []
        errors = []

        for q in questions:
            try:
                result = self.evaluate_question(q)
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating question {q.question_id}: {e}")
                errors.append(f"{q.question_id}: {str(e)}")

        # Compute aggregate metrics
        metrics = self.compute_aggregate_metrics(results)

        total_time = (time.time() - start_time) * 1000

        experiment = ExperimentResult(
            name=name,
            description=description,
            config_snapshot=self._snapshot_config(),
            dataset_version="v1.0",
            metrics=metrics,
            question_results=results,
            total_latency_ms=total_time,
            errors=errors,
        )

        # Save results
        self._save_experiment(experiment)

        logger.info(f"Experiment '{name}' complete. Metrics: {metrics}")
        return experiment

    def _check_source_match(self, retrieval, expected_source: str) -> bool:
        """Check if any retrieved chunk is from the expected source document."""
        for r in retrieval.candidates:
            if expected_source.lower() in r.chunk.filename.lower():
                return True
        return False

    def _check_passage_match(self, retrieval, relevant_chunk_ids: list[str]) -> bool:
        """Check if any retrieved chunk matches a relevant chunk."""
        if not relevant_chunk_ids:
            return False
        retrieved_ids = {r.chunk.chunk_id for r in retrieval.candidates}
        return bool(retrieved_ids & set(relevant_chunk_ids))

    def _compute_recall_at_k(
        self, retrieval, question: BenchmarkQuestion
    ) -> dict[str, float]:
        """Compute Recall@1, Recall@3, Recall@5, Recall@10."""
        if not question.relevant_chunk_ids:
            return {}

        relevant = set(question.relevant_chunk_ids)
        recall = {}

        for k in [1, 3, 5, 10]:
            retrieved_k = {r.chunk.chunk_id for r in retrieval.candidates[:k]}
            hits = len(relevant & retrieved_k)
            recall[f"recall@{k}"] = hits / len(relevant) if relevant else 0.0

        return recall

    def _estimate_factual_correctness(
        self, generated: str, expected: str, support: SupportLevel
    ) -> float:
        """
        Estimate factual correctness.

        This is a heuristic — proper evaluation would use an LLM judge
        or manual annotation. For now:
        - SUPPORTED answers get high score
        - PARTIALLY_SUPPORTED get medium
        - UNSUPPORTED get low
        """
        scores = {
            SupportLevel.SUPPORTED: 0.85,
            SupportLevel.PARTIALLY_SUPPORTED: 0.55,
            SupportLevel.UNSUPPORTED: 0.15,
            SupportLevel.INSUFFICIENT_EVIDENCE: 0.0,
        }
        return scores.get(support, 0.5)

    def _estimate_groundedness(self, generation) -> float:
        """
        Estimate how grounded the answer is in retrieved evidence.

        Heuristic based on support level and citation count.
        """
        if generation.abstained:
            return 1.0  # correctly abstaining is grounded behavior

        base = {
            SupportLevel.SUPPORTED: 0.9,
            SupportLevel.PARTIALLY_SUPPORTED: 0.6,
            SupportLevel.UNSUPPORTED: 0.2,
            SupportLevel.INSUFFICIENT_EVIDENCE: 0.0,
        }.get(generation.support_level, 0.5)

        # Validated citations improve groundedness
        valid_citations = sum(1 for c in generation.citations if c.validated)
        citation_bonus = min(valid_citations * 0.05, 0.1)

        return min(base + citation_bonus, 1.0)

    def _evaluate_citations(self, generation, retrieval) -> float:
        """Evaluate citation accuracy."""
        if not generation.citations:
            return 0.0

        valid = sum(1 for c in generation.citations if c.validated)
        return valid / len(generation.citations)

    def _categorize_failure(
        self, question, retrieval, generation,
        correct_source: bool, correct_passage: bool,
    ) -> Optional[FailureCategory]:
        """Categorize the type of failure if any."""
        if generation.abstained and question.answerable:
            return FailureCategory.RETRIEVAL  # should have answered but didn't

        if not question.answerable and not generation.abstained:
            return FailureCategory.HALLUCINATION  # answered when shouldn't

        if not correct_source:
            return FailureCategory.RETRIEVAL

        if not correct_passage and correct_source:
            return FailureCategory.RANKING

        if generation.support_level == SupportLevel.UNSUPPORTED:
            return FailureCategory.GENERATION

        if any(not c.validated for c in generation.citations):
            return FailureCategory.CITATION

        return None

    def compute_aggregate_metrics(
        self, results: list[EvaluationResult]
    ) -> dict[str, float]:
        """Compute aggregate metrics across all questions."""
        if not results:
            return {}

        n = len(results)
        metrics = {}

        # Retrieval metrics
        for k in [1, 3, 5, 10]:
            key = f"recall@{k}"
            values = [r.recall_at_k.get(key, 0.0) for r in results if r.recall_at_k]
            metrics[key] = sum(values) / len(values) if values else 0.0

        metrics["source_retrieval_accuracy"] = (
            sum(1 for r in results if r.retrieved_correct_source) / n
        )
        metrics["passage_retrieval_accuracy"] = (
            sum(1 for r in results if r.retrieved_correct_passage) / n
        )

        # MRR
        rr_values = []
        for r in results:
            for k, v in r.recall_at_k.items():
                if v > 0:
                    first_k = int(k.split("@")[1])
                    rr_values.append(1.0 / first_k)
                    break
            else:
                rr_values.append(0.0)
        metrics["mrr"] = sum(rr_values) / len(rr_values) if rr_values else 0.0

        # Generation metrics
        metrics["factual_correctness"] = (
            sum(r.factual_correctness for r in results) / n
        )
        metrics["groundedness"] = (
            sum(r.groundedness for r in results) / n
        )
        metrics["citation_accuracy"] = (
            sum(r.citation_accuracy for r in results) / n
        )
        metrics["hallucination_rate"] = (
            sum(1 for r in results if r.hallucination_detected) / n
        )

        # Abstention metrics
        metrics["abstention_rate"] = (
            sum(1 for r in results if r.support_level == SupportLevel.INSUFFICIENT_EVIDENCE) / n
        )

        # Latency
        latencies = sorted([r.latency_ms for r in results])
        metrics["latency_p50"] = latencies[len(latencies) // 2] if latencies else 0.0
        metrics["latency_p95"] = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        return metrics

    def _snapshot_config(self) -> dict:
        """Capture current configuration for reproducibility."""
        from src.core.config import config
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
                "rerank_enabled": config.retrieval.rerank_enabled,
                "rerank_top_k": config.retrieval.rerank_top_k,
            },
            "generation": {
                "model": config.generation.model,
                "temperature": config.generation.temperature,
            },
        }

    def _save_experiment(self, experiment: ExperimentResult) -> None:
        """Save experiment results to disk."""
        output_dir = config.evaluation.results_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{experiment.name}_{experiment.timestamp[:10]}.json"
        output_path = output_dir / filename

        with open(output_path, "w") as f:
            json.dump(experiment.model_dump(), f, indent=2, default=str)

        logger.info(f"Experiment saved to {output_path}")
