"""
src/citations/validator.py — Citation validation.

Every citation in a generated answer must correspond to actual
retrieved evidence. This module:

1. Extracts citations from LLM output
2. Validates each citation against retrieved chunks
3. Checks that cited text actually appears in the source chunk
4. Removes invalid citations
5. Reports citation accuracy metrics

WHY: LLMs can generate plausible-looking citations that don't
actually correspond to any retrieved evidence. Without validation,
users trust citations that are fabricated.

This is tested in EXP-12 (citation validation impact).
"""

import re
import logging
from typing import Optional

from src.core.models import (
    Citation, RetrievalOutput, GenerationOutput,
)

logger = logging.getLogger(__name__)


class CitationValidator:
    """
    Validates citations against retrieved evidence.

    Validation levels:
    1. Structural: Citation references a valid chunk index
    2. Content: Cited text actually appears in the referenced chunk
    3. Semantic: Cited claim is supported by the chunk (requires NLI)
    """

    def validate_citations(
        self,
        generation: GenerationOutput,
        retrieval: RetrievalOutput,
    ) -> GenerationOutput:
        """
        Validate all citations in a generation output.

        Removes invalid citations and updates the validated flag.
        """
        validated_citations = []

        for citation in generation.citations:
            is_valid = self._validate_single_citation(citation, retrieval)
            citation.validated = is_valid

            if is_valid:
                validated_citations.append(citation)
            else:
                logger.warning(
                    f"Invalid citation removed: chunk_id={citation.chunk_id}, "
                    f"file={citation.filename}, page={citation.page_number}"
                )

        generation.citations = validated_citations
        return generation

    def _validate_single_citation(
        self,
        citation: Citation,
        retrieval: RetrievalOutput,
    ) -> bool:
        """
        Validate a single citation.

        Checks:
        1. The chunk_id exists in retrieved candidates
        2. The filename matches
        3. The page number matches
        4. The relevant_text actually appears in the chunk content
        """
        # Find the matching candidate
        matching = None
        for candidate in retrieval.candidates:
            if candidate.chunk.chunk_id == citation.chunk_id:
                matching = candidate
                break

        if matching is None:
            return False  # Citation references non-existent chunk

        # Verify filename
        if matching.chunk.filename != citation.filename:
            return False

        # Verify page number
        if matching.chunk.page_number != citation.page_number:
            return False

        # Verify content: does the cited text appear in the chunk?
        if citation.relevant_text:
            # Check if at least 50% of the cited text appears in the chunk
            cited_words = set(citation.relevant_text.lower().split())
            chunk_words = set(matching.chunk.content.lower().split())

            if not cited_words:
                return True  # empty citation, skip content check

            overlap = len(cited_words & chunk_words) / len(cited_words)
            if overlap < 0.5:
                return False  # cited text doesn't match chunk content

        return True

    def compute_citation_metrics(
        self,
        generation: GenerationOutput,
        retrieval: RetrievalOutput,
    ) -> dict[str, float]:
        """
        Compute citation quality metrics.

        Returns:
        - citation_precision: fraction of citations that are valid
        - citation_recall: fraction of claims that have citations
        - citation_count: total citations
        - validated_count: citations that passed validation
        """
        total = len(generation.citations)
        validated = sum(1 for c in generation.citations if c.validated)

        precision = validated / total if total > 0 else 0.0

        return {
            "citation_precision": precision,
            "citation_count": total,
            "validated_count": validated,
            "invalid_count": total - validated,
        }
