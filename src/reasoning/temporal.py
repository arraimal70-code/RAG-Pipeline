"""
src/reasoning/temporal.py — Temporal reasoning for financial QA.

Financial documents are inherently temporal — revenue figures belong to
specific fiscal years, quarters, and reporting periods. This module:

1. Extracts temporal context from chunks and queries
2. Aligns retrieved evidence with the question's temporal requirements
3. Detects temporal mismatches (e.g., returning FY2023 data for FY2024 question)
4. Orders evidence chronologically for temporal reasoning

WHY: A common failure mode in financial RAG is retrieving the CORRECT
number but for the WRONG period. "What was revenue in FY2024?" should
not return FY2023 revenue, even if the chunk is otherwise relevant.

This module prevents that class of errors.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.core.models import TextChunk, RetrievalOutput

logger = logging.getLogger(__name__)


class TemporalGranularity(str, Enum):
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    DAY = "day"
    UNKNOWN = "unknown"


@dataclass
class TemporalContext:
    """Parsed temporal information from text."""
    raw_text: str
    year: Optional[int] = None
    quarter: Optional[int] = None     # 1-4
    month: Optional[int] = None       # 1-12
    fiscal_year: Optional[str] = None  # "FY2024"
    granularity: TemporalGranularity = TemporalGranularity.UNKNOWN
    is_start_of_period: bool = False
    is_end_of_period: bool = False


@dataclass
class TemporalMatch:
    """Result of matching query temporal requirements against evidence."""
    chunk: TextChunk
    temporal_context: TemporalContext
    matches_query: bool
    match_quality: float  # 0.0 to 1.0
    mismatch_reason: Optional[str] = None


# ──────────────────────────────────────────────
# Temporal extraction patterns
# ──────────────────────────────────────────────

FISCAL_YEAR_PATTERN = re.compile(
    r'(?:FY|fiscal\s+year)\s*[-:]?\s*(20\d{2})',
    re.IGNORECASE
)

QUARTER_PATTERN = re.compile(
    r'Q([1-4])\s*(?:20\d{2})?',
    re.IGNORECASE
)

YEAR_PATTERN = re.compile(r'\b(20\d{2})\b')

MONTH_PATTERN = re.compile(
    r'(January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+(20\d{2})',
    re.IGNORECASE
)

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


class TemporalReasoner:
    """
    Handles temporal reasoning for financial document QA.

    Pipeline:
    1. Extract temporal context from the query
    2. Extract temporal context from each retrieved chunk
    3. Match query temporal requirements against chunk temporal context
    4. Score and filter chunks based on temporal alignment
    5. Order remaining chunks chronologically
    """

    def extract_temporal_context(self, text: str) -> list[TemporalContext]:
        """
        Extract all temporal references from text.

        Returns a list of TemporalContext objects, one for each
        temporal reference found.
        """
        contexts = []

        # Fiscal year (highest priority)
        for match in FISCAL_YEAR_PATTERN.finditer(text):
            year = int(match.group(1))
            contexts.append(TemporalContext(
                raw_text=match.group(0),
                year=year,
                fiscal_year=f"FY{year}",
                granularity=TemporalGranularity.YEAR,
            ))

        # Quarter
        for match in QUARTER_PATTERN.finditer(text):
            quarter = int(match.group(1))
            # Try to find year nearby
            year_match = YEAR_PATTERN.search(
                text[max(0, match.start()-20):match.end()+20]
            )
            year = int(year_match.group(1)) if year_match else None
            contexts.append(TemporalContext(
                raw_text=match.group(0),
                year=year,
                quarter=quarter,
                granularity=TemporalGranularity.QUARTER,
            ))

        # Month + Year
        for match in MONTH_PATTERN.finditer(text):
            month_name = match.group(1).lower()
            year = int(match.group(2))
            month = MONTH_NAMES.get(month_name)
            if month:
                contexts.append(TemporalContext(
                    raw_text=match.group(0),
                    year=year,
                    month=month,
                    granularity=TemporalGranularity.MONTH,
                ))

        # Standalone year (lowest priority — only if no other match)
        if not contexts:
            for match in YEAR_PATTERN.finditer(text):
                year = int(match.group(1))
                if 2000 <= year <= 2030:  # reasonable range
                    contexts.append(TemporalContext(
                        raw_text=match.group(0),
                        year=year,
                        granularity=TemporalGranularity.YEAR,
                    ))

        return contexts

    def extract_query_temporal_requirements(self, question: str) -> dict:
        """
        Determine what temporal information the question requires.

        Returns dict with:
        - required_year: specific year if mentioned
        - required_quarter: specific quarter if mentioned
        - temporal_comparison: whether comparing two periods
        - period_1, period_2: the two periods for comparison
        """
        question_lower = question.lower()
        result = {
            "required_year": None,
            "required_quarter": None,
            "temporal_comparison": False,
            "period_1": None,
            "period_2": None,
        }

        # Extract fiscal years
        fy_matches = FISCAL_YEAR_PATTERN.findall(question)
        years = [int(y) for y in fy_matches]

        # Extract quarters
        q_matches = QUARTER_PATTERN.findall(question)
        quarters = [int(q) for q in q_matches]

        # Extract standalone years
        year_matches = YEAR_PATTERN.findall(question)
        standalone_years = [int(y) for y in year_matches if 2000 <= int(y) <= 2030]

        all_years = years + standalone_years

        if len(all_years) >= 2:
            result["temporal_comparison"] = True
            result["period_1"] = all_years[0]
            result["period_2"] = all_years[1]
        elif len(all_years) == 1:
            result["required_year"] = all_years[0]

        if len(quarters) >= 1:
            result["required_quarter"] = quarters[0]

        return result

    def score_temporal_match(
        self,
        query_requirements: dict,
        chunk_temporal: list[TemporalContext],
    ) -> tuple[float, Optional[str]]:
        """
        Score how well chunk temporal context matches query requirements.

        Returns (score, mismatch_reason):
        - score: 0.0 (no match) to 1.0 (perfect match)
        - mismatch_reason: why the match is imperfect, if any
        """
        if not chunk_temporal:
            # No temporal info in chunk — can't verify, neutral score
            return 0.5, "No temporal context in chunk"

        if not query_requirements.get("required_year") and \
           not query_requirements.get("required_quarter") and \
           not query_requirements.get("temporal_comparison"):
            # Query doesn't specify temporal requirements
            return 1.0, None

        # Check year match
        if query_requirements.get("required_year"):
            required_year = query_requirements["required_year"]
            chunk_years = [tc.year for tc in chunk_temporal if tc.year]

            if required_year in chunk_years:
                year_score = 1.0
            else:
                year_score = 0.0
                return 0.0, f"Chunk contains years {chunk_years}, query requires {required_year}"
        else:
            year_score = 1.0

        # Check quarter match
        if query_requirements.get("required_quarter"):
            required_quarter = query_requirements["required_quarter"]
            chunk_quarters = [tc.quarter for tc in chunk_temporal if tc.quarter]

            if required_quarter in chunk_quarters:
                quarter_score = 1.0
            elif chunk_quarters:
                quarter_score = 0.0
                return 0.0, f"Chunk contains quarters {chunk_quarters}, query requires Q{required_quarter}"
            else:
                quarter_score = 0.5  # no quarter info, partial credit
        else:
            quarter_score = 1.0

        return year_score * quarter_score, None

    def filter_by_temporal_relevance(
        self,
        question: str,
        retrieval: RetrievalOutput,
    ) -> RetrievalOutput:
        """
        Filter and re-rank retrieval results based on temporal relevance.

        Chunks that match the query's temporal requirements are boosted.
        Chunks that mismatch are penalized or removed.
        """
        query_requirements = self.extract_query_temporal_requirements(question)

        # If query has no temporal requirements, return as-is
        if not any([
            query_requirements.get("required_year"),
            query_requirements.get("required_quarter"),
            query_requirements.get("temporal_comparison"),
        ]):
            return retrieval

        scored_candidates = []
        for candidate in retrieval.candidates:
            chunk = candidate.chunk
            chunk_temporal = self.extract_temporal_context(chunk.content)
            score, mismatch = self.score_temporal_match(query_requirements, chunk_temporal)

            if score > 0:  # keep chunks with any temporal match
                # Boost score by temporal match quality
                adjusted_score = candidate.score * (0.5 + 0.5 * score)
                scored_candidates.append((candidate, adjusted_score, score, mismatch))

        # Sort by adjusted score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Rebuild retrieval output
        from src.core.models import RetrievalResult
        new_candidates = []
        for rank, (candidate, adj_score, temp_score, mismatch) in enumerate(scored_candidates):
            new_candidates.append(RetrievalResult(
                chunk=candidate.chunk,
                score=adj_score,
                retrieval_method=candidate.retrieval_method + "+temporal",
                rank=rank,
            ))

        return RetrievalOutput(
            query=retrieval.query,
            candidates=new_candidates,
            total_candidates=len(new_candidates),
            retrieval_latency_ms=retrieval.retrieval_latency_ms,
            method_details={
                **retrieval.method_details,
                "temporal_filtering": {
                    "query_requirements": query_requirements,
                    "candidates_before": len(retrieval.candidates),
                    "candidates_after": len(new_candidates),
                },
            },
        )

    def order_chronologically(self, chunks: list[TextChunk]) -> list[TextChunk]:
        """
        Order chunks chronologically based on their temporal context.

        Useful for temporal reasoning questions like "how did X change over time?"
        """
        def get_sort_key(chunk: TextChunk) -> tuple:
            temporal = self.extract_temporal_context(chunk.content)
            if temporal:
                tc = temporal[0]  # use first temporal reference
                return (tc.year or 0, tc.quarter or 0, tc.month or 0)
            return (0, 0, 0)

        return sorted(chunks, key=get_sort_key)
