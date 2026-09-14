"""
src/indexing/bm25_index.py — BM25 lexical index.

BM25 provides strong keyword matching that complements dense retrieval.
Where dense retrieval finds semantically similar content, BM25 finds
content with exact term matches — critical for proper nouns, technical
terms, and specific references.

Uses rank_bm25 library for efficient scoring.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from src.core.config import config
from src.core.models import TextChunk

logger = logging.getLogger(__name__)


class BM25Index:
    """
    BM25 lexical index for keyword-based retrieval.

    Design decisions:
    - Uses Okapi BM25 (standard variant, well-tested)
    - Tokenizes on whitespace + punctuation (simple but effective)
    - Persists to disk for fast reload
    - Stores chunk references for metadata retrieval
    """

    def __init__(self):
        self.index_dir = config.BM25_INDEX_DIR
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: list[dict] = []  # parallel to BM25 corpus
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        """Load existing index from disk if available."""
        index_file = self.index_dir / "bm25.pkl"
        meta_file = self.index_dir / "bm25_meta.json"

        if index_file.exists() and meta_file.exists():
            try:
                with open(index_file, "rb") as f:
                    self.bm25 = pickle.load(f)
                with open(meta_file, "r") as f:
                    self.chunks = json.load(f)
                logger.info(f"Loaded BM25 index with {len(self.chunks)} chunks")
            except Exception as e:
                logger.warning(f"Failed to load BM25 index: {e}. Will rebuild.")
                self.bm25 = None
                self.chunks = []

    def build(self, chunks: list[TextChunk]) -> None:
        """Build BM25 index from chunks."""
        logger.info(f"Building BM25 index from {len(chunks)} chunks...")

        # Tokenize
        corpus = [self._tokenize(c.content) for c in chunks]

        # Build BM25
        self.bm25 = BM25Okapi(corpus)

        # Store chunk metadata (not full content — saved in vector store)
        self.chunks = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "filename": c.filename,
                "page_number": c.page_number,
                "section": c.section or "",
                "content": c.content,  # needed for BM25 result text
            }
            for c in chunks
        ]

        # Persist
        self._save()
        logger.info(f"BM25 index built and saved: {len(self.chunks)} chunks")

    def search(self, query: str, top_k: int = 50) -> list[dict]:
        """
        Search BM25 index.

        Returns list of dicts with: chunk_id, content, metadata, score
        """
        if self.bm25 is None:
            logger.warning("BM25 index not built. Returning empty results.")
            return []

        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        # Get top-k indices
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] <= 0:
                break
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "metadata": {
                    "document_id": chunk["document_id"],
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"],
                    "section": chunk["section"],
                },
                "score": float(scores[idx]),
                "rank": rank,
            })

        return results

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase + split on non-alphanumeric."""
        import re
        return re.findall(r'\w+', text.lower())

    def _save(self) -> None:
        """Persist index to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

        with open(self.index_dir / "bm25.pkl", "wb") as f:
            pickle.dump(self.bm25, f)

        with open(self.index_dir / "bm25_meta.json", "w") as f:
            json.dump(self.chunks, f)

    def count(self) -> int:
        return len(self.chunks)
