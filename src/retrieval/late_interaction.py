"""
src/retrieval/late_interaction.py — ColBERT-Style Token-Level Late Interaction Engine.

Implements Stanford ColBERT (Khattab & Zaharia, SIGIR 2020) Late Interaction
with Token MaxSim Scoring:
    MaxSim(Q, D) = sum_{i in Q} w_i * max_{j in D} (E_{q,i} . E_{d,j}^T)

Preserves token-level semantic granularity without compressing
the entire document/query into a single 1D vector.
"""

import hashlib
import logging
import math
import re
from dataclasses import dataclass, field
from typing import ClassVar

from src.core.models import RetrievalResult

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
    alignments: list[TokenAlignment] = field(default_factory=list)
    unmatched_query_tokens: list[str] = field(default_factory=list)


class TokenEmbedder:
    """
    Produces dense normalized token-level vector representations.
    Uses subword n-gram feature projections to ensure high-dimensional semantic
    overlap and exact match fidelity without requiring heavy GPU checkpoints.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    def _hash_token_feature(self, token: str, seed: int) -> int:
        h = hashlib.sha256(f"{seed}:{token}".encode()).digest()
        return int.from_bytes(h[:4], "little") % self.dimension

    def embed_token(self, token: str) -> list[float]:
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
                    ngram = token_clean[k:k + n]
                    ng_idx = self._hash_token_feature(ngram, 53 + n)
                    vec[ng_idx] += 0.35 / len(token_clean)

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        return vec

    def embed_sequence(self, tokens: list[str]) -> list[list[float]]:
        """Embed an ordered list of tokens into token vectors."""
        return [self.embed_token(tok) for tok in tokens]


class LateInteractionScorer:
    """
    ColBERT-style Late-Interaction Token MaxSim Scoring & Reranking Engine.
    """

    STOPWORDS: ClassVar[set[str]] = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "and", "or", "but", "if", "then", "else", "what",
        "which", "who", "whom", "this", "that", "these", "those"
    }

    def __init__(self, dimension: int = 128, stopword_penalty: float = 0.3) -> None:
        self.embedder = TokenEmbedder(dimension=dimension)
        self.stopword_penalty = stopword_penalty

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into alphanumeric words and technical terms."""
        if not text:
            return []
        return re.findall(r"[A-Za-z0-9]+(?:[\-_.$%][A-Za-z0-9]+)*", text)

    @staticmethod
    def _dot_product(vec1: list[float], vec2: list[float]) -> float:
        """Compute inner product between two unit-normalized vectors."""
        return sum(a * b for a, b in zip(vec1, vec2, strict=False))

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
        alignments: list[TokenAlignment] = []
        unmatched: list[str] = []

        for i, (q_tok, q_vec) in enumerate(zip(q_tokens, q_vectors, strict=False)):
            q_lower = q_tok.lower()
            weight = self.stopword_penalty if q_lower in self.STOPWORDS else 1.0
            total_weight += weight

            best_sim = -1.0
            best_j = -1
            best_d_tok = ""

            for j, (d_tok, d_vec) in enumerate(zip(d_tokens, d_vectors, strict=False)):
                sim = self._dot_product(q_vec, d_vec)
                # Exact match boost
                if q_lower == d_tok.lower():
                    sim = max(sim, 1.0)

                if sim > best_sim:
                    best_sim = sim
                    best_j = j
                    best_d_tok = d_tok

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

        normalized = total_score / total_weight if total_weight > 0 else 0.0

        return MaxSimScore(
            raw_score=total_score,
            normalized_score=min(1.0, normalized),
            alignments=alignments,
            unmatched_query_tokens=unmatched,
        )

    def score_passage(self, query: str, doc_text: str) -> MaxSimScore:
        """Alias for compute_maxsim."""
        return self.compute_maxsim(query, doc_text)

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int = 5,
        alpha: float = 0.4,
    ) -> list[RetrievalResult]:
        """
        Rerank retrieval candidates using ColBERT-style Late-Interaction MaxSim scoring.
        """
        if not candidates:
            return []

        scored_candidates: list[tuple[float, RetrievalResult, MaxSimScore]] = []
        max_orig_score = max((c.score for c in candidates), default=1.0)
        if max_orig_score <= 0.0:
            max_orig_score = 1.0

        for candidate in candidates:
            maxsim = self.compute_maxsim(query, candidate.chunk.content)
            norm_orig_score = max(0.0, candidate.score / max_orig_score)
            blended_score = alpha * norm_orig_score + (1.0 - alpha) * maxsim.normalized_score

            candidate_copy = RetrievalResult(
                chunk=candidate.chunk,
                score=blended_score,
                retrieval_method=f"{candidate.retrieval_method}+colbert_maxsim",
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

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        reranked: list[RetrievalResult] = []
        for rank, (_, cand, _) in enumerate(scored_candidates[:top_k], start=1):
            cand.rank = rank
            reranked.append(cand)

        return reranked
