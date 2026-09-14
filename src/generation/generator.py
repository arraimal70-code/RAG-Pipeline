"""
src/generation/generator.py — LLM generation with reliability features.

Features:
- Faithful generation grounded in retrieved evidence
- Explicit abstention when evidence is insufficient
- Citation extraction and validation
- Support-level classification (SUPPORTED / PARTIALLY / UNSUPPORTED / UNKNOWN)
- Structured output parsing
"""

import logging
import time
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

from src.core.config import config
from src.core.models import (
    RetrievalOutput, GenerationOutput, Citation, SupportLevel,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────

GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a precise, evidence-based question answering assistant.

You MUST follow these rules:
1. Answer ONLY using information from the provided context.
2. If the context does not contain enough information to answer, respond with:
   "[ABSTAIN] I don't have enough evidence in the provided documents to answer this question."
3. When you cite information, reference it as [CITE:chunk_N] where N is the chunk number.
4. Do not add information beyond what the context provides.
5. If different chunks contradict each other, note the contradiction.
6. Be precise about numbers, dates, and names.

Classify your answer's support level:
- SUPPORTED: The answer is directly and clearly supported by the context.
- PARTIALLY_SUPPORTED: The answer is partially supported but requires inference.
- UNSUPPORTED: The answer goes beyond what the context provides.
- INSUFFICIENT_EVIDENCE: Not enough context to provide a reliable answer.
"""),
    ("human", """Context chunks:
{context}

---

Question: {question}

---

Provide your answer with citations, then on a new line state the support level:
[SUPPORT_LEVEL: SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|INSUFFICIENT_EVIDENCE]
"""),
])


class Generator:
    """
    LLM generator with reliability features.

    The generator:
    1. Formats retrieved chunks into context
    2. Sends to LLM with strict grounding instructions
    3. Parses citations from the response
    4. Validates citations against actual retrieved chunks
    5. Classifies support level
    6. Handles abstention
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.generation.model,
            temperature=config.generation.temperature,
            max_tokens=config.generation.max_tokens,
            api_key=config.openai_api_key,
        )
        self.chain = GENERATION_PROMPT | self.llm | StrOutputParser()

    def generate(self, question: str, retrieval: RetrievalOutput) -> GenerationOutput:
        """
        Generate an answer with citations and validation.

        Pipeline:
        1. Format context from retrieval results
        2. Generate answer via LLM
        3. Parse citations
        4. Validate citations
        5. Classify support level
        6. Handle abstention
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

        # Format context
        context = self._format_context(retrieval)

        # Generate
        raw_response = self.chain.invoke({
            "context": context,
            "question": question,
        })

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
        # Extract support level
        support_match = re.search(
            r'\[SUPPORT_LEVEL:\s*(SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|INSUFFICIENT_EVIDENCE)\]',
            raw
        )
        if support_match:
            level = SupportLevel(support_match.group(1))
            answer = raw[:support_match.start()].strip()
        else:
            level = SupportLevel.PARTIALLY_SUPPORTED  # default if not classified
            answer = raw.strip()

        # Clean up abstention markers from answer
        answer = answer.replace("[ABSTAIN]", "").strip()

        return answer, level

    def _extract_citations(
        self, raw_response: str, retrieval: RetrievalOutput
    ) -> list[Citation]:
        """
        Extract citations from the response and validate them.

        Citations are in format [CITE:chunk_N] where N is 1-indexed.
        We validate each citation maps to an actual retrieved chunk.
        """
        citations = []
        cite_pattern = re.compile(r'\[CITE:chunk_(\d+)\]')
        matches = cite_pattern.findall(raw_response)

        seen = set()
        for match in matches:
            idx = int(match) - 1  # convert to 0-indexed
            if idx < 0 or idx >= len(retrieval.candidates):
                continue  # invalid citation — skip (don't create fake citations)
            if idx in seen:
                continue
            seen.add(idx)

            result = retrieval.candidates[idx]
            chunk = result.chunk

            # Find the relevant text span (heuristic: sentence containing the citation)
            relevant_text = chunk.content[:200]  # first 200 chars as evidence

            citations.append(Citation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                relevant_text=relevant_text,
                validated=True,  # validated against retrieval results
            ))

        return citations

    def _compute_confidence(
        self,
        support_level: SupportLevel,
        citations: list[Citation],
        retrieval: RetrievalOutput,
    ) -> float:
        """
        Compute confidence score based on multiple signals.

        Signals:
        - Support level (primary)
        - Number of citations (more = more confident)
        - Retrieval scores (higher = more relevant evidence)
        """
        # Base confidence from support level
        level_confidence = {
            SupportLevel.SUPPORTED: 0.9,
            SupportLevel.PARTIALLY_SUPPORTED: 0.6,
            SupportLevel.UNSUPPORTED: 0.2,
            SupportLevel.INSUFFICIENT_EVIDENCE: 0.0,
        }
        base = level_confidence.get(support_level, 0.5)

        # Citation bonus (more citations = more grounded)
        citation_factor = min(len(citations) / 3.0, 1.0) * 0.1

        # Retrieval score factor
        if retrieval.candidates:
            avg_score = sum(c.score for c in retrieval.candidates) / len(retrieval.candidates)
            retrieval_factor = avg_score * 0.1
        else:
            retrieval_factor = 0.0

        return min(base + citation_factor + retrieval_factor, 1.0)
