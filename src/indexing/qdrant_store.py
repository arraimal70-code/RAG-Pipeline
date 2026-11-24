"""
src/indexing/qdrant_store.py — Enterprise Qdrant Hybrid & Multi-Vector Store.

Provides:
- HNSW dense vector indexing with cosine distance.
- Multi-tenant isolation with payload filtering (`tenant_id`, `user_role`).
- Automatic in-memory (:memory:) fallback for deterministic CI/CD and offline tests.
- Support for remote cluster connection with API key and gRPC transport.
"""

import logging
import uuid
from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.core.config import config
from src.core.models import EmbeddedChunk

logger = logging.getLogger(__name__)


class QdrantStore:
    """
    Enterprise Qdrant vector index supporting dense vectors, payload metadata filtering,
    multi-tenancy, and seamless in-memory or clustered operation.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        dimension: int | None = None,
        use_memory: bool | None = None,
    ) -> None:
        self.collection_name = collection_name or config.qdrant.collection_name
        self.dimension = dimension or config.embedding.dimension
        self.use_memory = use_memory if use_memory is not None else config.qdrant.use_memory

        self.client: QdrantClient = self._initialize_client()
        self._ensure_collection()

    def _initialize_client(self) -> QdrantClient:
        """Initialize Qdrant client, with seamless memory fallback for CI/offline."""
        if self.use_memory:
            logger.info("Initializing in-memory Qdrant client (:memory:)")
            return QdrantClient(location=":memory:")

        try:
            logger.info(
                f"Connecting to Qdrant cluster at {config.qdrant.host}:{config.qdrant.port}"
            )
            client = QdrantClient(
                host=config.qdrant.host,
                port=config.qdrant.port,
                grpc_port=config.qdrant.grpc_port,
                api_key=config.qdrant.api_key,
                prefer_grpc=config.qdrant.prefer_grpc,
                timeout=2.0,  # Fast failover if daemon is not running
            )
            # Test connectivity
            client.get_collections()
            return client
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"Could not connect to Qdrant daemon ({e}). "
                "Engaging high-performance embedded in-memory Qdrant store."
            )
            return QdrantClient(location=":memory:")

    def _ensure_collection(self) -> None:
        """Create collection with HNSW cosine distance if it does not already exist."""
        try:
            existing = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(
                    f"Created Qdrant collection '{self.collection_name}' (dim={self.dimension}, metric=cosine)"
                )
        except (UnexpectedResponse, Exception) as e:  # noqa: BLE001
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    def _chunk_id_to_uuid(self, chunk_id: str) -> str:
        """Ensure point ID is a valid RFC 4122 UUID required by Qdrant."""
        try:
            val = uuid.UUID(chunk_id, version=4)
            return str(val)
        except ValueError:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

    def add_chunks(
        self,
        chunks: Sequence[EmbeddedChunk],
        tenant_id: str = "default",
        user_roles: list[str] | None = None,
    ) -> None:
        """Add embedded chunks to Qdrant with tenant payload isolation."""
        if not chunks:
            return

        points: list[PointStruct] = []
        for c in chunks:
            point_id = self._chunk_id_to_uuid(c.chunk_id)
            payload: dict[str, Any] = {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "filename": c.filename,
                "page_number": c.page_number,
                "section": c.section or "",
                "token_count": c.token_count,
                "char_offset": c.char_offset,
                "content": c.content,
                "metadata": c.metadata,
                "tenant_id": tenant_id,
                "user_roles": user_roles or ["viewer", "admin"],
            }
            if hasattr(c, "sparse_weights") and c.sparse_weights:
                payload["sparse_weights"] = c.sparse_weights

            points.append(
                PointStruct(
                    id=point_id,
                    vector=c.embedding,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(f"Upserted {len(points)} points into Qdrant collection '{self.collection_name}'")

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 50,
        filter_metadata: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        user_role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search nearest chunks using cosine similarity with optional metadata and tenant filters."""
        if top_k <= 0 or self.count() == 0:
            return []

        conditions: list[Any] = []
        if tenant_id:
            conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))
        if user_role:
            conditions.append(FieldCondition(key="user_roles", match=MatchAny(any=[user_role])))
        if filter_metadata:
            for k, v in filter_metadata.items():
                conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))

        qdrant_filter = Filter(must=conditions) if conditions else None

        # Search points
        try:
            # Try search API first (supported in both remote and memory)
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        except Exception:  # noqa: BLE001
            # Fallback to query_points if newer API
            query_res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            results = query_res.points

        formatted: list[dict[str, Any]] = []
        for pt in results:
            p = pt.payload or {}
            score = float(pt.score)
            formatted.append({
                "chunk_id": p.get("chunk_id", str(pt.id)),
                "content": p.get("content", ""),
                "metadata": p.get("metadata", {}),
                "distance": max(0.0, 1.0 - score),
                "score": score,
                "document_id": p.get("document_id", ""),
                "filename": p.get("filename", ""),
                "page_number": p.get("page_number", 0),
                "section": p.get("section", ""),
                "tenant_id": p.get("tenant_id", "default"),
            })
        return formatted

    def count(self) -> int:
        """Return the number of points in the collection."""
        try:
            res = self.client.count(collection_name=self.collection_name)
            return int(res.count)
        except Exception:  # noqa: BLE001
            return 0

    def delete_by_document(self, document_id: str, tenant_id: str | None = None) -> None:
        """Remove all chunks associated with a document ID."""
        conditions = [FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        if tenant_id:
            conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(must=conditions),
        )
        logger.info(f"Deleted chunks for document {document_id} from Qdrant")

    def clear(self) -> None:
        """Clear the collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:  # noqa: BLE001, S110
            pass
        self._ensure_collection()
        logger.info(f"Qdrant collection '{self.collection_name}' cleared")
