"""
src/reasoning/numerical.py — Numerical reasoning for financial QA.

Extracts numerical values from retrieved evidence and performs
programmatic calculations to avoid LLM arithmetic hallucination.

WHY: LLMs are notoriously unreliable at arithmetic. When a question
asks "what was the growth rate?" or "how did revenue change?", we
should extract the numbers programmatically and compute the answer
rather than trusting the LLM to do math.

This module:
1. Identifies numerical claims in retrieved chunks
2. Extracts values with their units and temporal context
3. Performs calculations (growth rates, differences, ratios)
4. Returns structured numerical evidence for the generator
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from src.core.models import TextChunk, RetrievalOutput

logger = logging.getLogger(__name__)


class NumericalOperation(str, Enum):
    EXTRACT = "extract"           # Just extract the number
    DIFFERENCE = "difference"     # A - B
    PERCENT_CHANGE = "pct_change" # (A - B) / B * 100
    RATIO = "ratio"               # A / B
    SUM = "sum"                   # A + B + ...
    COMPARE = "compare"           # A > B, A < B, A == B


@dataclass
class NumericalValue:
    """A numerical value extracted from text with context."""
    value: float
    unit: str                      # "$", "%", "million", "billion", etc.
    raw_text: str                  # original text span
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    temporal_context: Optional[str] = None  # "FY2024", "Q3 2023", etc.
    entity: Optional[str] = None  # "revenue", "operating margin", etc.


@dataclass
class NumericalResult:
    """Result of a numerical reasoning operation."""
    operation: NumericalOperation
    result: Optional[float] = None
    unit: str = ""
    confidence: float = 0.0
    source_values: list[NumericalValue] = field(default_factory=list)
    reasoning: str = ""
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Number extraction patterns
# ──────────────────────────────────────────────

# Matches: $12.5M, $1,234.56, 12.5%, 1,234 million, etc.
NUMBER_PATTERN = re.compile(
    r'(\$?\s*[\d,]+\.?\d*)\s*'
    r'(%|percent|million|mn|mn\.|billion|bn|bn\.|thousand|k|K|trillion)?'
)

# Temporal patterns
TEMPORAL_PATTERN = re.compile(
    r'(FY\s*20\d{2}|'           # FY2024
    r'fiscal\s+year\s+20\d{2}|' # fiscal year 2024
    r'Q[1-4]\s*(?:20\d{2})?|'   # Q1, Q3 2024
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+20\d{2}|'
    r'20\d{2})',                 # 2024
    re.IGNORECASE
)

# Financial entity patterns
ENTITY_PATTERN = re.compile(
    r'(revenue|sales|income|profit|loss|margin|expense|cost|'
    r'asset|liability|equity|cash|debt|ebitda|eps|'
    r'capital\s+expenditure|capex|capex|operating\s+income|'
    r'net\s+income|gross\s+profit|operating\s+margin|'
    r'return\s+on\s+equity|dividend)',
    re.IGNORECASE
)


class NumericalReasoner:
    """
    Extracts and computes with numerical values from retrieved evidence.

    Pipeline:
    1. Scan retrieved chunks for numerical values
    2. Associate each value with temporal context and entity
    3. Determine what operation is needed based on the question
    4. Perform the calculation programmatically
    5. Return structured result with source attribution
    """

    def extract_values(self, chunks: list[TextChunk]) -> list[NumericalValue]:
        """
        Extract all numerical values from a list of chunks.

        Each value is annotated with:
        - The numerical value (normalized to float)
        - Unit (dollars, percent, millions, etc.)
        - Temporal context (fiscal year, quarter)
        - Entity (revenue, margin, etc.)
        - Source location (chunk_id, page, document)
        """
        values = []

        for chunk in chunks:
            # Find all number matches in the chunk
            for match in NUMBER_PATTERN.finditer(chunk.content):
                raw_number = match.group(1).replace(",", "").replace("$", "").strip()
                unit = (match.group(2) or "").lower()

                try:
                    value = float(raw_number)
                except ValueError:
                    continue

                # Normalize units
                if unit in ("million", "mn", "mn."):
                    value *= 1_000_000
                    unit = "dollars"
                elif unit in ("billion", "bn", "bn."):
                    value *= 1_000_000_000
                    unit = "dollars"
                elif unit in ("thousand", "k"):
                    value *= 1_000
                    unit = "dollars"
                elif unit == "%":
                    unit = "percent"
                elif unit == "" and "$" in match.group(1):
                    unit = "dollars"

                # Extract temporal context from surrounding text
                # Look in a window around the match
                start = max(0, match.start() - 100)
                end = min(len(chunk.content), match.end() + 100)
                context_window = chunk.content[start:end]

                temporal_match = TEMPORAL_PATTERN.search(context_window)
                temporal = temporal_match.group(0) if temporal_match else None

                # Extract entity from surrounding text
                entity_match = ENTITY_PATTERN.search(context_window)
                entity = entity_match.group(0).lower() if entity_match else None

                values.append(NumericalValue(
                    value=value,
                    unit=unit,
                    raw_text=match.group(0),
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    temporal_context=temporal,
                    entity=entity,
                ))

        logger.info(f"Extracted {len(values)} numerical values from {len(chunks)} chunks")
        return values

    def compute_growth_rate(
        self, old_value: NumericalValue, new_value: NumericalValue
    ) -> NumericalResult:
        """
        Compute percentage growth rate: (new - old) / old * 100

        This is done programmatically to avoid LLM arithmetic errors.
        """
        if old_value.value == 0:
            return NumericalResult(
                operation=NumericalOperation.PERCENT_CHANGE,
                error="Cannot compute growth rate: old value is zero",
                source_values=[old_value, new_value],
            )

        growth = ((new_value.value - old_value.value) / abs(old_value.value)) * 100

        return NumericalResult(
            operation=NumericalOperation.PERCENT_CHANGE,
            result=round(growth, 2),
            unit="percent",
            confidence=0.95,  # high confidence — it's exact arithmetic
            source_values=[old_value, new_value],
            reasoning=(
                f"Growth rate = ({new_value.raw_text} - {old_value.raw_text}) "
                f"/ |{old_value.raw_text}| × 100 = {growth:.2f}%"
            ),
        )

    def compute_difference(
        self, value_a: NumericalValue, value_b: NumericalValue
    ) -> NumericalResult:
        """Compute absolute difference: A - B."""
        diff = value_a.value - value_b.value

        return NumericalResult(
            operation=NumericalOperation.DIFFERENCE,
            result=round(diff, 2),
            unit=value_a.unit,
            confidence=0.95,
            source_values=[value_a, value_b],
            reasoning=f"Difference = {value_a.raw_text} - {value_b.raw_text} = {diff:.2f}",
        )

    def compute_ratio(
        self, numerator: NumericalValue, denominator: NumericalValue
    ) -> NumericalResult:
        """Compute ratio: A / B."""
        if denominator.value == 0:
            return NumericalResult(
                operation=NumericalOperation.RATIO,
                error="Cannot compute ratio: denominator is zero",
                source_values=[numerator, denominator],
            )

        ratio = numerator.value / denominator.value

        return NumericalResult(
            operation=NumericalOperation.RATIO,
            result=round(ratio, 4),
            unit="ratio",
            confidence=0.95,
            source_values=[numerator, denominator],
            reasoning=f"Ratio = {numerator.raw_text} / {denominator.raw_text} = {ratio:.4f}",
        )

    def find_values_for_entity(
        self,
        values: list[NumericalValue],
        entity: str,
        temporal: Optional[str] = None,
    ) -> list[NumericalValue]:
        """
        Filter extracted values by entity and optionally by temporal context.

        This is critical for financial QA — we need to match the RIGHT
        number (e.g., "revenue in FY2024" not "revenue in FY2023").
        """
        filtered = [v for v in values if v.entity and entity.lower() in v.entity.lower()]

        if temporal:
            # Normalize temporal patterns for comparison
            temporal_norm = temporal.upper().replace(" ", "")
            temporal_filtered = [
                v for v in filtered
                if v.temporal_context and
                temporal_norm in v.temporal_context.upper().replace(" ", "")
            ]
            if temporal_filtered:
                return temporal_filtered

        return filtered

    def reason_about_question(
        self,
        question: str,
        chunks: list[TextChunk],
    ) -> Optional[NumericalResult]:
        """
        Analyze a question and perform the appropriate numerical reasoning.

        This is a rule-based approach that identifies:
        1. What entity is being asked about
        2. What temporal periods are involved
        3. What operation is needed (growth, difference, comparison)

        Returns None if the question doesn't require numerical reasoning.
        """
        question_lower = question.lower()

        # Check if this is a numerical question
        is_numerical = any(kw in question_lower for kw in [
            "revenue", "income", "profit", "margin", "growth",
            "change", "increase", "decrease", "percent", "%",
            "how much", "how many", "compare", "difference",
            "ratio", "rate", "total", "sum",
        ])

        if not is_numerical:
            return None

        # Extract values from chunks
        values = self.extract_values(chunks)
        if not values:
            return None

        # Determine entity
        entity_match = ENTITY_PATTERN.search(question)
        entity = entity_match.group(0).lower() if entity_match else None

        # Determine temporal periods
        temporal_matches = TEMPORAL_PATTERN.findall(question)

        # Determine operation
        if any(kw in question_lower for kw in ["growth", "change", "increase", "decrease", "rate"]):
            operation = NumericalOperation.PERCENT_CHANGE
        elif any(kw in question_lower for kw in ["difference", "compare"]):
            operation = NumericalOperation.DIFFERENCE
        elif any(kw in question_lower for kw in ["ratio", "proportion"]):
            operation = NumericalOperation.RATIO
        else:
            operation = NumericalOperation.EXTRACT

        # Find relevant values
        if entity:
            relevant_values = self.find_values_for_entity(values, entity)
        else:
            relevant_values = values

        if not relevant_values:
            return NumericalResult(
                operation=operation,
                error=f"No numerical values found for entity '{entity}'",
                reasoning="Could not find matching numerical evidence in retrieved chunks.",
            )

        # For growth/change, we need two temporal periods
        if operation == NumericalOperation.PERCENT_CHANGE and len(temporal_matches) >= 2:
            old_values = self.find_values_for_entity(values, entity or "", temporal_matches[0])
            new_values = self.find_values_for_entity(values, entity or "", temporal_matches[1])

            if old_values and new_values:
                return self.compute_growth_rate(old_values[0], new_values[0])

        # For difference, same logic
        if operation == NumericalOperation.DIFFERENCE and len(temporal_matches) >= 2:
            val_a = self.find_values_for_entity(values, entity or "", temporal_matches[0])
            val_b = self.find_values_for_entity(values, entity or "", temporal_matches[1])

            if val_a and val_b:
                return self.compute_difference(val_a[0], val_b[0])

        # Default: return extracted values
        return NumericalResult(
            operation=NumericalOperation.EXTRACT,
            source_values=relevant_values[:5],  # top 5
            confidence=0.7,
            reasoning=f"Found {len(relevant_values)} numerical values matching the query.",
        )
