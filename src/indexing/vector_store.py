"""
src/indexing/vector_store.py — Vector index using ChromaDB.

ChromaDB provides:
- Persistent storage (survives restarts)
- Metadata filtering
- Built-in similarity search
- No separate server required
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from src.core.config import config
from src.core.models import TextChunk, EmbeddedChunk

logger = logging.getLogger(__name__)


class VectorIndex:
    """
    ChromaDB-backed vector index.

    Stores embeddings with full metadata for retrieval and citation.
    Persists to disk so re-running doesn't require re-embedding.
    """

    COLLECTION_NAME = "rag_documents"

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )
        logger.info(
            f"Vector index initialized. "
            f"Collection '{self.COLLECTION_NAME}' has {self.collection.count()} vectors."
        )

    def add_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        """Add embedded chunks to the index."""
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        embeddings = [c.embedding for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "filename": c.filename,
                "page_number": c.page_number,
                "section": c.section or "",
                "token_count": c.token_count,
                "char_offset": c.char_offset,
            }
            for c in chunks
        ]

        # Upsert to handle re-ingestion
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(chunks)} chunks to vector index")

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 50,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search for similar chunks.

        Returns list of dicts with: id, content, metadata, distance
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append({
                    "chunk_id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "score": 1 - results["distances"][0][i],  # cosine distance → similarity
                })

        return formatted

    def count(self) -> int:
        """Return number of vectors in the index."""
        return self.collection.count()

    def delete_by_document(self, document_id: str) -> None:
        """Remove all chunks for a document."""
        self.collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted chunks for document {document_id}")

    def clear(self) -> None:
        """Clear the entire index."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Vector index cleared")
