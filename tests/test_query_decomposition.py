"""
tests/test_query_decomposition.py — Unit tests for Stanford DSPy-style Query Decomposition.
"""

from src.adaptive.query_decomposer import QueryDecomposer


def test_atomic_query_no_decomposition():
    decomposer = QueryDecomposer()
    plan = decomposer.decompose("What is Alphabet's Q4 revenue?")
    assert not plan.is_multi_hop
    assert len(plan.sub_queries) == 1
    assert plan.sub_queries[0].sub_query == "What is Alphabet's Q4 revenue?"


def test_comparative_query_decomposition():
    decomposer = QueryDecomposer()
    query = "Compare the revenue of Apple and Microsoft"
    plan = decomposer.decompose(query)
    assert plan.is_multi_hop
    assert len(plan.sub_queries) == 2
    sub_texts = [sq.sub_query.lower() for sq in plan.sub_queries]
    assert any("apple" in s for s in sub_texts)
    assert any("microsoft" in s for s in sub_texts)


def test_versus_query_decomposition():
    decomposer = QueryDecomposer()
    query = "Google Cloud vs AWS growth rate"
    plan = decomposer.decompose(query)
    assert plan.is_multi_hop
    assert len(plan.sub_queries) == 2
    assert "google cloud" in plan.sub_queries[0].sub_query.lower()
    assert "aws" in plan.sub_queries[1].sub_query.lower()
