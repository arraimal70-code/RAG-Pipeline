"""
src/graph/graph_rag.py — In-Memory GraphRAG & Entity-Relationship Network Engine.

Based on Microsoft GraphRAG (Edge et al., 2024):
Standard vector and lexical search fail on global, thematic, and multi-entity
relational questions (e.g., "What are the overarching risks across all divisions?"
or "How is Entity A related to Entity B?").

This module implements an in-memory, zero-dependency Knowledge Graph engine:
1. Entity Extraction: Identifies named entities (Organizations, Metrics, Concepts, Temporal Markers)
2. Relation Extraction: Identifies co-occurrence and relational edge triples between entities
3. Community Detection: Partitions entities into thematic community clusters
4. Graph Traversal: Extracts multi-hop subgraphs and computes degree centrality
5. Global Community Search: Synthesizes global holistic answers from graph clusters
"""

import re
import math
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.core.models import TextChunk, RetrievalResult, RetrievalOutput

logger = logging.getLogger(__name__)


@dataclass
class EntityNode:
    """A named entity extracted from documents."""
    name: str
    entity_type: str  # ORGANIZATION, METRIC, TEMPORAL, LOCATION, CONCEPT
    mentions: int = 1
    chunk_ids: Set[str] = field(default_factory=set)
    degree: int = 0
    community_id: int = -1


@dataclass
class RelationEdge:
    """A directed or undirected relationship between two entities."""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    chunk_ids: Set[str] = field(default_factory=set)
    evidence_snippets: List[str] = field(default_factory=list)


@dataclass
class CommunityCluster:
    """A dense cluster/community of related entities representing a high-level theme."""
    community_id: int
    entity_names: List[str]
    dominant_type: str
    summary: str = ""
    chunk_ids: Set[str] = field(default_factory=set)


