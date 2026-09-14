# Engineering Decision Records

## ADR-001: ChromaDB over FAISS
**Decision**: ChromaDB as primary vector store.
**Alternatives**: FAISS (faster, no persistence), Pinecone (managed, paid), Weaviate (heavy).
**Rationale**: Built-in persistence, metadata filtering, simple API, free, local.
**Tradeoff**: Slower than FAISS at scale. Acceptable for research.

## ADR-002: BM25 alongside dense retrieval
**Decision**: Both dense and BM25 retrieval.
**Rationale**: Dense fails on exact matches (names, numbers). BM25 fails on semantic similarity. Hybrid combines both.
**Evidence**: IR literature consistently shows hybrid > either alone.

## ADR-003: Reciprocal Rank Fusion
**Decision**: RRF for combining retrieval results.
**Alternatives**: Weighted score fusion (needs normalization), Learning-to-rank (needs training data).
**Rationale**: Parameter-free, robust to score scale differences, well-documented (Cormack et al., 2009).

## ADR-004: Cross-encoder reranking
**Decision**: Cross-encoder (ms-marco-MiniLM) as reranker.
**Rationale**: Bi-encoders fast but less accurate. Cross-encoders process query+document together. Reranking 20 candidates is fast enough.
**Tradeoff**: ~50ms additional latency for improved precision.

## ADR-005: all-MiniLM-L6-v2 as default embedding
**Decision**: Default to local sentence-transformers model.
**Alternatives**: OpenAI (better, costs money), BGE-large (better, slower).
**Rationale**: Free, fast, small (80MB), good enough quality, works offline.

## ADR-006: Multiple chunking strategies
**Decision**: 4 strategies (fixed, sentence, recursive, structure-aware).
**Rationale**: Different document types benefit from different strategies. No single strategy is universally best.

## ADR-007: Abstention over always answering
**Decision**: Explicit abstention when evidence is insufficient.
**Rationale**: Cost of wrong answer > cost of no answer. System classifies: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, INSUFFICIENT_EVIDENCE.

## ADR-008: Rule-based query classification
**Decision**: Rule-based (not LLM-based) query classification.
**Alternatives**: LLM classifier (adds latency, cost, noise).
**Rationale**: Fast, deterministic, debuggable. Sufficient for the granularity needed.

## ADR-009: Evidence sufficiency before generation
**Decision**: Assess evidence quality before generating answer.
**Rationale**: Prevents hallucination by checking retrieval scores, agreement, coverage, and contradictions before LLM invocation.

## ADR-010: Pydantic models for data flow
**Decision**: Pydantic models for all inter-component data.
**Rationale**: Type safety, validation, serialization, documentation, IDE support.
