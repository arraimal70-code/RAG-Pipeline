# Enterprise Tier-1 RAG Architecture Specification

This document specifies the end-to-end architecture of the **Evidence-Aware RAG Pipeline**, engineered to meet the operational standards of Tier-1 production systems (e.g., Glean, Harvey, Perplexity).

---

## 1. System Topology & Data Flow

```mermaid
flowchart TD
    subgraph Ingestion ["1. Document AST & Hierarchical Ingestion"]
        Doc[PDF / SEC 10-K / TXT] --> Parser[Layout Parser & Table Linearizer]
        Parser --> AST[Document AST Builder\nDocumentRoot > Section > Blocks]
        AST --> Chunker[Hierarchical Small-to-Big Chunker]
        Chunker --> Dense[(HNSW Dense Vector Store\nChromaDB)]
        Chunker --> BM25[(Sparse Lexical Index\nBM25+ / Okapi)]
    end

    subgraph Funnel ["2. Multi-Stage Retrieval Funnel"]
        Query[User Question / SEC Query] --> Runtime[Stateful Agentic Runtime]
        Runtime --> Decompose[Query AST Decomposition & Acronym Expansion]
        Decompose --> Stage1[Stage 1: High Recall Retrieval\nDense + BM25 RRF (k=60)]
        Stage1 --> Stage2[Stage 2: Precision Reranking\nCross-Encoder / ColBERT MaxSim]
        Stage2 --> Stage3[Stage 3: Contextual Extractive Compression\nNoise Pruning & Lost-in-the-Middle Mitigation]
        Stage3 --> Stage4[Stage 4: Small-to-Big Context Expansion\nParent Section AST Context Retrieval]
    end

    subgraph Grounding ["3. NLI Factual Grounding & Hallucination Gatekeeper"]
        Stage4 --> Generator[Grounded LLM Generator]
        Generator --> Claims[Stanford FActScore Atomic Claim Extractor]
        Claims --> NLI[NLI Entailment Verifier\nEntailment / Contradiction / Neutral]
        NLI --> Spans[Character-Span & Token Alignment\nExact Offsets in Source Chunks]
        Spans --> Gatekeeper{Hallucination Gatekeeper}
        Gatekeeper -->|Contradiction / Hallucination| Redact[Excise Sentence / Principled Abstention]
        Gatekeeper -->|Verified Entailment| Output[Stream Verified Completion + Telemetry]
    end

    subgraph Graph ["4. Enterprise Knowledge Graph"]
        AST -.-> KG[Entity Resolution Engine\nAlias Clustering & Canonicalization]
        KG --> Cypher[OpenCypher Export\nNeo4j / Neptune Ready]
        KG --> GraphTraverse[k-Hop Subgraph Traversal & Community Clusters]
    end
```

---

## 2. Ingestion Engine: Document Abstract Syntax Tree (AST)

Standard RAG architectures fragment multi-page documents into disconnected character slices, decoupling table cells from column headers and shredding section hierarchies.

### Hierarchical Tree Representation
Documents are parsed into a formal **Document AST** (`src/parsing/document_ast.py`):
```
DocumentRoot (file_id, total_pages)
  └── SectionNode (H1: ITEM 7. MD&A)
        ├── ParagraphNode (lead summary)
        ├── TableNode (linearized matrix with row-column triples)
        └── SectionNode (H2: Results of Operations)
              └── ParagraphNode (child chunk with parent section pointer)
```

### Small-to-Big (Parent-Child) Retrieval
1. **Index-Time Granularity**: Fine-grained child chunks (128–256 tokens) are embedded and indexed in ChromaDB and BM25 for maximum semantic matching precision.
2. **Provenance Metadata**: Every child chunk retains a `parent_id` and pre-rendered `parent_context` (the enclosing section and surrounding paragraphs).
3. **Query-Time Expansion**: At generation time, the retriever returns the child chunk for rank ordering, but passes the enclosing parent section context to the LLM generation prompt, eliminating context truncation.

---

## 3. Multi-Stage Retrieval Funnel

To achieve sub-second P99 latencies without sacrificing recall against dense financial filings, retrieval operates across four disciplined stages:

