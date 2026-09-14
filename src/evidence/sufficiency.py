"""
src/evidence/sufficiency.py — Evidence sufficiency assessment.

BEFORE generating an answer, we assess whether the retrieved evidence
is sufficient. This is the key mechanism for reducing hallucination.

The assessment considers:
1. Retrieval scores (are the top results actually relevant?)
2. Evidence agreement (do sources agree or contradict?)
3. Evidence coverage (does the evidence address the full question?)
4. Source quality (are sources from reliable sections?)
5. Contradiction presence (do sources disagree?)

If evidence is insufficient, the system can:
- Retrieve more evidence (adaptive retrieval)
- Change retrieval strategy
- Abstain (refuse to answer)

RESEARCH QUESTION: Does evidence sufficiency assessment reduce
hallucination without excessive false refusals?

Tested in EXP-11 (abstention impact).
"""

import logging
import re
from typing import Optional

from src.core.config import config
from src.core.models import (
    RetrievalOutput, EvidenceAssessment, Contradiction,
    QueryType, SupportLevel,
)

logger = logging.getLogger(__name__)


class EvidenceSufficiencyChecker:
    """
    Assesses whether retrieved evidence is sufficient to answer a query.

    This is NOT a simple threshold on retrieval score. It combines
    multiple signals to make a more robust determination.
    """

    def __init__(self):
        self.cfg = config.evidence

    def assess(
        self,
        query: str,
        retrieval: RetrievalOutput,
    ) -> EvidenceAssessment:
        """
        Assess evidence sufficiency.

        Returns EvidenceAssessment with:
        - is_sufficient: boolean
        - confidence: 0.0 to 1.0
        - recommendation: "answer", "retrieve_more", or "abstain"
        - contradictions: list of detected contradictions
        """
        if not retrieval.candidates:
            return EvidenceAssessment(
                is_sufficient=False,
                confidence=0.0,
                evidence_score=0.0,
                coverage=0.0,
                agreement=0.0,
                recommendation="abstain",
                reasoning="No candidates retrieved.",
            )

        # Signal 1: Retrieval score quality
        score_signal = self._assess_score_quality(retrieval)

        # Signal 2: Evidence agreement
        agreement_signal = self._assess_agreement(retrieval)

        # Signal 3: Evidence coverage
        coverage_signal = self._assess_coverage(query, retrieval)

        # Signal 4: Contradiction detection
        contradictions = self._detect_contradictions(retrieval)
        contradiction_signal = 1.0 - (len(contradictions) * 0.2)
        contradiction_signal = max(0.0, min(1.0, contradiction_signal))

        # Combine signals
        evidence_score = (
            score_signal * 0.35 +
            agreement_signal * 0.25 +
            coverage_signal * 0.25 +
            contradiction_signal * 0.15
        )

        # Determine recommendation
        if evidence_score >= self.cfg.min_evidence_score:
            recommendation = "answer"
            is_sufficient = True
        elif len(retrieval.candidates) < 5:
            recommendation = "retrieve_more"
            is_sufficient = False
        else:
            recommendation = "abstain"
            is_sufficient = False

        # Build reasoning
        reasoning = self._build_reasoning(
            score_signal, agreement_signal, coverage_signal,
            contradiction_signal, contradictions, recommendation,
        )

        return EvidenceAssessment(
            is_sufficient=is_sufficient,
            confidence=evidence_score,
            evidence_score=evidence_score,
            coverage=coverage_signal,
            agreement=agreement_signal,
            contradictions=[c.model_dump() for c in contradictions],
            recommendation=recommendation,
            reasoning=reasoning,
        )

    def _assess_score_quality(self, retrieval: RetrievalOutput) -> float:
        """
        Assess the quality of retrieval scores.

        High top-1 score + good score distribution = high quality.
        Low scores across the board = poor retrieval.
        """
        if not retrieval.candidates:
            return 0.0

        top_score = retrieval.candidates[0].score
        avg_score = sum(c.score for c in retrieval.candidates) / len(retrieval.candidates)

        # Normalize: scores above 0.7 are good, below 0.3 are poor
        top_normalized = min(top_score / 0.7, 1.0)
        avg_normalized = min(avg_score / 0.5, 1.0)

        return (top_normalized * 0.6 + avg_normalized * 0.4)

    def _assess_agreement(self, retrieval: RetrievalOutput) -> float:
        """
        Assess whether retrieved sources agree with each other.

        High agreement = sources tell a consistent story.
        Low agreement = sources may contradict or be irrelevant.

        Uses simple lexical overlap as a proxy for semantic agreement.
        A more sophisticated approach would use NLI models.
        """
        if len(retrieval.candidates) < 2:
            return 0.8  # single source, assume reasonable

        contents = [c.chunk.content.lower() for c in retrieval.candidates[:5]]

        # Compute pairwise overlap
        overlaps = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                words_i = set(contents[i].split())
                words_j = set(contents[j].split())
                if not words_i or not words_j:
                    continue
                overlap = len(words_i & words_j) / min(len(words_i), len(words_j))
                overlaps.append(overlap)

        if not overlaps:
            return 0.5

        avg_overlap = sum(overlaps) / len(overlaps)
        # Map overlap to agreement score (0.1 overlap → 0.5 agreement, 0.3 → 0.9)
        return min(avg_overlap * 3.0, 1.0)

    def _assess_coverage(self, query: str, retrieval: RetrievalOutput) -> float:
        """
        Assess how well the evidence covers the question.

        Uses keyword overlap as a simple proxy.
        A more sophisticated approach would use query decomposition.
        """
        query_words = set(query.lower().split())
        # Remove stop words
        stop_words = {"what", "is", "the", "how", "does", "why", "when", "where", "who", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or"}
        query_words -= stop_words

        if not query_words:
            return 0.5  # can't assess

        # Check how many query terms appear in retrieved content
        all_content = " ".join(c.chunk.content.lower() for c in retrieval.candidates)
        content_words = set(all_content.split())

        coverage = len(query_words & content_words) / len(query_words)
        return min(coverage * 1.5, 1.0)  # slight boost for partial coverage

    def _detect_contradictions(self, retrieval: RetrievalOutput) -> list[Contradiction]:
        """
        Detect contradictions between retrieved sources.

        Uses a simple heuristic: if two chunks from different documents
        contain the same entity but different numbers, flag as potential
        contradiction.

        A production system would use NLI (Natural Language Inference)
        models for more accurate contradiction detection.
        """
        contradictions = []
        candidates = retrieval.candidates[:5]

        # Look for numerical contradictions
        number_pattern = re.compile(r'\b(\d+\.?\d*)\s*(%|percent|million|billion|thousand)\b')

        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                ci = candidates[i].chunk
                cj = candidates[j].chunk

                # Only check cross-document contradictions
                if ci.document_id == cj.document_id:
                    continue

                nums_i = set(number_pattern.findall(ci.content))
                nums_j = set(number_pattern.findall(cj.content))

                # If same unit but different numbers, potential contradiction
                units_i = {u for _, u in nums_i}
                units_j = {u for _, u in nums_j}
                common_units = units_i & units_j

                for unit in common_units:
                    vals_i = {n for n, u in nums_i if u == unit}
                    vals_j = {n for n, u in nums_j if u == unit}
                    if vals_i != vals_j and vals_i and vals_j:
                        contradictions.append(Contradiction(
                            claim_a=f"Value: {', '.join(vals_i)} {unit}",
                            claim_b=f"Value: {', '.join(vals_j)} {unit}",
                            source_a=ci.filename,
                            source_b=cj.filename,
                            page_a=ci.page_number,
                            page_b=cj.page_number,
                            severity="major",
                        ))

        return contradictions

    def _build_reasoning(
        self,
        score: float,
        agreement: float,
        coverage: float,
        contradiction: float,
        contradictions: list[Contradiction],
        recommendation: str,
    ) -> str:
        """Build human-readable reasoning for the assessment."""
        parts = []

        if score < 0.3:
            parts.append("Low retrieval scores suggest poor relevance.")
        elif score < 0.5:
            parts.append("Moderate retrieval scores.")
        else:
            parts.append("Good retrieval scores.")

        if agreement < 0.3:
            parts.append("Sources show low agreement — may be unrelated.")
        elif agreement < 0.6:
            parts.append("Sources show moderate agreement.")

        if coverage < 0.3:
            parts.append("Evidence does not adequately cover the question.")

        if contradictions:
            parts.append(f"Detected {len(contradictions)} potential contradiction(s).")

        parts.append(f"Recommendation: {recommendation}.")

        return " ".join(parts)
