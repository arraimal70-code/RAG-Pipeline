# Document AST & Ingestion Specification

## 1. Overview
This specification details the structural document parsing and hierarchical chunking engine implemented in `src/parsing/document_ast.py` and `src/chunking/hierarchical_chunker.py`.

Unlike traditional character-slicing ingestion pipelines, this system constructs a formal **Document Abstract Syntax Tree (AST)** that preserves:
- Hierarchical heading breadcrumbs (`H1 > H2 > H3`)
- Multi-column financial table matrices and semantic row-column triples
- Parent-child lineage for Small-to-Big context expansion

---

## 2. Document AST Schema

```
ASTNode
├── node_id: str                (Unique identifier)
├── node_type: ASTNodeType      (DOCUMENT | SECTION | HEADING | PARAGRAPH | TABLE | LIST | CODE_BLOCK)
├── title: Optional[str]        (Heading title if section)
├── level: int                  (Nesting depth: 0=root, 1=H1, 2=H2, etc.)
├── content: str                (Raw text or table markdown)
├── page_number: int            (Physical document page number)
├── char_start: int             (Character offset start in source document)
├── char_end: int               (Character offset end in source document)
├── parent_id: Optional[str]    (Pointer to enclosing parent ASTNode)
├── children: List[ASTNode]     (Sub-sections or nested block elements)
└── metadata: Dict[str, Any]    (Table schema, breadcrumbs, parent_context)
```

---

## 3. Small-to-Big (Parent-Child) Retrieval Protocol

### The Chunking Tradeoff
- **Small Chunks (128–256 tokens)**: Optimal for embedding bi-encoders and BM25 index matching. Avoids diluting specific metrics, dates, and names across a long passage.
- **Large Chunks (512–1024 tokens)**: Necessary for LLM reasoning to understand context, surrounding conditions, footnotes, and accounting caveats.

### The Implementation
1. **Tree Traversal**: The `DocumentAST` flattens leaf nodes (`PARAGRAPH`, `TABLE`) into individual `TextChunk` records.
2. **Context Pre-Rendering**: For every leaf chunk, `get_parent_context(node_id)` extracts the entire parent section text (including all siblings) and injects it into `chunk.metadata["parent_context"]`.
3. **Situated Prefixing**: Every chunk content string prepends situated breadcrumb context:
   ```
   [Item 7. MD&A > Results of Operations] Cloud Platform Revenue reached $18,450.0 million...
   ```
4. **Query Resolution**: The retriever ranks against the situated child chunk. If `HierarchicalChunker.get_generation_context(chunk)` is invoked, the broader enclosing section is passed to the generation prompt.

---

## 4. Table Linearization Architecture

In standard token chunkers, table lines like `| Metric | FY2024 |` get split across chunk boundaries, severing numbers from headers.

The `TableParser` (`src/parsing/table_parser.py`) processes table blocks into three distinct representations:
1. **Markdown Matrix**: Standard pipe-delimited table preserved intact as a single atomic `ASTNode`.
2. **Entity-Attribute-Value Triples**: Linearized statements binding every cell to its column header:
   ```
   [Row 1] Metric: Cloud Platform Revenue | FY2024: $18,450.0 | FY2023: $14,820.0 | YoY Change (%): +24.5%
   ```
3. **Table Schema Synopsis**: A natural language header description prepended for dense vector indexing.