| Stage | Mechanism | Model / Algorithm | Output Cardinality |
| :--- | :--- | :--- | :--- |
| **Stage 1: High Recall** | Parallel Dual Search | HNSW Cosine Dense + BM25+ Sparse | Top-50 candidates |
| **Fusion** | Score Calibration | Weighted Reciprocal Rank Fusion (RRF, $k=60$) | Top-20 candidates |
| **Stage 2: Precision Rerank** | Cross-Attention Scoring | `cross-encoder/ms-marco-MiniLM-L-6-v2` or ColBERT MaxSim | Top-5 candidates |
| **Stage 3: Compression** | Extractive Noise Pruning | Sentence-level lexical & semantic relevance scoring | High-density evidence |
| **Stage 4: Expansion** | Small-to-Big Context | Document AST Parent Section Context Linking | Full prompt context |

### ColBERT Late-Interaction MaxSim Formulation
When configured with `rerank_backend="colbert_maxsim"`, the system computes token-to-token late interaction:
$$\text{MaxSim}(Q, D) = \sum_{i \in Q} \max_{j \in D} \left( E_{q, i} \cdot E_{d, j}^\top \right)$$
Preserving individual numerical tokens, dates, and metric names without 1D sentence embedding compression.

### Contextual Extractive Compression
Raw retrieved chunks contain irrelevant boilerplates that induce the *"Lost-in-the-Middle"* hallucination effect. The `ContextualCompressor` decomposes candidate chunks into discrete sentences, filters out low-salience noise, and preserves high-density evidence sentences in original document order.

---

## 4. Factual Grounding & Hallucination Gatekeeping

### The Limitation of String Matching
Naive RAG systems evaluate citations using substring or word-frequency overlap. If a source passage states:
> *"Legacy Data Services revenue decreased by 17.8% in fiscal 2024."*

A hallucinated LLM generation stating:
> *"Legacy Data Services revenue increased by 17.8% in fiscal 2024."*

shares >80% word overlap with the source passage. String-matching validators mark this hallucination as "verified".

### NLI Premise-Hypothesis Verification Engine
The `NLIVerifier` (`src/claims/nli_verifier.py`) evaluates atomic claims using Natural Language Inference:
- **ENTAILMENT**: Premise strictly proves the hypothesis claim.
- **CONTRADICTION**: Premise refutes the hypothesis claim (detected via directional polarity antonyms, numerical attribute mismatch, or negation inversions).
- **NEUTRAL**: Evidence is insufficient to corroborate the hypothesis claim.

### Pre-Stream Hallucination Gatekeeper
Operating as a pre-delivery circuit breaker (`src/grounding/gatekeeper.py`):
1. **Pass Policy**: Emits response when zero contradictions exist and factual support ratio exceeds threshold ($\ge 0.70$).
2. **Redact Policy**: Automatically excises contradicted or unsupported sentences from the completion, preserving grounded facts.
3. **Abstain Policy**: If core claims fail grounding or contradictions are detected, replaces output with principled abstention (`SupportLevel.INSUFFICIENT_EVIDENCE` or `CONTRADICTORY_EVIDENCE`), returning detailed audit telemetry.

---

## 5. Enterprise Knowledge Graph & Entity Resolution

### Automated Entity Resolution
Mentions in financial documents exhibit high lexical variance (*"Alphabet Inc."*, *"Google"*, *"Alphabet"*, *"GOOGL"*). The `EntityResolver` (`src/experimental/graph_rag.py`):
- Normalizes corporate suffixes (`Inc.`, `Corp.`, `LLC`, `plc`).
- Maps alias dictionaries and computes token similarity.
- Unifies disparate mentions into a single canonical `EntityNode`.

### OpenCypher Export
The graph engine exports directly to openCypher statements compatible with Neo4j, Amazon Neptune, and Memgraph:
```cypher
MERGE (n:ORGANIZATION {name: 'Alphabet', mentions: 3});
MATCH (a {name: 'Alphabet'}), (b {name: 'Microsoft'}) MERGE (a)-[:COMPETES_WITH {weight: 2.0}]->(b);
```

---

## 6. Stateful Agentic Reasoning Runtime

The `StatefulAgentRuntime` (`src/agentic/runtime.py`) manages multi-hop queries:
1. **Query AST Decomposition**: Analyzes comparative and multi-period queries (e.g., *"Compare Cloud revenue of A and B in FY2024"*), creating an acyclic dependency graph of sub-tasks.
2. **Acronym & Semantic Expansion**: Expands financial acronyms (EBITDA, EPS, FCF, CAGR) into canonical forms before retrieval.
3. **Speculative Parallel Retrieval**: Concurrently dispatches sub-queries to maximize throughput.
4. **Dynamic Plan Correction**: If intermediate retrieval yields low-confidence candidates ($\text{score} < 0.25$), automatically triggers query relaxation and sub-task reformulation.
5. **Bounded Budgets**: Enforces strict token ceilings and millisecond timeouts.
