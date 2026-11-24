"""
src/agentic/rag_graph.py — Stateful Agentic & Corrective RAG (LangGraph State Machine).

State Machine Architecture:
START -> analyze_and_plan -> retrieve_and_funnel -> grade_documents -> [conditional]
       -> rewrite_query (loop if insufficient & retries < limit)
       -> synthesize_and_ground -> hallucination_gatekeeper -> END
       -> abstain -> END (if retries exceeded or contradictory)
"""

import logging
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.claims.nli_verifier import NLIRelation, NLIVerifier
from src.retrieval.reranker import MultiStageRerankerFunnel

logger = logging.getLogger(__name__)


class RAGGraphState(TypedDict):
    """Execution state passed through the LangGraph agentic loop."""
    query: str
    original_query: str
    sub_queries: list[str]
    retrieved_chunks: list[dict[str, Any]]
    evidence_grade: str  # "sufficient", "partial", "insufficient"
    crag_action: str  # "correct", "ambiguous", "incorrect"
    rewritten_query: str | None
    draft_response: str
    final_response: str
    citations: list[dict[str, Any]]
    hallucination_verdict: str  # "pass", "redact", "abstain"
    retry_count: int
    max_retries: int
    token_budget: int
    step_trace: list[str]


# ─────────────────────────────────────────────────────────────
# Graph Nodes
# ─────────────────────────────────────────────────────────────

def analyze_and_plan(state: RAGGraphState) -> dict[str, Any]:
    """Decompose query into sub-queries and initialize execution plan."""
    query = state.get("query", "")
    trace = list(state.get("step_trace", []))
    trace.append(f"analyze_and_plan: '{query}'")

    # Sub-query decomposition for multi-hop or comparative questions
    sub_queries = [query]
    if " and " in query.lower() or " compared to " in query.lower() or " vs " in query.lower():
        parts = re.split(r"\s+(?:and|compared to|vs|versus)\s+", query, flags=re.IGNORECASE)
        sub_queries = [p.strip() for p in parts if len(p.strip()) > 3]

    return {
        "sub_queries": sub_queries,
        "step_trace": trace,
        "token_budget": state.get("token_budget", 4096) - 50,
    }


def retrieve_and_funnel(state: RAGGraphState) -> dict[str, Any]:
    """Retrieve candidates through the hybrid vector store and multi-stage reranker."""
    query = state.get("query", "")
    trace = list(state.get("step_trace", []))
    trace.append(f"retrieve_and_funnel: retrieving for '{query}'")

    # If mock candidates are already provided in state (e.g. for deterministic testing), funnel them
    existing = state.get("retrieved_chunks")
    if existing is not None and len(existing) > 0:
        funnel = MultiStageRerankerFunnel(colbert_prune_top_k=20, final_top_k=5, enable_compression=True)
        reranked = funnel.execute_funnel(query, existing)
    elif existing == []:
        reranked = []
    else:
        from src.indexing.vector_store import VectorIndex
        vindex = VectorIndex()
        if vindex.count() == 0:
            reranked = []
        else:
            from src.retrieval.hybrid_retriever import HybridRetriever
            retriever = HybridRetriever()
            retrieval_res = retriever.retrieve(query)
            candidates = [
                {
                    "chunk_id": r.chunk.chunk_id,
                    "content": r.chunk.content,
                    "score": r.score,
                    "document_id": r.chunk.document_id,
                    "filename": r.chunk.filename,
                    "section": r.chunk.section,
                    "page_number": r.chunk.page_number,
                    "metadata": r.chunk.metadata,
                }
                for r in retrieval_res.candidates
            ]
            funnel = MultiStageRerankerFunnel(colbert_prune_top_k=20, final_top_k=5, enable_compression=True)
            reranked = funnel.execute_funnel(query, candidates)

    return {
        "retrieved_chunks": reranked,
        "step_trace": trace,
        "token_budget": state.get("token_budget", 4096) - 150,
    }


def grade_documents(state: RAGGraphState) -> dict[str, Any]:
    """Assess whether retrieved documents contain sufficient evidence (CRAG grading)."""
    query = state.get("query", "")
    chunks = state.get("retrieved_chunks", [])
    trace = list(state.get("step_trace", []))

    if not chunks:
        trace.append("grade_documents: no chunks retrieved -> incorrect")
        return {
            "evidence_grade": "insufficient",
            "crag_action": "incorrect",
            "step_trace": trace,
        }

    q_tokens = set(re.findall(r"\w+", query.lower()))
    best_overlap_ratio = 0.0

    for c in chunks:
        c_tokens = set(re.findall(r"\w+", c.get("content", "").lower()))
        if q_tokens:
            overlap = len(q_tokens & c_tokens) / len(q_tokens)
            best_overlap_ratio = max(best_overlap_ratio, overlap)

    if best_overlap_ratio >= 0.5:
        grade = "sufficient"
        action = "correct"
    elif best_overlap_ratio >= 0.25:
        grade = "partial"
        action = "ambiguous"
    else:
        grade = "insufficient"
        action = "incorrect"

    trace.append(f"grade_documents: overlap={best_overlap_ratio:.2f} -> {action}")
    return {
        "evidence_grade": grade,
        "crag_action": action,
        "step_trace": trace,
    }


def decide_next_step(state: RAGGraphState) -> Literal["synthesize_and_ground", "rewrite_query", "abstain"]:
    """Conditional router based on evidence grade and retry budget."""
    action = state.get("crag_action", "incorrect")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if action in ("correct", "ambiguous") and state.get("retrieved_chunks"):
        return "synthesize_and_ground"

    if retry_count < max_retries:
        return "rewrite_query"

    return "abstain"


