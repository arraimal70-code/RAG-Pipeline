"""
src/evaluation/ragas_runner.py — Automated RAGAS Framework for Frontier RAG Benchmarking.

Evaluates Frontier Tier-1 RAG pipelines across the 4 foundational dimensions:
1. Faithfulness: Entailment ratio of generated assertions grounded in retrieved contexts (via NLI).
2. Answer Relevancy: Semantic alignment between user query and generated response.
3. Context Precision: Signal-to-noise ratio and rank order of relevant contexts.
4. Context Recall: Proportion of ground-truth reference facts recovered in retrieval.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from src.claims.nli_verifier import NLIRelation, NLIVerifier
from src.embeddings.embedder import DeterministicTermVectorEmbedder

logger = logging.getLogger(__name__)


@dataclass
class RAGASDatasetItem:
    """A benchmark item for RAGAS evaluation."""
    question: str
    contexts: list[str]
    answer: str
    ground_truth: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGASItemScores:
    """Individual scores for a single evaluation item."""
    question: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall_score: float
    latency_ms: float = 0.0


@dataclass
class RAGASEvaluationResult:
    """Aggregated scorecard for a dataset evaluation run."""
    total_samples: int
    mean_faithfulness: float
    mean_answer_relevancy: float
    mean_context_precision: float
    mean_context_recall: float
    overall_score: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    item_scores: list[RAGASItemScores] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "mean_faithfulness": round(self.mean_faithfulness, 4),
            "mean_answer_relevancy": round(self.mean_answer_relevancy, 4),
            "mean_context_precision": round(self.mean_context_precision, 4),
            "mean_context_recall": round(self.mean_context_recall, 4),
            "overall_score": round(self.overall_score, 4),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
        }


class RAGASRunner:
    """
    Automated RAGAS Evaluator supporting standalone NLI and embedding-based scoring.
    """

    def __init__(self) -> None:
        self.nli_verifier = NLIVerifier()
        self.embedder = DeterministicTermVectorEmbedder(dimension=384)

    def compute_faithfulness(self, answer: str, contexts: list[str]) -> float:
        """
        Calculates Faithfulness:
        Fraction of atomic statements in the answer that are entailed by context.
        """
        if not answer or not contexts:
            return 0.0

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(s.strip()) > 10]
        if not sentences:
            return 1.0

        full_context = " ".join(contexts)
        entailed_count = 0

        for s in sentences:
            pred = self.nli_verifier.predict(premise=full_context, hypothesis=s)
            if pred.relation == NLIRelation.ENTAILMENT and pred.confidence >= 0.5:
                entailed_count += 1

        return round(entailed_count / len(sentences), 4)

    def compute_answer_relevancy(self, question: str, answer: str) -> float:
        """
        Calculates Answer Relevancy:
        Cosine similarity between question and answer semantic embeddings.
        """
        if not question or not answer:
            return 0.0

        q_vec = self.embedder.embed_query(question)
        a_vec = self.embedder.embed_query(answer)

        # Dot product of unit-normalized vectors is cosine similarity
        sim = sum(a * b for a, b in zip(q_vec, a_vec, strict=False))
        # Scale to [0, 1] range
        relevancy = max(0.0, min(1.0, (sim + 1.0) / 2.0))
        return round(relevancy, 4)

    def compute_context_precision(self, question: str, contexts: list[str], ground_truth: str) -> float:
        """
        Calculates Context Precision:
        Average Precision (AP@K) of retrieved contexts containing ground truth answers.
        """
        if not contexts:
            return 0.0

        gt_terms = set(re.findall(r"\w+", ground_truth.lower()))
        if not gt_terms:
            return 1.0

        relevant_at_k: list[int] = []
        for c in contexts:
            c_terms = set(re.findall(r"\w+", c.lower()))
            overlap = len(gt_terms & c_terms) / len(gt_terms)
            relevant_at_k.append(1 if overlap >= 0.4 else 0)

        # Compute Mean Average Precision
        cum_relevant = 0
        precisions: list[float] = []
        for k, rel in enumerate(relevant_at_k, start=1):
            if rel:
                cum_relevant += 1
                precisions.append(cum_relevant / k)

        if not precisions:
            return 0.0

        return round(sum(precisions) / len(precisions), 4)

    def compute_context_recall(self, ground_truth: str, contexts: list[str]) -> float:
        """
        Calculates Context Recall:
        Fraction of ground truth sentences that can be attributed to retrieved context.
        """
        if not ground_truth:
            return 1.0
        if not contexts:
            return 0.0

        gt_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ground_truth) if len(s.strip()) > 8]
        if not gt_sentences:
            return 1.0

        full_context = " ".join(contexts)
        recalled_count = 0

        for gt_s in gt_sentences:
            pred = self.nli_verifier.predict(premise=full_context, hypothesis=gt_s)
            if pred.relation == NLIRelation.ENTAILMENT and pred.confidence >= 0.5:
                recalled_count += 1

        return round(recalled_count / len(gt_sentences), 4)

    def evaluate_item(self, item: RAGASDatasetItem) -> RAGASItemScores:
        """Evaluate a single test case across all 4 metrics."""
        start = time.time()
        faithfulness = self.compute_faithfulness(item.answer, item.contexts)
        relevancy = self.compute_answer_relevancy(item.question, item.answer)
        precision = self.compute_context_precision(item.question, item.contexts, item.ground_truth)
        recall = self.compute_context_recall(item.ground_truth, item.contexts)

        overall = round((faithfulness + relevancy + precision + recall) / 4.0, 4)
        latency = (time.time() - start) * 1000.0

        return RAGASItemScores(
            question=item.question,
            faithfulness=faithfulness,
            answer_relevancy=relevancy,
            context_precision=precision,
            context_recall=recall,
            overall_score=overall,
            latency_ms=latency,
        )

    def evaluate_dataset(self, dataset: list[RAGASDatasetItem]) -> RAGASEvaluationResult:
        """Run full evaluation suite across the entire benchmark dataset."""
        if not dataset:
            return RAGASEvaluationResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        scores: list[RAGASItemScores] = []
        latencies: list[float] = []

        for item in dataset:
            score = self.evaluate_item(item)
            scores.append(score)
            latencies.append(score.latency_ms)

        latencies.sort()
        n = len(latencies)
        p50 = latencies[int(0.50 * (n - 1))]
        p95 = latencies[int(0.95 * (n - 1))]
        p99 = latencies[int(0.99 * (n - 1))]

        mean_f = sum(s.faithfulness for s in scores) / n
        mean_r = sum(s.answer_relevancy for s in scores) / n
        mean_p = sum(s.context_precision for s in scores) / n
        mean_rec = sum(s.context_recall for s in scores) / n
        mean_overall = (mean_f + mean_r + mean_p + mean_rec) / 4.0

        return RAGASEvaluationResult(
            total_samples=n,
            mean_faithfulness=round(mean_f, 4),
            mean_answer_relevancy=round(mean_r, 4),
            mean_context_precision=round(mean_p, 4),
            mean_context_recall=round(mean_rec, 4),
            overall_score=round(mean_overall, 4),
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            item_scores=scores,
        )
