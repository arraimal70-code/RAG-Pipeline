# Failure Analysis Framework

## Overview

Every RAG system will fail. The question is whether we can detect, categorize, and learn from failures. This document defines a 15-category failure taxonomy.

## Failure Taxonomy

### 1. Retrieval Failure
Correct evidence exists in the index but was not retrieved.
**Detection**: Recall@K metrics. **Mitigation**: Increase top-K, add BM25.

### 2. Chunking Failure
Relevant information split across chunks making it unretrievable.
**Detection**: Compare chunking strategies. **Mitigation**: Increase overlap, use structure-aware.

### 3. Embedding Failure
Query and relevant text have low semantic similarity despite being related.
**Detection**: Low dense retrieval scores for relevant content. **Mitigation**: Try different embedding model.

### 4. Ranking Failure
Relevant chunks retrieved but ranked below irrelevant ones.
**Detection**: nDCG metrics. **Mitigation**: Add reranking, tune fusion weights.

### 5. Context Window Failure
Too much context overwhelms the LLM, causing it to ignore relevant evidence.
**Detection**: Correct retrieval but wrong answer. **Mitigation**: Reduce context size, better chunk selection.

### 6. Generation Failure
Evidence retrieved correctly but LLM produced incorrect answer.
**Detection**: Compare answer to expected. **Mitigation**: Better prompt engineering, lower temperature.

### 7. Citation Failure
Answer correct but citations don't point to actual evidence.
**Detection**: Citation validation. **Mitigation**: Structured citation format, post-validation.

### 8. Hallucination
Answer contains information not in any retrieved evidence.
**Detection**: Support level = UNSUPPORTED. **Mitigation**: Stronger grounding, abstention.

### 9. Parsing Failure
PDF text extraction produced incorrect or incomplete text.
**Detection**: Compare extracted text to visual inspection. **Mitigation**: Alternative parsers, OCR.

### 10. OCR Failure
Scanned document text not recognized.
**Detection**: Empty or garbled pages. **Mitigation**: Better OCR engine.

### 11. Table Understanding Failure
Tabular data not correctly interpreted.
**Detection**: Numerical answers wrong for table-based questions. **Mitigation**: Table extraction.

### 12. Contradictory Source Failure
Different documents contain contradictory information.
**Detection**: Contradiction detection module. **Mitigation**: Flag contradictions, cite both sources.

### 13. Unanswerable Question Failure
System should have refused but answered anyway.
**Detection**: Unanswerable benchmark questions that receive answers. **Mitigation**: Evidence sufficiency check.

### 14. Latency/Resource Failure
System exceeds acceptable response time or resource limits.
**Detection**: p95 latency monitoring. **Mitigation**: Caching, batching, smaller models.

### 15. Prompt Injection Failure
Malicious content in documents or queries manipulates the system.
**Detection**: Adversarial benchmark questions. **Mitigation**: Input sanitization, system prompt hardening.

## Retrieval vs Generation Failure Decomposition

Critical distinction:
- **Retrieval failure**: Correct evidence exists but wasn't retrieved
- **Generation failure**: Evidence was retrieved but answer is wrong
- **Citation failure**: Answer is correct but citations are wrong
- **Evidence failure**: Evidence itself is conflicting or insufficient

This decomposition appears in the evaluation framework.

## Failure Log Format

```json
{
  "question_id": "q042",
  "question": "...",
  "expected_answer": "...",
  "generated_answer": "...",
  "failure_category": "retrieval_failure",
  "root_cause": "Relevant chunk ranked 15th, outside top-5",
  "retrieved_evidence": [...],
  "mitigation": "Increase rerank_top_k from 5 to 10",
  "mitigation_worked": null
}
```
