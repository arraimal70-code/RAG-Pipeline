"""
src/retrieval/hierarchical.py — Parent-Child Hierarchical Small-to-Big Indexing & Retrieval.

Overcomes the fundamental trade-off in dense retrieval:
- Small chunks (100–200 tokens) yield superior vector similarity precision because
  their embedding representations are highly focused.
- Large chunks (600–1200 tokens) provide superior generation context because the LLM
  needs full surrounding paragraphs, qualifying clauses, and section headers to avoid hallucination.

Small-to-Big Retrieval:
1. Document is split into large Parent Chunks (preserving narrative structure).
2. Each Parent Chunk is split into smaller Child Chunks linked via `parent_id`.
3. Vector similarity search indexes and searches Child Chunks.
4. At query time, retrieved Child Chunks are resolved back to their Parent Chunks.
5. Contiguous or duplicate Parent Chunks are merged into unified context windows.
"""

import re
import uuid
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

from src.core.models import TextChunk

logger = logging.getLogger(__name__)


@dataclass
class ParentChunk:
    """A broad contextual parent window (section, page, or multi-paragraph block)."""
    parent_id: str
    document_id: str
    filename: str
    page_number: int
    content: str
    section: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)


@dataclass
class HierarchicalIndexBundle:
    """Bundle containing both parent store and child chunks ready for vector indexing."""
    parent_store: Dict[str, ParentChunk]
    child_chunks: List[TextChunk]


class HierarchicalChunker:
    """
    Splits document text into a two-tier hierarchy: broad Parents and granular Children.
    """

    def __init__(self, parent_size: int = 1200, child_size: int = 300, child_overlap: int = 50):
        self.parent_size = parent_size
        self.child_size = child_size
        self.child_overlap = child_overlap

    def chunk_document(
        self,
        text: str,
        document_id: str,
        filename: str,
        page_number: int = 0,
        section: Optional[str] = None,
    ) -> HierarchicalIndexBundle:
        """
        Produce linked parent and child chunks.
        """
        parents: Dict[str, ParentChunk] = {}
        children: List[TextChunk] = []

        # Step 1: Split into parent windows by paragraph boundaries
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_parent_text = []
        current_len = 0
        parent_idx = 0

        for p in paragraphs:
            current_parent_text.append(p)
            current_len += len(p)

            if current_len >= self.parent_size:
                p_text = "\n\n".join(current_parent_text)
                p_id = f"parent_{document_id[:8]}_{parent_idx}"
                parent = ParentChunk(
                    parent_id=p_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_number,
                    content=p_text,
                    section=section,
                )
                parents[p_id] = parent

                # Step 2: Split parent into granular children
                child_chunks = self._generate_children(parent)
                children.extend(child_chunks)

                current_parent_text = []
                current_len = 0
                parent_idx += 1

        # Handle remaining buffer
        if current_parent_text:
            p_text = "\n\n".join(current_parent_text)
            p_id = f"parent_{document_id[:8]}_{parent_idx}"
            parent = ParentChunk(
                parent_id=p_id,
                document_id=document_id,
                filename=filename,
                page_number=page_number,
                content=p_text,
                section=section,
            )
            parents[p_id] = parent
            child_chunks = self._generate_children(parent)
            children.extend(child_chunks)

        logger.info(f"Hierarchical Chunker: Created {len(parents)} parents and {len(children)} children for {filename}")
        return HierarchicalIndexBundle(parent_store=parents, child_chunks=children)

    def _generate_children(self, parent: ParentChunk) -> List[TextChunk]:
        """Split parent content into small overlapping child TextChunks."""
        sentences = re.split(r'(?<=[.!?])\s+', parent.content)
        child_chunks: List[TextChunk] = []
        curr_tokens: List[str] = []
        curr_len = 0
        c_idx = 0

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            curr_tokens.append(s_clean)
            curr_len += len(s_clean)

            if curr_len >= self.child_size:
                child_content = " ".join(curr_tokens)
                c_id = f"child_{parent.parent_id}_{c_idx}"
                chunk = TextChunk(
                    chunk_id=c_id,
                    document_id=parent.document_id,
                    filename=parent.filename,
                    page_number=parent.page_number,
                    content=child_content,
                    section=parent.section,
                    metadata={"parent_id": parent.parent_id},
                    char_offset=0,
                    token_count=len(child_content.split()),
                )
                parent.child_ids.append(c_id)
                child_chunks.append(chunk)

                # Keep overlap
                curr_tokens = curr_tokens[-1:] if self.child_overlap > 0 else []
                curr_len = sum(len(t) for t in curr_tokens)
                c_idx += 1

        if curr_tokens:
            child_content = " ".join(curr_tokens)
            c_id = f"child_{parent.parent_id}_{c_idx}"
            chunk = TextChunk(
                chunk_id=c_id,
                document_id=parent.document_id,
                filename=parent.filename,
                page_number=parent.page_number,
                content=child_content,
                section=parent.section,
                metadata={"parent_id": parent.parent_id},
                char_offset=0,
                token_count=len(child_content.split()),
            )
            parent.child_ids.append(c_id)
            child_chunks.append(chunk)

        return child_chunks


class HierarchicalRetriever:
    """
    Expands retrieved child chunks back to their corresponding parent context windows.
    """

    def __init__(self, parent_store: Optional[Dict[str, ParentChunk]] = None):
        self.parent_store: Dict[str, ParentChunk] = parent_store or {}

    def register_parents(self, parent_store: Dict[str, ParentChunk]) -> None:
        """Register parent chunks in memory store."""
        self.parent_store.update(parent_store)

    def expand_to_parents(self, child_chunks: List[TextChunk]) -> List[TextChunk]:
        """
        Map child chunks to parent chunks and merge duplicates to avoid context redundancy.
        """
        seen_parent_ids: Set[str] = set()
        expanded_chunks: List[TextChunk] = []

        for child in child_chunks:
            p_id = child.metadata.get("parent_id")
            if p_id and p_id in self.parent_store:
                if p_id not in seen_parent_ids:
                    seen_parent_ids.add(p_id)
                    p = self.parent_store[p_id]
                    expanded_chunks.append(TextChunk(
                        chunk_id=f"expanded_{p.parent_id}",
                        document_id=p.document_id,
                        filename=p.filename,
                        page_number=p.page_number,
                        content=p.content,
                        section=p.section,
                        metadata={"is_expanded_parent": True, "source_child_id": child.chunk_id},
                        char_offset=0,
                        token_count=len(p.content.split()),
                    ))
            else:
                # If child has no parent registered, retain original child chunk
                expanded_chunks.append(child)

        logger.debug(f"Hierarchical Retriever: Expanded {len(child_chunks)} children to {len(expanded_chunks)} parents")
        return expanded_chunks

    def clear(self) -> None:
        """Clear parent store."""
        self.parent_store.clear()
