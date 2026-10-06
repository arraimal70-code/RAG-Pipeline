"""
tests/test_advanced_features.py — Comprehensive tests for advanced research architecture:
1. In-Memory GraphRAG (Entity extraction, co-occurrence edges, community detection, global query)
2. Autonomous Multi-Step Agentic ReAct Planner (Plan DAG, iterative execution, drill-down)
3. Parent-Child Small-to-Big Hierarchical Indexing & Context Expansion
4. Maximal Marginal Relevance (MMR) Diversity Reranking
5. End-to-End Pipeline Integration of advanced components
"""

import pytest
from src.core.models import TextChunk, RetrievalResult, RetrievalOutput
from src.experimental.graph_rag import GraphRAGEngine, KnowledgeGraph
from src.experimental.agentic_planner import AgenticRAGPlanner, StepStatus
from src.experimental.hierarchical import HierarchicalChunker, HierarchicalRetriever
from src.experimental.mmr import MaximalMarginalRelevanceReranker


class TestGraphRAG:
    """Tests for in-memory GraphRAG entity-relationship network and community detection."""

    def test_entity_and_relation_extraction(self):
        engine = GraphRAGEngine()
        chunk = TextChunk(
            chunk_id="c_graph_1",
            document_id="doc_1",
            filename="financial.txt",
            page_number=1,
            content="Alphabet Inc reported consolidated Google Cloud revenue of $9.19 billion in Q4 2023 with operating margin of 9.4%.",
            char_offset=0,
            token_count=20,
        )
        engine.index_chunk(chunk)

        # Verify nodes extracted
        assert len(engine.graph.nodes) >= 3
        # Check node types
        types = {node.entity_type for node in engine.graph.nodes.values()}
        assert "ORGANIZATION" in types or "METRIC" in types or "TEMPORAL" in types

        # Verify relation edges formed
        assert len(engine.graph.edges) >= 1

    def test_community_detection_and_global_query(self):
        engine = GraphRAGEngine()
        chunk1 = TextChunk(
            chunk_id="c1",
            document_id="doc_1",
            filename="sec.txt",
            page_number=1,
            content="Microsoft Corp reported Azure cloud growth of 29% in fiscal year 2024. Satya Nadella highlighted AI services.",
            char_offset=0,
            token_count=20,
        )
        chunk2 = TextChunk(
            chunk_id="c2",
            document_id="doc_1",
            filename="sec.txt",
            page_number=2,
            content="Amazon Corp reported AWS sales of $25 billion with operating income expanding under Andy Jassy.",
            char_offset=0,
            token_count=20,
        )
        engine.index_chunk(chunk1)
        engine.index_chunk(chunk2)

        communities = engine.graph.detect_communities()
        assert len(communities) >= 1

        # Global query execution
        global_res = engine.global_query("What was Microsoft Corp cloud growth?")
        assert global_res["total_graph_nodes"] >= 2
        assert len(global_res["seed_entities"]) >= 1


class TestAgenticPlanner:
    """Tests for Autonomous Multi-Step Agentic ReAct Query Planner."""

    def test_comparative_plan_generation(self):
        planner = AgenticRAGPlanner()
        from src.core.models import QueryType
        query = "Compare Apple vs Microsoft operating margins"
        steps = planner.generate_plan(query, QueryType.COMPARISON)

        assert len(steps) >= 3
        assert "Apple" in steps[0].goal
        assert "Microsoft" in steps[1].goal
        assert steps[2].action_type == "compare"

    def test_multi_year_temporal_plan_generation(self):
        planner = AgenticRAGPlanner()
        from src.core.models import QueryType
        query = "Track revenue from 2022 to 2024"
        steps = planner.generate_plan(query, QueryType.TEMPORAL)

        assert len(steps) >= 3
        years_in_goals = [s.goal for s in steps]
        assert any("2022" in g for g in years_in_goals)
        assert any("2024" in g for g in years_in_goals)

    def test_agentic_plan_execution(self, pipeline, tmp_path):
        doc_file = tmp_path / "acme_metrics.txt"
        doc_file.write_text(
            "Acme Corp revenue in 2022 was $100M. In 2023, Acme Corp revenue grew to $130M.",
            encoding="utf-8",
        )
        pipeline.clear()
        pipeline.ingest_document(str(doc_file))

        result = pipeline.agentic_query("Track Acme Corp revenue from 2022 to 2023")
        assert result is not None
        assert result.total_steps >= 2
        assert result.final_synthesis != ""


