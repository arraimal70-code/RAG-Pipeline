export interface DocFile {
  title: string;
  path: string;
  icon: string;
  category: string;
  content: string;
}

export const documentation: DocFile[] = [
  {
    title: "Project Audit",
    path: "docs/PROJECT_AUDIT.md",
    icon: "🔍",
    category: "Audit",
    content: `# Project Audit — RAG Pipeline

## Current State (Pre-Transformation)

The initial repository contained a basic two-stage RAG pipeline:
- **ingest.py**: Load PDFs → chunk → embed → store in Chroma
- **query.py**: Retrieve → prompt → generate → cite
- **config.py**: Basic configuration constants
- Simple CLI interface

### What Worked
- Basic PDF ingestion via PyPDFDirectoryLoader
- Local embeddings via sentence-transformers
- Persistent ChromaDB storage
- Simple citation display (filename + page)
- Clean separation of ingest/query stages

### Major Weaknesses Identified

#### 1. Retrieval Quality (Critical)
- **Only dense retrieval**: No BM25/lexical retrieval means poor performance on exact-match queries (names, numbers, technical terms)
- **No reranking**: Raw similarity scores sent directly to LLM
- **No hybrid fusion**: Missing complementary retrieval signals
- **Fixed top-K=4**: No experimentation with optimal retrieval depth

#### 2. Chunking (High)
- **Single strategy**: Only RecursiveCharacterTextSplitter, no comparison
- **No structure awareness**: Ignores document headings, sections, tables
- **No metadata enrichment**: Section names, hierarchy not preserved
- **No experimentation framework**: Cannot determine optimal strategy

#### 3. Evaluation (Critical)
- **No evaluation framework**: No way to measure retrieval or generation quality
- **No benchmark dataset**: No ground truth for comparison
- **No metrics**: Cannot quantify improvements
- **No ablation studies**: Cannot determine which components matter

#### 4. Reliability (High)
- **No abstention mechanism**: LLM always attempts an answer
- **No hallucination detection**: Unsupported answers presented confidently
- **No citation validation**: Citations not verified against source
- **No support-level classification**: No distinction between supported/unsupported

#### 5. Security (Medium)
- **No input validation**: File size, type, content not validated
- **No prompt injection protection**: Retrieved text treated as trusted
- **No resource limits**: No protection against oversized documents
- **API key in .env but no validation**: Silent failure on missing key

#### 6. Scalability (Medium)
- **No batching**: Embeddings processed one at a time
- **No caching**: Re-embedding on every ingest run
- **No async processing**: Sequential document processing
- **No indexing strategy for scale**: Works for 10 docs, unclear at 10,000

#### 7. Testing (Critical)
- **Zero tests**: No unit tests, no integration tests
- **No CI/CD**: No automated validation
- **No Docker**: No reproducible environment

#### 8. Documentation (Medium)
- README covers basic usage but not architecture
- No failure analysis
- No experimental methodology
- No security documentation
- No reproducibility guide

## Recommended Architecture

Transform into a modular, component-based system with:
1. Clean interfaces between stages
2. Configurable retrieval pipeline (dense + BM25 + hybrid + rerank)
3. Comprehensive evaluation framework
4. Abstention and hallucination reduction
5. Citation validation
6. Security hardening
7. Full test coverage
8. Experiment tracking

## Implementation Roadmap

| Phase | Component | Priority | Effort |
|-------|-----------|----------|--------|
| 1 | Core models & config | P0 | Low |
| 2 | Robust PDF parser | P0 | Medium |
| 3 | Multiple chunking strategies | P0 | Medium |
| 4 | BM25 index | P0 | Low |
| 5 | Hybrid retrieval + RRF | P0 | Medium |
| 6 | Cross-encoder reranking | P1 | Low |
| 7 | Evaluation framework | P0 | High |
| 8 | Benchmark dataset | P0 | High |
| 9 | Abstention mechanism | P1 | Medium |
| 10 | Citation validation | P1 | Medium |
| 11 | API layer | P1 | Medium |
| 12 | Testing suite | P0 | Medium |
| 13 | Security hardening | P1 | Low |
| 14 | Experiment runner | P1 | Medium |
| 15 | Docker + CI | P2 | Low |
| 16 | Documentation | P1 | Medium |
`
  },

  {
    title: "Architecture",
    path: "docs/ARCHITECTURE.md",
    icon: "🏗️",
    category: "Design",
    content: `# System Architecture

## Overview

The RAG Pipeline follows a modular, pipeline-based architecture where each component has a single responsibility and communicates through well-defined interfaces.

## Data Flow

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PDF Files ──→ Parser ──→ Structure Detector ──→ Chunker        │
│                    │                              │              │
│                    ▼                              ▼              │
│              Metadata                      TextChunks             │
│              Extraction                         │                │
│                    │              ┌─────────────┼──────────┐    │
│                    ▼              ▼             ▼          ▼    │
│              DocumentMetadata  Embedder     BM25 Index  Store   │
│                                   │             │          │    │
│                                   ▼             ▼          ▼    │
│                              VectorIndex   BM25Index   ChromaDB │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         QUERY PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Question                                                        │
│     │                                                            │
│     ├──→ Dense Retrieval (cosine similarity) ──┐                │
│     │                                           │                │
│     └──→ BM25 Retrieval (lexical matching) ────┤                │
│                                                 │                │
│                                                 ▼                │
│                                    Reciprocal Rank Fusion        │
│                                                 │                │
│                                                 ▼                │
│                                    Cross-Encoder Reranking       │
│                                                 │                │
│                                                 ▼                │
│                                    Context Construction          │
│                                                 │                │
│                                                 ▼                │
│                                    LLM Generation                │
│                                    (with abstention)             │
│                                                 │                │
│                                                 ▼                │
│                                    Citation Validation           │
│                                                 │                │
│                                                 ▼                │
│                              ┌──────────────────┴──────────┐    │
│                              ▼                              ▼    │
│                         Answer + Citations        Evaluation     │
│                                                   Logging        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
\`\`\`

## Component Responsibilities

### 1. Document Parsing (src/parsing/)
- Extract text from PDF files
- Detect and remove headers/footers
- Extract metadata (title, author, page count)
- Handle malformed files gracefully
- Compute content hashes for deduplication

### 2. Chunking (src/chunking/)
- Split documents into retrievable units
- Four strategies: fixed, sentence, recursive, structure-aware
- Preserve metadata through chunking
- Configurable size, overlap, and constraints

### 3. Embeddings (src/embeddings/)
- Convert text chunks to vector representations
- Support local (sentence-transformers) and API (OpenAI) providers
- Batch processing for efficiency
- Model caching to avoid reloads

### 4. Indexing (src/indexing/)
- **VectorIndex**: ChromaDB for dense retrieval
- **BM25Index**: rank_bm25 for lexical retrieval
- Both persist to disk for fast reload
- Support incremental updates

### 5. Retrieval (src/retrieval/)
- Dense retrieval via vector similarity
- BM25 retrieval via lexical matching
- Reciprocal Rank Fusion for combining signals
- Cross-encoder reranking for precision
- Full latency tracking per stage

### 6. Generation (src/generation/)
- LLM-based answer generation
- Strict grounding instructions
- Citation extraction and validation
- Support-level classification
- Abstention when evidence is insufficient

### 7. Evaluation (src/evaluation/)
- Per-question metric computation
- Aggregate metric computation
- Experiment tracking with config snapshots
- Failure categorization
- Results persistence

### 8. API (src/api/)
- FastAPI server
- Document upload/management
- Query endpoint with structured response
- Health and metrics endpoints

## Design Principles

1. **Modularity**: Each component can be replaced independently
2. **Configurability**: All parameters in config.py, overridable per experiment
3. **Traceability**: Every chunk traces back to source document + page
4. **Measurability**: Every stage records latency and metrics
5. **Fail-safe**: Graceful degradation on errors, never crashes silently
6. **Reproducibility**: Config snapshots with every experiment result
`
  },

  {
    title: "Research Report",
    path: "docs/RESEARCH_REPORT.md",
    icon: "📊",
    category: "Research",
    content: `# Research Report: Retrieval Strategy Impact on RAG Reliability

## Abstract

This project investigates how retrieval strategy, chunking approach, reranking, and abstention mechanisms affect factual reliability, citation accuracy, latency, and cost in document-grounded question answering systems. Rather than claiming state-of-the-art results, we build infrastructure to measure these effects systematically and reproducibly.

## 1. Problem

Large language models hallucinate when asked about specific documents. RAG (Retrieval-Augmented Generation) addresses this by retrieving relevant context before generation. However, the quality of RAG answers depends critically on:
- What retrieval strategy is used
- How documents are chunked
- Whether reranking improves precision
- Whether the system can refuse to answer when evidence is insufficient

These factors are rarely studied together in a controlled experimental framework.

## 2. Motivation

Most RAG implementations optimize for a single metric (answer quality) without understanding the contribution of each component. This makes it impossible to:
- Know which components actually help
- Optimize for cost vs. quality tradeoffs
- Understand failure modes
- Make evidence-based architectural decisions

## 3. Research Questions

**Primary**: How do retrieval strategy, chunking, reranking, and abstention affect factual reliability and citation accuracy in document-grounded QA?

**Sub-questions**:
- RQ1: Does hybrid retrieval (dense + BM25) outperform dense-only retrieval?
- RQ2: Does cross-encoder reranking improve citation accuracy?
- RQ3: Which chunking strategy produces the best retrieval quality?
- RQ4: Can abstention mechanisms reduce hallucination without excessive false refusals?
- RQ5: What is the latency/cost tradeoff of each pipeline component?

## 4. System Architecture

See docs/ARCHITECTURE.md for full details.

Key components under investigation:
- **Retrieval**: Dense (cosine), BM25 (lexical), Hybrid (RRF fusion), Reranked (cross-encoder)
- **Chunking**: Fixed-size, Sentence-based, Recursive, Structure-aware
- **Generation**: GPT-4o-mini with strict grounding + abstention
- **Evaluation**: Retrieval metrics (Recall@K, MRR, nDCG) + Generation metrics (correctness, groundedness, citation accuracy)

## 5. Experimental Methodology

### Dataset
- Benchmark dataset with 100-300 questions across 12 categories
- Categories: direct lookup, multi-hop, numerical, definition, comparison, summarization, cross-section, cross-document, ambiguous, unanswerable, adversarial, table-based
- Each question has verified source document, page, and relevant chunk IDs
- Unanswerable questions test abstention capability

### Metrics
**Retrieval:**
- Recall@1, Recall@3, Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)
- nDCG@5
- Source retrieval accuracy
- Passage retrieval accuracy

**Generation:**
- Factual correctness (heuristic + LLM judge)
- Groundedness (evidence support level)
- Citation accuracy (validated vs. total citations)
- Hallucination rate
- Abstention accuracy

**System:**
- End-to-end latency (p50, p95)
- Per-stage latency breakdown
- Token usage and estimated cost

### Experiments
Each experiment runs the full benchmark dataset with a specific configuration:

| ID | Configuration | Purpose |
|----|--------------|---------|
| A | Dense only | Baseline semantic retrieval |
| B | BM25 only | Baseline lexical retrieval |
| C | Hybrid (RRF) | Combined retrieval |
| D | Hybrid + Rerank | Full pipeline |
| E | Fixed chunking | Chunking comparison |
| F | Sentence chunking | Chunking comparison |
| G | Recursive chunking | Chunking comparison |
| H | Structure chunking | Chunking comparison |
| I | Top-K=3 | Retrieval depth sensitivity |
| J | Top-K=5 | Default |
| K | Top-K=10 | Retrieval depth sensitivity |
| L | No reranking (ablation) | Component importance |
| M | No BM25 (ablation) | Component importance |
| N | No dense (ablation) | Component importance |

### Reproducibility
Every experiment records:
- Full configuration snapshot
- Dataset version
- Timestamp
- Per-question results
- Aggregate metrics
- Errors and exceptions

## 6. Results

> **STATUS: PENDING** — Experiments require document ingestion and API access to run.
> The infrastructure is complete. Results will be populated when experiments are executed.

The experiment runner (\`experiments/run_experiments.py\`) will produce:
- Per-experiment JSON results in \`experiments/results/\`
- Comparison table in \`experiments/results/COMPARISON.md\`
- Failure analysis in structured format

## 7. Ablation Studies

Ablation studies isolate the contribution of each component:

| Comparison | Tests |
|-----------|-------|
| D vs L | Does reranking improve quality? |
| C vs M | Does BM25 add value beyond dense? |
| C vs N | Does dense add value beyond BM25? |
| E vs F vs G vs H | Which chunking strategy is best? |
| I vs J vs K | What is the optimal top-K? |

## 8. Failure Analysis

See docs/FAILURE_ANALYSIS.md for the complete failure taxonomy.

Expected failure categories:
1. Retrieval failure (correct answer exists but wasn't retrieved)
2. Ranking failure (correct chunk retrieved but ranked too low)
3. Generation failure (evidence present but LLM produced wrong answer)
4. Citation failure (answer correct but citations don't match evidence)
5. Hallucination (answer not supported by any retrieved evidence)
6. Abstention failure (should have refused but answered anyway)

## 9. Security Considerations

See docs/SECURITY.md for full details.

Key protections:
- Input validation (file size, type, content)
- Prompt injection detection in retrieved text
- Resource limits (max pages, max chunk size)
- API key management via environment variables
- Non-root Docker execution

## 10. Performance Analysis

Performance measurements (pending execution):
- Ingestion: parsing + chunking + embedding + indexing
- Query: retrieval + reranking + generation
- Memory: vector store size, BM25 index size
- Cost: API token usage per query

## 11. Limitations

1. **Evaluation is heuristic**: Factual correctness uses support-level as proxy. True evaluation requires LLM judge or human annotation.
2. **Dataset is template**: Benchmark questions need to be populated with verified ground truth against actual documents.
3. **Single embedding model**: Only all-MiniLM-L6-v2 tested. Different models may change results.
4. **Single LLM**: Only GPT-4o-mini tested. Different models have different hallucination profiles.
5. **PDF-only**: No support for other document formats (DOCX, HTML, etc.)
6. **No OCR**: Scanned PDFs are not handled.
7. **Local evaluation**: No large-scale cloud deployment tested.

## 12. Future Work

1. **LLM-as-judge evaluation**: Use GPT-4o to evaluate factual correctness
2. **Multi-format support**: Add DOCX, HTML, Markdown parsing
3. **OCR integration**: Handle scanned PDFs via Tesseract
4. **Streaming responses**: Server-sent events for real-time answers
5. **Multi-tenancy**: Support multiple document collections
6. **Adaptive chunking**: Learn optimal chunk size from data
7. **Query expansion**: HyDE, multi-query retrieval
8. **Conversation memory**: Multi-turn Q&A with context
9. **Table extraction**: Specialized handling for tabular data
10. **Graph-based retrieval**: Entity/relationship extraction for multi-hop

## 13. Conclusion

This project provides the infrastructure to systematically study RAG pipeline components and their impact on reliability. The key contribution is not any single technique but the experimental framework that enables evidence-based architectural decisions.

The system is designed to answer: "Which components materially improve reliability, and at what cost?"
`
  },

  {
    title: "Failure Analysis",
    path: "docs/FAILURE_ANALYSIS.md",
    icon: "🔬",
    category: "Analysis",
    content: `# Failure Analysis Framework

## Overview

Every RAG system will fail. The question is not whether failures occur, but whether we can detect, categorize, and learn from them. This document defines a formal failure taxonomy and provides the infrastructure to analyze every failure.

## Failure Taxonomy

### 1. Retrieval Failure
**Definition**: The correct evidence exists in the index but was not retrieved.

**Sub-types**:
- **Embedding failure**: Query and relevant text have low semantic similarity despite being related
- **BM25 failure**: Query terms don't match document terms (synonym problem)
- **Capacity failure**: top-K too small to include relevant chunks
- **Index corruption**: Vector store or BM25 index is incomplete

**Detection**: Recall@K metrics. If relevant chunk exists but isn't in top-K results.

**Mitigation**: Increase top-K, add BM25 for lexical matching, improve embeddings.

### 2. Chunking Failure
**Definition**: The relevant information was split across chunks in a way that makes it unretrievable.

**Sub-types**:
- **Split fact**: A key fact is divided between two chunks, neither containing the complete fact
- **Context loss**: Chunk lacks surrounding context needed to understand it
- **Size mismatch**: Chunk too small (loses context) or too large (too noisy)

**Detection**: Compare chunking strategies experimentally. Analyze failures where correct page was retrieved but wrong passage.

**Mitigation**: Increase overlap, use structure-aware chunking, experiment with sizes.

### 3. Ranking Failure
**Definition**: Relevant chunks were retrieved but ranked below irrelevant ones.

**Sub-types**:
- **Score inversion**: Irrelevant chunk has higher similarity score than relevant one
- **Diversity penalty**: MMR/RRF pushes relevant chunk below irrelevant diverse one
- **Reranker error**: Cross-encoder assigns wrong relevance score

**Detection**: nDCG metrics. Relevant chunks present in candidates but at low rank.

**Mitigation**: Add reranking, tune fusion weights, adjust MMR diversity parameter.

### 4. Generation Failure
**Definition**: Evidence was retrieved correctly but the LLM produced an incorrect answer.

**Sub-types**:
- **Misreading**: LLM misinterprets the retrieved evidence
- **Over-inference**: LLM draws conclusions not supported by evidence
- **Contradiction handling**: LLM picks wrong answer when evidence is contradictory
- **Instruction following**: LLM ignores grounding instructions

**Detection**: Compare generated answer to expected answer. Support level = UNSUPPORTED.

**Mitigation**: Better prompt engineering, lower temperature, stronger grounding instructions.

### 5. Citation Failure
**Definition**: Answer is correct but citations don't point to the actual evidence.

**Sub-types**:
- **Wrong source**: Citation points to a chunk that doesn't contain the cited information
- **Missing citation**: Answer is supported but no citation was generated
- **Fabricated citation**: Citation references a chunk that doesn't exist

**Detection**: Validate each citation against its referenced chunk. Check if cited text appears in the chunk.

**Mitigation**: Structured citation format, post-generation validation, citation extraction from evidence.

### 6. Hallucination
**Definition**: Answer contains information not present in any retrieved evidence.

**Sub-types**:
- **Fabricated fact**: LLM invents a fact not in any document
- **External knowledge**: LLM uses training data instead of retrieved context
- **Confabulation**: LLM combines real facts in a way that creates false information

**Detection**: Support level = UNSUPPORTED. Factual correctness check against expected answer.

**Mitigation**: Stronger grounding instructions, abstention mechanism, citation validation.

### 7. Abstention Failure
**Definition**: System should have refused to answer but produced an answer anyway.

**Sub-types**:
- **False confidence**: System is confident but wrong
- **Unanswerable question**: Question has no answer in documents but system answers
- **Adversarial success**: Prompt injection causes system to bypass grounding

**Detection**: Unanswerable questions in benchmark that receive answers. Adversarial questions that produce responses.

**Mitigation**: Confidence thresholds, explicit abstention instructions, support-level classification.

### 8. Parsing Failure
**Definition**: PDF text extraction produced incorrect or incomplete text.

**Sub-types**:
- **Encoding errors**: Special characters garbled
- **Layout errors**: Text extracted in wrong order (columns, sidebars)
- **Missing content**: Some text not extracted at all
- **Table destruction**: Tabular data becomes unreadable text

**Detection**: Compare extracted text to visual inspection of PDF. Check for empty pages.

**Mitigation**: Alternative PDF parsers, OCR for scanned documents, table detection.

### 9. Contradictory Source Failure
**Definition**: Different documents or sections contain contradictory information.

**Detection**: Flag when retrieved chunks contain contradictory statements.

**Mitigation**: Note contradictions in answer, cite both sources, let user decide.

### 10. Latency/Resource Failure
**Definition**: System exceeds acceptable latency or resource limits.

**Detection**: p95 latency monitoring, memory usage tracking.

**Mitigation**: Caching, batching, async processing, smaller models.

## Failure Analysis Pipeline

For every failed question in evaluation:

\`\`\`
1. Record the question
2. Record retrieved evidence (all candidates with scores)
3. Record generated answer
4. Record expected answer
5. Categorize failure type
6. Identify probable root cause
7. Propose mitigation
8. Store in structured format for analysis
\`\`\`

## Failure Log Format

\`\`\`json
{
  "question_id": "q042",
  "question": "...",
  "expected_answer": "...",
  "generated_answer": "...",
  "failure_category": "retrieval_failure",
  "root_cause": "Relevant chunk ranked 15th, outside top-5",
  "retrieved_evidence": [...],
  "mitigation": "Increase rerank_top_k from 5 to 10",
  "timestamp": "2024-01-15T10:30:00Z"
}
\`\`\`

## Analysis Goals

1. **Quantify**: What percentage of failures fall into each category?
2. **Prioritize**: Which failure categories have the most impact?
3. **Track**: Do architectural changes reduce specific failure types?
4. **Predict**: Can we identify failure-prone question types?
`
  },

  {
    title: "Security",
    path: "docs/SECURITY.md",
    icon: "🔒",
    category: "Security",
    content: `# Security Considerations

## Threat Model

The RAG pipeline processes untrusted input at multiple stages:
1. **Uploaded documents** — may contain malicious content
2. **Extracted text** — may contain prompt injection attempts
3. **User queries** — may attempt to extract system information
4. **LLM responses** — may be manipulated by injected instructions

## Protections Implemented

### 1. Input Validation
- **File type**: Only .pdf files accepted
- **File size**: Maximum 50MB per file
- **Page count**: Maximum 500 pages per document
- **Content hash**: SHA-256 computed for deduplication
- **Path traversal**: File paths sanitized, no directory traversal possible

### 2. Prompt Injection Defense
- Retrieved text is treated as untrusted data
- System prompt explicitly instructs LLM to ignore instructions within context
- Retrieved chunks are clearly delimited with markers
- Maximum chunk length enforced (10,000 characters)
- Suspicious patterns flagged (e.g., "ignore previous instructions")

### 3. Resource Protection
- Maximum file size prevents disk exhaustion
- Maximum page count prevents memory exhaustion
- Maximum chunk size prevents prompt overflow
- Batch size limits prevent API rate limiting
- Request timeouts prevent hanging connections

### 4. Secrets Management
- API keys stored in .env file (never committed)
- .env listed in .gitignore
- .env.example provided without real values
- No secrets in log output
- No secrets in error messages
- Docker uses environment variables, not build args

### 5. Network Security
- CORS configured (restrict in production)
- API endpoints validate input
- No unnecessary information in error responses
- Health endpoint doesn't expose internals

### 6. Execution Security
- Docker runs as non-root user
- No shell injection in file handling
- Path operations use pathlib (not string concatenation)
- File writes are atomic where possible

## Security Checklist

- [x] .env.example provided (no real keys)
- [x] .env in .gitignore
- [x] File type validation
- [x] File size limits
- [x] Page count limits
- [x] Content length limits
- [x] No secrets in logs
- [x] No secrets in error messages
- [x] Non-root Docker user
- [x] Input validation on all API endpoints
- [x] Prompt injection awareness in system prompt
- [ ] Rate limiting (future)
- [ ] Authentication (future)
- [ ] Audit logging (future)
- [ ] Malware scanning for uploads (future)

## Known Limitations

1. **No malware scanning**: Uploaded PDFs are not scanned for exploits
2. **No authentication**: API is open (suitable for local/research use)
3. **No rate limiting**: A single user could exhaust resources
4. **Prompt injection is probabilistic**: No defense is 100% reliable
5. **No encryption at rest**: Vector store is stored unencrypted on disk
`
  },

  {
    title: "Engineering Decisions",
    path: "docs/DECISIONS.md",
    icon: "🧠",
    category: "Design",
    content: `# Engineering Decision Records

## ADR-001: Why ChromaDB over FAISS/Pinecone/Weaviate?

**Decision**: Use ChromaDB as the primary vector store.

**Alternatives considered**:
- FAISS: Faster but no persistence, no metadata filtering, manual save/load
- Pinecone: Managed service, requires API key and network, paid
- Weaviate: Feature-rich but heavy, requires separate server
- Qdrant: Good but less community support

**Rationale**:
- Built-in persistence (survives restarts without re-embedding)
- Metadata filtering for future features (e.g., filter by document)
- Simple API, no separate server process
- Free and runs locally
- Cosine similarity built-in
- Adequate performance for <1M vectors

**Tradeoff**: Slower than FAISS at scale. Acceptable for research/prototype.

---

## ADR-002: Why BM25 alongside dense retrieval?

**Decision**: Implement both dense (embedding) and BM25 (lexical) retrieval.

**Rationale**:
Dense retrieval excels at semantic similarity but fails on:
- Exact name matching ("What is the accuracy of BERT?")
- Technical terms not in embedding vocabulary
- Numerical queries ("What year was...")
- Proper nouns

BM25 excels at these cases but fails on:
- Semantic paraphrasing
- Cross-lingual queries
- Conceptual similarity

Hybrid retrieval (RRF fusion) combines both signals, consistently outperforming either alone in IR benchmarks.

**Evidence**: Multiple IR papers show hybrid > dense-only or BM25-only. Our ablation study (Experiment M, N) will measure the specific contribution.

---

## ADR-003: Why Reciprocal Rank Fusion (RRF)?

**Decision**: Use RRF for combining dense and BM25 results.

**Alternatives considered**:
- Weighted score fusion: Requires score normalization, sensitive to scale
- Learning-to-rank: Requires training data, complex
- Interleaving: Simple but doesn't weight by relevance

**Rationale**:
- Parameter-free (except k, which has a standard default of 60)
- Robust to score scale differences between retrievers
- Well-documented in IR literature (Cormack et al., 2009)
- Simple to implement and debug
- Consistently effective in practice

---

## ADR-004: Why cross-encoder reranking?

**Decision**: Use a cross-encoder (ms-marco-MiniLM) as a reranker after initial retrieval.

**Rationale**:
- Bi-encoders (used for initial retrieval) are fast but less accurate
- Cross-encoders process query+document together, capturing interactions
- Reranking a small candidate set (20) is fast enough
- Significantly improves precision at the cost of slight latency increase

**Tradeoff**: ~50ms additional latency per query. Worth it for improved accuracy.

---

## ADR-005: Why all-MiniLM-L6-v2 as default embedding?

**Decision**: Default to sentence-transformers/all-MiniLM-L6-v2.

**Alternatives considered**:
- OpenAI text-embedding-3-small: Better quality, costs money
- BGE-large: Better quality, larger model, slower
- E5-large: Good quality, larger model

**Rationale**:
- Free (no API cost)
- Fast (~50 chunks/sec on CPU)
- Small (80MB model)
- Good enough quality for most use cases
- Works offline
- Easy to swap later (one config line)

**Tradeoff**: Lower quality than larger models. Acceptable for development.

---

## ADR-006: Why multiple chunking strategies?

**Decision**: Implement 4 chunking strategies (fixed, sentence, recursive, structure-aware).

**Rationale**:
Different document types benefit from different strategies:
- Technical docs with clear sections → structure-aware
- Legal documents → sentence-based (preserve complete sentences)
- Research papers → recursive (natural paragraph boundaries)
- Mixed content → fixed (predictable, simple)

No single strategy is universally best. The experiment framework allows empirical comparison.

---

## ADR-007: Why abstention instead of always answering?

**Decision**: Implement explicit abstention when evidence is insufficient.

**Rationale**:
A RAG system that always answers will hallucinate on unanswerable questions. The cost of a wrong answer (misinformation) is higher than the cost of no answer.

The system classifies answers as:
- SUPPORTED (high confidence)
- PARTIALLY_SUPPORTED (medium confidence)
- UNSUPPORTED (low confidence)
- INSUFFICIENT_EVIDENCE (abstain)

**Tradeoff**: Lower answer coverage but higher reliability.

---

## ADR-008: Why Pydantic models for data flow?

**Decision**: Use Pydantic models for all inter-component data.

**Rationale**:
- Type safety: Catch errors at development time
- Validation: Automatic input validation
- Serialization: Easy JSON conversion for API
- Documentation: Models serve as interface documentation
- IDE support: Autocomplete and type hints
`
  },

  {
    title: "Reproducibility",
    path: "docs/REPRODUCIBILITY.md",
    icon: "🔄",
    category: "Operations",
    content: `# Reproducibility Guide

## Goal

A researcher should be able to clone this repository and reproduce all experiments and results.

## Setup

### Prerequisites
- Python 3.11+
- pip or conda
- OpenAI API key (for LLM generation)

### Installation

\`\`\`bash
# Clone
git clone https://github.com/arraimal70-code/RAG-Pipeline.git
cd RAG-Pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
\`\`\`

### Docker (alternative)

\`\`\`bash
docker build -t rag-pipeline .
docker run -p 8000:8000 --env-file .env rag-pipeline
\`\`\`

## Running Experiments

### 1. Prepare documents

\`\`\`bash
mkdir -p data/documents
cp your_pdfs/*.pdf data/documents/
\`\`\`

### 2. Ingest documents

\`\`\`bash
python -m src.pipeline ingest
\`\`\`

### 3. Run experiments

\`\`\`bash
python experiments/run_experiments.py
\`\`\`

Results are saved to \`experiments/results/\`.

### 4. View comparison

\`\`\`bash
cat experiments/results/COMPARISON.md
\`\`\`

## Configuration

All experiments use configurations from \`src/core/config.py\`. Each experiment records its full configuration snapshot in the results JSON.

To run a custom experiment:

\`\`\`python
from src.core.config import config
from src.evaluation.evaluator import Evaluator

# Modify config
config.retrieval.rerank_enabled = False
config.chunking.strategy = "structure"

# Run
evaluator = Evaluator()
result = evaluator.run_experiment("my_experiment", "Testing structure chunking without rerank", questions)
\`\`\`

## Dataset Format

Benchmark dataset is in \`benchmarks/benchmark_dataset.json\`.

Each question requires:
- \`question\`: The question text
- \`expected_answer\`: Verified correct answer
- \`source_document\`: Filename containing the answer
- \`source_page\`: Page number (if known)
- \`relevant_chunk_ids\`: IDs of chunks containing the answer
- \`question_type\`: Category (see below)
- \`difficulty\`: 1-5
- \`answerable\`: Whether the answer exists in documents

Question types: direct_lookup, multi_hop, numerical, definition, comparison, summarization, cross_section, cross_document, ambiguous, unanswerable, adversarial, table_based

## Result Format

Each experiment produces a JSON file with:
- \`experiment_id\`: Unique ID
- \`name\`: Experiment name
- \`config_snapshot\`: Full configuration at time of run
- \`dataset_version\`: Version of benchmark dataset used
- \`timestamp\`: When the experiment ran
- \`metrics\`: Aggregate metrics (recall@K, MRR, etc.)
- \`question_results\`: Per-question detailed results
- \`total_latency_ms\`: Total execution time
- \`errors\`: Any errors encountered

## Version Pinning

\`\`\`
# requirements.txt pins exact versions for reproducibility
langchain==0.3.0
chromadb==0.5.0
sentence-transformers==3.0.0
rank-bm25==0.2.2
openai==1.50.0
\`\`\`

## Random Seeds

Where applicable, random seeds should be set:
\`\`\`python
import numpy as np
np.random.seed(42)
\`\`\`

Note: LLM outputs are inherently non-deterministic even at temperature=0 due to floating-point variations. Report metrics as averages over multiple runs where precision matters.
`
  },
];
