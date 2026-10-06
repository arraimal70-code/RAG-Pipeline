# Mathematical Formulations & Retrieval Theory

This document details the mathematical formulations implemented in the Evidence-Aware RAG Pipeline and its experimental research extensions.

---

## 1. Hybrid Reciprocal Rank Fusion (RRF)

To combine disjoint score distributions from dense semantic embeddings and sparse lexical BM25 retrieval without arbitrary score scaling, Reciprocal Rank Fusion (Cormack et al., SIGIR 2009) is formulated with query-adaptive weights:

\[
\text{RRF}(d) = \sum_{m \in M} w_m \cdot \frac{1}{k + r_m(d)}
\]

Where:
- \( M = \{\text{dense}, \text{lexical}\} \) is the set of retrieval modalities.
- \( r_m(d) \in \mathbb{N}_{\ge 1} \) is the 1-based rank of document chunk \( d \) in modality \( m \).
- \( k = 60 \) is the standard smoothing constant preventing top-ranked documents from dominating.
- \( w_m \) are weights assigned dynamically by the query analyzer policy based on query intent (e.g. \( w_{\text{lexical}} > w_{\text{dense}} \) for exact code/symbol lookups, \( w_{\text{dense}} > w_{\text{lexical}} \) for conceptual questions, with \( \sum_m w_m = 1 \)).

---

## 2. Contextual Chunk Grounding

Following Anthropic's Contextual Retrieval formulation, each text segment \( c_i \) within document \( D \) is situated before embedding and inverted indexing:

\[
c'_i = \mathcal{P}(D, S_i) \circ c_i = \left[ \text{Document: } \mathcal{T}(D) \mid \text{Section: } \mathcal{H}(S_i) \mid \text{Scope: } \mathcal{E}(D) \right] \circ c_i
\]

Where:
- \( \mathcal{T}(D) \) is the document title or identifier.
- \( \mathcal{H}(S_i) \) is the hierarchical section breadcrumb.
- \( \mathcal{E}(D) \) is the document scope synopsis.
- \( \circ \) denotes prefix concatenation.

Situating text chunks prevents loss of antecedent scope when text is chunked into small windows.

---

## 3. Atomic Claim Faithfulness (FActScore Method)

Following Min et al. (EMNLP 2023), generated answers \( y \) are decomposed into atomic assertions \( A(y) = \{a_1, a_2, \dots, a_m\} \):

\[
\text{Faithfulness}(y, \mathcal{C}) = \frac{1}{|A(y)|} \sum_{a \in A(y)} \mathbb{I}\left( \mathcal{C} \models a \right)
\]

\[
\text{HallucinationRate}(y, \mathcal{C}) = 1.0 - \text{Faithfulness}(y, \mathcal{C})
\]

Where \( \mathbb{I}\left( \mathcal{C} \models a \right) = 1 \) if claim \( a \) is entailed by retrieved context evidence \( \mathcal{C} \), and \( 0 \) otherwise.

---

## 4. Information Retrieval Metrics

For ranking evaluation over queries \( Q \):

### Discounted Cumulative Gain (NDCG@K)
\[
\text{DCG@K} = \sum_{i=1}^{K} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}, \quad \text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}
\]

### Mean Reciprocal Rank (MRR@K)
\[
\text{MRR@K} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\min(\{r \le K : \text{rel}_r(q) = 1\} \cup \{\infty\})}
\]

---

## 5. Experimental Extensions

### Late-Interaction Token MaxSim Scoring (`src/experimental/late_interaction.py`)
Inspired by ColBERT (Khattab & Zaharia, SIGIR 2020), token-level alignment avoids cross-attention overhead:

\[
\text{MaxSim}(Q, D) = \sum_{i=1}^{|Q|} \max_{j=1}^{|D|} \left( \mathbf{e}_{q,i}^\top \mathbf{e}_{d,j} \right)
\]

### Pseudo-Relevance Feedback (Rocchio PRF, `src/experimental/prf.py`)
Expands initial query representation with top-ranked pseudo-relevant candidates while applying cosine-drift guardrails:

\[
\mathbf{q}_{\text{exp}} = \alpha \mathbf{q}_0 + \frac{\beta}{|D_R|} \sum_{d \in D_R} \mathbf{d}, \quad \text{Condition: } \cos(\mathbf{q}_0, \mathbf{q}_{\text{exp}}) \ge \tau_{\text{drift}}
\]

### Maximal Marginal Relevance (MMR, `src/experimental/mmr.py`)
Balances query relevance and document diversity (Carbonell & Goldstein, SIGIR 1998):

\[
\text{MMR} = \arg\max_{d_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}(d_i, Q) - (1 - \lambda) \max_{d_j \in S} \text{Sim}(d_i, d_j) \right]
\]
