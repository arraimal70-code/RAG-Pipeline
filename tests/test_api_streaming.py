"""
tests/test_api_streaming.py — Unit test suite for Phase 7: Streaming API, Redis Semantic Cache & RBAC.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.cache.semantic_cache import SemanticCache
from src.core.models import QueryResponse, SupportLevel
from src.embeddings.embedder import DeterministicTermVectorEmbedder


def test_streaming_api_events_and_rbac():
    client = TestClient(app)

    response = client.post(
        "/api/v1/query/stream",
        json={"question": "What was the reported growth rate for Google Cloud in fiscal 2024?"},
        headers={
            "X-Tenant-ID": "test_corp",
            "X-User-Role": "analyst",
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    assert "event: plan" in body
    assert "event: retrieval" in body
    assert "event: token" in body
    assert "event: gatekeeper" in body
    assert "event: done" in body
    assert "test_corp" in body


def test_semantic_cache_tenant_isolation():
    embedder = DeterministicTermVectorEmbedder(dimension=128)
    cache = SemanticCache(similarity_threshold=0.65, embedder=embedder)
    cache.clear()

    query = "Google Cloud growth in fiscal year 2024"

    q_response = QueryResponse(
        question=query,
        answer="Google Cloud grew 28% in FY2024 to $40.0 billion.",
        support_level=SupportLevel.SUPPORTED,
        confidence=0.95,
        citations=[],
        retrieval_metadata={"source": "test"},
    )

    # Store for tenant A
    cache.put(query, q_response, tenant_id="tenant_a")

    # Lookup by tenant A should hit
    hit_a = cache.get(query, tenant_id="tenant_a")
    assert hit_a is not None
    assert "28%" in hit_a.answer

    # Lookup by tenant B should miss (strict multi-tenant partition)
    miss_b = cache.get(query, tenant_id="tenant_b")
    assert miss_b is None

    # Semantic similarity hit for tenant A
    similar_q = "How much did Google Cloud grow in fiscal 2024?"
    sem_hit = cache.get(similar_q, tenant_id="tenant_a")
    assert sem_hit is not None

    stats = cache.stats()
    assert stats["total_lookups"] >= 2
    assert stats["total_hits"] >= 2
