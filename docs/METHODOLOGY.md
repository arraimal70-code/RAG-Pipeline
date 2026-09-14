# Methodology

## Research Approach

This project follows a systematic experimental methodology to investigate how RAG system components affect retrieval quality, factual reliability, latency, and cost.

## Experimental Design

### Independent Variables
- Retrieval strategy (dense, BM25, hybrid, adaptive)
- Chunking strategy (fixed, sentence, recursive, structure)
- Reranking (enabled/disabled)
- Evidence sufficiency (enabled/disabled)
- Citation validation (enabled/disabled)
- Top-K values (3, 5, 10)

### Dependent Variables
- Retrieval: Recall@K, MRR, nDCG
- Generation: Factual correctness, groundedness, hallucination rate
- Citations: Precision, recall, validation accuracy
- System: Latency (p50, p95), token usage, cost
- Abstention: Correct refusal rate, false refusal rate

### Control Variables
- Same benchmark dataset for all experiments
- Same embedding model (unless testing embeddings)
- Same LLM (unless testing LLMs)
- Same document set

## Experiment Execution

1. **Setup**: Configure experiment parameters
2. **Ingest**: Parse documents, chunk, embed, index
3. **Evaluate**: Run each benchmark question through the pipeline
4. **Measure**: Record metrics for each question
5. **Aggregate**: Compute aggregate metrics across all questions
6. **Compare**: Compare against baseline and other experiments
7. **Analyze**: Interpret results, identify patterns
8. **Document**: Record findings in RESULTS.md and FINDINGS.md

## Evaluation Protocol

### Retrieval Evaluation
For each question:
1. Retrieve top-K candidates
2. Check if correct source document is in candidates
3. Check if correct passage is in candidates
4. Compute Recall@1, Recall@3, Recall@5, Recall@10
5. Compute MRR (rank of first relevant result)
6. Compute nDCG@5

### Generation Evaluation
For each question:
1. Generate answer with citations
2. Compare to gold answer
3. Extract atomic claims
4. Evaluate each claim against evidence
5. Compute factual correctness, groundedness
6. Validate citations against retrieved chunks
7. Detect hallucinations (unsupported claims)

### Abstention Evaluation
For unanswerable questions:
1. Check if system abstains
2. Compute correct abstention rate
3. Compute false abstention rate (on answerable questions)
4. Compute unsupported answer rate

## Statistical Analysis

Where appropriate:
- **Bootstrap confidence intervals**: For metrics with variance
- **Paired comparisons**: When comparing two configurations on same questions
- **Effect size**: To determine if improvements are meaningful

**Note**: Statistical tests require sufficient sample size. With <30 questions, results are indicative but not statistically significant.

## Reproducibility

Every experiment records:
- Full configuration snapshot
- Dataset version
- Model versions (embedding, LLM, reranker)
- Timestamp
- Git commit SHA (if available)
- Random seeds (where applicable)

This allows exact reproduction of any experiment.

## Limitations of Methodology

1. **Heuristic evaluation**: Factual correctness uses support-level as proxy, not LLM-as-judge
2. **Small sample**: 20 questions is insufficient for robust conclusions
3. **Single domain**: Financial documents only, may not generalize
4. **No human evaluation**: All metrics are automated
5. **No statistical significance**: Sample size too small for rigorous testing

## Mitigations

1. Add LLM-as-judge evaluation (GPT-4o)
2. Expand benchmark to 200+ questions
3. Test on multiple document domains
4. Conduct small human evaluation (5-10 evaluators)
5. Run experiments multiple times with different seeds

## Ethical Considerations

- **No financial advice**: System is for research, not investment decisions
- **Public documents only**: Uses publicly available SEC filings
- **No personal data**: No PII in benchmark or documents
- **Transparent limitations**: Clearly states what is and isn't validated
