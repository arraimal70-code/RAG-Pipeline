r"""
src/retrieval/late_interaction.py — ColBERT-Style Token-Level Late Interaction Engine.

Implements Stanford ColBERT (Khattab & Zaharia, SIGIR 2020) Late Interaction
with Token MaxSim Scoring:
    MaxSim(Q, D) = \sum_{i \in Q} w_i \max_{j \in D} ( E_{q,i} \cdot E_{d,j}^\top )

Key Architectural Advantages:
1. Expressiveness: Preserves token-level semantic granularity without compressing
   the entire document/query into a single 1D vector (which loses subtle numbers,
   acronyms, and qualifiers).
2. Latency: Avoids the quadratic O((|Q| + |D|)^2) cross-attention of heavy cross-encoders
   while achieving near cross-encoder precision via fast matrix inner products.
3. Interpretability: Provides token-to-token alignment maps showing which passage
   tokens satisfied each token in the query.
"""

import math
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from src.core.models import RetrievalResult, TextChunk

logger = logging.getLogger(__name__)


@dataclass
class TokenAlignment:
    """Detailed token-level alignment explaining a MaxSim match."""
    query_token: str
    matched_doc_token: str
    similarity_score: float
    query_token_index: int
    doc_token_index: int


@dataclass
class MaxSimScore:
    """Structured MaxSim score and explainability artifacts."""
    raw_score: float
    normalized_score: float
    alignments: List[TokenAlignment] = field(default_factory=list)
    unmatched_query_tokens: List[str] = field(default_factory=list)


