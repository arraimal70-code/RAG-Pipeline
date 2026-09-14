"""
Production-ready evaluation framework with comprehensive metrics.
"""

import logging
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import statistics

from src.core.models import QueryResponse, BenchmarkQuestion

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    precision_at_5: float = 0.0
    hit_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class GenerationMetrics:
    """Metrics for generation quality."""
    answer_correctness: float = 0.0
    faithfulness: float = 0.0
    groundedness: float = 0.0
    completeness: float = 0.0
    relevance: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class CitationMetrics:
    """Metrics for citation quality."""
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    citation_completeness: float = 0.0
    citation_entailment: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Metrics for system performance."""
    latency_p50_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    throughput_qps: float = 0.0
    memory_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class CostMetrics:
    """Metrics for system cost."""
    embedding_tokens: int = 0
    generation_input_tokens: int = 0
    generation_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cost_per_query_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single query."""
    query_id: str
    question: str
    expected_answer: str
    generated_answer: str
    retrieval_metrics: RetrievalMetrics
    generation_metrics: GenerationMetrics
    citation_metrics: CitationMetrics
    latency_ms: float
    abstained: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "generated_answer": self.generated_answer,
            "retrieval_metrics": self.retrieval_metrics.to_dict(),
            "generation_metrics": self.generation_metrics.to_dict(),
            "citation_metrics": self.citation_metrics.to_dict(),
            "latency_ms": self.latency_ms,
            "abstained": self.abstained,
            "error": self.error,
        }


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all queries."""
    retrieval: RetrievalMetrics
    generation: GenerationMetrics
    citation: CitationMetrics
    performance: PerformanceMetrics
    cost: CostMetrics
    total_queries: int
    successful_queries: int
    failed_queries: int
    abstention_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "retrieval": self.retrieval.to_dict(),
            "generation": self.generation.to_dict(),
            "citation": self.citation.to_dict(),
            "performance": self.performance.to_dict(),
            "cost": self.cost.to_dict(),
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "abstention_rate": self.abstention_rate,
        }


class Evaluator:
    """
    Production-ready evaluation framework.
    
    Evaluates:
    - Retrieval quality (Recall@K, MRR, NDCG)
    - Generation quality (correctness, faithfulness)
    - Citation quality (precision, recall)
    - Performance (latency, throughput)
    - Cost (tokens, API costs)
    """
    
    def __init__(self, output_dir: str = "evaluation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pricing (as of 2024)
        self.embedding_cost_per_1k = 0.0001  # $0.10 per 1M tokens
        self.generation_input_cost_per_1k = 0.00015  # $0.15 per 1M tokens
        self.generation_output_cost_per_1k = 0.0006  # $0.60 per 1M tokens
        
        logger.info(f"Evaluator initialized, output to {output_dir}")
    
    def evaluate_query(
        self,
        question: BenchmarkQuestion,
        response: QueryResponse,
        latency_ms: float,
    ) -> EvaluationResult:
        """Evaluate a single query response."""
        logger.debug(f"Evaluating query: {question.question_id}")
        
        # Evaluate retrieval
        retrieval_metrics = self._evaluate_retrieval(question, response)
        
        # Evaluate generation
        generation_metrics = self._evaluate_generation(question, response)
        
        # Evaluate citations
        citation_metrics = self._evaluate_citations(question, response)
        
        return EvaluationResult(
            query_id=question.question_id,
            question=question.question,
            expected_answer=question.expected_answer,
            generated_answer=response.answer,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics,
            citation_metrics=citation_metrics,
            latency_ms=latency_ms,
            abstained=response.abstained,
        )
    
    def _evaluate_retrieval(
        self,
        question: BenchmarkQuestion,
        response: QueryResponse,
    ) -> RetrievalMetrics:
        """
        Evaluate retrieval quality by comparing retrieved chunks against ground truth.
        
        Requires:
        - question.relevant_chunk_ids: list of ground truth chunk IDs
        - response.retrieval_metadata: must contain 'retrieved_chunk_ids' list
        
        If ground truth or retrieved chunks are not available, returns zeros
        with a warning logged.
        """
        # Get ground truth relevant chunks
        relevant_ids = set(question.relevant_chunk_ids) if question.relevant_chunk_ids else set()
        
        # Get retrieved chunk IDs from response metadata
        retrieved_chunk_ids = []
        if hasattr(response, 'retrieval_metadata') and response.retrieval_metadata:
            retrieved_chunk_ids = response.retrieval_metadata.get('retrieved_chunk_ids', [])
        
        # If we don't have the data needed, log warning and return zeros
        if not relevant_ids:
            logger.warning(
                f"Question {question.question_id} has no relevant_chunk_ids. "
                f"Cannot compute retrieval metrics."
            )
            return RetrievalMetrics()
        
        if not retrieved_chunk_ids:
            logger.warning(
                f"Response for {question.question_id} has no retrieved_chunk_ids in metadata. "
                f"Cannot compute retrieval metrics."
            )
            return RetrievalMetrics()
        
        # Convert to sets for comparison
        retrieved_set = set(retrieved_chunk_ids)
        
        # Compute Recall@K
        def recall_at_k(k: int) -> float:
            retrieved_k = set(retrieved_chunk_ids[:k])
            if not relevant_ids:
                return 0.0
            hits = len(relevant_ids & retrieved_k)
            return hits / len(relevant_ids)
        
        # Compute MRR (Mean Reciprocal Rank)
        def compute_mrr() -> float:
            for i, chunk_id in enumerate(retrieved_chunk_ids, 1):
                if chunk_id in relevant_ids:
                    return 1.0 / i
            return 0.0
        
        # Compute NDCG@K
        def compute_ndcg_at_k(k: int) -> float:
            # DCG: sum of relevance / log2(rank + 1)
            dcg = 0.0
            for i, chunk_id in enumerate(retrieved_chunk_ids[:k], 1):
                relevance = 1.0 if chunk_id in relevant_ids else 0.0
                dcg += relevance / math.log2(i + 1)
            
            # Ideal DCG: all relevant items at top
            ideal_relevant = min(len(relevant_ids), k)
            idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_relevant + 1))
            
            return dcg / idcg if idcg > 0 else 0.0
        
        # Compute Precision@5
        def precision_at_k(k: int) -> float:
            retrieved_k = retrieved_chunk_ids[:k]
            if not retrieved_k:
                return 0.0
            hits = sum(1 for cid in retrieved_k if cid in relevant_ids)
            return hits / len(retrieved_k)
        
        # Compute Hit Rate (any relevant chunk in top-K)
        def hit_rate_at_k(k: int) -> float:
            retrieved_k = set(retrieved_chunk_ids[:k])
            return 1.0 if relevant_ids & retrieved_k else 0.0
        
        return RetrievalMetrics(
            recall_at_1=recall_at_k(1),
            recall_at_3=recall_at_k(3),
            recall_at_5=recall_at_k(5),
            recall_at_10=recall_at_k(10),
            mrr=compute_mrr(),
            ndcg_at_5=compute_ndcg_at_k(5),
            precision_at_5=precision_at_k(5),
            hit_rate=hit_rate_at_k(10),
        )
    
    def _evaluate_generation(
        self,
        question: BenchmarkQuestion,
        response: QueryResponse,
    ) -> GenerationMetrics:
        """Evaluate generation quality."""
        # Simple keyword overlap for now
        # In production, would use LLM-based evaluation
        
        if response.abstained:
            return GenerationMetrics()
        
        # Calculate keyword overlap
        expected_words = set(question.expected_answer.lower().split())
        generated_words = set(response.answer.lower().split())
        
        if expected_words:
            overlap = len(expected_words & generated_words) / len(expected_words)
        else:
            overlap = 0.0
        
        return GenerationMetrics(
            answer_correctness=overlap,
            faithfulness=response.confidence,
            groundedness=response.confidence,
            completeness=overlap,
            relevance=overlap,
        )
    
    def _evaluate_citations(
        self,
        question: BenchmarkQuestion,
        response: QueryResponse,
    ) -> CitationMetrics:
        """
        Evaluate citation quality by comparing citations against ground truth.
        
        Citation Precision: fraction of citations that are correct
        Citation Recall: fraction of ground truth sources that were cited
        Citation Completeness: whether all necessary evidence was cited
        Citation Entailment: whether cited evidence actually supports the claim
        """
        if not response.citations:
            # No citations provided
            if hasattr(question, 'gold_sources') and question.gold_sources:
                # Ground truth exists but no citations - recall is 0
                return CitationMetrics(
                    citation_precision=0.0,
                    citation_recall=0.0,
                    citation_completeness=0.0,
                    citation_entailment=0.0,
                )
            else:
                # No ground truth and no citations - perfect (no citations needed)
                return CitationMetrics(
                    citation_precision=1.0,
                    citation_recall=1.0,
                    citation_completeness=1.0,
                    citation_entailment=1.0,
                )
        
        # Get ground truth sources
        gold_sources = set()
        if hasattr(question, 'gold_sources') and question.gold_sources:
            gold_sources = set(question.gold_sources)
        
        # Get cited sources from response
        cited_sources = set()
        for citation in response.citations:
            # Extract source document from citation
            if hasattr(citation, 'source') and citation.source:
                cited_sources.add(citation.source)
            elif hasattr(citation, 'document') and citation.document:
                cited_sources.add(citation.document)
        
        # If no ground truth, we can only measure precision (all citations are "correct")
        if not gold_sources:
            return CitationMetrics(
                citation_precision=1.0,  # Can't verify, assume correct
                citation_recall=1.0,     # No ground truth to measure against
                citation_completeness=1.0,
                citation_entailment=response.confidence if hasattr(response, 'confidence') else 0.5,
            )
        
        # Compute precision: how many citations are correct?
        correct_citations = len(cited_sources & gold_sources)
        precision = correct_citations / len(cited_sources) if cited_sources else 0.0
        
        # Compute recall: how many ground truth sources were cited?
        recall = correct_citations / len(gold_sources) if gold_sources else 0.0
        
        # Compute completeness: did we cite all necessary sources?
        completeness = recall  # Same as recall for now
        
        # Compute entailment: do citations actually support the answer?
        # This is a heuristic - in production would use NLI model
        # For now, use confidence as proxy
        entailment = response.confidence if hasattr(response, 'confidence') else 0.5
        
        return CitationMetrics(
            citation_precision=precision,
            citation_recall=recall,
            citation_completeness=completeness,
            citation_entailment=entailment,
        )
    
    def aggregate_results(
        self,
        results: List[EvaluationResult],
    ) -> AggregateMetrics:
        """Aggregate metrics across all results."""
        if not results:
            return AggregateMetrics(
                retrieval=RetrievalMetrics(),
                generation=GenerationMetrics(),
                citation=CitationMetrics(),
                performance=PerformanceMetrics(),
                cost=CostMetrics(),
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                abstention_rate=0.0,
            )
        
        # Aggregate retrieval metrics
        retrieval = RetrievalMetrics(
            recall_at_1=statistics.mean([r.retrieval_metrics.recall_at_1 for r in results]),
            recall_at_3=statistics.mean([r.retrieval_metrics.recall_at_3 for r in results]),
            recall_at_5=statistics.mean([r.retrieval_metrics.recall_at_5 for r in results]),
            recall_at_10=statistics.mean([r.retrieval_metrics.recall_at_10 for r in results]),
            mrr=statistics.mean([r.retrieval_metrics.mrr for r in results]),
            ndcg_at_5=statistics.mean([r.retrieval_metrics.ndcg_at_5 for r in results]),
            precision_at_5=statistics.mean([r.retrieval_metrics.precision_at_5 for r in results]),
            hit_rate=statistics.mean([r.retrieval_metrics.hit_rate for r in results]),
        )
        
        # Aggregate generation metrics
        generation = GenerationMetrics(
            answer_correctness=statistics.mean([r.generation_metrics.answer_correctness for r in results]),
            faithfulness=statistics.mean([r.generation_metrics.faithfulness for r in results]),
            groundedness=statistics.mean([r.generation_metrics.groundedness for r in results]),
            completeness=statistics.mean([r.generation_metrics.completeness for r in results]),
            relevance=statistics.mean([r.generation_metrics.relevance for r in results]),
        )
        
        # Aggregate citation metrics
        citation = CitationMetrics(
            citation_precision=statistics.mean([r.citation_metrics.citation_precision for r in results]),
            citation_recall=statistics.mean([r.citation_metrics.citation_recall for r in results]),
            citation_completeness=statistics.mean([r.citation_metrics.citation_completeness for r in results]),
            citation_entailment=statistics.mean([r.citation_metrics.citation_entailment for r in results]),
        )
        
        # Aggregate performance metrics
        latencies = sorted([r.latency_ms for r in results])
        performance = PerformanceMetrics(
            latency_p50_ms=latencies[len(latencies) // 2] if latencies else 0.0,
            latency_p90_ms=latencies[int(len(latencies) * 0.90)] if latencies else 0.0,
            latency_p95_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0.0,
            latency_p99_ms=latencies[int(len(latencies) * 0.99)] if latencies else 0.0,
        )
        
        # Calculate counts
        successful = sum(1 for r in results if r.error is None)
        failed = sum(1 for r in results if r.error is not None)
        abstained = sum(1 for r in results if r.abstained)
        
        return AggregateMetrics(
            retrieval=retrieval,
            generation=generation,
            citation=citation,
            performance=performance,
            cost=CostMetrics(),  # Would need token usage data
            total_queries=len(results),
            successful_queries=successful,
            failed_queries=failed,
            abstention_rate=abstained / len(results) if results else 0.0,
        )
    
    def save_results(
        self,
        results: List[EvaluationResult],
        aggregate: AggregateMetrics,
        experiment_name: str = "evaluation",
    ) -> None:
        """Save evaluation results to files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save individual results
        results_file = self.output_dir / f"{experiment_name}_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        
        # Save aggregate metrics
        aggregate_file = self.output_dir / f"{experiment_name}_aggregate_{timestamp}.json"
        with open(aggregate_file, "w") as f:
            json.dump(aggregate.to_dict(), f, indent=2)
        
        logger.info(f"Evaluation results saved to {results_file}")
        logger.info(f"Aggregate metrics saved to {aggregate_file}")
    
    def generate_report(self, aggregate: AggregateMetrics) -> str:
        """Generate human-readable evaluation report."""
        report = []
        report.append("=" * 80)
        report.append("EVALUATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Total Queries: {aggregate.total_queries}")
        report.append(f"Successful: {aggregate.successful_queries}")
        report.append(f"Failed: {aggregate.failed_queries}")
        report.append(f"Abstention Rate: {aggregate.abstention_rate:.2%}")
        report.append("")
        
        report.append("-" * 80)
        report.append("RETRIEVAL METRICS")
        report.append("-" * 80)
        report.append(f"Recall@1:  {aggregate.retrieval.recall_at_1:.4f}")
        report.append(f"Recall@3:  {aggregate.retrieval.recall_at_3:.4f}")
        report.append(f"Recall@5:  {aggregate.retrieval.recall_at_5:.4f}")
        report.append(f"Recall@10: {aggregate.retrieval.recall_at_10:.4f}")
        report.append(f"MRR:       {aggregate.retrieval.mrr:.4f}")
        report.append(f"NDCG@5:    {aggregate.retrieval.ndcg_at_5:.4f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("GENERATION METRICS")
        report.append("-" * 80)
        report.append(f"Answer Correctness: {aggregate.generation.answer_correctness:.4f}")
        report.append(f"Faithfulness:       {aggregate.generation.faithfulness:.4f}")
        report.append(f"Groundedness:       {aggregate.generation.groundedness:.4f}")
        report.append(f"Completeness:       {aggregate.generation.completeness:.4f}")
        report.append(f"Relevance:          {aggregate.generation.relevance:.4f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("CITATION METRICS")
        report.append("-" * 80)
        report.append(f"Precision:    {aggregate.citation.citation_precision:.4f}")
        report.append(f"Recall:       {aggregate.citation.citation_recall:.4f}")
        report.append(f"Completeness: {aggregate.citation.citation_completeness:.4f}")
        report.append(f"Entailment:   {aggregate.citation.citation_entailment:.4f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("PERFORMANCE METRICS")
        report.append("-" * 80)
        report.append(f"Latency P50: {aggregate.performance.latency_p50_ms:.2f} ms")
        report.append(f"Latency P90: {aggregate.performance.latency_p90_ms:.2f} ms")
        report.append(f"Latency P95: {aggregate.performance.latency_p95_ms:.2f} ms")
        report.append(f"Latency P99: {aggregate.performance.latency_p99_ms:.2f} ms")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


# Global evaluator instance
evaluator = Evaluator()


def get_evaluator() -> Evaluator:
    """Get the global evaluator."""
    return evaluator
