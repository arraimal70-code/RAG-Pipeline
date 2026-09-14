# Findings

> **STATUS: PENDING** — This document will be populated after experiments are executed.

## Purpose

This document records actual research findings discovered through experimentation. Findings are NOT pre-written — they emerge from running experiments and analyzing results.

## Expected Finding Categories

### Retrieval Method Findings
- Does hybrid retrieval outperform dense-only or BM25-only?
- For which query types does each method excel?
- Is RRF fusion better than weighted fusion?

### Adaptive Retrieval Findings
- Does query-type-aware weighting improve performance?
- Which query categories benefit most from adaptation?
- Is the overhead of classification justified?

### Chunking Findings
- Which chunking strategy produces best retrieval?
- Does structure-aware chunking help for financial documents?
- What is the optimal chunk size?

### Reranking Findings
- Does cross-encoder reranking justify its latency cost?
- What is the quality/latency tradeoff?
- Is there a Pareto-optimal configuration?

### Evidence Sufficiency Findings
- Does evidence checking reduce hallucination?
- What is the false refusal rate?
- Can the system reliably detect unanswerable questions?

### Citation Findings
- How often do LLMs generate unsupported citations?
- Does citation validation catch real errors?
- What is the citation precision/recall?

### Cost/Quality Findings
- What is the quality/cost Pareto frontier?
- Is GPT-4o-mini sufficient or is GPT-4o needed?
- What is the cost per query at different quality levels?

## How Findings Will Be Documented

Each finding will include:
1. **Observation**: What was measured
2. **Data**: Actual numbers from experiments
3. **Interpretation**: Why this might be the case
4. **Confidence**: How confident we are (sample size, variance)
5. **Implication**: What this means for system design
6. **Caveats**: Limitations of the finding

## Example Finding (Hypothetical)

> **Finding**: Adaptive retrieval improves Recall@5 by 8% for numerical queries but shows no improvement for conceptual queries.
>
> **Data**: EXP-06 (adaptive) vs EXP-03 (fixed hybrid). Numerical queries: 0.72 vs 0.66 Recall@5. Conceptual queries: 0.68 vs 0.67 Recall@5.
>
> **Interpretation**: Query classification successfully identifies numerical queries and shifts weights toward BM25, which excels at exact number matching. For conceptual queries, both methods use similar weights, so no improvement.
>
> **Confidence**: Medium. Based on 15 numerical queries and 20 conceptual queries. Variance is moderate.
>
> **Implication**: Adaptive retrieval is worth implementing if the workload contains many numerical queries. For purely conceptual workloads, fixed hybrid is sufficient.
>
> **Caveats**: Small sample size. May not generalize to other document types.

---

*This document will be updated as experiments are executed and results are analyzed.*
