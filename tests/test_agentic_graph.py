"""
tests/test_agentic_graph.py — Unit test suite for Phase 5: Stateful Agentic & Corrective RAG (LangGraph).
"""

from src.agentic.rag_graph import FrontierRAGGraph


def test_rag_graph_happy_path():
    graph = FrontierRAGGraph()
    query = "What was the cloud revenue growth in fiscal year 2024?"

    sample_chunks = [
        {
            "chunk_id": "c-101",
            "document_id": "doc-alpha",
            "filename": "Alphabet_10K.pdf",
            "page_number": 4,
            "content": "Google Cloud revenue growth reached 28% in fiscal year 2024, driven by enterprise AI adoption.",
            "score": 0.88,
        }
    ]

    result = graph.run(query=query, retrieved_chunks=sample_chunks)

    assert result["evidence_grade"] == "sufficient"
    assert result["crag_action"] == "correct"
    assert result["final_response"] != ""
    assert "Alphabet_10K.pdf" in result["final_response"]
    assert len(result["citations"]) > 0
    assert result["hallucination_verdict"] == "pass"

    # Step trace verification
    trace = " -> ".join(result["step_trace"])
    assert "analyze_and_plan" in trace
    assert "retrieve_and_funnel" in trace
    assert "grade_documents" in trace
    assert "synthesize_and_ground" in trace
    assert "hallucination_gatekeeper" in trace


def test_rag_graph_rewrite_loop():
    graph = FrontierRAGGraph()
    query = "Could you please tell me about obscure unregistered tokenized securities?"

    # Run with empty initial chunks and max_retries=1
    result = graph.run(query=query, retrieved_chunks=[], max_retries=1)

    trace = " -> ".join(result["step_trace"])
    assert "rewrite_query" in trace
    assert result["retry_count"] >= 1
    assert result["rewritten_query"] is not None


def test_rag_graph_abstention():
    graph = FrontierRAGGraph()
    query = "Completely ungrounded fabricated query that cannot be answered."

    result = graph.run(query=query, retrieved_chunks=[], max_retries=0)

    assert result["hallucination_verdict"] == "abstain"
    assert "cannot answer" in result["final_response"].lower()
    trace = " -> ".join(result["step_trace"])
    assert "abstain" in trace


def test_rag_graph_budget_tracking():
    graph = FrontierRAGGraph()
    initial_budget = 4096
    result = graph.run(query="Standard query", retrieved_chunks=[], max_retries=0, token_budget=initial_budget)

    assert result["token_budget"] < initial_budget
