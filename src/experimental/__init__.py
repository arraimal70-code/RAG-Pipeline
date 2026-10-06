"""
src/experimental/ — Optional & Experimental RAG Research Modules.

Contains advanced research implementations that extend beyond the core
document question-answering pipeline:
- graph_rag: In-memory Entity-Relationship Knowledge Graph and Community Detection
- agentic_planner: Multi-step ReAct Agent Planner for iterative retrieval
- hyde: Hypothetical Document Embeddings (Gao et al., ACL 2023)
- prf: Rocchio and RM3 Pseudo-Relevance Feedback Query Expansion
- late_interaction: ColBERT-style token-level MaxSim alignment scoring
- hierarchical: Parent-Child small-to-big context expansion
- mmr: Maximal Marginal Relevance diversity reranking
- crag: Corrective RAG evaluation and Self-RAG reflection critiques
"""

from src.experimental.graph_rag import GraphRAGEngine, KnowledgeGraph
from src.experimental.agentic_planner import AgenticRAGPlanner, AgenticPlanResult, StepStatus
from src.experimental.hyde import HypotheticalDocumentGenerator
from src.experimental.prf import PseudoRelevanceFeedbackEngine, PRFExpansionResult
from src.experimental.late_interaction import LateInteractionScorer, MaxSimScore, TokenAlignment
from src.experimental.hierarchical import HierarchicalRetriever, HierarchicalChunker
from src.experimental.mmr import MaximalMarginalRelevanceReranker
from src.experimental.crag import CorrectiveRAGEngine, CRAGAction, SelfRAGCritique

__all__ = [
    "GraphRAGEngine",
    "KnowledgeGraph",
    "AgenticRAGPlanner",
    "AgenticPlanResult",
    "StepStatus",
    "HypotheticalDocumentGenerator",
    "PseudoRelevanceFeedbackEngine",
    "PRFExpansionResult",
    "LateInteractionScorer",
    "MaxSimScore",
    "TokenAlignment",
    "HierarchicalRetriever",
    "HierarchicalChunker",
    "MaximalMarginalRelevanceReranker",
    "CorrectiveRAGEngine",
    "CRAGAction",
    "SelfRAGCritique",
]
