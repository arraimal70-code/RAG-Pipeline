"""
tests/test_tier1_components.py — Production Test Suite for Tier-1 RAG Architecture.

Covers:
1. NLI Premise-Hypothesis Claim Verification (Entailment, Contradiction, Neutral)
2. Character-Span Citation Attribution & Alignment
3. Hallucination Gatekeeper Pre-Stream Gating Policies (Pass, Redact, Abstain)
4. Hierarchical Document AST & Small-to-Big Parent Document Context Extraction
5. Contextual Extractive Compression & Sentence Pruning
6. Knowledge Graph Automated Entity Resolution & OpenCypher Export
7. Stateful Agentic Reasoning Runtime & Query AST Decomposition
"""

import pytest
from src.core.models import (
    TextChunk, GenerationOutput, RetrievalOutput, RetrievalResult,
    SupportLevel, Citation,
)
from src.claims.nli_verifier import NLIVerifier, NLIRelation
from src.claims.extractor import AtomicClaim, ClaimSupport, ClaimExtractor
from src.citations.validator import CitationValidator
from src.grounding.gatekeeper import HallucinationGatekeeper, GatekeeperAction
from src.parsing.document_ast import DocumentASTBuilder, ASTNodeType
from src.chunking.hierarchical_chunker import HierarchicalChunker
from src.retrieval.contextual_compressor import ContextualCompressor
from src.experimental.graph_rag import KnowledgeGraph, EntityResolver
from src.agentic.runtime import StatefulAgentRuntime, QueryASTValidator, TaskStatus


# ─────────────────────────────────────────────────────────────
# 1. NLI Grounding & Claim Verification Tests
# ─────────────────────────────────────────────────────────────

def test_nli_entailment_factual():
    verifier = NLIVerifier()
    premise = "Apex Cloud revenue increased by 24.5% to $18,450 million in FY2024."
    hypothesis = "Cloud revenue grew 24.5% in fiscal 2024."
    pred = verifier.predict(premise, hypothesis)

    assert pred.relation == NLIRelation.ENTAILMENT
    assert pred.is_grounded()


def test_nli_contradiction_polarity():
    verifier = NLIVerifier()
    premise = "Legacy Data Services revenue declined by 17.8% in fiscal year 2024."
    hypothesis = "Legacy Data Services revenue increased significantly in FY2024."
    pred = verifier.predict(premise, hypothesis)

    assert pred.relation == NLIRelation.CONTRADICTION
    assert pred.confidence >= 0.75


def test_nli_contradiction_numerical():
    verifier = NLIVerifier()
    premise = "Apex accrued a legal contingency reserve of $185.0 million for antitrust inquiries."
    hypothesis = "Apex accrued a legal contingency reserve of $500.0 million."
    pred = verifier.predict(premise, hypothesis)

    assert pred.relation == NLIRelation.CONTRADICTION


def test_nli_neutral_unsupported():
    verifier = NLIVerifier()
    premise = "Total revenue was $38,280 million in FY2024."
    hypothesis = "The CEO purchased a commercial jetliner for executive travel."
    pred = verifier.predict(premise, hypothesis)

    assert pred.relation == NLIRelation.NEUTRAL


# ─────────────────────────────────────────────────────────────
# 2. Citation Character-Span & Alignment Tests
# ─────────────────────────────────────────────────────────────

def test_citation_validator_char_span():
    chunk = TextChunk(
        chunk_id="chunk_sec_01",
        document_id="doc_1",
        filename="10-K_FY2024.pdf",
        page_number=32,
        content="Management accrued a legal contingency reserve of $185.0 million as of December 31, 2024.",
    )
    retrieval = RetrievalOutput(
        query="What is the legal reserve?",
        candidates=[RetrievalResult(chunk=chunk, score=0.92, retrieval_method="hybrid", rank=0)],
        total_candidates=1,
        retrieval_latency_ms=12.0,
    )
    citation = Citation(
        document_id="doc_1",
        filename="10-K_FY2024.pdf",
        page_number=32,
        chunk_id="chunk_sec_01",
        relevant_text="legal contingency reserve of $185.0 million",
    )
    gen = GenerationOutput(
        answer="Apex accrued a $185M reserve.",
        support_level=SupportLevel.FULL_SUPPORT,
        confidence=0.95,
        citations=[citation],
    )

    validator = CitationValidator()
    validated_gen = validator.validate_citations(gen, retrieval)

    assert len(validated_gen.citations) == 1
    assert validated_gen.citations[0].validated is True
    assert validated_gen.citations[0].char_start is not None
    assert validated_gen.citations[0].char_end is not None


# ─────────────────────────────────────────────────────────────
# 3. Hallucination Gatekeeper Circuit-Breaker Tests
# ─────────────────────────────────────────────────────────────

def test_gatekeeper_pass():
    chunk = TextChunk(
        chunk_id="c1",
        document_id="d1",
        filename="report.txt",
        page_number=1,
        content="Cloud Platform Revenue reached $18,450.0 million in FY2024.",
    )
    retrieval = RetrievalOutput(
        query="What was Cloud revenue?",
        candidates=[RetrievalResult(chunk=chunk, score=0.95, retrieval_method="dense", rank=0)],
        total_candidates=1,
        retrieval_latency_ms=10.0,
    )
    gen = GenerationOutput(
        answer="Cloud Platform Revenue reached $18,450.0 million in FY2024.",
        support_level=SupportLevel.FULL_SUPPORT,
        confidence=0.9,
    )

    gatekeeper = HallucinationGatekeeper()
    out, decision = gatekeeper.audit_and_gate(gen, retrieval)

    assert decision.action == GatekeeperAction.PASS
    assert decision.passed is True


