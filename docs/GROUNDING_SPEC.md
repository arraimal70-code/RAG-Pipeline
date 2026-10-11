# Factual Grounding & Hallucination Mitigation Specification

## 1. Overview
This specification details the factual reliability, citation attribution, and pre-stream hallucination gating architecture implemented in:
- `src/claims/nli_verifier.py`
- `src/citations/validator.py`
- `src/grounding/gatekeeper.py`

Unlike naive RAG systems that rely on string substring search or word-overlap ratios, this framework enforces **Natural Language Inference (NLI)** premise-hypothesis validation.

---

## 2. NLI Premise-Hypothesis Verification Protocol

### Failure Mode of Keyword Matching
Given the source evidence:
> *"Legacy Data Services revenue fell by 17.8% to $5,896.0 million in FY2024."*

A hallucinated statement:
> *"Legacy Data Services revenue rose by 17.8% to $5,896.0 million in FY2024."*

shares 85% lexical overlap. Standard token validators mark this hallucinated claim as "fully supported".

### 3-Class NLI Logic
The `NLIVerifier` evaluates the premise $P$ (retrieved document chunks) against hypothesis $H$ (generated atomic claim):

$$\text{NLI}(P, H) \in \{\text{ENTAILMENT}, \text{NEUTRAL}, \text{CONTRADICTION}\}$$

1. **Directional Polarity Checks**: Evaluates financial antonym sets (e.g. `increase` / `gain` / `growth` vs `decrease` / `drop` / `decline`). If hypothesis directional polarity opposes premise evidence, relation is classified as `CONTRADICTION` with high confidence.
2. **Explicit Negation Inversion**: Detects negation inversions (`not`, `never`, `failed to`) between premise and claim.
3. **Numerical Attribute Binding**: Confirms that specific numerical entities, currency amounts, and percentages in the hypothesis match the exact values and metrics in the source text.

---

## 3. Character-Span Citation Attribution

The `CitationValidator` locates character offsets for cited claims:
1. **Exact Substring Match**: Searches for case-insensitive substring in `chunk.content`. If found, computes `char_start` and `char_end`.
2. **Sliding-Window Token Alignment**: If punctuation or whitespace differs, runs sliding-window token alignment across the passage to locate optimal start/end indices.
3. **Contradiction Invalidation**: Discards any citation where the cited passage contradicts the assertion.

---

## 4. Pre-Stream Hallucination Gatekeeper Policies

The `HallucinationGatekeeper` acts as an automated circuit-breaker between generation and presentation:

| Policy | Trigger Condition | System Action | Output Support Level |
| :--- | :--- | :--- | :--- |
| **PASS** | $\text{Contradictions} = 0 \land \text{Support Ratio} \ge 0.70$ | Emits completion unaltered with citation metadata. | `SUPPORTED` |
| **REDACT** | $\text{Support Ratio} \ge 0.40 \land \text{Contradictions} \le 1$ | Automatically excises unsupported sentences; preserves grounded sentences. | `PARTIALLY_SUPPORTED` |
| **ABSTAIN** | $\text{Support Ratio} < 0.40 \lor \text{Contradictions} > 1$ | Suppresses answer. Emits explicit structured abstention with audit log. | `INSUFFICIENT_EVIDENCE` or `CONTRADICTORY_EVIDENCE` |
