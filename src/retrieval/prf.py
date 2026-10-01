r"""
src/retrieval/prf.py — Rocchio Pseudo-Relevance Feedback (PRF) & RM3 Query Expansion Engine.

Implements classic Information Retrieval Rocchio & RM3 Pseudo-Relevance Feedback:
    q_new = \alpha q_0 + \frac{\beta}{|D_R|} \sum_{d \in D_R} d

Key Architectural Features:
1. Lexical PRF (RM3-style): Extracts top discriminative non-stopword terms from
   the top pseudo-relevant passages using Robertson-Spärck Jones (RSJ) / BM25 salience.
2. Dense Rocchio Expansion: Blends the dense query embedding with the mean centroid
   of top pseudo-relevant document embeddings.
3. Anti-Drift Guardrail: Enforces a semantic cosine threshold between original query
   and expanded query vector to prevent semantic drift.
"""

import math
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

from src.core.models import RetrievalResult, TextChunk
from src.embeddings.embedder import Embedder, get_embedder

logger = logging.getLogger(__name__)


@dataclass
class PRFExpansionResult:
    """Artifact of PRF query expansion."""
    original_query: str
    expanded_query: str
    expansion_terms: List[Tuple[str, float]]
    dense_vector_drift: float  # Cosine similarity between q0 and q_exp
    feedback_docs_count: int
    drift_guarded: bool


