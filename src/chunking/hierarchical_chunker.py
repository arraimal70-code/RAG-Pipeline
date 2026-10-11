"""
src/chunking/hierarchical_chunker.py — Small-to-Big Hierarchical Chunker.

Addresses the Tier-1 Chunking requirement:
Implements Small-to-Big / Parent-Child Retrieval:
1. Breaks text into fine-grained child units (paragraphs, table rows) for high-precision
   embedding and BM25 index matching.
2. Preserves the full enclosing parent section AST context in chunk metadata.
3. Allows retrieval to match specific narrow sentences while passing the broader
   parent context to the LLM generation prompt, eliminating context truncation.
"""

import logging
from typing import List, Optional
from src.core.models import TextChunk
from src.core.config import ChunkingConfig
from src.parsing.document_ast import DocumentASTBuilder, DocumentAST

logger = logging.getLogger(__name__)


class HierarchicalChunker:
    """
    Hierarchical Document AST Chunker for Small-to-Big Retrieval.
    """

    def __init__(self, small_to_big: bool = True):
        self.builder = DocumentASTBuilder()
        self.small_to_big = small_to_big

    def chunk(self, pages: List[TextChunk], cfg: Optional[ChunkingConfig] = None) -> List[TextChunk]:
        """
        Build Document AST across pages and generate hierarchical chunks.
        """
        if not pages:
            return []

        filename = pages[0].filename
        all_chunks: List[TextChunk] = []

        # If multiple pages, process page-by-page preserving page numbers
        for page in pages:
            if not page.content.strip():
                continue

            ast = self.builder.build_from_text(
                text=page.content,
                filename=filename,
                page_number=page.page_number
            )

            page_chunks = ast.to_flattened_chunks(small_to_big=self.small_to_big)
            for c in page_chunks:
                c.document_id = page.document_id
                c.filename = page.filename
            all_chunks.extend(page_chunks)

        if not all_chunks:
            # Fallback to returning original page chunks if AST produced nothing
            return pages

        logger.info(f"HierarchicalChunker produced {len(all_chunks)} chunks for {filename}")
        return all_chunks

    @staticmethod
    def get_generation_context(chunk: TextChunk) -> str:
        """
        Expand chunk to its enclosing parent context for LLM prompt generation.
        """
        parent_ctx = chunk.metadata.get("parent_context", "")
        if parent_ctx and len(parent_ctx.strip()) > len(chunk.content.strip()):
            return parent_ctx
        return chunk.content