class KnowledgeGraph:
    """
    In-memory Knowledge Graph representation with adjacency indices and community detection.
    """

    def __init__(self):
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: Dict[Tuple[str, str], RelationEdge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.communities: List[CommunityCluster] = []

    def add_node(self, name: str, entity_type: str, chunk_id: Optional[str] = None) -> EntityNode:
        clean_name = name.strip()
        if clean_name not in self.nodes:
            self.nodes[clean_name] = EntityNode(
                name=clean_name,
                entity_type=entity_type,
                mentions=1,
                chunk_ids={chunk_id} if chunk_id else set(),
            )
        else:
            self.nodes[clean_name].mentions += 1
            if chunk_id:
                self.nodes[clean_name].chunk_ids.add(chunk_id)
        return self.nodes[clean_name]

    def add_edge(
        self,
        source: str,
        target: str,
        relation_type: str = "relates_to",
        weight: float = 1.0,
        chunk_id: Optional[str] = None,
        evidence: Optional[str] = None,
    ) -> RelationEdge:
        src = source.strip()
        tgt = target.strip()
        if src == tgt:
            return None

        key = (src, tgt) if src < tgt else (tgt, src)
        if key not in self.edges:
            edge = RelationEdge(
                source=key[0],
                target=key[1],
                relation_type=relation_type,
                weight=weight,
                chunk_ids={chunk_id} if chunk_id else set(),
                evidence_snippets=[evidence] if evidence else [],
            )
            self.edges[key] = edge
            self.adjacency[key[0]].add(key[1])
            self.adjacency[key[1]].add(key[0])
        else:
            edge = self.edges[key]
            edge.weight += weight
            if chunk_id:
                edge.chunk_ids.add(chunk_id)
            if evidence and len(edge.evidence_snippets) < 5:
                edge.evidence_snippets.append(evidence)

        # Update node degrees
        if key[0] in self.nodes:
            self.nodes[key[0]].degree = len(self.adjacency[key[0]])
        if key[1] in self.nodes:
            self.nodes[key[1]].degree = len(self.adjacency[key[1]])

        return edge

    def get_subgraph(self, seed_entities: List[str], max_hops: int = 1) -> Dict[str, Any]:
        """Extract a multi-hop neighborhood around seed entities."""
        visited_nodes: Set[str] = set()
        queue = deque([(entity, 0) for entity in seed_entities if entity in self.nodes])

        while queue:
            curr_entity, hops = queue.popleft()
            if curr_entity in visited_nodes:
                continue
            visited_nodes.add(curr_entity)

            if hops < max_hops:
                for neighbor in self.adjacency[curr_entity]:
                    if neighbor not in visited_nodes:
                        queue.append((neighbor, hops + 1))

        # Extract related edges
        sub_edges = []
        for (u, v), edge in self.edges.items():
            if u in visited_nodes and v in visited_nodes:
                sub_edges.append({
                    "source": u,
                    "target": v,
                    "relation": edge.relation_type,
                    "weight": edge.weight,
                    "evidence": edge.evidence_snippets[:2],
                })

        return {
            "entities": [
                {
                    "name": name,
                    "type": self.nodes[name].entity_type,
                    "degree": self.nodes[name].degree,
                    "mentions": self.nodes[name].mentions,
                }
                for name in visited_nodes
            ],
            "relations": sub_edges,
        }

    def detect_communities(self) -> List[CommunityCluster]:
        """
        Partition the knowledge graph into connected component communities
        for macro-thematic summarization.
        """
        visited: Set[str] = set()
        communities = []
        comm_id = 0

        for node_name in self.nodes:
            if node_name not in visited:
                # Run BFS to discover connected community
                cluster_nodes = []
                queue = deque([node_name])
                visited.add(node_name)

                while queue:
                    curr = queue.popleft()
                    cluster_nodes.append(curr)
                    self.nodes[curr].community_id = comm_id

                    for neighbor in self.adjacency[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                if len(cluster_nodes) >= 2:
                    # Determine dominant entity type
                    type_counts = defaultdict(int)
                    chunk_ids = set()
                    for c_node in cluster_nodes:
                        node = self.nodes[c_node]
                        type_counts[node.entity_type] += 1
                        chunk_ids.update(node.chunk_ids)

                    dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
                    cluster = CommunityCluster(
                        community_id=comm_id,
                        entity_names=cluster_nodes,
                        dominant_type=dominant_type,
                        summary=f"Community {comm_id}: {dominant_type} network containing {', '.join(cluster_nodes[:6])}",
                        chunk_ids=chunk_ids,
                    )
                    communities.append(cluster)
                    comm_id += 1

        self.communities = communities
        return communities


class GraphRAGEngine:
    """
    GraphRAG Orchestrator: extracts entities/triples from ingested documents
    and executes graph-grounded relational and global queries.
    """

    def __init__(self):
        self.graph = KnowledgeGraph()
        self._compiled_patterns = self._build_entity_patterns()

    def _build_entity_patterns(self) -> Dict[str, re.Pattern]:
        return {
            "TEMPORAL": re.compile(r'\b(19\d\d|20\d\d|Q[1-4]\s*(?:20\d\d|19\d\d)?|FY\s*20\d\d|fiscal\s+year\s+20\d\d)\b', re.IGNORECASE),
            "METRIC": re.compile(r'\b(?:\$\d+(?:\.\d+)?\s*(?:billion|million|trillion|B|M)?|\d+(?:\.\d+)?%|operating\s+margin|net\s+profit|gross\s+revenue|EBITDA)\b', re.IGNORECASE),
            "ORGANIZATION": re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|Corporation|LLC|Ltd|Group|Technologies|Holdings|Solutions))?)\b'),
        }

    def index_chunk(self, chunk: TextChunk) -> None:
        """Extract entities and relation edges from a text chunk into the knowledge graph."""
        text = chunk.content
        extracted_entities: List[Tuple[str, str]] = []

        # 1. Extract Metrics
        for m in self._compiled_patterns["METRIC"].finditer(text):
            val = m.group(0).strip()
            if len(val) >= 2:
                self.graph.add_node(val, "METRIC", chunk.chunk_id)
                extracted_entities.append((val, "METRIC"))

        # 2. Extract Temporal Markers
        for m in self._compiled_patterns["TEMPORAL"].finditer(text):
            val = m.group(0).strip()
            self.graph.add_node(val, "TEMPORAL", chunk.chunk_id)
            extracted_entities.append((val, "TEMPORAL"))

        # 3. Extract Organizations and Proper Entities
        for m in self._compiled_patterns["ORGANIZATION"].finditer(text):
            val = m.group(0).strip()
            if len(val) > 3 and val.lower() not in {"this", "that", "there", "these", "section", "company", "total", "segment"}:
                self.graph.add_node(val, "ORGANIZATION", chunk.chunk_id)
                extracted_entities.append((val, "ORGANIZATION"))

        # 4. Form co-occurrence relation edges between entities in the same sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sent_entities = [name for name, _ in extracted_entities if name in sentence]
            for i in range(len(sent_entities)):
                for j in range(i + 1, min(len(sent_entities), i + 4)):
                    self.graph.add_edge(
                        source=sent_entities[i],
                        target=sent_entities[j],
                        relation_type="co_occurs_with",
                        weight=1.0,
                        chunk_id=chunk.chunk_id,
                        evidence=sentence[:150],
                    )

    def global_query(self, query: str) -> Dict[str, Any]:
        """
        Execute GraphRAG Global Query: finds relevant communities and traverses
        subgraphs to answer macro-thematic and relational questions.
        """
        # Detect communities if not already detected
        if not self.graph.communities:
            self.graph.detect_communities()

        # Identify mentioned seed entities in query
        q_clean = query.lower()
        seed_entities = [name for name in self.graph.nodes if name.lower() in q_clean]

        subgraph = self.graph.get_subgraph(seed_entities, max_hops=2) if seed_entities else {"entities": [], "relations": []}

        # Find matching communities
        matched_communities = []
        for comm in self.graph.communities:
            if any(e.lower() in q_clean for e in comm.entity_names) or any(w in comm.dominant_type.lower() for w in q_clean.split()):
                matched_communities.append({
                    "community_id": comm.community_id,
                    "type": comm.dominant_type,
                    "entities": comm.entity_names[:8],
                    "summary": comm.summary,
                    "num_chunks": len(comm.chunk_ids),
                })

        return {
            "query": query,
            "seed_entities": seed_entities,
            "subgraph": subgraph,
            "matched_communities": matched_communities,
            "total_graph_nodes": len(self.graph.nodes),
            "total_graph_edges": len(self.graph.edges),
        }

    def clear(self) -> None:
        """Reset the knowledge graph."""
        self.graph = KnowledgeGraph()
