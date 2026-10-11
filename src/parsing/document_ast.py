"""
src/parsing/document_ast.py — Hierarchical Document Abstract Syntax Tree (AST).

Addresses the Tier-1 Ingestion requirement:
Standard RAG treats documents as flat, disconnected strings of text.
When text is sliced into arbitrary 512-token chunks, document structure,
heading breadcrumbs, and table row-column relationships are destroyed.

This module implements a formal Document AST:
1. Represents documents as hierarchical trees:
   DocumentRoot -> SectionNode -> SubSectionNode -> [ParagraphNode, TableNode, ListNode]
2. Preserves parent-child lineage for Small-to-Big (Parent Document) retrieval:
   Child nodes (leaf paragraphs/tables) can always expand to their parent section context.
3. Automatically computes breadcrumb ancestry (e.g. "Item 7 > Liquidity > Capital Resources").
"""

import re
import uuid
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, field

from src.core.models import TextChunk

logger = logging.getLogger(__name__)


class ASTNodeType(str, Enum):
    DOCUMENT = "document"
    SECTION = "section"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE_BLOCK = "code_block"


@dataclass
class ASTNode:
    """A single node within the hierarchical Document Abstract Syntax Tree."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    node_type: ASTNodeType = ASTNodeType.PARAGRAPH
    title: Optional[str] = None
    level: int = 0  # 0 for root, 1 for H1, 2 for H2, etc.
    content: str = ""
    page_number: int = 1
    char_start: int = 0
    char_end: int = 0
    parent_id: Optional[str] = None
    children: List["ASTNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: "ASTNode") -> "ASTNode":
        child.parent_id = self.node_id
        self.children.append(child)
        return child

    def get_token_count(self) -> int:
        return max(1, len(self.content.split()))

    def to_situated_text(self, breadcrumbs: Optional[List[str]] = None) -> str:
        """Format node text with situated hierarchical breadcrumbs."""
        crumbs = breadcrumbs or self.metadata.get("breadcrumbs", [])
        crumb_prefix = f"[{' > '.join(crumbs)}] " if crumbs else ""
        return f"{crumb_prefix}{self.content}".strip()

    def traverse(self) -> Iterator["ASTNode"]:
        """Depth-first traversal generator."""
        yield self
        for child in self.children:
            yield from child.traverse()


class DocumentAST:
    """
    Hierarchical Document Tree representing the full structural layout of an ingested file.
    """

    def __init__(self, filename: str, document_id: Optional[str] = None):
        self.document_id = document_id or str(uuid.uuid4())
        self.filename = filename
        self.root = ASTNode(
            node_id=f"root_{self.document_id[:8]}",
            node_type=ASTNodeType.DOCUMENT,
            title=filename,
            level=0,
            content="",
            page_number=1,
            metadata={"filename": filename, "doc_id": self.document_id}
        )
        self._node_index: Dict[str, ASTNode] = {self.root.node_id: self.root}

    def index_node(self, node: ASTNode) -> None:
        self._node_index[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[ASTNode]:
        return self._node_index.get(node_id)

    def get_breadcrumbs(self, node_id: str) -> List[str]:
        """Compute top-down breadcrumb trail from root to the specified node."""
        crumbs = []
        curr = self.get_node(node_id)
        while curr and curr.parent_id:
            curr = self.get_node(curr.parent_id)
            if curr and curr.title and curr.node_type in {ASTNodeType.SECTION, ASTNodeType.HEADING}:
                crumbs.append(curr.title)
        crumbs.reverse()
        return crumbs

    def get_parent_context(self, node_id: str, max_tokens: int = 768) -> str:
        """
        Small-to-Big expansion: retrieve the broader parent section content.
        """
        node = self.get_node(node_id)
        if not node or not node.parent_id:
            return node.content if node else ""

        parent = self.get_node(node.parent_id)
        if not parent or parent.node_type == ASTNodeType.DOCUMENT:
            return node.content

        # Assemble parent section text including siblings
        parts = []
        if parent.title:
            parts.append(f"# {parent.title}\n")
        for child in parent.children:
            parts.append(child.content)

        full_text = "\n\n".join(parts)
        words = full_text.split()
        if len(words) > max_tokens:
            return " ".join(words[:max_tokens]) + " [...]"
        return full_text

    def to_flattened_chunks(self, small_to_big: bool = True) -> List[TextChunk]:
        """
        Convert the AST leaves into TextChunks enriched with parent lineage and breadcrumbs.
        """
        chunks = []
        for node in self.root.traverse():
            # Only leaf nodes with real content become retrievable chunks
            if node.node_type in {ASTNodeType.PARAGRAPH, ASTNodeType.TABLE, ASTNodeType.LIST, ASTNodeType.CODE_BLOCK}:
                if not node.content.strip():
                    continue

                crumbs = self.get_breadcrumbs(node.node_id)
                breadcrumb_str = " > ".join(crumbs) if crumbs else node.title or ""

                # Situated body text prepends breadcrumbs
                situated_content = node.to_situated_text(crumbs)
                parent_context = self.get_parent_context(node.node_id) if small_to_big else ""

                chunk = TextChunk(
                    chunk_id=node.node_id,
                    document_id=self.document_id,
                    filename=self.filename,
                    page_number=node.page_number,
                    section=breadcrumb_str,
                    content=situated_content,
                    char_offset=node.char_start,
                    token_count=max(1, len(situated_content.split())),
                    metadata={
                        "node_type": node.node_type.value,
                        "parent_id": node.parent_id,
                        "breadcrumbs": crumbs,
                        "parent_context": parent_context,
                        "is_table": node.node_type == ASTNodeType.TABLE,
                        **node.metadata
                    }
                )
                chunks.append(chunk)

        logger.info(f"Generated {len(chunks)} hierarchical AST chunks for {self.filename}")
        return chunks


class DocumentASTBuilder:
    """
    Constructs a DocumentAST from text, Markdown, or PDF document streams.
    """

    HEADING_REGEX = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    SEC_ITEM_REGEX = re.compile(r'^(ITEM\s+\d+[A-Z]?\.?)\s*(.*)$', re.IGNORECASE | re.MULTILINE)
    TABLE_MARKER_REGEX = re.compile(r'^\s*\|.*?\|\s*$', re.MULTILINE)

    def build_from_text(self, text: str, filename: str, page_number: int = 1) -> DocumentAST:
        """
        Parse raw document content into a hierarchical AST.
        """
        ast = DocumentAST(filename=filename)
        root = ast.root

        # Track active heading stack: list of (level, ASTNode)
        stack: List[Tuple[int, ASTNode]] = [(0, root)]

        # Split into blocks by double newlines or table boundaries
        blocks = self._split_into_blocks(text)
        current_offset = 0

        for block in blocks:
            b_text = block.strip()
            if not b_text:
                continue

            b_len = len(block)
            char_start = current_offset
            char_end = current_offset + b_len
            current_offset += b_len

            # Check if block is a Markdown heading
            h_match = self.HEADING_REGEX.match(b_text)
            if h_match:
                level = len(h_match.group(1))
                title = h_match.group(2).strip()
                sec_node = ASTNode(
                    node_type=ASTNodeType.SECTION,
                    title=title,
                    level=level,
                    content=b_text,
                    page_number=page_number,
                    char_start=char_start,
                    char_end=char_end,
                )
                ast.index_node(sec_node)
                # Unwind stack until parent level < current level
                while stack and stack[-1][0] >= level:
                    stack.pop()
                parent_node = stack[-1][1] if stack else root
                parent_node.add_child(sec_node)
                stack.append((level, sec_node))
                continue

            # Check if block is an SEC Filing Header (e.g. ITEM 1. BUSINESS)
            sec_match = self.SEC_ITEM_REGEX.match(b_text)
            if sec_match:
                level = 1
                title = f"{sec_match.group(1)} {sec_match.group(2)}".strip()
                sec_node = ASTNode(
                    node_type=ASTNodeType.SECTION,
                    title=title,
                    level=level,
                    content=b_text,
                    page_number=page_number,
                    char_start=char_start,
                    char_end=char_end,
                )
                ast.index_node(sec_node)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                parent_node = stack[-1][1] if stack else root
                parent_node.add_child(sec_node)
                stack.append((level, sec_node))
                continue

            # Check if block is a Markdown Table
            if "|" in b_text and "\n" in b_text and self.TABLE_MARKER_REGEX.search(b_text):
                table_node = ASTNode(
                    node_type=ASTNodeType.TABLE,
                    content=b_text,
                    page_number=page_number,
                    char_start=char_start,
                    char_end=char_end,
                    metadata={"format": "markdown_table"}
                )
                ast.index_node(table_node)
                parent = stack[-1][1]
                parent.add_child(table_node)
                continue

            # Standard Paragraph Node
            para_node = ASTNode(
                node_type=ASTNodeType.PARAGRAPH,
                content=b_text,
                page_number=page_number,
                char_start=char_start,
                char_end=char_end,
            )
            ast.index_node(para_node)
            parent = stack[-1][1]
            parent.add_child(para_node)

        return ast

    def _split_into_blocks(self, text: str) -> List[str]:
        """Split text while preserving table integrity."""
        lines = text.split("\n")
        blocks = []
        current_block: List[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            is_table_line = stripped.startswith("|") and stripped.endswith("|")

            if is_table_line:
                if not in_table:
                    # Flush previous non-table block
                    if current_block:
                        blocks.append("\n".join(current_block))
                        current_block = []
                    in_table = True
                current_block.append(line)
            else:
                if in_table:
                    # Flush table block
                    blocks.append("\n".join(current_block))
                    current_block = []
                    in_table = False

                if not stripped:
                    if current_block:
                        blocks.append("\n".join(current_block))
                        current_block = []
                else:
                    current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return blocks
