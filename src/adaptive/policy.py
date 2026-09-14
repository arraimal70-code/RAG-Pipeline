"""
src/adaptive/policy.py — Retrieval policy generation from query characteristics.

This module creates RetrievalPolicy objects that determine how retrieval
should be performed based on query type and characteristics.

WHY: Different query types benefit from different retrieval strategies.
A numerical query needs lexical-heavy retrieval. A conceptual query
needs semantic-heavy retrieval. This module translates query classification
into concrete retrieval parameters.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from src.core.models import QueryType

logger = logging.getLogger(__name__)


@dataclass
class RetrievalPolicy:
    """
    Concrete retrieval parameters for a specific query.
    
    This policy determines:
    - How much to weight dense vs lexical retrieval
    - How many candidates to retrieve
    - Whether to enable reranking
    - Whether to expand retrieval for ambiguous queries
    """
    # Fusion weights
    dense_weight: float = 0.5
    lexical_weight: float = 0.5
    
    # Candidate counts
    dense_top_k: int = 50
    lexical_top_k: int = 50
    post_fusion_top_k: int = 20
    
    # Reranking
    rerank_enabled: bool = True
    rerank_top_k: int = 5
    
    # Expansion for ambiguous/multi-hop queries
    retrieval_expansion: float = 1.0  # multiplier for top_k
    
    # Evidence threshold
    evidence_threshold: float = 0.3
    
    # Metadata
    query_type: QueryType = QueryType.UNKNOWN
    reasoning: str = ""
    
    def to_dict(self) -> dict:
        """Convert policy to dictionary for logging/tracing."""
        return {
            "dense_weight": self.dense_weight,
            "lexical_weight": self.lexical_weight,
            "dense_top_k": self.dense_top_k,
            "lexical_top_k": self.lexical_top_k,
            "post_fusion_top_k": self.post_fusion_top_k,
            "rerank_enabled": self.rerank_enabled,
            "rerank_top_k": self.rerank_top_k,
            "retrieval_expansion": self.retrieval_expansion,
            "evidence_threshold": self.evidence_threshold,
            "query_type": self.query_type.value,
            "reasoning": self.reasoning,
        }


class PolicyGenerator:
    """
    Generates RetrievalPolicy from query characteristics.
    
    This is the core of adaptive retrieval — translating query classification
    into concrete retrieval parameters.
    """
    
    # Default policies for each query type
    # These are starting points and should be tuned experimentally
    DEFAULT_POLICIES = {
        QueryType.EXACT: {
            "dense_weight": 0.3,
            "lexical_weight": 0.7,
            "reasoning": "Exact queries (names, numbers, IDs) benefit from lexical matching",
        },
        QueryType.CONCEPTUAL: {
            "dense_weight": 0.8,
            "lexical_weight": 0.2,
            "reasoning": "Conceptual queries benefit from semantic understanding",
        },
        QueryType.MULTI_HOP: {
            "dense_weight": 0.6,
            "lexical_weight": 0.4,
            "retrieval_expansion": 1.5,  # retrieve more candidates
            "reasoning": "Multi-hop queries need broader retrieval to find all relevant passages",
        },
        QueryType.AMBIGUOUS: {
            "dense_weight": 0.5,
            "lexical_weight": 0.5,
            "retrieval_expansion": 2.0,  # retrieve even more
            "reasoning": "Ambiguous queries need expanded retrieval to cover interpretations",
        },
        QueryType.COMPARISON: {
            "dense_weight": 0.5,
            "lexical_weight": 0.5,
            "retrieval_expansion": 1.5,
            "reasoning": "Comparison queries need balanced retrieval across entities",
        },
        QueryType.UNKNOWN: {
            "dense_weight": 0.5,
            "lexical_weight": 0.5,
            "reasoning": "Unknown query type uses balanced default",
        },
    }
    
    def generate_policy(
        self,
        query_type: QueryType,
        query: str,
        base_config: Optional[dict] = None,
    ) -> RetrievalPolicy:
        """
        Generate a RetrievalPolicy for the given query.
        
        Args:
            query_type: Classified query type
            query: Original query text (for additional analysis)
            base_config: Base configuration to override
            
        Returns:
            RetrievalPolicy with concrete parameters
        """
        # Start with defaults for this query type
        policy_dict = self.DEFAULT_POLICIES.get(query_type, self.DEFAULT_POLICIES[QueryType.UNKNOWN]).copy()
        
        # Apply base config if provided
        if base_config:
            policy_dict.update(base_config)
        
        # Create policy object
        policy = RetrievalPolicy(
            dense_weight=policy_dict.get("dense_weight", 0.5),
            lexical_weight=policy_dict.get("lexical_weight", 0.5),
            dense_top_k=int(50 * policy_dict.get("retrieval_expansion", 1.0)),
            lexical_top_k=int(50 * policy_dict.get("retrieval_expansion", 1.0)),
            post_fusion_top_k=20,
            rerank_enabled=policy_dict.get("rerank_enabled", True),
            rerank_top_k=5,
            retrieval_expansion=policy_dict.get("retrieval_expansion", 1.0),
            evidence_threshold=policy_dict.get("evidence_threshold", 0.3),
            query_type=query_type,
            reasoning=policy_dict.get("reasoning", ""),
        )
        
        # Additional adjustments based on query characteristics
        policy = self._adjust_for_query_characteristics(policy, query)
        
        logger.info(
            f"Generated policy for {query_type.value}: "
            f"dense={policy.dense_weight:.2f}, lexical={policy.lexical_weight:.2f}, "
            f"expansion={policy.retrieval_expansion:.2f}"
        )
        
        return policy
    
    def _adjust_for_query_characteristics(
        self,
        policy: RetrievalPolicy,
        query: str,
    ) -> RetrievalPolicy:
        """
        Make additional adjustments based on query characteristics.
        
        This is where we can add more sophisticated logic beyond
        simple query type classification.
        """
        query_lower = query.lower()
        
        # If query has both numerical and conceptual elements, use balanced approach
        has_numbers = any(c.isdigit() for c in query)
        has_conceptual = any(word in query_lower for word in [
            "how", "why", "explain", "describe", "relationship", "impact"
        ])
        
        if has_numbers and has_conceptual:
            # Mixed query — use balanced weights
            policy.dense_weight = 0.5
            policy.lexical_weight = 0.5
            policy.reasoning += " (adjusted: mixed numerical/conceptual)"
        
        # Very long queries might benefit from more expansion
        if len(query.split()) > 20:
            policy.retrieval_expansion *= 1.2
            policy.reasoning += " (adjusted: long query)"
        
        # Queries with multiple entities might need more candidates
        entity_indicators = ["compare", "versus", "vs", "between", "and"]
        if any(indicator in query_lower for indicator in entity_indicators):
            policy.retrieval_expansion *= 1.3
            policy.reasoning += " (adjusted: multiple entities)"
        
        return policy


# Global policy generator instance
policy_generator = PolicyGenerator()
