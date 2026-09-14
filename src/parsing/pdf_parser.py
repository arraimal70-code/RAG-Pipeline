"""
src/parsing/pdf_parser.py — Robust PDF document parser.

Handles normal text PDFs, multi-page documents, metadata extraction,
repeated header/footer detection, and graceful degradation for
malformed files.
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PageObject
from pypdf.errors import PdfReadError

from src.core.models import DocumentMetadata, TextChunk
from src.core.config import config

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Parses PDF files into structured text chunks with full metadata.

    Design decisions:
    - Uses pypdf (pure Python) for reliability over speed
    - Detects and removes repeated headers/footers
    - Preserves page numbers for citation tracking
    - Handles malformed PDFs with graceful degradation
    - Computes content hash for deduplication
    """

    def __init__(self):
        self.security = config.security

    def parse(self, file_path: Path) -> tuple[DocumentMetadata, list[TextChunk]]:
        """
        Parse a PDF file into metadata and text chunks.

        Returns:
            Tuple of (DocumentMetadata, list[TextChunk])

        Raises:
            ValueError: If file fails validation
            PdfReadError: If PDF is unreadable
        """
        # Validate before parsing
        self._validate_file(file_path)

        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            raise

        # Extract metadata
        metadata = self._extract_metadata(file_path, reader)

        # Extract text per page
        pages_text = self._extract_page_texts(reader, metadata.num_pages)

        # Detect and remove repeated headers/footers
        pages_text = self._remove_repeated_elements(pages_text)

        # Convert to chunks (one chunk per page at this stage)
        chunks = self._pages_to_chunks(pages_text, metadata)

        logger.info(
            f"Parsed {file_path.name}: {metadata.num_pages} pages, "
            f"{len(chunks)} chunks, {sum(c.token_count for c in chunks)} tokens"
        )

        return metadata, chunks

    def _validate_file(self, file_path: Path) -> None:
        """Validate file before processing."""
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in self.security.allowed_extensions:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Allowed: {self.security.allowed_extensions}"
            )

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.security.max_file_size_mb:
            raise ValueError(
                f"File too large: {size_mb:.1f}MB. "
                f"Max: {self.security.max_file_size_mb}MB"
            )

    def _extract_metadata(self, file_path: Path, reader: PdfReader) -> DocumentMetadata:
        """Extract document metadata from PDF."""
        info = reader.metadata or {}
        num_pages = len(reader.pages)

        if num_pages > self.security.max_pages_per_document:
            logger.warning(
                f"Document {file_path.name} has {num_pages} pages "
                f"(max: {self.security.max_pages_per_document})"
            )

        # Compute content hash for dedup
        content_hash = self._compute_content_hash(reader)

        return DocumentMetadata(
            filename=file_path.name,
            file_path=str(file_path),
            file_size_bytes=file_path.stat().st_size,
            num_pages=num_pages,
            title=info.get("/Title", None) if isinstance(info, dict) else None,
            author=info.get("/Author", None) if isinstance(info, dict) else None,
            content_hash=content_hash,
        )

    def _compute_content_hash(self, reader: PdfReader) -> str:
        """Compute SHA-256 hash of document content for deduplication."""
        hasher = hashlib.sha256()
        for page in reader.pages[:10]:  # hash first 10 pages for speed
            text = page.extract_text() or ""
            hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()[:16]

    def _extract_page_texts(self, reader: PdfReader, num_pages: int) -> list[dict]:
        """Extract text from each page with page numbers."""
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({
                "page_number": i,
                "text": text,
                "char_count": len(text),
            })
        return pages

    def _remove_repeated_elements(self, pages: list[dict]) -> list[dict]:
        """
        Detect and remove repeated headers/footers.

        Strategy: If a line appears identically in >50% of pages,
        it's likely a header or footer. Remove it.
        """
        if len(pages) < 3:
            return pages  # too few pages for reliable detection

        # Count line frequencies across pages
        line_counts: dict[str, int] = {}
        for page in pages:
            lines = page["text"].split("\n")
            # Check first 2 and last 2 lines (typical header/footer positions)
            candidates = lines[:2] + lines[-2:]
            for line in candidates:
                stripped = line.strip()
                if len(stripped) > 3:  # ignore very short lines
                    line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Lines appearing in >50% of pages are headers/footers
        threshold = len(pages) * 0.5
        repeated = {line for line, count in line_counts.items() if count > threshold}

        if not repeated:
            return pages

        # Remove repeated lines from page text
        for page in pages:
            lines = page["text"].split("\n")
            filtered = [l for l in lines if l.strip() not in repeated]
            page["text"] = "\n".join(filtered)

        logger.debug(f"Removed {len(repeated)} repeated header/footer lines")
        return pages

    def _pages_to_chunks(
        self, pages: list[dict], metadata: DocumentMetadata
    ) -> list[TextChunk]:
        """Convert page texts to TextChunk objects."""
        chunks = []
        for page in pages:
            text = page["text"].strip()
            if not text:
                continue

            # Estimate token count (rough: chars / 4)
            token_count = len(text) // 4

            chunks.append(TextChunk(
                document_id=metadata.document_id,
                filename=metadata.filename,
                page_number=page["page_number"],
                content=text,
                char_offset=0,
                token_count=token_count,
                metadata={
                    "source": metadata.file_path,
                    "total_pages": metadata.num_pages,
                },
            ))

        return chunks