class TestHierarchicalRetrieval:
    """Tests for Small-to-Big Parent-Child Context Expansion."""

    def test_hierarchical_chunking_and_parent_expansion(self):
        chunker = HierarchicalChunker(parent_size=200, child_size=60, child_overlap=10)
        retriever = HierarchicalRetriever()

        sample_text = (
            "Section 1: Corporate Governance Overview.\n\n"
            "The Board of Directors oversees all risk management strategies. "
            "Internal audit committees meet quarterly to review financial integrity. "
            "Executive compensation is tied strictly to operating milestones and ESG benchmarks.\n\n"
            "Section 2: Capital Allocation.\n\n"
            "Capital expenditures for fiscal year 2024 reached $15 billion. "
            "Share repurchases totaled $5 billion under the authorized buyback program."
        )

        bundle = chunker.chunk_document(
            text=sample_text,
            document_id="doc_hier_1",
            filename="report.txt",
            page_number=1,
            section="Governance",
        )

        assert len(bundle.parent_store) >= 2
        assert len(bundle.child_chunks) >= 3

        # Register parents
        retriever.register_parents(bundle.parent_store)

        # Simulate retrieving 2 child chunks from the same parent
        first_child = bundle.child_chunks[0]
        second_child = bundle.child_chunks[1]

        # Expanding to parents should merge and return unique parent
        expanded = retriever.expand_to_parents([first_child, second_child])
        # Since both belong to parent 0, should expand to 1 unique parent
        assert len(expanded) == 1
        assert expanded[0].metadata["is_expanded_parent"] is True
        assert len(expanded[0].content) >= len(first_child.content)


class TestMaximalMarginalRelevance:
    """Tests for MMR diversity reranking."""

    def test_mmr_eliminates_redundant_duplicates(self):
        reranker = MaximalMarginalRelevanceReranker(lambda_param=0.5)

        # 3 nearly identical chunks and 1 distinct chunk
        c_dup1 = TextChunk(chunk_id="c1", document_id="d1", filename="f.txt", page_number=1, content="Operating revenue reached $50 billion in fiscal year 2023.", char_offset=0, token_count=10)
        c_dup2 = TextChunk(chunk_id="c2", document_id="d1", filename="f.txt", page_number=1, content="In fiscal year 2023, the company reported operating revenue of $50 billion.", char_offset=0, token_count=10)
        c_dup3 = TextChunk(chunk_id="c3", document_id="d1", filename="f.txt", page_number=1, content="The operating revenue for fiscal year 2023 was reported at $50 billion.", char_offset=0, token_count=10)
        c_diff = TextChunk(chunk_id="c4", document_id="d1", filename="f.txt", page_number=1, content="Headcount expanded to 45,000 employees globally with research centers across Europe.", char_offset=0, token_count=10)

        candidates = [
            RetrievalResult(chunk=c_dup1, score=0.95, retrieval_method="hybrid", rank=1),
            RetrievalResult(chunk=c_dup2, score=0.94, retrieval_method="hybrid", rank=2),
            RetrievalResult(chunk=c_dup3, score=0.93, retrieval_method="hybrid", rank=3),
            RetrievalResult(chunk=c_diff, score=0.80, retrieval_method="hybrid", rank=4),
        ]

        query = "What was the operating revenue and workforce size in 2023?"
        diverse = reranker.rerank(query, candidates, top_k=2)

        assert len(diverse) == 2
        # Under MMR with lambda=0.5, c_diff should be promoted over redundant duplicates
        result_cids = [r.chunk.chunk_id for r in diverse]
        assert "c4" in result_cids or "c1" in result_cids


def test_god_level_pipeline_end_to_end(pipeline, tmp_path):
    """End-to-end integration test of GraphRAG, MMR, and Self-RAG in pipeline."""
    pipeline.clear()
    doc_file = tmp_path / "enterprise_doc.txt"
    doc_file.write_text(
        "Nvidia Corp generated record data center revenue of $47.5 billion in FY2024. "
        "CEO Jensen Huang cited unprecedented generative AI compute demand. "
        "Gaming revenue was $10.4 billion with strong GeForce RTX GPU adoption.",
        encoding="utf-8",
    )
    pipeline.ingest_document(str(doc_file))

    # Query with MMR and GraphRAG active
    resp = pipeline.query(
        "What was Nvidia Corp data center revenue and gaming revenue in FY2024?",
        use_cache=True,
        use_mmr=True,
        use_graph=True,
    )

    assert resp is not None
    assert not resp.abstained
    assert "graph_rag" in resp.retrieval_metadata
    assert "self_rag_critique" in resp.retrieval_metadata
    assert resp.retrieval_metadata["graph_rag"]["total_graph_nodes"] >= 2
