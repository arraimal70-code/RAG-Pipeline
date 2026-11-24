"""
tests/test_embeddings.py — Unit test suite for Phase 2: Contextual Retrieval & BGE-M3 Multi-Vector Embeddings.
"""

import math

from src.chunking.contextual_chunker import ContextualChunker
from src.core.config import config
from src.core.models import EmbeddedChunk, TextChunk
from src.embeddings.embedder import (
    BGEM3Embedder,
    DeterministicTermVectorEmbedder,
    get_embedder,
)


def test_deterministic_dense_dimension_and_norm():
    embedder_384 = DeterministicTermVectorEmbedder(dimension=384)
    embedder_1024 = DeterministicTermVectorEmbedder(dimension=1024)

    text = "Frontier Tier-1 Retrieval Augmented Generation architecture with BGE-M3 embeddings."
    vec_384 = embedder_384.embed_query(text)
    vec_1024 = embedder_1024.embed_query(text)

    assert len(vec_384) == 384
    assert len(vec_1024) == 1024

    norm_384 = math.sqrt(sum(v * v for v in vec_384))
    norm_1024 = math.sqrt(sum(v * v for v in vec_1024))
    assert abs(norm_384 - 1.0) < 1e-4
    assert abs(norm_1024 - 1.0) < 1e-4


def test_deterministic_sparse_lexical_weights():
    embedder = DeterministicTermVectorEmbedder(dimension=1024)
    text = "Alphabet Google Cloud enterprise revenue accelerated by 28 percent."
    sparse = embedder._text_to_sparse(text)

    assert isinstance(sparse, dict)
    assert len(sparse) > 0
    assert "alphabet" in sparse
    assert "revenue" in sparse
    assert all(w > 0 for w in sparse.values())


def test_deterministic_colbert_multivector():
    embedder = DeterministicTermVectorEmbedder(dimension=1024, colbert_dim=128)
    text = "Late interaction MaxSim scoring over token embeddings."
    colbert_vecs = embedder.embed_colbert([text])[0]

    assert len(colbert_vecs) > 0
    assert len(colbert_vecs[0]) == 128
    for tok_vec in colbert_vecs:
        norm = math.sqrt(sum(v * v for v in tok_vec))
        assert abs(norm - 1.0) < 1e-4


def test_bge_m3_multi_vector_pipeline():
    embedder = BGEM3Embedder(dimension=1024)
    texts = [
        "In Q3 2024, enterprise cloud infrastructure demonstrated robust margins.",
        "Operating expenses decreased due to accelerated hardware scheduling.",
    ]

    dense, sparse, colbert = embedder.embed_multi_vector(texts)

    assert len(dense) == 2
    assert len(dense[0]) == 1024
    assert len(sparse) == 2
    assert isinstance(sparse[0], dict)
    assert "cloud" in sparse[0] or "q3" in sparse[0]
    assert len(colbert) == 2
    assert len(colbert[0][0]) == 128


def test_embedded_chunk_multivector_fields():
    chunk = TextChunk(
        document_id="doc-corp-01",
        filename="10k_sec_filing.pdf",
        page_number=1,
        content="Free cash flow grew to $21.5 billion.",
    )

    embedder = BGEM3Embedder(dimension=1024)
    q_dense, q_sparse, q_colbert = embedder.embed_query_multi_vector(chunk.content)

    embedded = EmbeddedChunk(
        document_id=chunk.document_id,
        filename=chunk.filename,
        page_number=chunk.page_number,
        content=chunk.content,
        embedding=q_dense,
        sparse_weights=q_sparse,
        colbert_vecs=q_colbert,
    )

    assert len(embedded.embedding) == 1024
    assert isinstance(embedded.sparse_weights, dict)
    assert "cash" in embedded.sparse_weights
    assert len(embedded.colbert_vecs) > 0
    assert len(embedded.colbert_vecs[0]) == 128


def test_contextual_chunker_enrichment():
    chunker = ContextualChunker()
    chunks = [
        TextChunk(
            document_id="doc-fin-02",
            filename="Apple_10Q.pdf",
            page_number=4,
            section="Services Division",
            content="Services revenue rose 14% to a new all-time high of $24.2 billion.",
        ),
        TextChunk(
            document_id="doc-fin-02",
            filename="Apple_10Q.pdf",
            page_number=5,
            section="Wearables",
            content="Wearables and accessories declined 2% due to foreign exchange headwinds.",
        ),
    ]

    enriched = chunker.enrich_chunks(chunks, doc_synopsis="Apple FY24 Q3 Quarterly Financial Report")

    assert len(enriched) == 2
    for ec in enriched:
        assert ec.content.startswith("[Document: Apple_10Q.pdf")
        assert "Services Division" in ec.content or "Wearables" in ec.content
        assert "Apple FY24 Q3 Quarterly Financial Report" in ec.content
        assert ec.metadata.get("chunk_strategy") == "contextual"
        assert "raw_content" in ec.metadata


def test_factory_bge_m3_provider(monkeypatch):
    monkeypatch.setattr(config.embedding, "provider", "bge_m3")
    embedder = get_embedder()
    assert embedder is not None
    assert embedder.dimension == 1024
