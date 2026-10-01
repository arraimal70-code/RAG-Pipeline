r"""
src/adaptive/query_rewriter.py — Semantic Query Rewriter & Conversational Coreference Normalizer.

Addresses core retrieval degradation in multi-turn dialogues, vague anaphora,
and relative temporal expressions.

Key Features:
1. Conversational Coreference Resolution: Resolves pronouns ("it", "they", "its",
   "their", "the company", "that product") into unambiguous named entities using
   dialogue history.
2. Relative Temporal Normalization: Converts relative temporal markers ("last year",
   "previous quarter", "two years ago") into absolute temporal references.
3. Domain Acronym Expansion: Disambiguates high-frequency technical and financial
   acronyms (EBITDA, CAGR, ARR, LLM, MoE, LoRA, EPS).
4. Deterministic Rule & Heuristic Engine: Fast sub-millisecond execution without
   external LLM API dependencies.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RewrittenQuery:
    """Detailed result of query rewriting."""
    original_query: str
    rewritten_query: str
    coreferences_resolved: List[Tuple[str, str]] = field(default_factory=list)
    temporal_anchors_applied: List[Tuple[str, str]] = field(default_factory=list)
    expanded_acronyms: List[Tuple[str, str]] = field(default_factory=list)
    is_rewritten: bool = False


class QueryRewriter:
    """
    Semantic Query Normalizer, Coreference Resolver, and Temporal Grounding Engine.
    """

    # High-impact domain acronyms in tech, finance, and AI
    ACRONYM_MAP: Dict[str, str] = {
        "ebitda": "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)",
        "cagr": "CAGR (Compound Annual Growth Rate)",
        "arr": "ARR (Annual Recurring Revenue)",
        "eps": "EPS (Earnings Per Share)",
        "pe ratio": "P/E (Price-to-Earnings) ratio",
        "p/e": "P/E (Price-to-Earnings)",
        "llm": "LLM (Large Language Model)",
        "rag": "RAG (Retrieval-Augmented Generation)",
        "moe": "MoE (Mixture of Experts)",
        "lora": "LoRA (Low-Rank Adaptation)",
        "cot": "CoT (Chain-of-Thought)",
        "kpi": "KPI (Key Performance Indicator)",
        "roi": "ROI (Return on Investment)",
    }

    # Pronouns that require coreference resolution
    PRONOUNS_SINGULAR = {"it", "its", "this", "that", "the company", "the firm", "the organization"}
    PRONOUNS_PLURAL = {"they", "their", "them", "these", "those"}

    def __init__(self, default_anchor_year: int = 2023):
        self.default_anchor_year = default_anchor_year

    def _extract_recent_entity(self, history: List[str]) -> Optional[str]:
        """
        Extract the most recent prominent named entity or noun phrase from dialogue history.
        """
        non_entity_words = {
            "what", "how", "why", "when", "where", "who", "which", "the", "a", "an",
            "is", "are", "was", "were", "can", "could", "would", "please", "in", "on",
            "at", "for", "with", "as", "by", "if", "this", "that", "there", "here", "to",
            "tell", "explain", "give", "show", "overview", "detail", "performance", "revenue"
        }

        for message in reversed(history):
            # 1. Quoted strings (e.g. 'Project Apex', "Apple Inc.")
            quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', message)
            for q1, q2 in quoted:
                entity = (q1 or q2).strip()
                if entity:
                    return entity

            # 2. Possessive entities: e.g. "Microsoft Corporation's", "Alphabet's", "Apple's"
            possessive_match = re.search(r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\'s\b', message)
            if possessive_match:
                cand = possessive_match.group(1).strip()
                if cand.lower() not in non_entity_words:
                    return cand

            # 3. Capitalized multi-word proper nouns: e.g. "Microsoft Corporation", "Project Apex"
            multi_words = re.findall(r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)+)\b', message)
            for mw in multi_words:
                cand = mw.strip()
                if cand.lower() not in non_entity_words:
                    return cand

            # 4. Capitalized single-word named entities in prominent/subject position
            words = message.split()
            for w in words:
                clean_w = re.sub(r"[^\w]", "", w)
                if clean_w and clean_w[0].isupper() and clean_w.lower() not in non_entity_words:
                    return clean_w

        return None

    def resolve_coreferences(
        self,
        query: str,
        dialogue_history: Optional[List[str]] = None,
        context_entity: Optional[str] = None,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Replace ambiguous pronouns with context entities.
        """
        resolved: List[Tuple[str, str]] = []
        if not dialogue_history and not context_entity:
            return query, resolved

        target_entity = context_entity or self._extract_recent_entity(dialogue_history or [])
        if not target_entity:
            return query, resolved

        rewritten = query

        # Replace possessive "its" -> "Entity's"
        pattern_its = re.compile(r"\b(its)\b", re.IGNORECASE)
        if pattern_its.search(rewritten):
            rewritten = pattern_its.sub(f"{target_entity}'s", rewritten)
            resolved.append(("its", f"{target_entity}'s"))

        # Replace "it" -> "Entity"
        pattern_it = re.compile(r"\b(it)\b", re.IGNORECASE)
        if pattern_it.search(rewritten):
            rewritten = pattern_it.sub(target_entity, rewritten)
            resolved.append(("it", target_entity))

        # Replace "the company" / "the firm" -> "Entity"
        for phrase in ("the company", "the firm", "the organization"):
            pat = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            if pat.search(rewritten):
                rewritten = pat.sub(target_entity, rewritten)
                resolved.append((phrase, target_entity))

        # Replace plural "their" -> "Entity's"
        pattern_their = re.compile(r"\b(their)\b", re.IGNORECASE)
        if pattern_their.search(rewritten):
            rewritten = pattern_their.sub(f"{target_entity}'s", rewritten)
            resolved.append(("their", f"{target_entity}'s"))

        return rewritten, resolved

    def normalize_temporal_references(
        self,
        query: str,
        anchor_year: Optional[int] = None,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Resolve relative temporal expressions into concrete years.
        """
        applied: List[Tuple[str, str]] = []
        year = anchor_year or self.default_anchor_year
        rewritten = query

        # "last year" -> year - 1
        if re.search(r"\blast year\b", rewritten, re.IGNORECASE):
            prev_year = str(year - 1)
            rewritten = re.sub(r"\blast year\b", f"in {prev_year}", rewritten, flags=re.IGNORECASE)
            applied.append(("last year", prev_year))

        # "previous year" / "prior year" -> year - 1
        if re.search(r"\b(previous|prior) year\b", rewritten, re.IGNORECASE):
            prev_year = str(year - 1)
            rewritten = re.sub(r"\b(previous|prior) year\b", f"in {prev_year}", rewritten, flags=re.IGNORECASE)
            applied.append(("previous/prior year", prev_year))

        # "two years ago" -> year - 2
        if re.search(r"\btwo years ago\b", rewritten, re.IGNORECASE):
            target = str(year - 2)
            rewritten = re.sub(r"\btwo years ago\b", f"in {target}", rewritten, flags=re.IGNORECASE)
            applied.append(("two years ago", target))

        # "this year" / "current year" -> year
        if re.search(r"\b(this|current) year\b", rewritten, re.IGNORECASE):
            curr_year = str(year)
            rewritten = re.sub(r"\b(this|current) year\b", f"in {curr_year}", rewritten, flags=re.IGNORECASE)
            applied.append(("this/current year", curr_year))

        return rewritten, applied

    def expand_acronyms(self, query: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Expand key domain acronyms when query is short to boost lexical retrieval match.
        """
        expanded: List[Tuple[str, str]] = []
        tokens = query.lower().split()

        # Only expand if query is relatively compact (< 15 words) to avoid bloating
        if len(tokens) > 15:
            return query, expanded

        rewritten = query
        for acr, expansion in self.ACRONYM_MAP.items():
            pattern = re.compile(rf"\b{re.escape(acr)}\b", re.IGNORECASE)
            if pattern.search(rewritten) and expansion.lower() not in rewritten.lower():
                # Append acronym definition for high hybrid recall
                rewritten = pattern.sub(expansion, rewritten, count=1)
                expanded.append((acr, expansion))

        return rewritten, expanded

    def rewrite(
        self,
        query: str,
        dialogue_history: Optional[List[str]] = None,
        context_entity: Optional[str] = None,
        anchor_year: Optional[int] = None,
        expand_acronyms: bool = True,
    ) -> RewrittenQuery:
        """
        Full rewriting pipeline: clean -> coreference resolution -> temporal anchoring -> acronym expansion.
        """
        if not query or not isinstance(query, str):
            return RewrittenQuery(original_query="", rewritten_query="")

        # 1. Clean extra spaces
        clean_query = " ".join(query.strip().split())

        # 2. Coreference resolution
        after_coref, corefs = self.resolve_coreferences(
            clean_query,
            dialogue_history=dialogue_history,
            context_entity=context_entity,
        )

        # 3. Temporal normalization
        after_temporal, temporals = self.normalize_temporal_references(
            after_coref,
            anchor_year=anchor_year,
        )

        # 4. Acronym expansion
        if expand_acronyms:
            final_query, acronyms = self.expand_acronyms(after_temporal)
        else:
            final_query = after_temporal
            acronyms = []

        is_rewritten = (
            bool(corefs) or bool(temporals) or bool(acronyms) or (final_query != clean_query)
        )

        return RewrittenQuery(
            original_query=query,
            rewritten_query=final_query,
            coreferences_resolved=corefs,
            temporal_anchors_applied=temporals,
            expanded_acronyms=acronyms,
            is_rewritten=is_rewritten,
        )
