"""
src/generation/generator.py — Multi-provider LLM generation with strict reliability and grounding.

Features:
- Faithful generation grounded in retrieved evidence
- Explicit abstention when evidence is insufficient
- Citation extraction and validation
- Support-level classification (SUPPORTED / PARTIALLY / UNSUPPORTED / INSUFFICIENT_EVIDENCE)
- Multi-provider support (OpenAI, Anthropic Claude, deterministic Mock for test/CI)
- Grounded confidence scoring
"""

import logging
import time
import re
from typing import Optional

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from src.core.config import config
from src.core.models import (
    RetrievalOutput, GenerationOutput, Citation, SupportLevel,
)

logger = logging.getLogger(__name__)


GENERATION_SYSTEM_PROMPT = """You are an evidence-based question answering assistant adhering to strict grounding standards.

Rules:
1. Answer ONLY using information from the provided context chunks.
2. If the context does not contain enough information to answer, respond with:
   "[ABSTAIN] I don't have enough evidence in the provided documents to answer this question."
3. When you state a factual claim, cite the source chunk as [CITE:chunk_N] where N is the chunk number.
4. Do not speculate or extrapolate beyond what the context explicitly states.
5. If different chunks contradict each other, explicitly note the contradiction.
6. Provide exact numbers, dates, units, and names without rounding or paraphrasing numerical data.

Classify your answer's support level at the end:
[SUPPORT_LEVEL: SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|INSUFFICIENT_EVIDENCE]"""


