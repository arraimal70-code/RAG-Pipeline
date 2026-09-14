"""
src/chunking/chunker.py — Configurable chunking strategies.

Implements four strategies:
1. Fixed-size: Simple character/token-based splitting
2. Sentence-based: Split at sentence boundaries
3. Recursive: LangChain-style recursive character splitting
4. Structure-aware: Split at section/heading boundaries

Each strategy preserves metadata and produces traceable chunks.
"""

import re
import logging
from typing import Protocol, Optional
from src.core.models import TextChunk
from src.core.config import config, ChunkingConfig

logger = logging.getLogger(__name__)


class Chunker(Protocol):
    """Interface for chunking strategies."""
    def chunk(self, pages: list[TextChunk], cfg: ChunkingConfig) -> list[TextChunk]:
        ...


class FixedSizeChunker:
    """
    Fixed-size chunking: split every N characters with overlap.

    Pros: Simple, predictable chunk sizes.
    Cons: May split mid-sentence.
    """

    def chunk(self, pages: list[TextChunk], cfg: ChunkingConfig) -> list[TextChunk]:
        results = []
        char_size = cfg.chunk_size * 4  # approximate tokens→chars
        char_overlap = cfg.chunk_overlap * 4

        for page in pages:
            text = page.content
            start = 0
            while start < len(text):
                end = start + char_size
                chunk_text = text[start:end]

                if len(chunk_text.strip()) < cfg.min_chunk_size * 4:
                    break

                results.append(TextChunk(
                    document_id=page.document_id,
                    filename=page.filename,
                    page_number=page.page_number,
                    content=chunk_text.strip(),
                    char_offset=page.char_offset + start,
                    token_count=len(chunk_text) // 4,
                    metadata={**page.metadata, "chunk_strategy": "fixed"},
                ))
                start = end - char_overlap

        return results


class SentenceChunker:
    """
    Sentence-based chunking: group sentences until chunk is full.

    Pros: Never splits mid-sentence.
    Cons: Variable chunk sizes.
    """

    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')

    def chunk(self, pages: list[TextChunk], cfg: ChunkingConfig) -> list[TextChunk]:
        results = []
        char_size = cfg.chunk_size * 4

        for page in pages:
            sentences = self.SENTENCE_PATTERN.split(page.content)
            current_chunk = []
            current_length = 0

            for sentence in sentences:
                sentence_len = len(sentence)

                if current_length + sentence_len > char_size and current_chunk:
                    # Flush current chunk
                    chunk_text = " ".join(current_chunk)
                    results.append(self._make_chunk(page, chunk_text, cfg))
                    # Keep overlap sentences
                    overlap_text = " ".join(current_chunk)
                    overlap_chars = cfg.chunk_overlap * 4
                    while len(overlap_text) > overlap_chars and current_chunk:
                        current_chunk.pop(0)
                        overlap_text = " ".join(current_chunk)
                    current_length = len(overlap_text)

                current_chunk.append(sentence)
                current_length += sentence_len

            # Flush remaining
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= cfg.min_chunk_size * 4:
                    results.append(self._make_chunk(page, chunk_text, cfg))

        return results

    def _make_chunk(self, page: TextChunk, text: str, cfg: ChunkingConfig) -> TextChunk:
        return TextChunk(
            document_id=page.document_id,
            filename=page.filename,
            page_number=page.page_number,
            content=text.strip(),
            char_offset=page.char_offset,
            token_count=len(text) // 4,
            metadata={**page.metadata, "chunk_strategy": "sentence"},
        )


