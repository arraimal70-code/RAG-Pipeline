# Engineering Decision Records (Architecture Decision Records)

This document records the architectural and engineering decisions taken in the `RAG-Pipeline` system, explicitly documenting **context**, **alternatives considered**, **rationale**, **tradeoffs**, and **failure modes addressed**.

---

## ADR-001: ChromaDB over FAISS
- **Decision**: ChromaDB as primary local vector store.
- **Alternatives Considered**: FAISS (faster search, but lacks built-in disk persistence and document metadata filtering), Pinecone (managed SaaS, paid subscription required), Weaviate (heavy Docker footprint).
- **Rationale**: Provides built-in SQLite persistence, metadata filtering by document ID and chunk scope, simple Python API, and works 100% offline without cost.
- **Tradeoff**: Slightly higher query latency than raw in-memory FAISS indices at massive scale (>10M vectors). Acceptable for document search up to 100k chunks.

## ADR-002: BM25 Alongside Dense Retrieval (Hybrid Search)
- **Decision**: Index documents into both dense semantic embeddings and sparse lexical Okapi BM25.
- **Rationale**: Dense semantic search frequently fails on exact keyword identifiers, part numbers, ticker symbols, and numerical values. BM25 excels on exact terminology but fails on conceptual synonyms. Hybrid search bridges this gap.
- **Evidence**: Information Retrieval literature and our internal benchmarks demonstrate that hybrid search consistently outperforms either modality alone.

## ADR-003: Reciprocal Rank Fusion (RRF) for Multi-Modal Ranking
- **Decision**: Reciprocal Rank Fusion (RRF) to combine dense and sparse search candidate ranks.
- **Alternatives Considered**: Weighted score fusion (requires fragile min-max score normalization across differing distribution scales), Learning-to-Rank (requires extensive annotated ranking datasets).
- **Rationale**: Parameter-free, immune to disparate score distributions between BM25 and cosine distance, and mathematically proven (Cormack et al., SIGIR 2009).
- **Formula**:
  $$\text{RRF}(d) = w_{\text{dense}} \cdot \frac{1}{k + r_{\text{dense}}(d)} + w_{\text{lexical}} \cdot \frac{1}{k + r_{\text{lexical}}(d)}$$

## ADR-004: Cross-Encoder Reranking
- **Decision**: Cross-encoder (`ms-marco-MiniLM-L-6-v2`) to rerank top candidates following RRF fusion.
- **Rationale**: Bi-encoders encode queries and passages independently, missing cross-attention term interactions. A cross-encoder performs full cross-attention over query-document pairs, boosting precision significantly.
- **Tradeoff**: ~50–100ms additional computation latency per query. Solved by only reranking the top-20 RRF candidates down to top-5.

## ADR-005: all-MiniLM-L6-v2 as Default Local Embedding
- **Decision**: Default to `sentence-transformers/all-MiniLM-L6-v2`.
- **Alternatives Considered**: OpenAI `text-embedding-3-small` (stronger representation, but requires paid API keys and cloud data transmission), BGE-large (higher memory footprint and slower inference).
- **Rationale**: Free, compact (80 MB model size), fast CPU inference (<30ms), strong baseline benchmark accuracy, runs fully offline.

## ADR-006: Multi-Strategy Chunking with Contextual Situating
- **Decision**: Support 4 chunking strategies (Fixed, Sentence, Recursive, Structure-Aware) with document-level situated context prefixes.
- **Rationale**: Context fragmentation is the primary root cause of retrieval failure in technical documents. Situating chunks with document titles and section hierarchies prevents orphan chunks.

## ADR-007: Principled Abstention Over Confident Speculation
- **Decision**: Return explicit abstention (`INSUFFICIENT_EVIDENCE`) when source evidence is incomplete or unverified.
- **Rationale**: In enterprise legal, financial, and healthcare workflows, the cost of a hallucinated answer is orders of magnitude greater than an explicit abstention.
- **Classification States**: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `INSUFFICIENT_EVIDENCE`.

## ADR-008: Rule-Based Deterministic Query Classification
- **Decision**: Lightweight regex and linguistic rule-based query classifier over an LLM classification step.
- **Alternatives Considered**: LLM classifier prompt (introduces 300–800ms extra latency, API cost, and non-deterministic classifications).
- **Rationale**: Sub-millisecond execution, completely deterministic, easily auditable and testable in CI.

## ADR-009: Pre-Generation Evidence Sufficiency Verification
- **Decision**: Evaluate candidate relevance scores, agreement, and contradiction *before* calling the LLM generator.
- **Rationale**: Prevents hallucination at the source by refusing to feed ungrounded context to the generator.

## ADR-010: Pydantic Schema Validation Across System Boundaries
- **Decision**: Enforce strict Pydantic models for all data exchange between pipeline stages.
- **Rationale**: Prevents silent runtime failures, provides schema validation, guarantees type safety, and enables deterministic serializability.

## ADR-011: Automated Benchmark Quality Gate in CI/CD
- **Context**: Code refactoring, prompt adjustments, or hyperparameter changes often cause silent regressions in retrieval accuracy.
- **Decision**: Integrate quantitative evaluation into GitHub Actions (`.github/workflows/ci.yml`) using `benchmarks/run_benchmark.py --fail-under-hit1 0.50 --fail-under-ndcg 0.65`.
- **Rationale**: Directly enforces the production engineering standard: any regression in retrieval precision or factual faithfulness automatically fails the CI build before merging.
- **Tradeoff**: Adds ~15–30 seconds to the CI test suite. High return on investment by guaranteeing zero regression.

## ADR-012: Deterministic Embedding Fallback for Zero-Cost Offline Testing
- **Context**: Test suites and offline benchmark evaluation must function in environments without internet access or GPU acceleration.
- **Decision**: Implement `DeterministicTermVectorEmbedder` (384-dimensional subword term hashing) as an automatic fallback when heavy neural models or API keys are unavailable.
- **Rationale**: Ensures that 100% of unit tests and regression checks run without external dependencies or cloud subscription fees.
