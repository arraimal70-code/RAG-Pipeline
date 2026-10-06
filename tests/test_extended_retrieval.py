r"""
tests/test_extended_retrieval.py — Verification and resilience test suite for extended retrieval methods:
1. ColBERT-style Late-Interaction Token MaxSim Scoring & Alignments
2. Rocchio & RM3 Pseudo-Relevance Feedback (PRF) with Anti-Drift Guardrails
3. Conversational Coreference Normalizer & Relative Temporal Grounder
4. Markdown Table & Matrix Linearization Engine
5. High-concurrency query execution across retrieval modules
6. Adversarial malformed table payloads, unicode handling, and edge-case inputs
"""

import os
import re
import sys
import time
import uuid
import pytest
import concurrent.futures
from typing import List

from src.pipeline import RAGPipeline
from src.core.models import TextChunk, RetrievalResult, QueryType
from src.experimental.late_interaction import LateInteractionScorer, TokenAlignment
from src.experimental.prf import PseudoRelevanceFeedbackEngine
from src.adaptive.query_rewriter import QueryRewriter
from src.parsing.table_parser import TableParser, ParsedTable
from src.embeddings.embedder import DeterministicTermVectorEmbedder


@pytest.fixture
def late_scorer():
    return LateInteractionScorer(dimension=128)


@pytest.fixture
def prf_engine():
    embedder = DeterministicTermVectorEmbedder(dimension=384)
    return PseudoRelevanceFeedbackEngine(embedder=embedder, min_cosine_guardrail=0.60)


@pytest.fixture
def query_rewriter():
    return QueryRewriter(default_anchor_year=2024)


@pytest.fixture
def table_parser():
    return TableParser()


@pytest.fixture
def clean_pipeline():
    pipeline = RAGPipeline()
    pipeline.clear()
    return pipeline


# ══════════════════════════════════════════════════════════════════
# 1. ColBERT Late-Interaction Token MaxSim Tests
# ══════════════════════════════════════════════════════════════════
class TestLateInteractionMaxSim:
    def test_exact_match_yields_top_maxsim(self, late_scorer):
        query = "NVIDIA TensorRT GPU acceleration"
        passage = "NVIDIA TensorRT provides deep learning inference GPU acceleration."
        score = late_scorer.compute_maxsim(query, passage)
        assert score.normalized_score > 0.85
        assert len(score.alignments) == 4
        # Verify alignment for NVIDIA
        nvidia_align = next(a for a in score.alignments if a.query_token.lower() == "nvidia")
        assert nvidia_align.matched_doc_token.lower() == "nvidia"
        assert nvidia_align.similarity_score >= 0.99

    def test_disjoint_vocabulary_yields_low_score(self, late_scorer):
        query = "quantum entanglement photon spins"
        passage = "culinary recipes for baking chocolate sourdough bread"
        score = late_scorer.compute_maxsim(query, passage)
        assert score.normalized_score < 0.35

    def test_empty_and_whitespace_inputs(self, late_scorer):
        s1 = late_scorer.compute_maxsim("", "some passage")
        assert s1.normalized_score == 0.0
        assert s1.raw_score == 0.0

        s2 = late_scorer.compute_maxsim("query", "")
        assert s2.normalized_score == 0.0

    def test_reranking_discriminates_fine_grained_keywords(self, late_scorer):
        query = "H100 SXM5 floating point precision"
        # Candidate 1: Generic GPU talk
        c1 = RetrievalResult(
            chunk=TextChunk(
                document_id="doc1",
                filename="f1.txt",
                page_number=1,
                content="Standard graphic cards render video frames with high display rate.",
            ),
            score=0.70,
            retrieval_method="hybrid",
            rank=1,
        )
        # Candidate 2: Specific H100 SXM5 precision match
        c2 = RetrievalResult(
            chunk=TextChunk(
                document_id="doc2",
                filename="f2.txt",
                page_number=1,
                content="The H100 SXM5 accelerator delivers unprecedented FP8 floating point precision.",
            ),
            score=0.65,
            retrieval_method="hybrid",
            rank=2,
        )

        reranked = late_scorer.rerank(query, [c1, c2], top_k=2, alpha=0.3)
        assert reranked[0].chunk.document_id == "doc2"
        assert reranked[0].score > reranked[1].score
        assert "maxsim_score" in reranked[0].chunk.metadata