def test_gatekeeper_abstain_on_contradiction():
    chunk = TextChunk(
        chunk_id="c1",
        document_id="d1",
        filename="report.txt",
        page_number=1,
        content="Legacy Data Services revenue dropped by 17.8% in fiscal 2024.",
    )
    retrieval = RetrievalOutput(
        query="How did Legacy Data Services perform?",
        candidates=[RetrievalResult(chunk=chunk, score=0.9, retrieval_method="dense", rank=0)],
        total_candidates=1,
        retrieval_latency_ms=10.0,
    )
    # Hallucinated answer claiming growth
    gen = GenerationOutput(
        answer="Legacy Data Services revenue grew rapidly by 17.8% in fiscal 2024.",
        support_level=SupportLevel.FULL_SUPPORT,
        confidence=0.9,
    )

    gatekeeper = HallucinationGatekeeper(min_support_ratio=0.8, max_contradictions=0)
    out, decision = gatekeeper.audit_and_gate(gen, retrieval)

    assert decision.action == GatekeeperAction.ABSTAIN
    assert decision.passed is False
    assert "INSUFFICIENT_EVIDENCE" in out.answer
    assert out.support_level == SupportLevel.CONTRADICTORY_EVIDENCE


# ─────────────────────────────────────────────────────────────
# 4. Hierarchical Document AST & Parent-Child Retrieval Tests
# ─────────────────────────────────────────────────────────────

def test_document_ast_builder():
    sample_text = """# ITEM 1. BUSINESS

The Company provides enterprise cloud solutions.

## Cloud Infrastructure

Our cloud platforms expanded to 42 data centers worldwide.

| Region | Capacity |
| :--- | :--- |
| US-East | 100MW |
| EU-Central | 75MW |
"""
    builder = DocumentASTBuilder()
    ast = builder.build_from_text(sample_text, filename="annual_report.md")

    chunks = ast.to_flattened_chunks(small_to_big=True)
    assert len(chunks) >= 3

    # Verify table node preservation
    table_chunks = [c for c in chunks if c.metadata.get("is_table")]
    assert len(table_chunks) == 1
    assert "US-East" in table_chunks[0].content

    # Verify Small-to-Big parent context
    child_chunk = [c for c in chunks if "42 data centers" in c.content][0]
    parent_ctx = ast.get_parent_context(child_chunk.chunk_id)
    assert "Cloud Infrastructure" in parent_ctx


# ─────────────────────────────────────────────────────────────
# 5. Contextual Extractive Compression Tests
# ─────────────────────────────────────────────────────────────

def test_contextual_compressor():
    chunk = TextChunk(
        chunk_id="chunk_comp_1",
        document_id="doc_1",
        filename="filing.txt",
        page_number=1,
        content=(
            "The Company was founded in Delaware in 1998. "
            "Our headquarters are located in New York City. "
            "Total consolidated revenue reached $38,280 million in fiscal year 2024. "
            "We maintain extensive employee health and wellness benefit packages."
        ),
    )
    compressor = ContextualCompressor(similarity_threshold=0.25, max_sentences_per_chunk=1)
    compressed_text, report = compressor.compress_chunk("What was total consolidated revenue in 2024?", chunk)

    assert "38,280" in compressed_text
    assert "Delaware in 1998" not in compressed_text
    assert report.compression_ratio < 1.0


# ─────────────────────────────────────────────────────────────
# 6. Knowledge Graph Entity Resolution & Cypher Tests
# ─────────────────────────────────────────────────────────────

def test_entity_resolution_and_cypher():
    kg = KnowledgeGraph()

    # Add entity mentions in varied surface formats
    n1 = kg.add_node("Alphabet Inc.", "ORGANIZATION", "chunk_1")
    n2 = kg.add_node("Google", "ORGANIZATION", "chunk_2")
    n3 = kg.add_node("Alphabet", "ORGANIZATION", "chunk_3")

    # They should resolve to the identical canonical node
    assert n1.canonical_name == "Alphabet"
    assert n2.canonical_name == "Alphabet"
    assert n3.canonical_name == "Alphabet"
    assert len(kg.nodes) == 1
    assert kg.nodes["Alphabet"].mentions == 3

    kg.add_node("Microsoft Corp.", "ORGANIZATION", "chunk_4")
    kg.add_edge("Google", "Microsoft Corp.", "competes_with", 2.0)

    cypher = kg.export_to_cypher()
    assert "MERGE (n:ORGANIZATION {name: 'Alphabet'" in cypher
    assert "MERGE (n:ORGANIZATION {name: 'Microsoft'" in cypher
    assert "COMPETES_WITH" in cypher


# ─────────────────────────────────────────────────────────────
# 7. Stateful Agentic Reasoning Runtime Tests
# ─────────────────────────────────────────────────────────────

def test_agentic_runtime_decomposition():
    runtime = StatefulAgentRuntime()

    # Test comparative decomposition
    subtasks = runtime.decompose_query("Compare Microsoft Cloud and Alphabet Cloud revenue in 2024")
    assert len(subtasks) == 2
    assert "Microsoft" in subtasks[0].query
    assert "Alphabet" in subtasks[1].query

    # Test acronym expansion
    clean, expansions = QueryASTValidator.expand_and_validate("What was EBITDA margin in 2024?")
    assert len(expansions) >= 1
    assert "Earnings Before Interest" in expansions[0]
