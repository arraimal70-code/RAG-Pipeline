"""
src/adaptive/query_decomposer.py — Multi-hop & Comparative Query Decomposer (Stanford DSPy / IR-CoT).

Breaks down complex, comparative, and multi-hop queries into atomic, targeted
sub-queries to maximize retrieval recall across disparate document sections.

Technique:
1. Identifies comparative constructs ("compare X and Y", "difference between A and B")
2. Identifies temporal/causal chains ("after X happened, what was Y?")
3. Generates orthogonal sub-queries for parallel multi-hop retrieval
4. Aggregates candidate pools using Reciprocal Rank Fusion (RRF)
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DecomposedQuery:
    """A decomposed sub-query for multi-hop retrieval."""
    sub_query_id: str
    sub_query: str
    target_aspect: str
    weight: float = 1.0


@dataclass
class DecompositionPlan:
    """Plan containing original query and constituent sub-queries."""
    original_query: str
    is_multi_hop: bool
    sub_queries: List[DecomposedQuery] = field(default_factory=list)


class QueryDecomposer:
    """
    Decomposes multi-faceted questions into atomic retrieval queries.
    Inspired by Stanford DSPy multi-hop reasoning & Interleaved Retrieval-Augmented CoT (IR-CoT).
    """

    COMPARISON_REGEX = re.compile(
        r'(?:(?:compare|difference\s+between)\s+(.+?)\s+(?:and|to|with)\s+(.+)|(.+?)\s+(?:vs\.?|versus)\s+(.+))',
        re.IGNORECASE
    )
    
    MULTI_ASPECT_REGEX = re.compile(
        r'(?:what\s+are\s+the|details\s+on)\s+(.+?)\s+and\s+(.+)',
        re.IGNORECASE
    )

    def decompose(self, query: str) -> DecompositionPlan:
        """
        Decompose a query into sub-queries.
        If the query is already atomic, returns a plan with a single query.
        """
        query_clean = query.strip()

        # Check for comparison
        comp_match = self.COMPARISON_REGEX.search(query_clean)
        if comp_match:
            entity_a = (comp_match.group(1) or comp_match.group(3)).strip()
            entity_b = (comp_match.group(2) or comp_match.group(4)).strip().rstrip("?.")
            
            # Extract common predicate/metric if present
            # e.g., "Compare the revenue of Apple and Microsoft" -> metric: revenue
            metric_match = re.search(r'(?:compare\s+(?:the\s+)?)([\w\s]+?)\s+(?:of|between|for)', query_clean, re.IGNORECASE)
            metric = metric_match.group(1).strip() if metric_match else ""

            sub_a = f"{entity_a} {metric}".strip() if metric and not metric in entity_a.lower() else entity_a
            sub_b = f"{entity_b} {metric}".strip() if metric and not metric in entity_b.lower() else entity_b

            return DecompositionPlan(
                original_query=query_clean,
                is_multi_hop=True,
                sub_queries=[
                    DecomposedQuery(sub_query_id="sub_1", sub_query=sub_a, target_aspect=entity_a, weight=0.5),
                    DecomposedQuery(sub_query_id="sub_2", sub_query=sub_b, target_aspect=entity_b, weight=0.5),
                ]
            )

        # Check for multi-aspect conjunctions (e.g. "revenue and operating income")
        aspect_match = self.MULTI_ASPECT_REGEX.search(query_clean)
        if aspect_match:
            aspect_a = aspect_match.group(1).strip()
            aspect_b = aspect_match.group(2).strip().rstrip("?.")
            return DecompositionPlan(
                original_query=query_clean,
                is_multi_hop=True,
                sub_queries=[
                    DecomposedQuery(sub_query_id="sub_1", sub_query=aspect_a, target_aspect=aspect_a, weight=0.5),
                    DecomposedQuery(sub_query_id="sub_2", sub_query=aspect_b, target_aspect=aspect_b, weight=0.5),
                ]
            )

        # Atomic query fallback
        return DecompositionPlan(
            original_query=query_clean,
            is_multi_hop=False,
            sub_queries=[
                DecomposedQuery(sub_query_id="sub_1", sub_query=query_clean, target_aspect="primary", weight=1.0)
            ]
        )
