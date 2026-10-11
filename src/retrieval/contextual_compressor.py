"""
src/retrieval/contextual_compressor.py — Contextual Extractive Compression Engine.

Addresses the Tier-1 Retrieval Funnel requirement:
Downstream LLM generators degrade when overloaded with irrelevant context
(the "Lost-in-the-Middle" phenomenon, Liu et al., 2023).

This module implements sentence-level contextual compression:
1. Deconstructs retrieved candidate chunks into discrete sentence units.
2. Evaluates semantic relevance and keyword alignment of each sentence against the query.
3. Retains only high-salience evidence sentences, pruning boilerplate and distracting noise.
4. Preserves character lineage while drastically improving prompt signal-to-noise ratio
   and reducing generation token latency.
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from src.core.models import RetrievalResult, TextChunk

logger = logging.getLogger(__name__)


@dataclass
class CompressedSentence:
    text: str
    score: float
    sentence_idx: int
    char_offset: int


@dataclass
class CompressionReport:
    original_chars: int
    compressed_chars: int
    compression_ratio: float
    retained_sentences: int
    total_sentences: int


class ContextualCompressor:
    """
    Sentence-level extractive contextual compressor for retrieved candidate chunks.
    """

    SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')

    def __init__(
        self,
        similarity_threshold: float = 0.25,
        max_sentences_per_chunk: int = 5,
        min_sentences_per_chunk: int = 1,
        include_adjacent_context: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_sentences_per_chunk = max_sentences_per_chunk
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.include_adjacent_context = include_adjacent_context

    def compress_chunk(self, query: str, chunk: TextChunk) -> Tuple[str, CompressionReport]:
        """
        Compress a single chunk by scoring its sentences against the query.
        """
        raw_content = chunk.content.strip()
        if not raw_content:
            return "", CompressionReport(0, 0, 1.0, 0, 0)

        # Do not compress structured tables (preserving matrix integrity)
        if "|" in raw_content and "\n" in raw_content and chunk.metadata.get("is_table"):
            return raw_content, CompressionReport(len(raw_content), len(raw_content), 1.0, 1, 1)

        raw_sentences = self.SENTENCE_SPLIT_REGEX.split(raw_content)
        raw_sentences = [s.strip() for s in raw_sentences if s.strip()]

        if len(raw_sentences) <= self.min_sentences_per_chunk:
            return raw_content, CompressionReport(len(raw_content), len(raw_content), 1.0, len(raw_sentences), len(raw_sentences))

        # Score each sentence against query
        q_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        scored_sents: List[CompressedSentence] = []
        offset = 0

        for idx, s in enumerate(raw_sentences):
            s_tokens = set(re.findall(r'\b\w+\b', s.lower()))
            if not s_tokens:
                offset += len(s) + 1
                continue

            # Compute lexical intersection with query
            overlap = len(q_tokens & s_tokens)
            score = overlap / math.sqrt(max(len(q_tokens), 1) * len(s_tokens))

            # Query phrase containment bonus
            if any(term in s.lower() for term in query.lower().split() if len(term) > 3):
                score += 0.2

            scored_sents.append(CompressedSentence(
                text=s,
                score=score,
                sentence_idx=idx,
                char_offset=offset
            ))
            offset += len(s) + 1

        # Sort sentences by relevance
        scored_sents.sort(key=lambda x: x.score, reverse=True)

        # Select sentences meeting threshold up to max_sentences
        selected_indices = set()
        for cs in scored_sents:
            if cs.score >= self.similarity_threshold or len(selected_indices) < self.min_sentences_per_chunk:
                selected_indices.add(cs.sentence_idx)
                if self.include_adjacent_context:
                    # Include immediate previous or next sentence if relevant
                    if cs.sentence_idx > 0 and cs.score > 0.4:
                        selected_indices.add(cs.sentence_idx - 1)
                    if cs.sentence_idx < len(raw_sentences) - 1 and cs.score > 0.4:
                        selected_indices.add(cs.sentence_idx + 1)
            if len(selected_indices) >= self.max_sentences_per_chunk:
                break

        if not selected_indices:
            # Fallback: keep first sentence
            selected_indices = {0}

        # Re-assemble in original document order
        sorted_indices = sorted(selected_indices)
        compressed_text = " ".join(raw_sentences[i] for i in sorted_indices)

        orig_len = len(raw_content)
        comp_len = len(compressed_text)
        report = CompressionReport(
            original_chars=orig_len,
            compressed_chars=comp_len,
            compression_ratio=round(comp_len / max(orig_len, 1), 3),
            retained_sentences=len(sorted_indices),
            total_sentences=len(raw_sentences)
        )
        return compressed_text, report

    def compress_candidates(
        self,
        query: str,
        candidates: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Compress all retrieved candidates in-place while archiving uncompressed content.
        """
        for item in candidates:
            orig_text = item.chunk.content
            compressed_text, report = self.compress_chunk(query, item.chunk)

            # Store original in metadata
            item.chunk.metadata["uncompressed_content"] = orig_text
            item.chunk.metadata["compression_ratio"] = report.compression_ratio
            item.chunk.content = compressed_text
            item.chunk.token_count = max(1, len(compressed_text.split()))

        logger.info(
            f"ContextualCompressor compressed {len(candidates)} candidates. "
            f"Average retention: {sum(c.chunk.metadata.get('compression_ratio', 1.0) for c in candidates)/max(len(candidates),1):.1%}"
        )
        return candidates