# ══════════════════════════════════════════════════════════════════
# 2. Rocchio PRF & Drift Guardrail Tests
# ══════════════════════════════════════════════════════════════════
class TestPseudoRelevanceFeedback:
    def test_prf_term_extraction_and_query_expansion(self, prf_engine):
        query = "transformer architecture"
        feedback_docs = [
            "Transformers rely on multi-head attention mechanisms and feed-forward sublayers.",
            "Attention mechanisms in transformer networks compute query-key dot products.",
        ]
        terms = prf_engine.extract_salient_terms(query, feedback_docs, top_m=4)
        assert len(terms) > 0
        extracted_words = [t[0] for t in terms]
        assert "attention" in extracted_words or "mechanisms" in extracted_words

    def test_prf_drift_guardrail_activates_on_adversarial_drift(self, prf_engine):
        query = "quarterly revenue EBITDA margin"
        # Malicious / off-topic feedback docs that would completely corrupt the query vector
        adversarial_docs = [
            RetrievalResult(
                chunk=TextChunk(
                    document_id="adv1",
                    filename="adv.txt",
                    page_number=1,
                    content="Paleolithic volcanic obsidian arrowheads found in deep subterranean caves.",
                ),
                score=0.9,
                retrieval_method="adversarial",
                rank=1,
            )
        ]
        # Force a very strict guardrail to trigger drift protection
        strict_prf = PseudoRelevanceFeedbackEngine(
            embedder=prf_engine.embedder,
            alpha=0.2,
            beta=0.8,
            min_cosine_guardrail=0.95,
        )
        res, exp_vec = strict_prf.expand_query(query, adversarial_docs)
        assert res.drift_guarded is True
        # Original query string preserved to avoid query poisoning
        assert res.expanded_query == query


# ══════════════════════════════════════════════════════════════════
# 3. Semantic Query Rewriter & Coreference Tests
# ══════════════════════════════════════════════════════════════════
class TestSemanticQueryRewriter:
    def test_coreference_resolution_with_dialogue_history(self, query_rewriter):
        history = [
            "Can you give me an overview of Microsoft Corporation's cloud performance?",
            "Microsoft reported substantial Azure revenue growth across enterprise accounts.",
        ]
        query = "What was its operating income?"
        res = query_rewriter.rewrite(query, dialogue_history=history)
        assert res.is_rewritten is True
        assert "Microsoft" in res.rewritten_query
        assert any("its" == pair[0] for pair in res.coreferences_resolved)

    def test_explicit_context_entity_override(self, query_rewriter):
        query = "How much did the company spend on research and development?"
        res = query_rewriter.rewrite(query, context_entity="Apple")
        assert res.is_rewritten is True
        assert "Apple" in res.rewritten_query
        assert not re.search(r"\bthe company\b", res.rewritten_query, re.I)

    def test_relative_temporal_normalization(self, query_rewriter):
        query = "How much did operating margin increase last year?"
        # default_anchor_year = 2024 -> last year = 2023
        res = query_rewriter.rewrite(query, anchor_year=2024)
        assert res.is_rewritten is True
        assert "2023" in res.rewritten_query
        assert "last year" not in res.rewritten_query.lower()

    def test_domain_acronym_expansion(self, query_rewriter):
        query = "What was the firm EBITDA and ARR?"
        res = query_rewriter.rewrite(query, expand_acronyms=True)
        assert "Earnings Before Interest" in res.rewritten_query
        assert "Annual Recurring Revenue" in res.rewritten_query


# ══════════════════════════════════════════════════════════════════
# 4. Table & Matrix Linearization Tests
# ══════════════════════════════════════════════════════════════════
class TestTableMatrixLinearization:
    SAMPLE_TABLE = """
    # Financial Highlights
    | Metric | FY2021 | FY2022 | FY2023 |
    | :--- | :--- | :--- | :--- |
    | Revenue | $365.8B | $394.3B | $383.3B |
    | Net Income | $94.7B | $99.8B | $96.9B |
    | Operating Margin | 29.8% | 30.3% | 29.8% |
    """

    def test_table_parsing_structure(self, table_parser):
        tables = table_parser.parse_markdown_tables(self.SAMPLE_TABLE)
        assert len(tables) == 1
        tbl = tables[0]
        assert tbl.num_rows == 3
        assert tbl.num_cols == 4
        assert tbl.headers == ["Metric", "FY2021", "FY2022", "FY2023"]
        assert tbl.column_types["FY2023"] in ("currency", "numeric", "percentage")

    def test_linearized_triples_generation(self, table_parser):
        tables = table_parser.parse_markdown_tables(self.SAMPLE_TABLE)
        triples = tables[0].to_linearized_triples()
        assert len(triples) == 3
        assert "[Row 1] Metric: Revenue | FY2021: $365.8B | FY2022: $394.3B | FY2023: $383.3B" in triples[0]
        assert "Margin" in triples[2]

    def test_document_augmentation_with_tables(self, table_parser):
        augmented = table_parser.linearize_document_tables(self.SAMPLE_TABLE)
        assert "--- [Linearized Table Representation #1] ---" in augmented
        assert "Semantic Row Records:" in augmented
        assert "[Row 1]" in augmented