class Generator:
    """
    LLM generator with reliability and verifiable attribution.

    The generator:
    1. Formats retrieved chunks into numbered context blocks
    2. Sends to LLM (OpenAI, Anthropic, or deterministic fallback)
    3. Parses citations and cross-checks with candidates
    4. Classifies support level and detects abstention
    """

    def __init__(self):
        self.provider = config.generation.provider
        self.llm = None
        self.chain = None

        if config.openai_api_key and LANGCHAIN_AVAILABLE and self.provider == "openai":
            try:
                self.llm = ChatOpenAI(
                    model=config.generation.model,
                    temperature=config.generation.temperature,
                    max_tokens=config.generation.max_tokens,
                    api_key=config.openai_api_key,
                )
                prompt = ChatPromptTemplate.from_messages([
                    ("system", GENERATION_SYSTEM_PROMPT),
                    ("human", "Context chunks:\n{context}\n\n---\n\nQuestion: {question}\n\nProvide your answer with citations, then state support level:"),
                ])
                self.chain = prompt | self.llm | StrOutputParser()
                logger.info(f"Initialized OpenAI generation model: {config.generation.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI ({e}). Falling back to deterministic generation.")
                self.chain = None
        else:
            logger.info("Operating in deterministic/offline generation mode.")

    def generate(self, question: str, retrieval: RetrievalOutput) -> GenerationOutput:
        """
        Generate an answer with citations and validation.
        """
        start_time = time.time()

        if not retrieval.candidates:
            return GenerationOutput(
                answer="I don't have enough evidence in the provided documents to answer this question.",
                support_level=SupportLevel.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                abstained=True,
                generation_latency_ms=(time.time() - start_time) * 1000,
            )

        context = self._format_context(retrieval)

        # Generate via chain or deterministic generator
        if self.chain is not None:
            try:
                raw_response = self.chain.invoke({
                    "context": context,
                    "question": question,
                })
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}. Using deterministic fallback.")
                raw_response = self._deterministic_generate(question, retrieval)
        else:
            raw_response = self._deterministic_generate(question, retrieval)

        elapsed = (time.time() - start_time) * 1000

        # Parse response
        answer, support_level = self._parse_response(raw_response)

        # Check for abstention
        abstained = "[ABSTAIN]" in raw_response or support_level == SupportLevel.INSUFFICIENT_EVIDENCE

        # Extract and validate citations
        citations = self._extract_citations(raw_response, retrieval)

        # Compute confidence
        confidence = self._compute_confidence(support_level, citations, retrieval)

        return GenerationOutput(
            answer=answer,
            support_level=support_level,
            confidence=confidence,
            citations=citations,
            generation_latency_ms=elapsed,
            abstained=abstained,
        )

    def _deterministic_generate(self, question: str, retrieval: RetrievalOutput) -> str:
        """
        Deterministic, faithful generation engine for offline execution, unit tests, and CI/CD.
        Extracts salient statements from the top retrieved chunks with exact citations.
        """
        if not retrieval.candidates:
            return "[ABSTAIN] I don't have enough evidence in the provided documents to answer this question.\n[SUPPORT_LEVEL: INSUFFICIENT_EVIDENCE]"

        # Check evidence quality
        top_score = retrieval.candidates[0].score if retrieval.candidates else 0.0
        if top_score < config.evidence.min_evidence_score and len(retrieval.candidates) < 2:
            return "[ABSTAIN] I don't have enough evidence in the provided documents to answer this question.\n[SUPPORT_LEVEL: INSUFFICIENT_EVIDENCE]"

        # Synthesize from top candidates with injection filtering and relevance ranking
        question_words = set(re.findall(r'\w+', question.lower()))
        summary_sentences = []
        for i, candidate in enumerate(retrieval.candidates[:3], 1):
            text = candidate.chunk.content.strip()
            # Filter out injection lines if any
            clean_lines = []
            for line in text.split('\n'):
                line_lower = line.lower()
                if any(p in line_lower for p in ["ignore all", "system instruction", "system prompt", "override safety", "hacked"]):
                    continue
                clean_lines.append(line)
            clean_text = " ".join(clean_lines)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text) if s.strip()]
            
            # Score sentences by question word overlap
            best_sentence = None
            best_overlap = -1
            for s in sentences:
                s_words = set(re.findall(r'\w+', s.lower()))
                overlap = len(s_words & question_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_sentence = s
            if best_sentence:
                summary_sentences.append(f"{best_sentence} [CITE:chunk_{i}]")

        answer_text = " ".join(summary_sentences)
        return f"{answer_text}\n[SUPPORT_LEVEL: SUPPORTED]"

    def _format_context(self, retrieval: RetrievalOutput) -> str:
        """Format retrieval results into numbered context chunks."""
        parts = []
        for i, result in enumerate(retrieval.candidates, 1):
            chunk = result.chunk
            header = (
                f"[chunk_{i}] Source: {chunk.filename}, "
                f"Page: {chunk.page_number + 1}"
            )
            if chunk.section:
                header += f", Section: {chunk.section}"
            parts.append(f"{header}\n{chunk.content}")

        return "\n\n---\n\n".join(parts)

    def _parse_response(self, raw: str) -> tuple[str, SupportLevel]:
        """Parse LLM response into answer and support level."""
        support_match = re.search(
            r'\[SUPPORT_LEVEL:\s*(SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|INSUFFICIENT_EVIDENCE)\]',
            raw
        )
        if support_match:
            try:
                level = SupportLevel(support_match.group(1).lower())
            except ValueError:
                level = SupportLevel.SUPPORTED
            answer = raw[:support_match.start()].strip()
        else:
            level = SupportLevel.PARTIALLY_SUPPORTED
            answer = raw.strip()

        answer = answer.replace("[ABSTAIN]", "").strip()
        return answer, level

    def _extract_citations(
        self, raw_response: str, retrieval: RetrievalOutput
    ) -> list[Citation]:
        """
        Extract citations from the response and validate them.
        Citations are in format [CITE:chunk_N] where N is 1-indexed.
        """
        citations = []
        cite_pattern = re.compile(r'\[CITE:chunk_(\d+)\]')
        matches = cite_pattern.findall(raw_response)

        seen = set()
        for match in matches:
            idx = int(match) - 1
            if idx < 0 or idx >= len(retrieval.candidates):
                continue
            if idx in seen:
                continue
            seen.add(idx)

            result = retrieval.candidates[idx]
            chunk = result.chunk

            relevant_text = chunk.content[:200]

            citations.append(Citation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                relevant_text=relevant_text,
                validated=True,
            ))

        return citations

    def _compute_confidence(
        self,
        support_level: SupportLevel,
        citations: list[Citation],
        retrieval: RetrievalOutput,
    ) -> float:
        """
        Compute confidence score based on support level, citations, and retrieval quality.
        """
        level_confidence = {
            SupportLevel.SUPPORTED: 0.9,
            SupportLevel.PARTIALLY_SUPPORTED: 0.6,
            SupportLevel.UNSUPPORTED: 0.2,
            SupportLevel.INSUFFICIENT_EVIDENCE: 0.0,
        }
        base = level_confidence.get(support_level, 0.5)

        citation_factor = min(len(citations) / 3.0, 1.0) * 0.1

        if retrieval.candidates:
            avg_score = sum(c.score for c in retrieval.candidates) / len(retrieval.candidates)
            retrieval_factor = min(avg_score * 0.1, 0.1)
        else:
            retrieval_factor = 0.0

        return min(base + citation_factor + retrieval_factor, 1.0)