def rewrite_query(state: RAGGraphState) -> dict[str, Any]:
    """CRAG query rewrite: strip noisy punctuation and expand key entity terms."""
    query = state.get("query", "")
    trace = list(state.get("step_trace", []))
    retries = state.get("retry_count", 0) + 1

    # Strip conversational fillers
    clean = re.sub(r"(?i)\b(what is|tell me about|how much did|could you please|details on)\b", "", query).strip()
    words = re.findall(r"\w+", clean)
    rewritten = " ".join(words[:6]) if words else query

    trace.append(f"rewrite_query: attempt {retries} -> '{rewritten}'")
    return {
        "query": rewritten,
        "rewritten_query": rewritten,
        "retry_count": retries,
        "step_trace": trace,
        "token_budget": state.get("token_budget", 4096) - 50,
    }


def synthesize_and_ground(state: RAGGraphState) -> dict[str, Any]:
    """Synthesize grounded answer from top verified passages with citations."""
    chunks = state.get("retrieved_chunks", [])
    trace = list(state.get("step_trace", []))

    if not chunks:
        return {
            "draft_response": "Insufficient evidence available.",
            "citations": [],
            "step_trace": trace,
        }

    # Synthesize from top chunk
    top_chunk = chunks[0]
    passage = top_chunk.get("content", "").strip()
    filename = top_chunk.get("filename", "document.pdf")
    page = top_chunk.get("page_number", 1)

    draft = f"Based on {filename} (Page {page}), {passage}"
    citations = [
        {
            "filename": filename,
            "page_number": page,
            "chunk_id": top_chunk.get("chunk_id", ""),
            "text": passage[:120],
        }
    ]

    trace.append(f"synthesize_and_ground: draft generated ({len(draft)} chars)")
    return {
        "draft_response": draft,
        "final_response": draft,
        "citations": citations,
        "step_trace": trace,
    }


def hallucination_gatekeeper(state: RAGGraphState) -> dict[str, Any]:
    """Execute pre-stream NLI factual grounding gatekeeper."""
    draft = state.get("draft_response", "")
    chunks = state.get("retrieved_chunks", [])
    trace = list(state.get("step_trace", []))

    if not draft or not chunks:
        trace.append("hallucination_gatekeeper: empty draft -> abstain")
        return {
            "hallucination_verdict": "abstain",
            "final_response": "I cannot answer this query with sufficient factual confidence.",
            "step_trace": trace,
        }

    evidence_text = " ".join(c.get("content", "") for c in chunks[:3])
    verifier = NLIVerifier()
    pred = verifier.predict(premise=evidence_text, hypothesis=draft)

    trace.append(f"hallucination_gatekeeper: relation={pred.relation.value}, confidence={pred.confidence:.2f}")

    if pred.relation == NLIRelation.CONTRADICTION:
        verdict = "abstain"
        final_text = "I cannot answer this query as the generated statement contradicts verified source documents."
    else:
        verdict = "pass"
        final_text = draft

    return {
        "hallucination_verdict": verdict,
        "final_response": final_text,
        "step_trace": trace,
    }


def abstain(state: RAGGraphState) -> dict[str, Any]:
    """Final fallback node when evidence is insufficient or contradicted."""
    trace = list(state.get("step_trace", []))
    trace.append("abstain: terminal node reached")
    return {
        "final_response": "I cannot answer this query with sufficient factual confidence based on the verified documents.",
        "hallucination_verdict": "abstain",
        "step_trace": trace,
    }


# ─────────────────────────────────────────────────────────────
# Graph Construction
# ─────────────────────────────────────────────────────────────

def create_rag_graph() -> Any:
    """Build and compile the complete LangGraph StateMachine."""
    builder = StateGraph(RAGGraphState)

    # Nodes
    builder.add_node("analyze_and_plan", analyze_and_plan)
    builder.add_node("retrieve_and_funnel", retrieve_and_funnel)
    builder.add_node("grade_documents", grade_documents)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("synthesize_and_ground", synthesize_and_ground)
    builder.add_node("hallucination_gatekeeper", hallucination_gatekeeper)
    builder.add_node("abstain", abstain)

    # Edges
    builder.add_edge(START, "analyze_and_plan")
    builder.add_edge("analyze_and_plan", "retrieve_and_funnel")
    builder.add_edge("retrieve_and_funnel", "grade_documents")

    builder.add_conditional_edges(
        "grade_documents",
        decide_next_step,
        {
            "synthesize_and_ground": "synthesize_and_ground",
            "rewrite_query": "rewrite_query",
            "abstain": "abstain",
        },
    )

    builder.add_edge("rewrite_query", "retrieve_and_funnel")
    builder.add_edge("synthesize_and_ground", "hallucination_gatekeeper")
    builder.add_edge("hallucination_gatekeeper", END)
    builder.add_edge("abstain", END)

    return builder.compile()


class FrontierRAGGraph:
    """
    High-level runner for the LangGraph-based stateful RAG agent.
    """

    def __init__(self) -> None:
        self.app = create_rag_graph()

    def run(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        max_retries: int = 2,
        token_budget: int = 4096,
    ) -> RAGGraphState:
        """Run the stateful agentic loop from query to grounded answer."""
        initial_state: RAGGraphState = {
            "query": query,
            "original_query": query,
            "sub_queries": [query],
            "retrieved_chunks": retrieved_chunks if retrieved_chunks is not None else [],
            "evidence_grade": "insufficient",
            "crag_action": "incorrect",
            "rewritten_query": None,
            "draft_response": "",
            "final_response": "",
            "citations": [],
            "hallucination_verdict": "pass",
            "retry_count": 0,
            "max_retries": max_retries,
            "token_budget": token_budget,
            "step_trace": [],
        }

        result = self.app.invoke(initial_state)
        return result
