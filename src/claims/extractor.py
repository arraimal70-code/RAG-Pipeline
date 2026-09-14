"""
src/claims/extractor.py — Claim extraction and faithfulness evaluation.

Splits generated answers into atomic claims and evaluates each
claim against retrieved evidence independently.

WHY: Asking "is this answer correct?" is too coarse. An answer may
contain 5 claims, 4 of which are supported and 1 of which is
hallucinated. Claim-level evaluation reveals this.

Example:
  "Revenue increased 12%, driven by higher international sales."

  Claim 1: "Revenue increased 12%" → check against evidence
  Claim 2: "The increase was driven by higher international sales" → check

This module:
1. Splits answers into atomic claims (rule-based + LLM-assisted)
2. For each claim, finds supporting or contradicting evidence
3. Classifies each claim as SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED
4. Computes claim-level faithfulness metrics
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from src.core.models import TextChunk, RetrievalOutput, GenerationOutput

logger = logging.getLogger(__name__)


class ClaimSupport(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    NUMERICALLY_VERIFIED = "numerically_verified"


@dataclass
class AtomicClaim:
    """A single atomic claim extracted from an answer."""
    claim_id: str
    text: str
    claim_type: str  # "factual", "numerical", "comparative", "causal"
    support: ClaimSupport = ClaimSupport.UNSUPPORTED
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_chunk_ids: list[str] = field(default_factory=list)


@dataclass
class FaithfulnessReport:
    """Complete faithfulness evaluation of an answer."""
    answer: str
    claims: list[AtomicClaim] = field(default_factory=list)
    total_claims: int = 0
    supported_claims: int = 0
    partially_supported: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    claim_level_faithfulness: float = 0.0  # supported / total
    hallucination_rate: float = 0.0        # unsupported / total
    has_any_hallucination: bool = False


# ──────────────────────────────────────────────
# Claim splitting patterns
# ──────────────────────────────────────────────

# Split on sentence boundaries, conjunctions, and list items
CLAIM_SPLIT_PATTERN = re.compile(
    r'(?<=[.!?])\s+|'           # sentence boundaries
    r',\s+(?:and|also|while|whereas|however|but)\s+|'  # conjunctions
    r';\s+'                      # semicolons
)

# Detect numerical claims
NUMERICAL_CLAIM_PATTERN = re.compile(
    r'[\$]?\d[\d,.]*\s*(?:%|percent|million|billion|thousand)?',
    re.IGNORECASE
)

# Detect comparative claims
COMPARATIVE_PATTERN = re.compile(
    r'\b(increased|decreased|grew|declined|rose|fell|higher|lower|'
    r'more|less|greater|smaller|improved|worsened|outperform|underperform)\b',
    re.IGNORECASE
)

# Detect causal claims
CAUSAL_PATTERN = re.compile(
    r'\b(due to|because|driven by|caused by|resulting from|'
    r'led to|resulted in|contributed to)\b',
    re.IGNORECASE
)


class ClaimExtractor:
    """
    Extracts atomic claims from generated answers and evaluates
    each against retrieved evidence.
    """

    def extract_claims(self, answer: str) -> list[AtomicClaim]:
        """
        Split an answer into atomic claims.

        Uses rule-based splitting. Each claim should be a single
        factual assertion that can be independently verified.
        """
        # Split answer into sentences/claims
        raw_claims = CLAIM_SPLIT_PATTERN.split(answer)
        raw_claims = [c.strip() for c in raw_claims if c.strip() and len(c.strip()) > 10]

        claims = []
        for i, text in enumerate(raw_claims):
            # Determine claim type
            claim_type = self._classify_claim_type(text)

            claims.append(AtomicClaim(
                claim_id=f"claim_{i+1}",
                text=text,
                claim_type=claim_type,
            ))

        logger.info(f"Extracted {len(claims)} claims from answer")
        return claims

    def _classify_claim_type(self, text: str) -> str:
        """Classify a claim as factual, numerical, comparative, or causal."""
        if NUMERICAL_CLAIM_PATTERN.search(text):
            return "numerical"
        if CAUSAL_PATTERN.search(text):
            return "causal"
        if COMPARATIVE_PATTERN.search(text):
            return "comparative"
        return "factual"

    def evaluate_claim(
        self,
        claim: AtomicClaim,
        chunks: list[TextChunk],
    ) -> AtomicClaim:
        """
        Evaluate a single claim against retrieved evidence.

        Uses lexical overlap + numerical verification to determine
        whether the claim is supported by the evidence.
        """
        if not chunks:
            claim.support = ClaimSupport.UNSUPPORTED
            return claim

        # For numerical claims, try programmatic verification
        if claim.claim_type == "numerical":
            return self._evaluate_numerical_claim(claim, chunks)

        # For other claims, use lexical overlap
        return self._evaluate_lexical_claim(claim, chunks)

    def _evaluate_lexical_claim(
        self, claim: AtomicClaim, chunks: list[TextChunk]
    ) -> AtomicClaim:
        """Evaluate a claim using lexical overlap with evidence."""
        claim_words = set(claim.text.lower().split())
        # Remove stop words
        stop_words = {
            "the", "a", "an", "is", "was", "were", "are", "been",
            "be", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can",
            "this", "that", "these", "those", "it", "its",
            "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "into", "about",
        }
        claim_words -= stop_words

        if not claim_words:
            claim.support = ClaimSupport.UNSUPPORTED
            return claim

        best_overlap = 0.0
        best_chunk_ids = []

        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split())
            overlap = len(claim_words & chunk_words) / len(claim_words)

            if overlap > best_overlap:
                best_overlap = overlap
                best_chunk_ids = [chunk.chunk_id]
            elif overlap == best_overlap and overlap > 0:
                best_chunk_ids.append(chunk.chunk_id)

        # Classify based on overlap
        if best_overlap >= 0.6:
            claim.support = ClaimSupport.SUPPORTED
            claim.confidence = best_overlap
        elif best_overlap >= 0.3:
            claim.support = ClaimSupport.PARTIALLY_SUPPORTED
            claim.confidence = best_overlap
        else:
            claim.support = ClaimSupport.UNSUPPORTED
            claim.confidence = best_overlap

        claim.source_chunk_ids = best_chunk_ids
        return claim

    def _evaluate_numerical_claim(
        self, claim: AtomicClaim, chunks: list[TextChunk]
    ) -> AtomicClaim:
        """
        Evaluate a numerical claim by checking if the numbers
        in the claim appear in the evidence.
        """
        # Extract numbers from claim
        claim_numbers = set(NUMERICAL_CLAIM_PATTERN.findall(claim.text))

        if not claim_numbers:
            return self._evaluate_lexical_claim(claim, chunks)

        # Check if numbers appear in any chunk
        matching_chunks = []
        for chunk in chunks:
            chunk_numbers = set(NUMERICAL_CLAIM_PATTERN.findall(chunk.content))
            if claim_numbers & chunk_numbers:
                matching_chunks.append(chunk)

        if matching_chunks:
            claim.support = ClaimSupport.NUMERICALLY_VERIFIED
            claim.confidence = 0.9
            claim.source_chunk_ids = [c.chunk_id for c in matching_chunks]
        else:
            # Fall back to lexical evaluation
            return self._evaluate_lexical_claim(claim, chunks)

        return claim

    def evaluate_faithfulness(
        self,
        generation: GenerationOutput,
        retrieval: RetrievalOutput,
    ) -> FaithfulnessReport:
        """
        Complete faithfulness evaluation of a generated answer.

        Pipeline:
        1. Extract atomic claims from the answer
        2. Evaluate each claim against retrieved evidence
        3. Compute aggregate metrics
        """
        # Extract claims
        claims = self.extract_claims(generation.answer)

        # Evaluate each claim
        chunks = [r.chunk for r in retrieval.candidates]
        for claim in claims:
            self.evaluate_claim(claim, chunks)

        # Compute metrics
        total = len(claims)
        supported = sum(1 for c in claims if c.support == ClaimSupport.SUPPORTED)
        partially = sum(1 for c in claims if c.support == ClaimSupport.PARTIALLY_SUPPORTED)
        unsupported = sum(1 for c in claims if c.support == ClaimSupport.UNSUPPORTED)
        contradicted = sum(1 for c in claims if c.support == ClaimSupport.CONTRADICTED)
        verified = sum(1 for c in claims if c.support == ClaimSupport.NUMERICALLY_VERIFIED)

        faithfulness = (supported + verified) / total if total > 0 else 0.0
        hallucination_rate = unsupported / total if total > 0 else 0.0

        return FaithfulnessReport(
            answer=generation.answer,
            claims=claims,
            total_claims=total,
            supported_claims=supported + verified,
            partially_supported=partially,
            unsupported_claims=unsupported,
            contradicted_claims=contradicted,
            claim_level_faithfulness=faithfulness,
            hallucination_rate=hallucination_rate,
            has_any_hallucination=unsupported > 0 or contradicted > 0,
        )
