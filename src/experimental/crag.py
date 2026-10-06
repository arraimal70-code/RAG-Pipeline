"""
src/evidence/crag.py — Corrective RAG (CRAG) & Self-RAG Reflection Engine.

Implements:
1. Corrective RAG (Yan et al., 2024):
   - Evaluates retrieval confidence: CORRECT / AMBIGUOUS / INCORRECT
   - Knowledge Refinement: segments retrieved chunks into fine-grained strips and filters noise
2. Self-RAG Critique Tokens (Asai et al., ICLR 2024):
   - [ISREL] (Relevance assessment)
   - [ISSUP] (Grounding verification)
   - [ISUSE] (Utility rating)
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from src.core.models import TextChunk, RetrievalOutput, GenerationOutput

logger = logging.getLogger(__name__)


class CRAGAction(str, Enum):
    CORRECT = "correct"        # High confidence: refine knowledge strips
    AMBIGUOUS = "ambiguous"    # Medium confidence: expand retrieval / rewrite query
    INCORRECT = "incorrect"    # Low confidence: abstain or trigger fallback


@dataclass
class KnowledgeStrip:
    """A fine-grained, filtered strip of knowledge extracted from a retrieved chunk."""
    strip_id: str
    content: str
    relevance_score: float
    source_chunk_id: str


@dataclass
class SelfRAGCritique:
    """Self-RAG reflection tokens for generated output."""
    is_relevant: bool           # [ISREL]
    is_supported: bool          # [ISSUP]
    utility_score: float        # [ISUSE] (0.0 to 1.0)
    critique_notes: str = ""


@dataclass
class CRAGAssessment:
    """Complete Corrective RAG and Self-RAG evaluation."""
    action: CRAGAction
    confidence_score: float
    refined_strips: List[KnowledgeStrip] = field(default_factory=list)
    self_critique: Optional[SelfRAGCritique] = None
    query_rewrites: List[str] = field(default_factory=list)


class CorrectiveRAGEngine:
    """
    Evaluates retrieved evidence quality, strips out noise, and performs
    self-reflective critique on generated answers.
    """

    def __init__(self, high_threshold: float = 0.65, low_threshold: float = 0.35):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def evaluate_retrieval(self, query: str, retrieval: RetrievalOutput) -> CRAGAssessment:
        """
        Evaluate retrieved candidate quality according to CRAG decision boundary.
        """
        if not retrieval.candidates:
            return CRAGAssessment(
                action=CRAGAction.INCORRECT,
                confidence_score=0.0,
                refined_strips=[],
                query_rewrites=self._generate_query_rewrites(query),
            )

        top_score = max(c.score for c in retrieval.candidates)
        avg_score = sum(c.score for c in retrieval.candidates[:3]) / min(3, len(retrieval.candidates))
        combined_score = 0.6 * top_score + 0.4 * avg_score

        if combined_score >= self.high_threshold:
            action = CRAGAction.CORRECT
        elif combined_score >= self.low_threshold:
            action = CRAGAction.AMBIGUOUS
        else:
            action = CRAGAction.INCORRECT

        # Knowledge Refinement: break chunks into sentence strips and filter noise
        refined_strips = self._refine_knowledge_strips(query, retrieval.candidates)

        rewrites = self._generate_query_rewrites(query) if action != CRAGAction.CORRECT else []

        logger.info(f"CRAG Evaluation: action={action.value}, score={combined_score:.3f}, strips={len(refined_strips)}")
        return CRAGAssessment(
            action=action,
            confidence_score=round(combined_score, 4),
            refined_strips=refined_strips,
            query_rewrites=rewrites,
        )

    def _refine_knowledge_strips(self, query: str, candidates: list) -> List[KnowledgeStrip]:
        """
        Knowledge Refinement: Decompose chunks into sentence-level strips,
        compute lexical relevance to query, and discard irrelevant sentences.
        """
        q_tokens = set(re.findall(r'\w+', query.lower()))
        strips = []
        strip_idx = 1

        for c in candidates[:5]:
            text = c.chunk.content
            # Split into individual sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) < 20:
                    continue

                s_tokens = set(re.findall(r'\w+', s_clean.lower()))
                overlap = len(q_tokens & s_tokens) / max(len(q_tokens), 1)

                # Keep strips that have semantic overlap
                if overlap > 0.15 or c.score >= 0.8:
                    strips.append(KnowledgeStrip(
                        strip_id=f"strip_{strip_idx}",
                        content=s_clean,
                        relevance_score=overlap,
                        source_chunk_id=c.chunk.chunk_id,
                    ))
                    strip_idx += 1

        # Sort by relevance score
        strips.sort(key=lambda s: s.relevance_score, reverse=True)
        return strips[:10]

    def _generate_query_rewrites(self, query: str) -> List[str]:
        """Generate alternative query formulations for ambiguous/incorrect retrieval."""
        clean_q = query.strip().rstrip("?.")
        rewrites = [
            f"Detailed overview of {clean_q}",
            f"Official statistics and metrics regarding {clean_q}",
            f"{clean_q} summary and annual report disclosures",
        ]
        return rewrites

    def self_reflect_critique(
        self, query: str, answer: str, supporting_chunks: List[TextChunk]
    ) -> SelfRAGCritique:
        """
        Self-RAG post-generation critique.
        Evaluates [ISREL], [ISSUP], [ISUSE] tokens.
        """
        q_tokens = set(re.findall(r'\w+', query.lower()))
        a_tokens = set(re.findall(r'\w+', answer.lower()))

        # [ISREL] Check relevance of answer to query
        q_overlap = len(q_tokens & a_tokens) / max(len(q_tokens), 1)
        is_relevant = q_overlap >= 0.25

        # [ISSUP] Check if answer statements are supported by evidence
        evidence_text = " ".join(c.content.lower() for c in supporting_chunks)
        e_tokens = set(re.findall(r'\w+', evidence_text))

        supported_tokens = len(a_tokens & e_tokens)
        grounding_ratio = supported_tokens / max(len(a_tokens), 1)
        is_supported = grounding_ratio >= 0.60

        # [ISUSE] Utility score based on completeness, conciseness, and citations
        has_citations = "[CITE:" in answer or "chunk_" in answer
        utility = min(1.0, 0.4 * q_overlap + 0.4 * grounding_ratio + (0.2 if has_citations else 0.0))

        return SelfRAGCritique(
            is_relevant=is_relevant,
            is_supported=is_supported,
            utility_score=round(utility, 3),
            critique_notes=f"Grounding ratio: {grounding_ratio:.1%}, Query overlap: {q_overlap:.1%}, Citations: {has_citations}"
        )
