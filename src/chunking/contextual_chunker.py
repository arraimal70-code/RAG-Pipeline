"""
src/chunking/contextual_chunker.py — Anthropic Contextual Retrieval Chunker.

Implements the Contextual Retrieval paradigm (Anthropic, 2024):
Standard chunking separates paragraphs from their parent document context.
Contextual Retrieval prepends situated context to each chunk before embedding
and indexing, significantly improving retrieval accuracy (up to 49% reduction
in retrieval failures when combined with BM25 and reranking).

Situated prefix format:
[Document: {filename} | Section: {section} | Topic: {synopsis}]
{chunk_content}
"""

import re
import logging
from typing import Optional, List
from src.core.models import TextChunk
from src.core.config import config, ChunkingConfig
from src.chunking.chunker import RecursiveChunker

logger = logging.getLogger(__name__)


class ContextualChunker:
    """
    Anthropic-style Contextual Chunker.

    Generates situated chunk prefixes combining document hierarchy, title,
    and section scope so that each chunk contains self-contained context
    prior to dense embedding and BM25 lexical indexing.
    """

    def __init__(self, base_chunker=None):
        self.base_chunker = base_chunker or RecursiveChunker()

    def _extract_document_synopsis(self, pages: List[TextChunk]) -> str:
        """
        Extract a concise document synopsis from the lead paragraphs.
        In offline mode, extracts the first key sentences with title terms.
        """
        if not pages:
            return "General document"

        first_page_content = pages[0].content.strip()
        lines = [line.strip() for line in first_page_content.split("\n") if line.strip()]
        
        if not lines:
            return f"Document {pages[0].filename}"

        # Look for opening summary / abstract / lead sentence
        lead_sentences = []
        for line in lines[:5]:
            if len(line) > 20 and not line.isupper():
                lead_sentences.append(line)
                if len(lead_sentences) >= 2:
                    break

        synopsis = " ".join(lead_sentences) if lead_sentences else lines[0]
        # Truncate to maximum 160 characters for crisp situated context
        if len(synopsis) > 160:
            synopsis = synopsis[:157] + "..."
        return synopsis

    def _detect_section_for_offset(self, content: str, offset: int) -> str:
        """Find the enclosing section header before the given offset."""
        lines = content[:offset].split("\n")
        heading_pattern = re.compile(
            r'^(\d+\.?\s+[A-Z].{2,60}$|^[A-Z][A-Za-z\s]{2,50}$|^Chapter\s+\d+|^Section\s+\d+)',
            re.MULTILINE
        )
        for line in reversed(lines):
            line_str = line.strip()
            if heading_pattern.match(line_str):
                return line_str
        return "General"

    def chunk(self, pages: List[TextChunk], cfg: ChunkingConfig) -> List[TextChunk]:
        """
        Create situated chunks using Anthropic Contextual Retrieval methodology.
        """
        # Step 1: Base chunking
        raw_chunks = self.base_chunker.chunk(pages, cfg)
        if not raw_chunks:
            return []

        # Step 2: Document-level context extraction
        doc_synopsis = self._extract_document_synopsis(pages)
        filename = pages[0].filename if pages else "document"

        # Step 3: Contextual augmentation for each chunk
        contextual_chunks = []
        for c in raw_chunks:
            section_name = c.section or self._detect_section_for_offset(
                pages[c.page_number].content if c.page_number < len(pages) else c.content,
                c.char_offset
            )

            # Construct situated context prefix
            prefix = f"[Document: {filename} | Section: {section_name} | Scope: {doc_synopsis}]"
            contextualized_content = f"{prefix}\n{c.content}"

            contextual_chunk = TextChunk(
                document_id=c.document_id,
                filename=c.filename,
                page_number=c.page_number,
                section=section_name,
                content=contextualized_content,
                char_offset=c.char_offset,
                token_count=len(contextualized_content) // 4,
                metadata={
                    **c.metadata,
                    "chunk_strategy": "contextual",
                    "context_prefix": prefix,
                    "raw_content": c.content,
                    "doc_synopsis": doc_synopsis,
                },
            )
            contextual_chunks.append(contextual_chunk)

        logger.info(f"Generated {len(contextual_chunks)} contextualized chunks for {filename}")
        return contextual_chunks