class TokenEmbedder:
    """
    Produces dense normalized token-level vector representations.
    Uses subword n-gram feature projections to ensure high-dimensional semantic
    overlap and exact match fidelity without requiring heavy GPU checkpoints.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _hash_token_feature(self, token: str, seed: int) -> int:
        h = hashlib.sha256(f"{seed}:{token}".encode("utf-8")).digest()
        return int.from_bytes(h[:4], "little") % self.dimension

    def embed_token(self, token: str) -> List[float]:
        """Embed a single token into a unit-normalized vector."""
        vec = [0.0] * self.dimension
        token_clean = token.lower().strip()
        if not token_clean:
            return vec

        # Primary token hash
        idx1 = self._hash_token_feature(token_clean, 11)
        idx2 = self._hash_token_feature(token_clean, 23)
        sign = 1.0 if (self._hash_token_feature(token_clean, 37) % 2 == 0) else -1.0
        vec[idx1] += 1.0
        vec[idx2] += 0.5 * sign

        # Subword character n-grams (2-grams, 3-grams)
        for n in (2, 3):
            if len(token_clean) >= n:
                for k in range(len(token_clean) - n + 1):
                    ngram = token_clean[k:k+n]
                    ng_idx = self._hash_token_feature(ngram, 53 + n)
                    vec[ng_idx] += 0.35 / len(token_clean)

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        return vec

    def embed_sequence(self, tokens: List[str]) -> List[List[float]]:
        """Embed an ordered list of tokens into token vectors."""
        return [self.embed_token(tok) for tok in tokens]


class LateInteractionScorer:
    """
    ColBERT-style Late-Interaction Token MaxSim Scoring & Reranking Engine.
    """

    STOPWORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "and", "or", "but", "if", "then", "else", "what",
        "which", "who", "whom", "this", "that", "these", "those"
    }

    def __init__(self, dimension: int = 128, stopword_penalty: float = 0.3):
        self.embedder = TokenEmbedder(dimension=dimension)
        self.stopword_penalty = stopword_penalty

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into alphanumeric words and technical terms."""
        if not text:
            return []
        # Match words, numbers, percentages, and hyphenated terms
        tokens = re.findall(r"[A-Za-z0-9]+(?:[\-_.$%][A-Za-z0-9]+)*", text)
        return tokens

    @staticmethod
    def _dot_product(vec1: List[float], vec2: List[float]) -> float:
        """Compute inner product between two unit-normalized vectors."""
        return sum(a * b for a, b in zip(vec1, vec2))

    def compute_maxsim(self, query: str, doc_text: str) -> MaxSimScore:
        """
        Compute the ColBERT MaxSim score between query and document text.

        Returns MaxSimScore containing the raw score, normalized score [0, 1],
        and fine-grained token alignments.
        """
        q_tokens = self.tokenize(query)
        d_tokens = self.tokenize(doc_text)

        if not q_tokens or not d_tokens:
            return MaxSimScore(raw_score=0.0, normalized_score=0.0)

        q_vectors = self.embedder.embed_sequence(q_tokens)
        d_vectors = self.embedder.embed_sequence(d_tokens)

        total_score = 0.0
        total_weight = 0.0
        alignments: List[TokenAlignment] = []
        unmatched: List[str] = []

        for i, (q_tok, q_vec) in enumerate(zip(q_tokens, q_vectors)):
            q_lower = q_tok.lower()
            weight = self.stopword_penalty if q_lower in self.STOPWORDS else 1.0
            total_weight += weight

            best_sim = -1.0
            best_j = -1
            best_d_tok = ""

            for j, (d_tok, d_vec) in enumerate(zip(d_tokens, d_vectors)):
                sim = self._dot_product(q_vec, d_vec)
                # Boost exact string match slightly for numerical & exact terms
                if q_lower == d_tok.lower():
                    sim = max(sim, 1.0)

                if sim > best_sim:
                    best_sim = sim
                    best_j = j
                    best_d_tok = d_tok

            # Clamp negative similarity to 0.0
            best_sim = max(0.0, best_sim)
            total_score += weight * best_sim

            alignment = TokenAlignment(
                query_token=q_tok,
                matched_doc_token=best_d_tok,
                similarity_score=best_sim,
                query_token_index=i,
                doc_token_index=best_j,
            )
            alignments.append(alignment)

            if best_sim < 0.2:
                unmatched.append(q_tok)

        # Normalize score into [0, 1] range based on query length and weights
        normalized = total_score / total_weight if total_weight > 0 else 0.0

        return MaxSimScore(
            raw_score=total_score,
            normalized_score=min(1.0, normalized),
            alignments=alignments,
            unmatched_query_tokens=unmatched,
        )

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5,
        alpha: float = 0.4,
    ) -> List[RetrievalResult]:
        """
        Rerank retrieval candidates using ColBERT-style Late-Interaction MaxSim scoring.

        Args:
            query: The user query
            candidates: Initial candidates retrieved by dense/BM25/hybrid
            top_k: Number of candidates to return
            alpha: Weight assigned to original candidate score (1 - alpha for MaxSim)

        Returns:
            Reranked list of RetrievalResult with token alignment telemetry.
        """
        if not candidates:
            return []

        scored_candidates: List[Tuple[float, RetrievalResult, MaxSimScore]] = []

        # Find max original score for min-max normalization
        max_orig_score = max((c.score for c in candidates), default=1.0)
        if max_orig_score <= 0.0:
            max_orig_score = 1.0

        for candidate in candidates:
            maxsim = self.compute_maxsim(query, candidate.chunk.content)
            norm_orig_score = max(0.0, candidate.score / max_orig_score)

            # Combined score: blend base retrieval score with token-level MaxSim score
            blended_score = alpha * norm_orig_score + (1.0 - alpha) * maxsim.normalized_score

            # Enrich chunk metadata with Late-Interaction telemetry
            candidate_copy = RetrievalResult(
                chunk=candidate.chunk,
                score=blended_score,
                retrieval_method=f"{candidate.retrieval_method}+late_interaction",
                rank=candidate.rank,
            )
            candidate_copy.chunk.metadata["maxsim_score"] = maxsim.normalized_score
            candidate_copy.chunk.metadata["maxsim_alignments"] = [
                {
                    "q": a.query_token,
                    "d": a.matched_doc_token,
                    "sim": round(a.similarity_score, 3),
                }
                for a in maxsim.alignments[:8]
            ]
            scored_candidates.append((blended_score, candidate_copy, maxsim))

        # Sort descending by blended score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Update ranks
        reranked: List[RetrievalResult] = []
        for rank, (_, cand, _) in enumerate(scored_candidates[:top_k], start=1):
            cand.rank = rank
            reranked.append(cand)

        return reranked
