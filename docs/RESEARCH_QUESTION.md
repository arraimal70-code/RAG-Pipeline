# Research Question

## Central Question

> **How can a document-grounded RAG system dynamically balance retrieval quality, factual reliability, latency, computational cost, and evidence sufficiency while recognizing when it should answer, retrieve more evidence, or abstain?**

## Sub-Questions

1. Does adaptive retrieval (query-type-aware weight adjustment) outperform fixed hybrid retrieval?
2. When does BM25 outperform dense retrieval, and vice versa?
3. Does hybrid retrieval (dense + BM25 + RRF) actually improve retrieval quality over either alone?
4. Does cross-encoder reranking justify its latency cost?
5. Can evidence sufficiency assessment reduce hallucinations without excessive false refusals?
6. Can the system reliably recognize unanswerable questions?
7. Can citation validation detect unsupported claims?
8. How should contradictory documents be handled?
9. What is the quality/latency/cost frontier?
10. Which pipeline components actually matter?

## Hypotheses

Each sub-question has an explicit hypothesis that can be proven WRONG:

- H1: Adaptive retrieval improves Recall@5 over fixed 50/50 hybrid
- H2: BM25 outperforms dense for exact-match queries (names, numbers)
- H3: Hybrid retrieval outperforms either dense-only or BM25-only
- H4: Reranking improves Precision@5 by >10% at <100ms additional latency
- H5: Evidence sufficiency reduces hallucination rate by >50%
- H6: Abstention achieves >80% accuracy on unanswerable questions
- H7: Citation validation catches >90% of unsupported claims
- H8: Contradiction detection flags >70% of conflicting sources
- H9: There exists a Pareto-optimal configuration on the quality/latency/cost frontier
- H10: At least 3 components materially improve performance (ablation study)

## What Would Falsify These?

- H1 fails if: adaptive retrieval performs the same or worse than fixed hybrid
- H2 fails if: BM25 does not outperform dense on exact-match queries
- H5 fails if: evidence sufficiency does not reduce hallucination rate
- H10 fails if: no component shows >5% improvement in ablation

**A negative result is valid research.** The experiments must be capable of proving hypotheses wrong.

## Status

**RESULTS PENDING** — Experiments require document ingestion and API access to execute.
