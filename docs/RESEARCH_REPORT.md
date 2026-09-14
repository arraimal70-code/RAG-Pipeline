# Research Report: Evidence-Aware Adaptive RAG

## 1. Abstract

This project investigates how retrieval strategy, chunking, reranking, adaptive weighting, and abstention mechanisms affect factual reliability, citation accuracy, latency, and cost in document-grounded question answering. We build infrastructure to measure these effects systematically. **Results are pending** — the framework is complete but experiments require document ingestion and API access.

## 2. Problem

LLMs hallucinate when asked about specific documents. RAG addresses this by retrieving context before generation. However, RAG quality depends on retrieval strategy, chunking, and whether the system can refuse to answer. These factors are rarely studied together.

## 3. Research Question

> How can a RAG system dynamically balance retrieval quality, factual reliability, latency, and computational cost while recognizing when available evidence is insufficient?

## 4. Hypotheses

- H1: Hybrid retrieval (dense + BM25) outperforms either alone
- H2: Cross-encoder reranking improves citation accuracy
- H3: Adaptive weighting (query-type-aware) improves retrieval over fixed weights
- H4: Evidence sufficiency assessment reduces hallucination
- H5: Structure-aware chunking produces better retrieval than fixed-size

## 5. System Architecture

See docs/ARCHITECTURE.md. Key innovations:
- Query analysis → adaptive retrieval weights
- Evidence sufficiency check before generation
- Contradiction detection across sources
- Citation validation against retrieved evidence

## 6. Retrieval Methods

- **Dense**: Cosine similarity via sentence-transformers
- **BM25**: Lexical matching via rank_bm25
- **Hybrid**: Weighted fusion with query-type-adaptive weights
- **RRF**: Reciprocal Rank Fusion as alternative
- **Reranking**: Cross-encoder (ms-marco-MiniLM)

## 7. Dataset

Benchmark dataset with 15 question categories:
direct_lookup, multi_hop, numerical, definition, comparison, summarization, cross_section, cross_document, ambiguous, unanswerable, adversarial, table_based, contradictory, temporal, long_context

Target: 100-300 verified questions. Template provided.

## 8. Experimental Methodology

19 experiments (EXP-01 through EXP-19) plus ablation studies.
Each experiment records: hypothesis, method, config snapshot, metrics, latency, errors.

## 9. Metrics

**Retrieval**: Recall@K, MRR, nDCG, source accuracy, passage accuracy
**Generation**: Factual correctness, groundedness, citation accuracy, hallucination rate
**System**: Latency (p50, p95), token usage, cost
**Abstention**: Correct refusal rate, false answering rate

## 10. Results

> **STATUS: RESULTS PENDING**

The experiment infrastructure is complete. Results will be populated when experiments are executed with actual documents and API access. Per the project's core rules, no results are fabricated.

## 11. Ablation Studies

| Comparison | Tests |
|-----------|-------|
| EXP-03 vs EXP-ABL_no_bm25 | Does BM25 add value? |
| EXP-03 vs EXP-ABL_no_dense | Does dense add value? |
| EXP-06 vs EXP-ABL_no_adaptive | Does adaptive weighting help? |
| EXP-19 vs EXP-ABL_no_evidence_check | Does evidence checking reduce hallucination? |

## 12. Failure Analysis

See docs/FAILURE_ANALYSIS.md. 15 failure categories defined.
Every failed question is preserved with: question, evidence, answer, category, cause, mitigation.

## 13. Security

See docs/SECURITY.md. Protections: input validation, prompt injection detection, resource limits, secrets management, non-root Docker.

## 14. Limitations

1. Evaluation uses heuristics — proper evaluation requires LLM judge or human annotation
2. Dataset is template — needs verified ground truth
3. Only one embedding model tested by default
4. Only GPT-4o-mini tested for generation
5. PDF-only — no other document formats
6. No OCR for scanned documents
7. Contradiction detection is heuristic-based

## 15. Future Work

1. LLM-as-judge evaluation
2. Multi-format document support
3. OCR integration
4. Adaptive chunking (learn optimal size from data)
5. Query expansion (HyDE, multi-query)
6. Conversation memory
7. Table extraction
8. Graph-based retrieval for multi-hop

## 16. Conclusion

This project provides infrastructure to systematically study RAG pipeline components. The key contribution is the experimental framework that enables evidence-based architectural decisions. The system is designed to answer: "Which components materially improve reliability, and at what cost?"
