"""
tests/test_adaptive_retrieval.py — Tests proving adaptive retrieval works.

CRITICAL: These tests verify that adaptive retrieval ACTUALLY ADAPTS.
Different query types must produce different retrieval behavior.

This is the most important test in the system because it validates
the core research contribution.
"""

import pytest
from src.adaptive.query_analyzer import QueryAnalyzer
from src.adaptive.policy import PolicyGenerator, RetrievalPolicy
from src.core.models import QueryType


class TestAdaptiveRetrieval:
    """Test that adaptive retrieval actually adapts."""

    @pytest.fixture
    def analyzer(self):
        return QueryAnalyzer()

    @pytest.fixture
    def policy_generator(self):
        return PolicyGenerator()

    def test_numerical_query_gets_lexical_heavy_policy(self, analyzer, policy_generator):
        """Numerical queries should get lexical-heavy retrieval."""
        query = "What was the revenue in Q3 2024?"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Numerical queries should favor lexical (BM25)
        assert policy.lexical_weight > policy.dense_weight
        assert policy.query_type == QueryType.EXACT
        assert "lexical" in policy.reasoning.lower()

    def test_conceptual_query_gets_semantic_heavy_policy(self, analyzer, policy_generator):
        """Conceptual queries should get semantic-heavy retrieval."""
        query = "How does the methodology compare to prior work?"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Conceptual queries should favor semantic (dense)
        assert policy.dense_weight > policy.lexical_weight
        assert policy.query_type == QueryType.CONCEPTUAL
        assert "semantic" in policy.reasoning.lower()

    def test_multi_hop_query_gets_expanded_retrieval(self, analyzer, policy_generator):
        """Multi-hop queries should retrieve more candidates."""
        query = "Compare the results between 2023 and 2024"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Multi-hop queries should expand retrieval
        assert policy.retrieval_expansion > 1.0
        assert policy.dense_top_k > 50  # More than default
        assert policy.lexical_top_k > 50

    def test_ambiguous_query_gets_maximum_expansion(self, analyzer, policy_generator):
        """Ambiguous queries should get maximum retrieval expansion."""
        query = "What does it mean for the company?"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Ambiguous queries should expand retrieval the most
        assert policy.retrieval_expansion >= 1.5
        assert policy.dense_top_k >= 75

    def test_different_queries_produce_different_policies(self, analyzer, policy_generator):
        """CRITICAL: Different query types must produce different policies."""
        queries = [
            ("What was the revenue in 2024?", QueryType.EXACT),
            ("How does the methodology work?", QueryType.CONCEPTUAL),
            ("Compare Q1 and Q2 results", QueryType.MULTI_HOP),
        ]

        policies = []
        for query, expected_type in queries:
            query_type = analyzer.classify(query)
            policy = policy_generator.generate_policy(query_type, query)
            policies.append(policy)

        # Verify policies are different
        # Exact vs Conceptual should have different weights
        assert policies[0].dense_weight != policies[1].dense_weight
        assert policies[0].lexical_weight != policies[1].lexical_weight

        # Multi-hop should have expansion
        assert policies[2].retrieval_expansion > 1.0

    def test_policy_to_dict(self, policy_generator):
        """Policy should be serializable for logging/tracing."""
        policy = RetrievalPolicy(
            dense_weight=0.7,
            lexical_weight=0.3,
            dense_top_k=60,
            lexical_top_k=40,
            query_type=QueryType.CONCEPTUAL,
            reasoning="Test reasoning",
        )

        policy_dict = policy.to_dict()

        assert isinstance(policy_dict, dict)
        assert policy_dict["dense_weight"] == 0.7
        assert policy_dict["lexical_weight"] == 0.3
        assert policy_dict["query_type"] == "conceptual"
        assert policy_dict["reasoning"] == "Test reasoning"

    def test_policy_weights_sum_to_one(self, analyzer, policy_generator):
        """Policy weights should always sum to 1.0."""
        queries = [
            "What was the revenue?",
            "How does it work?",
            "Compare A and B",
            "What does it mean?",
        ]

        for query in queries:
            query_type = analyzer.classify(query)
            policy = policy_generator.generate_policy(query_type, query)

            # Weights should sum to 1.0 (with small tolerance for floating point)
            weight_sum = policy.dense_weight + policy.lexical_weight
            assert abs(weight_sum - 1.0) < 0.01, f"Weights sum to {weight_sum}, not 1.0"

    def test_mixed_query_gets_balanced_policy(self, analyzer, policy_generator):
        """Queries with both numerical and conceptual elements get balanced policy."""
        query = "How did the 15% revenue growth impact the operating margin in 2024?"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Mixed queries should be more balanced
        # (not heavily weighted to either side)
        weight_diff = abs(policy.dense_weight - policy.lexical_weight)
        assert weight_diff < 0.4  # Not too extreme

    def test_long_query_gets_expanded_retrieval(self, analyzer, policy_generator):
        """Long queries should get expanded retrieval."""
        query = "What were the main factors contributing to the increase in research and development expenses during the fiscal year 2024 compared to the previous year?"
        query_type = analyzer.classify(query)
        policy = policy_generator.generate_policy(query_type, query)

        # Long queries should expand retrieval
        assert policy.retrieval_expansion > 1.0


class TestPolicyGeneratorEdgeCases:
    """Test edge cases in policy generation."""

    @pytest.fixture
    def policy_generator(self):
        return PolicyGenerator()

    def test_unknown_query_type_gets_default_policy(self, policy_generator):
        """Unknown query types should get balanced default policy."""
        policy = policy_generator.generate_policy(QueryType.UNKNOWN, "some query")

        assert policy.dense_weight == 0.5
        assert policy.lexical_weight == 0.5
        assert policy.retrieval_expansion == 1.0

    def test_policy_with_base_config_override(self, policy_generator):
        """Policy generator should respect base config overrides."""
        base_config = {
            "dense_weight": 0.9,
            "lexical_weight": 0.1,
        }

        policy = policy_generator.generate_policy(
            QueryType.CONCEPTUAL,
            "test query",
            base_config=base_config,
        )

        # Base config should override defaults
        assert policy.dense_weight == 0.9
        assert policy.lexical_weight == 0.1

    def test_policy_preserves_query_type(self, policy_generator):
        """Policy should preserve the query type for tracing."""
        for query_type in [QueryType.EXACT, QueryType.CONCEPTUAL, QueryType.MULTI_HOP]:
            policy = policy_generator.generate_policy(query_type, "test")
            assert policy.query_type == query_type


class TestAdaptiveRetrievalIntegration:
    """Integration tests for adaptive retrieval."""

    def test_full_adaptive_pipeline(self):
        """Test that the full pipeline uses adaptive retrieval."""
        from src.pipeline import RAGPipeline
        from src.core.models import QueryType

        pipeline = RAGPipeline()

        # This test would require actual documents to be ingested
        # For now, we just verify the pipeline has the right components
        assert hasattr(pipeline, 'query_analyzer')
        assert hasattr(pipeline, 'retriever')

        # Verify the retriever accepts policy parameter
        import inspect
        sig = inspect.signature(pipeline.retriever.retrieve)
        params = list(sig.parameters.keys())
        assert 'policy' in params, "Retriever must accept policy parameter"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
