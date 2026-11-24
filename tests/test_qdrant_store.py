"""
tests/test_qdrant_store.py — Unit test suite for Phase 3: Enterprise Qdrant Vector Store Migration.
"""

from src.core.models import EmbeddedChunk
from src.embeddings.embedder import DeterministicTermVectorEmbedder
from src.indexing.qdrant_store import QdrantStore


def test_qdrant_memory_init():
    store = QdrantStore(collection_name="test_init", dimension=128, use_memory=True)
    assert store.count() == 0


def test_qdrant_add_and_search():
    embedder = DeterministicTermVectorEmbedder(dimension=128)
    store = QdrantStore(collection_name="test_search", dimension=128, use_memory=True)

    text1 = "Consolidated revenue increased by 15% due to cloud platform acceleration."
    text2 = "Hardware sales experienced supply chain disruptions in the European sector."

    chunk1 = EmbeddedChunk(
        chunk_id="c-001",
        document_id="doc-10k",
        filename="SEC_10K.pdf",
        page_number=1,
        section="Executive Summary",
        content=text1,
        embedding=embedder.embed_query(text1),
    )
    chunk2 = EmbeddedChunk(
        chunk_id="c-002",
        document_id="doc-10k",
        filename="SEC_10K.pdf",
        page_number=2,
        section="Supply Chain",
        content=text2,
        embedding=embedder.embed_query(text2),
    )

    store.add_chunks([chunk1, chunk2])
    assert store.count() == 2

    query_vec = embedder.embed_query("How much did cloud revenue increase?")
    results = store.search(query_vec, top_k=2)

    assert len(results) == 2
    assert results[0]["chunk_id"] == "c-001"
    assert results[0]["score"] > 0.0
    assert results[0]["filename"] == "SEC_10K.pdf"
    assert results[0]["section"] == "Executive Summary"


def test_qdrant_multi_tenant_isolation():
    embedder = DeterministicTermVectorEmbedder(dimension=128)
    store = QdrantStore(collection_name="test_tenants", dimension=128, use_memory=True)

    c_tenant_a = EmbeddedChunk(
        chunk_id="c-tenant-a",
        document_id="doc-a",
        filename="Acme_Internal.pdf",
        page_number=1,
        content="Acme internal confidential strategic expansion plan.",
        embedding=embedder.embed_query("Acme strategic plan"),
    )
    c_tenant_b = EmbeddedChunk(
        chunk_id="c-tenant-b",
        document_id="doc-b",
        filename="Globex_Internal.pdf",
        page_number=1,
        content="Globex patent application details.",
        embedding=embedder.embed_query("Globex patent"),
    )

    store.add_chunks([c_tenant_a], tenant_id="tenant_acme")
    store.add_chunks([c_tenant_b], tenant_id="tenant_globex")

    assert store.count() == 2

    # Query with Acme tenant filter
    res_a = store.search(
        embedder.embed_query("internal plans"),
        top_k=5,
        tenant_id="tenant_acme",
    )
    assert len(res_a) == 1
    assert res_a[0]["chunk_id"] == "c-tenant-a"
    assert res_a[0]["tenant_id"] == "tenant_acme"

    # Query with Globex tenant filter
    res_b = store.search(
        embedder.embed_query("internal plans"),
        top_k=5,
        tenant_id="tenant_globex",
    )
    assert len(res_b) == 1
    assert res_b[0]["chunk_id"] == "c-tenant-b"
    assert res_b[0]["tenant_id"] == "tenant_globex"


def test_qdrant_rbac_filtering():
    embedder = DeterministicTermVectorEmbedder(dimension=128)
    store = QdrantStore(collection_name="test_rbac", dimension=128, use_memory=True)

    public_chunk = EmbeddedChunk(
        chunk_id="c-pub",
        document_id="doc-pub",
        filename="public_press_release.pdf",
        page_number=1,
        content="Public financial press release statement.",
        embedding=embedder.embed_query("financial statement"),
    )
    exec_chunk = EmbeddedChunk(
        chunk_id="c-exec",
        document_id="doc-exec",
        filename="board_minutes_unreleased.pdf",
        page_number=1,
        content="Confidential executive board minutes regarding unannounced merger.",
        embedding=embedder.embed_query("executive merger"),
    )

    store.add_chunks([public_chunk], user_roles=["viewer", "analyst", "admin"])
    store.add_chunks([exec_chunk], user_roles=["admin"])

    # Viewer search
    viewer_res = store.search(
        embedder.embed_query("merger and financial statement"),
        top_k=5,
        user_role="viewer",
    )
    assert len(viewer_res) == 1
    assert viewer_res[0]["chunk_id"] == "c-pub"

    # Admin search
    admin_res = store.search(
        embedder.embed_query("merger and financial statement"),
        top_k=5,
        user_role="admin",
    )
    assert len(admin_res) == 2


def test_qdrant_deletion_and_clear():
    embedder = DeterministicTermVectorEmbedder(dimension=128)
    store = QdrantStore(collection_name="test_ops", dimension=128, use_memory=True)

    c1 = EmbeddedChunk(
        chunk_id="c1",
        document_id="doc-alpha",
        filename="Alpha.pdf",
        page_number=1,
        content="Alpha content",
        embedding=embedder.embed_query("alpha"),
    )
    c2 = EmbeddedChunk(
        chunk_id="c2",
        document_id="doc-beta",
        filename="Beta.pdf",
        page_number=1,
        content="Beta content",
        embedding=embedder.embed_query("beta"),
    )

    store.add_chunks([c1, c2])
    assert store.count() == 2

    # Delete doc-alpha
    store.delete_by_document("doc-alpha")
    assert store.count() == 1

    remaining = store.search(embedder.embed_query("alpha beta"), top_k=5)
    assert len(remaining) == 1
    assert remaining[0]["chunk_id"] == "c2"

    # Clear
    store.clear()
    assert store.count() == 0
