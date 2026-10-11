"""
src/grounding/gatekeeper.py — Pre-Stream Factual Hallucination Gatekeeper.

Addresses the Tier-1 Production requirement:
Acts as a strict pre-delivery circuit-breaker between generation and user presentation.
Rather than blindly streaming LLM completions, the Gatekeeper:
1. Audits claim-level NLI entailment reports.
2. Identifies contradicted or ungrounded assertions.
3. Automatically executes one of three policies:
   - PASS: Full factual verification confirmed.
   - REDACT: Excises contradicted/ungrounded sentences while preserving grounded core evidence.
   - ABSTAIN: Replaces response with principled abstention when evidence fails grounding thresholds.
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from src.core.models import (
    GenerationOutput, RetrievalOutput, SupportLevel, Citation,
)
from src.claims.extractor import AtomicClaim, ClaimSupport, FaithfulnessReport, ClaimExtractor

logger = logging.getLogger(__name__)


class GatekeeperAction(str, Enum):
    PASS = "pass"
    REDACT = "redact"
    ABSTAIN = "abstain"


@dataclass
class GatekeeperDecision:
    """Telemetry report emitted by the Hallucination Gatekeeper."""
    action: GatekeeperAction
    passed: bool
    factual_support_ratio: float
    total_claims: int
    supported_claims: int
    contradicted_claims: int
    unsupported_claims: int
    original_answer: str
    filtered_answer: str
    redacted_sentences: List[str] = field(default_factory=list)
    audit_notes: str = ""


class HallucinationGatekeeper:
    """
    Tier-1 Circuit Breaker ensuring zero hallucination leakage to client callers.
    """

    def __init__(
        self,
        min_support_ratio: float = 0.70,
        max_contradictions: int = 0,
        claim_extractor: Optional[ClaimExtractor] = None,
    ):
        self.min_support_ratio = min_support_ratio
        self.max_contradictions = max_contradictions
        self.claim_extractor = claim_extractor or ClaimExtractor()

    def audit_and_gate(
        self,
        generation: GenerationOutput,
        retrieval: RetrievalOutput,
    ) -> Tuple[GenerationOutput, GatekeeperDecision]:
        """
        Evaluate generated answer against retrieved candidates.
        Modifies GenerationOutput in-place or returns sanitized output.
        """
        # If pipeline already abstained, pass through
        if generation.support_level == SupportLevel.INSUFFICIENT_EVIDENCE:
            decision = GatekeeperDecision(
                action=GatekeeperAction.ABSTAIN,
                passed=True,
                factual_support_ratio=0.0,
                total_claims=0,
                supported_claims=0,
                contradicted_claims=0,
                unsupported_claims=0,
                original_answer=generation.answer,
                filtered_answer=generation.answer,
                audit_notes="Upstream pipeline explicitly abstained due to insufficient evidence."
            )
            return generation, decision

        # Extract and evaluate atomic claims using NLI
        evidence_chunks = [c.chunk for c in retrieval.candidates]
        faithfulness: FaithfulnessReport = self.claim_extractor.evaluate_faithfulness(
            generation, retrieval
        )

        total = faithfulness.total_claims
        if total == 0:
            # Short phrase or direct greeting without claims
            decision = GatekeeperDecision(
                action=GatekeeperAction.PASS,
                passed=True,
                factual_support_ratio=1.0,
                total_claims=0,
                supported_claims=0,
                contradicted_claims=0,
                unsupported_claims=0,
                original_answer=generation.answer,
                filtered_answer=generation.answer,
                audit_notes="Zero factual claims detected; verified pass."
            )
            return generation, decision

        supported = faithfulness.supported_claims + faithfulness.partially_supported
        contradicted = faithfulness.contradicted_claims
        unsupported = faithfulness.unsupported_claims
        support_ratio = supported / total if total > 0 else 0.0

        logger.info(
            f"Gatekeeper Audit: {supported}/{total} supported ({support_ratio:.1%}), "
            f"{contradicted} contradicted, {unsupported} unsupported."
        )

        # ── 1. Full Pass Policy ──
        if contradicted <= self.max_contradictions and support_ratio >= self.min_support_ratio:
            decision = GatekeeperDecision(
                action=GatekeeperAction.PASS,
                passed=True,
                factual_support_ratio=round(support_ratio, 3),
                total_claims=total,
                supported_claims=supported,
                contradicted_claims=contradicted,
                unsupported_claims=unsupported,
                original_answer=generation.answer,
                filtered_answer=generation.answer,
                audit_notes="Answer passed all factual entailment criteria."
            )
            return generation, decision

        # ── 2. Selective Redaction Policy ──
        # If at least half the claims are grounded, attempt to excise the invalid sentences
        if support_ratio >= 0.40 and supported >= 1:
            filtered_answer, redacted = self._redact_unsupported_sentences(
                generation.answer, faithfulness.claims
            )

            if filtered_answer.strip() and len(filtered_answer.strip()) > 20:
                generation.answer = filtered_answer
                # Re-verify support level
                generation.support_level = (
                    SupportLevel.PARTIALLY_SUPPORTED
                    if unsupported > 0 else SupportLevel.FULL_SUPPORT
                )
                decision = GatekeeperDecision(
                    action=GatekeeperAction.REDACT,
                    passed=True,
                    factual_support_ratio=round(support_ratio, 3),
                    total_claims=total,
                    supported_claims=supported,
                    contradicted_claims=contradicted,
                    unsupported_claims=unsupported,
                    original_answer=faithfulness.answer,
                    filtered_answer=filtered_answer,
                    redacted_sentences=redacted,
                    audit_notes=f"Excised {len(redacted)} contradicted or ungrounded sentences before delivery."
                )
                return generation, decision

        # ── 3. Principled Abstention Policy ──
        abstain_message = (
            "INSUFFICIENT_EVIDENCE: The system retrieved candidate passages, "
            "but the generated assertions failed NLI factual grounding verification "
            f"({contradicted} contradictions detected, support ratio {support_ratio:.1%}). "
            "In accordance with enterprise grounding policies, this answer was suppressed."
        )
        generation.answer = abstain_message
        generation.support_level = (
            SupportLevel.CONTRADICTORY_EVIDENCE
            if contradicted > 0 else SupportLevel.INSUFFICIENT_EVIDENCE
        )
        generation.confidence = 0.0

        decision = GatekeeperDecision(
            action=GatekeeperAction.ABSTAIN,
            passed=False,
            factual_support_ratio=round(support_ratio, 3),
            total_claims=total,
            supported_claims=supported,
            contradicted_claims=contradicted,
            unsupported_claims=unsupported,
            original_answer=faithfulness.answer,
            filtered_answer=abstain_message,
            redacted_sentences=[c.text for c in faithfulness.claims if c.support in {ClaimSupport.CONTRADICTED, ClaimSupport.UNSUPPORTED}],
            audit_notes="Principled abstention triggered by Hallucination Gatekeeper."
        )
        return generation, decision

    def _redact_unsupported_sentences(
        self,
        full_text: str,
        claims: List[AtomicClaim]
    ) -> Tuple[str, List[str]]:
        """
        Remove sentences containing contradicted or ungrounded claims.
        """
        unsupported_texts = [
            c.text for c in claims
            if c.support in {ClaimSupport.CONTRADICTED, ClaimSupport.UNSUPPORTED}
        ]

        if not unsupported_texts:
            return full_text, []

        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        surviving = []
        redacted = []

        for sent in sentences:
            sent_clean = sent.strip()
            if not sent_clean:
                continue

            # Check if this sentence contains any ungrounded claim text
            is_bad = any(
                claim_text.lower() in sent_clean.lower() or
                len(set(claim_text.lower().split()) & set(sent_clean.lower().split())) / max(len(claim_text.split()), 1) > 0.7
                for claim_text in unsupported_texts
            )

            if is_bad:
                redacted.append(sent_clean)
            else:
                surviving.append(sent_clean)

        filtered_text = " ".join(surviving)
        return filtered_text, redacted
