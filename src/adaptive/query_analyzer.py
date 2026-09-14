"""
src/adaptive/query_analyzer.py — Query classification for adaptive retrieval.

Classifies queries into types that map to retrieval strategies:
- EXACT (names, numbers, IDs) → lexical-heavy (BM25)
- CONCEPTUAL (abstract ideas) → semantic-heavy (dense)
- TECHNICAL (domain terms) → balanced hybrid
- AMBIGUOUS (unclear intent) → expanded retrieval
- MULTI_HOP (multi-passage) → broader candidates + reranking
- COMPARISON (compare entities) → multi-document retrieval

WHY: Different query types benefit from different retrieval strategies.
A query like "What is the revenue in Q3 2024?" needs lexical matching.
A query like "How does the methodology compare to prior work?" needs
semantic understanding. Using one strategy for all queries leaves
retrieval quality on the table.

This is experimentally validated in EXP-06 (adaptive vs fixed hybrid).
"""

import re
import logging
from typing import Optional
from src.core.models import QueryType

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Classifies queries to inform adaptive retrieval strategy.

    Design decisions:
    - Uses rule-based classification (fast, deterministic, debuggable)
    - NOT using an LLM for classification (adds latency, cost, noise)
    - Rules are derived from IR literature and empirical observation
    - Falls back to UNKNOWN (balanced hybrid) when uncertain
    """

    # Patterns indicating exact/lexical queries
    EXACT_PATTERNS = [
        r'\b\d{4}\b',                    # years (2024, 2023)
        r'\$[\d,.]+',                      # dollar amounts
        r'\b\d+[%]\b',                    # percentages
        r'\bQ[1-4]\b',                     # quarters
        r'\b(page|chapter|section)\s+\d+', # specific locations
        r'\b(who|what year|how many|how much)\b',  # factoid questions
    ]

    # Patterns indicating conceptual queries
    CONCEPTUAL_PATTERNS = [
        r'\b(how does|why does|explain|describe|what is)\b',
        r'\b(relationship|impact|effect|influence)\b',
        r'\b(methodology|approach|framework|theory)\b',
    ]

    # Patterns indicating multi-hop
    MULTI_HOP_PATTERNS = [
        r'\b(compare|versus|vs\.?|difference)\b',
        r'\b(both|each|respectively)\b',
        r'\b(changed|improved|evolved)\b.*\b(between|from.*to)\b',
    ]

    # Patterns indicating ambiguity
    AMBIGUOUS_PATTERNS = [
        r'\b(it|they|this|that|the)\b.*\b(mean|refer|about)\b',
        r'\?$.*\bor\b',  # "X or Y?" questions
    ]

    def classify(self, query: str) -> QueryType:
        """
        Classify a query into a type for adaptive retrieval.

        Returns QueryType enum value.
        Falls back to UNKNOWN if no strong signal detected.
        """
        query_lower = query.lower()
        scores = {
            QueryType.EXACT: 0,
            QueryType.CONCEPTUAL: 0,
            QueryType.MULTI_HOP: 0,
            QueryType.AMBIGUOUS: 0,
        }

        # Score each type based on pattern matches
        for pattern in self.EXACT_PATTERNS:
            if re.search(pattern, query_lower):
                scores[QueryType.EXACT] += 2

        for pattern in self.CONCEPTUAL_PATTERNS:
            if re.search(pattern, query_lower):
                scores[QueryType.CONCEPTUAL] += 2

        for pattern in self.MULTI_HOP_PATTERNS:
            if re.search(pattern, query_lower):
                scores[QueryType.MULTI_HOP] += 2

        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, query_lower):
                scores[QueryType.AMBIGUOUS] += 2

        # Check for numerical content (strong exact signal)
        if re.search(r'\b\d+\.?\d*\b', query):
            scores[QueryType.EXACT] += 1

        # Check for proper nouns (likely exact lookup)
        if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', query):
            scores[QueryType.EXACT] += 1

        # Determine winner
        max_score = max(scores.values())
        if max_score == 0:
            return QueryType.UNKNOWN

        # Check for ties — if multiple types score equally, use hybrid
        top_types = [t for t, s in scores.items() if s == max_score]
        if len(top_types) > 1:
            return QueryType.UNKNOWN  # ambiguous → balanced hybrid

        winner = max(scores, key=scores.get)
        logger.debug(f"Query classified as {winner.value} (scores: {scores})")
        return winner

    def get_retrieval_weights(self, query_type: QueryType) -> dict[str, float]:
        """
        Map query type to optimal dense/BM25 weight ratio.

        These weights are starting points. They should be tuned
        experimentally (see EXP-06).
        """
        weight_map = {
            QueryType.EXACT: {"dense": 0.3, "bm25": 0.7},      # lexical-heavy
            QueryType.CONCEPTUAL: {"dense": 0.8, "bm25": 0.2},  # semantic-heavy
            QueryType.TECHNICAL: {"dense": 0.5, "bm25": 0.5},   # balanced
            QueryType.AMBIGUOUS: {"dense": 0.5, "bm25": 0.5},   # balanced
            QueryType.MULTI_HOP: {"dense": 0.6, "bm25": 0.4},   # slightly semantic
            QueryType.COMPARISON: {"dense": 0.5, "bm25": 0.5},  # balanced
            QueryType.UNKNOWN: {"dense": 0.5, "bm25": 0.5},     # balanced default
        }
        return weight_map.get(query_type, weight_map[QueryType.UNKNOWN])

    def get_candidate_multiplier(self, query_type: QueryType) -> int:
        """
        How many candidates to retrieve based on query type.

        Multi-hop and ambiguous queries need broader retrieval.
        Exact queries can be more precise.
        """
        multipliers = {
            QueryType.EXACT: 1,
            QueryType.CONCEPTUAL: 1,
            QueryType.TECHNICAL: 1,
            QueryType.AMBIGUOUS: 2,      # retrieve more for ambiguous
            QueryType.MULTI_HOP: 2,      # need broader coverage
            QueryType.COMPARISON: 2,     # multi-document
            QueryType.UNKNOWN: 1,
        }
        return multipliers.get(query_type, 1)