class PseudoRelevanceFeedbackEngine:
    """
    Rocchio & RM3 Pseudo-Relevance Feedback (PRF) Query Expansion Engine.
    """

    STOPWORDS: Set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an",
        "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
        "before", "being", "below", "between", "both", "but", "by", "can't",
        "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
        "doing", "don't", "down", "during", "each", "few", "for", "from",
        "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
        "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
        "i", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
        "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
        "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
        "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "should", "shouldn't", "so", "some", "such", "than", "that", "the",
        "their", "theirs", "them", "themselves", "then", "there", "these",
        "they", "this", "those", "through", "to", "too", "under", "until", "up",
        "very", "was", "wasn't", "we", "were", "weren't", "what", "when",
        "where", "which", "while", "who", "whom", "why", "with", "won't",
        "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
        "tell", "explain", "describe", "find", "give", "show", "list",
    }

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        alpha: float = 0.75,       # Original query weight
        beta: float = 0.25,        # Feedback documents weight
        num_feedback_docs: int = 3,
        num_expansion_terms: int = 5,
        min_cosine_guardrail: float = 0.60,
    ):
        self.embedder = embedder or get_embedder()
        self.alpha = alpha
        self.beta = beta
        self.num_feedback_docs = num_feedback_docs
        self.num_expansion_terms = num_expansion_terms
        self.min_cosine_guardrail = min_cosine_guardrail

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric words."""
        return re.findall(r"[a-z0-9]+(?:[\-_][a-z0-9]+)*", text.lower())

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        norm1 = math.sqrt(sum(x * x for x in vec1))
        norm2 = math.sqrt(sum(y * y for y in vec2))
        if norm1 < 1e-9 or norm2 < 1e-9:
            return 0.0
        return sum(a * b for a, b in zip(vec1, vec2)) / (norm1 * norm2)

    def extract_salient_terms(
        self,
        query: str,
        feedback_docs: List[str],
        top_m: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Extract top salient discriminative terms from feedback documents using
        TF-IDF / BM25 term salience, ignoring stopwords and original query terms.
        """
        query_terms = set(self._tokenize(query))
        query_stems = {t.rstrip('s') for t in query_terms}
        doc_token_lists = [self._tokenize(doc) for doc in feedback_docs]
        total_docs = len(doc_token_lists)

        if total_docs == 0:
            return []

        # Document frequencies across feedback set
        df: Counter = Counter()
        for doc_tokens in doc_token_lists:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                df[token] += 1

        # Term scores using RM3 pseudo-relevance feedback weighting:
        # P(t | D_R) is high when term occurs across feedback documents with high TF
        term_scores: Dict[str, float] = {}
        for doc_tokens in doc_token_lists:
            tf = Counter(doc_tokens)
            doc_len = max(len(doc_tokens), 1)
            for token, count in tf.items():
                tok_stem = token.rstrip('s')
                if token in self.STOPWORDS or token in query_terms or tok_stem in query_stems or len(token) < 3:
                    continue
                # Term frequency normalized by doc length
                tf_norm = count / doc_len
                # Feedback document frequency multiplier: terms appearing across multiple feedback docs are boosted
                doc_coverage = (df[token] + 0.5) / (total_docs + 0.5)
                score = tf_norm * (1.0 + math.log1p(doc_coverage * 2.0))
                term_scores[token] = term_scores.get(token, 0.0) + score

        # Sort descending
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:top_m]

    def expand_query(
        self,
        query: str,
        initial_candidates: List[RetrievalResult],
        query_embedding: Optional[List[float]] = None,
    ) -> Tuple[PRFExpansionResult, List[float]]:
        """
        Execute Rocchio PRF expansion over initial retrieval candidates.

        Returns:
            Tuple of (PRFExpansionResult, expanded_dense_vector).
        """
        if not initial_candidates:
            # Nothing to expand from
            q_emb = query_embedding or self.embedder.embed_query(query)
            return (
                PRFExpansionResult(
                    original_query=query,
                    expanded_query=query,
                    expansion_terms=[],
                    dense_vector_drift=1.0,
                    feedback_docs_count=0,
                    drift_guarded=False,
                ),
                q_emb,
            )

        # 1. Select top feedback documents
        top_candidates = initial_candidates[: self.num_feedback_docs]
        feedback_texts = [c.chunk.content for c in top_candidates]

        # 2. Extract salient terms for lexical expansion
        salient_terms = self.extract_salient_terms(
            query, feedback_texts, top_m=self.num_expansion_terms
        )
        expansion_words = [t[0] for t in salient_terms]

        if expansion_words:
            expanded_query_str = f"{query} " + " ".join(expansion_words)
        else:
            expanded_query_str = query

        # 3. Dense Rocchio vector computation
        q_emb = query_embedding or self.embedder.embed_query(query)
        doc_embeddings = self.embedder.embed(feedback_texts)

        # Centroid of feedback docs
        dim = len(q_emb)
        centroid = [0.0] * dim
        for doc_emb in doc_embeddings:
            for d in range(dim):
                centroid[d] += doc_emb[d]
        num_docs = len(doc_embeddings)
        centroid = [c / num_docs for c in centroid]

        # Rocchio formula: alpha * q0 + beta * centroid
        expanded_vec = [
            self.alpha * q_emb[d] + self.beta * centroid[d]
            for d in range(dim)
        ]

        # L2-normalize
        norm = math.sqrt(sum(x * x for x in expanded_vec))
        if norm > 1e-9:
            expanded_vec = [x / norm for x in expanded_vec]

        # 4. Anti-Drift Guardrail
        cosine_sim = self._cosine_similarity(q_emb, expanded_vec)
        drift_guarded = False

        if cosine_sim < self.min_cosine_guardrail:
            logger.warning(
                f"PRF query drift detected (cos={cosine_sim:.3f} < {self.min_cosine_guardrail:.3f}). "
                "Applying conservative interpolation guardrail."
            )
            # Pull vector back towards original query
            guarded_vec = [
                0.90 * q_emb[d] + 0.10 * expanded_vec[d]
                for d in range(dim)
            ]
            g_norm = math.sqrt(sum(x * x for x in guarded_vec))
            if g_norm > 1e-9:
                expanded_vec = [x / g_norm for x in guarded_vec]
            cosine_sim = self._cosine_similarity(q_emb, expanded_vec)
            drift_guarded = True
            # Revert expanded string to prevent lexical query poisoning
            expanded_query_str = query

        result = PRFExpansionResult(
            original_query=query,
            expanded_query=expanded_query_str,
            expansion_terms=salient_terms,
            dense_vector_drift=cosine_sim,
            feedback_docs_count=len(top_candidates),
            drift_guarded=drift_guarded,
        )

        return result, expanded_vec
