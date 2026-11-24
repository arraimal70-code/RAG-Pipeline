"""
tests/test_reranker.py — Unit test suite for Phase 4: High-Precision Reranking & Late Interaction.
"""

from src.retrieval.late_interaction import LateInteractionScorer
from src.retrieval.reranker import (
    BGEReranker,
    DeterministicReranker,
    MultiStageRerankerFunnel,
)


def test_colbert_maxsim_token_scoring():
    scorer = LateInteractionScorer(dimension=128)
    query = "Google Cloud revenue Q3 2024"
    doc_match = "Alphabet reported Google Cloud revenue growth of 28% in Q3 2024."
    doc_irrelevant = "The weather in Seattle during winter is predominantly rainy and overcast."

    res_match = scorer.compute_maxsim(query, doc_match)
    res_irrel = scorer.compute_maxsim(query, doc_irrelevant)

    assert res_match.normalized_score > res_irrel.normalized_score
    assert len(res_match.alignments) > 0
    # Check that key query terms have aligned doc tokens
    q_tokens = [a.query_token.lower() for a in res_match.alignments]
    assert "cloud" in q_tokens
    assert "revenue" in q_tokens


def test_deterministic_reranker_ordering():
    reranker = DeterministicReranker()
    query = "artificial intelligence infrastructure spending"

    candidates = [
        {"chunk_id": "c1", "content": "Consumer retail spending increased moderately.", "score": 0.5},
        {"chunk_id": "c2", "content": "Enterprise artificial intelligence infrastructure spending accelerated.", "score": 0.4},
        {"chunk_id": "c3", "content": "Unrelated agricultural commodity trends.", "score": 0.3},
    ]

    reranked = reranker.rerank(query, candidates, top_k=2)

    assert len(reranked) == 2
    assert reranked[0]["chunk_id"] == "c2"
    assert reranked[0]["score"] > reranked[1]["score"]


def test_bge_reranker_pipeline():
    reranker = BGEReranker()
    query = "operating cash flow"

    candidates = [
        {"chunk_id": "1", "content": "Free cash flow and operating cash flow reached records.", "score": 0.2},
        {"chunk_id": "2", "content": "Employee count remained steady across departments.", "score": 0.8},
    ]

    reranked = reranker.rerank(query, candidates, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["chunk_id"] == "1"


def test_multistage_reranker_funnel():
    funnel = MultiStageRerankerFunnel(
        colbert_prune_top_k=4,
        final_top_k=2,
        enable_compression=True,
    )

    query = "net interest margin"
    candidates = [
        {"chunk_id": f"c{i}", "content": f"Passage {i} discussing random corporate matters.", "score": 0.1 * i}
        for i in range(8)
    ]
    # Inject exact relevant candidate
    candidates.append({
        "chunk_id": "target_1",
        "content": "Net interest margin widened by 14 basis points due to central bank interest rate stabilization.",
        "score": 0.3,
    })

    result = funnel.execute_funnel(query, candidates)

    assert len(result) == 2
    assert result[0]["chunk_id"] == "target_1"
    assert "compressed_content" in result[0]
    assert len(result[0]["content"]) > 0
