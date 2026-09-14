# Limitations

## Honest Assessment of Current Limitations

### 1. No Experimental Results
**Status**: RESULTS PENDING
**Impact**: All claims about system performance are unvalidated.
**Reason**: Experiments require actual financial documents and OpenAI API access.
**Mitigation**: Infrastructure is complete. Run `python experiments/runner.py` with real data.

### 2. Benchmark is a Template
**Status**: 20 template questions, needs 200+ verified questions
**Impact**: Cannot produce meaningful evaluation metrics.
**Reason**: Gold answers must be verified against actual documents.
**Mitigation**: Use real SEC filings and manually verify each question.

### 3. Evaluation is Heuristic
**Status**: Factual correctness uses support-level as proxy
**Impact**: Metrics may not reflect true answer quality.
**Reason**: LLM-as-judge evaluation not yet implemented.
**Mitigation**: Add GPT-4o-based evaluation or human annotation.

### 4. Single Embedding Model
**Status**: Only all-MiniLM-L6-v2 tested
**Impact**: Cannot determine if better embeddings improve performance.
**Reason**: Computational cost of testing multiple models.
**Mitigation**: Add OpenAI and BGE embeddings to experiment suite.

### 5. Single LLM
**Status**: Only GPT-4o-mini tested
**Impact**: Cannot determine if better LLMs reduce hallucination.
**Reason**: API cost.
**Mitigation**: Test GPT-4o, Claude, and local models.

### 6. PDF-Only
**Status**: No support for DOCX, HTML, Markdown
**Impact**: Limited to PDF documents.
**Reason**: Scope constraint.
**Mitigation**: Add document format adapters.

### 7. No OCR
**Status**: Scanned PDFs not handled
**Impact**: Cannot process image-based PDFs.
**Reason**: OCR adds complexity and latency.
**Mitigation**: Integrate Tesseract or cloud OCR.

### 8. Contradiction Detection is Heuristic
**Status**: Rule-based, may miss subtle contradictions
**Impact**: False negatives on complex contradictions.
**Reason**: NLI models not yet integrated.
**Mitigation**: Add cross-encoder NLI for contradiction detection.

### 9. No Statistical Analysis
**Status**: Confidence intervals and significance tests not implemented
**Impact**: Cannot determine if improvements are statistically significant.
**Reason**: Requires multiple experiment runs.
**Mitigation**: Add bootstrap confidence intervals.

### 10. No Human Evaluation
**Status**: All metrics are automated
**Impact**: May not reflect human judgment of answer quality.
**Reason**: Human evaluation is expensive and time-consuming.
**Mitigation**: Conduct small-scale user study (5-10 evaluators, 20-30 questions).

## What Should NOT Be Claimed

Based on these limitations, the following claims should NOT be made:

- ❌ "The system achieves X% accuracy" (no experiments run)
- ❌ "Adaptive retrieval outperforms fixed hybrid" (not tested)
- ❌ "The system reduces hallucination by X%" (not measured)
- ❌ "State-of-the-art performance" (no baselines compared)
- ❌ "Production-ready" (no stress testing, no security audit)

## What CAN Be Claimed

- ✅ "The infrastructure for evaluation is complete"
- ✅ "The system implements adaptive retrieval, evidence sufficiency, and abstention"
- ✅ "The architecture supports reproducible experiments"
- ✅ "The code is modular and testable"
- ✅ "The system treats documents as untrusted input"

## Next Steps to Address Limitations

1. Obtain real financial documents (SEC EDGAR)
2. Populate benchmark with 200+ verified questions
3. Run all experiments
4. Add LLM-as-judge evaluation
5. Test multiple embedding models and LLMs
6. Conduct human evaluation
7. Add statistical analysis
8. Perform security audit
9. Stress test with 1000+ documents
10. Document actual findings