class RecursiveChunker:
    """
    Recursive character splitting (LangChain-style).

    Tries separators in order: paragraphs → lines → sentences → words.
    Only splits at a lower level if the current level produces chunks
    that are still too large.
    """

    def chunk(self, pages: list[TextChunk], cfg: ChunkingConfig) -> list[TextChunk]:
        results = []
        char_size = cfg.chunk_size * 4
        char_overlap = cfg.chunk_overlap * 4

        for page in pages:
            chunks = self._recursive_split(
                page.content, cfg.separators, char_size, char_overlap
            )
            for chunk_text in chunks:
                if len(chunk_text.strip()) < cfg.min_chunk_size * 4:
                    continue
                results.append(TextChunk(
                    document_id=page.document_id,
                    filename=page.filename,
                    page_number=page.page_number,
                    content=chunk_text.strip(),
                    char_offset=page.char_offset,
                    token_count=len(chunk_text) // 4,
                    metadata={**page.metadata, "chunk_strategy": "recursive"},
                ))

        return results

    def _recursive_split(
        self, text: str, separators: list[str], size: int, overlap: int
    ) -> list[str]:
        """Recursively split text using separators."""
        if len(text) <= size:
            return [text] if text.strip() else []

        # Find the best separator
        sep = separators[-1]  # default: split on spaces
        for s in separators:
            if s in text:
                sep = s
                break

        parts = text.split(sep)
        chunks = []
        current = ""

        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) > size and current:
                chunks.append(current)
                # Compute overlap
                if overlap > 0:
                    overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = overlap_text + sep + part
                else:
                    current = part
            else:
                current = candidate

        if current.strip():
            chunks.append(current)

        return chunks


class StructureAwareChunker:
    """
    Structure-aware chunking: detect headings and split at section boundaries.

    Uses heuristics to identify headings:
    - Lines that are significantly shorter than surrounding text
    - Lines with title-case patterns
    - Lines followed by blank lines

    Pros: Preserves document structure, chunks are topically coherent.
    Cons: Heuristic-based, may miss some structures.
    """

    HEADING_PATTERN = re.compile(
        r'^(\d+\.?\s+[A-Z].{2,60}$|'     # "1. Introduction"
        r'^[A-Z][A-Za-z\s]{2,50}$|'          # "INTRODUCTION" or "Introduction"
        r'^Chapter\s+\d+)'                   # "Chapter 3"
    )

    def chunk(self, pages: list[TextChunk], cfg: ChunkingConfig) -> list[TextChunk]:
        results = []
        char_size = cfg.chunk_size * 4

        for page in pages:
            sections = self._detect_sections(page.content)

            for section_name, section_text in sections:
                # If section is too large, sub-chunk it
                if len(section_text) > char_size:
                    sub_chunker = RecursiveChunker()
                    sub_page = TextChunk(
                        document_id=page.document_id,
                        filename=page.filename,
                        page_number=page.page_number,
                        content=section_text,
                    )
                    sub_chunks = sub_chunker.chunk([sub_page], cfg)
                    for sc in sub_chunks:
                        sc.section = section_name
                        sc.metadata["chunk_strategy"] = "structure"
                    results.extend(sub_chunks)
                elif len(section_text.strip()) >= cfg.min_chunk_size * 4:
                    results.append(TextChunk(
                        document_id=page.document_id,
                        filename=page.filename,
                        page_number=page.page_number,
                        section=section_name,
                        content=section_text.strip(),
                        char_offset=page.char_offset,
                        token_count=len(section_text) // 4,
                        metadata={**page.metadata, "chunk_strategy": "structure"},
                    ))

        return results

    def _detect_sections(self, text: str) -> list[tuple[str, str]]:
        """Detect section boundaries in text."""
        lines = text.split("\n")
        sections = []
        current_section = "preamble"
        current_text = []

        for line in lines:
            if self.HEADING_PATTERN.match(line.strip()):
                # Save current section
                if current_text:
                    sections.append((current_section, "\n".join(current_text)))
                current_section = line.strip()
                current_text = []
            else:
                current_text.append(line)

        if current_text:
            sections.append((current_section, "\n".join(current_text)))

        return sections


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────
CHUNKERS = {
    "fixed": FixedSizeChunker,
    "sentence": SentenceChunker,
    "recursive": RecursiveChunker,
    "structure": StructureAwareChunker,
}


def get_chunker(strategy: str) -> Chunker:
    """Get a chunker by strategy name."""
    if strategy not in CHUNKERS:
        raise ValueError(f"Unknown chunking strategy: {strategy}. Options: {list(CHUNKERS.keys())}")
    return CHUNKERS[strategy]()