# ══════════════════════════════════════════════════════════════════
# 5. Adversarial Malformed Table Payloads
# ══════════════════════════════════════════════════════════════════
class TestAdversarialTablePayloads:
    def test_zero_rows_table(self, table_parser):
        text = "| Col1 | Col2 |\n| --- | --- |"
        tables = table_parser.parse_markdown_tables(text)
        assert len(tables) == 1
        assert tables[0].num_rows == 0
        assert tables[0].to_linearized_triples() == []

    def test_mismatched_and_jagged_columns(self, table_parser):
        jagged = """
        | Header1 | Header2 | Header3 |
        |---|---|---|
        | Val1 | Val2 |
        | ValA | ValB | ValC | ExtraVal |
        | |||
        """
        tables = table_parser.parse_markdown_tables(jagged)
        assert len(tables) == 1
        assert tables[0].num_rows == 3
        triples = tables[0].to_linearized_triples()
        assert len(triples) >= 2

    def test_null_bytes_and_binary_blobs_in_tables(self, table_parser):
        binary_table = (
            "| Header \x00 Binary | Header2 |\n"
            "| --- | --- |\n"
            "| Cell \x1b\x00 Data | Normal Cell |\n"
        )
        augmented = table_parser.linearize_document_tables(binary_table)
        assert augmented is not None
        assert len(augmented) > 0


# ══════════════════════════════════════════════════════════════════
# 6. Full Integrated Pipeline with New Modules
# ══════════════════════════════════════════════════════════════════
class TestFullPipelineWithSOTAAdditions:
    def test_pipeline_with_maxsim_prf_and_rewriting(self, clean_pipeline, tmp_path):
        doc_path = tmp_path / "deepmind_report.txt"
        doc_path.write_text(
            """
            DeepMind Research Report 2023.
            Alphabet announced major breakthroughs in foundation models.
            The company reported operating revenue of $307 billion in FY2023.
            Alphabet's cloud division delivered $33.1 billion in revenue.
            
            | Segment | FY2022 | FY2023 |
            | :--- | :--- | :--- |
            | Google Cloud | $26.3B | $33.1B |
            | Google Services | $253.5B | $272.8B |
            """,
            encoding="utf-8",
        )

        clean_pipeline.ingest_document(str(doc_path))

        # Test conversational query needing coreference and PRF and MaxSim
        query = "What was its cloud revenue last year?"
        response = clean_pipeline.query(
            query,
            use_cache=False,
            use_maxsim=True,
            use_prf=True,
            use_rewriter=True,
            context_entity="Alphabet",
        )

        assert response is not None
        assert response.answer is not None
        assert "query_rewrite" in response.retrieval_metadata
        assert "late_interaction" in response.retrieval_metadata
        assert "prf" in response.retrieval_metadata


# ══════════════════════════════════════════════════════════════════
# 7. Brutal 30-Thread Concurrency Torture Test
# ══════════════════════════════════════════════════════════════════
class TestBrutalExtendedConcurrency:
    def test_concurrent_queries_under_full_sota_load(self, clean_pipeline, tmp_path):
        doc_path = tmp_path / "stress_doc.txt"
        doc_path.write_text(
            """
            Torture Test Corpus.
            Project Apex achieved 99.999% reliability across 50 global data centers.
            The server cluster consumed 4.2 megawatts with peak efficiency.
            Total annual operating expenditure was $18.4 million.
            """,
            encoding="utf-8",
        )
        clean_pipeline.ingest_document(str(doc_path))

        questions = [
            "What was the reliability of Project Apex?",
            "How much power in megawatts did the cluster consume?",
            "What was the annual operating expenditure?",
            "What was its peak reliability?",
            "Explain the efficiency of Project Apex.",
        ] * 6  # 30 concurrent queries

        def worker(q_idx: int) -> bool:
            q = questions[q_idx]
            resp = clean_pipeline.query(
                q,
                use_cache=True,
                use_maxsim=True,
                use_prf=True,
                use_rewriter=True,
                context_entity="Project Apex",
            )
            return resp.answer is not None and len(resp.answer) > 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(len(questions))]
            results = [f.result(timeout=60.0) for f in concurrent.futures.as_completed(futures)]

        assert all(results)
        assert len(results) == 30
