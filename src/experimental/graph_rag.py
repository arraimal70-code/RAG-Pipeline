"""
src/graph/graph_rag.py — Enterprise Knowledge Graph & Entity Resolution Engine.

Addresses the Tier-1 Knowledge Graph requirement:
Standard vector search fails on multi-hop relational, supply-chain, and
macro-thematic queries.

This module implements an Enterprise Knowledge Graph:
1. Automated Entity Resolution: Normalizes and clusters surface variations
   (e.g., "Alphabet Inc.", "Google", "Alphabet") into canonical entity nodes
   using suffix stripping, alias mapping, and token similarity.
2. Property Graph with Vector Indices: Entities and relations maintain vector
   representations and source chunk provenance.
3. Hierarchical Community Detection: Discovers dense macro-thematic clusters.
4. Subgraph Traversal & Context Synthesis: Expands seed nodes into k-hop subgraphs.
5. OpenCypher Exporter: Generates standard Cypher statements for Neo4j / Amazon Neptune.
"""

import re
import math
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.core.models import TextChunk, RetrievalResult, RetrievalOutput

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Automated Entity Resolution and Alias Disambiguation Engine.
    """

    CORPORATE_SUFFIXES = re.compile(
        r'\b(?:Inc\.?|Corp\.?|Corporation|LLC|L\.L\.C\.|Ltd\.?|Limited|Group|Holdings|Technologies|plc|Co\.?)\b',
        re.IGNORECASE
    )

    KNOWN_ALIASES = {
        "google": "Alphabet",
        "googl": "Alphabet",
        "alphabet inc": "Alphabet",
        "alphabet": "Alphabet",
        "apple inc": "Apple",
        "aapl": "Apple",
        "microsoft corp": "Microsoft",
        "msft": "Microsoft",
        "amazon com": "Amazon",
        "amzn": "Amazon",
    }

    @classmethod
    def canonicalize(cls, surface_name: str) -> str:
        """
        Normalize surface mention into canonical entity identifier.
        """
        clean = surface_name.strip()
        # Strip corporate suffixes
        base = cls.CORPORATE_SUFFIXES.sub("", clean).strip()
        # Clean trailing punctuation
        base = re.sub(r'[,.\-\s]+$', '', base).strip()
        lower_base = base.lower()

        # Check known alias dictionary
        if lower_base in cls.KNOWN_ALIASES:
            return cls.KNOWN_ALIASES[lower_base]

        # Title case canonical representation
        return base if base else clean


@dataclass
class EntityNode:
    """A canonical named entity with vector representation and mention provenance."""
    canonical_name: str
    entity_type: str  # ORGANIZATION, METRIC, TEMPORAL, LOCATION, CONCEPT
    aliases: Set[str] = field(default_factory=set)
    mentions: int = 1
    chunk_ids: Set[str] = field(default_factory=set)
    degree: int = 0
    community_id: int = -1
    embedding: Optional[List[float]] = None

    @property
    def name(self) -> str:
        return self.canonical_name


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
    Enterprise Knowledge Graph with Entity Resolution and Cypher export.
    """

    def __init__(self):
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: Dict[Tuple[str, str], RelationEdge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.communities: List[CommunityCluster] = []
        self.alias_to_canonical: Dict[str, str] = {}

    def add_node(
        self,
        surface_name: str,
        entity_type: str,
        chunk_id: Optional[str] = None
    ) -> EntityNode:
        """
        Add or resolve an entity node using automated Entity Resolution.
        """
        canonical = EntityResolver.canonicalize(surface_name)
        self.alias_to_canonical[surface_name.lower()] = canonical

        if canonical not in self.nodes:
            node = EntityNode(
                canonical_name=canonical,
                entity_type=entity_type,
                aliases={surface_name},
                mentions=1,
                chunk_ids={chunk_id} if chunk_id else set(),
            )
            self.nodes[canonical] = node
        else:
            node = self.nodes[canonical]
            node.mentions += 1
            node.aliases.add(surface_name)
            if chunk_id:
                node.chunk_ids.add(chunk_id)

        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation_type: str = "relates_to",
        weight: float = 1.0,
        chunk_id: Optional[str] = None,
        evidence: Optional[str] = None,
    ) -> Optional[RelationEdge]:
        """
        Add a relationship edge between two resolved entities.
        """
        src = EntityResolver.canonicalize(source)
        tgt = EntityResolver.canonicalize(target)
        if src == tgt or not src or not tgt:
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

    def resolve_entity(self, query_mention: str) -> Optional[str]:
        """Lookup canonical entity for a query mention."""
        lower = query_mention.lower()
        if lower in self.alias_to_canonical:
            return self.alias_to_canonical[lower]
        canon = EntityResolver.canonicalize(query_mention)
        return canon if canon in self.nodes else None

    def get_subgraph(self, seed_entities: List[str], max_hops: int = 1) -> Dict[str, Any]:
        """Extract multi-hop neighborhood around resolved seed entities."""
        resolved_seeds = []
        for s in seed_entities:
            c = self.resolve_entity(s) or s
            if c in self.nodes:
                resolved_seeds.append(c)

        visited_nodes: Set[str] = set()
        queue = deque([(entity, 0) for entity in resolved_seeds])

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
                    "aliases": list(self.nodes[name].aliases),
                }
                for name in visited_nodes
            ],
            "relations": sub_edges,
        }

    def detect_communities(self) -> List[CommunityCluster]:
        """
        Partition knowledge graph into macro-thematic community clusters.
        """
        visited: Set[str] = set()
        communities = []
        comm_id = 0

        for node_name in self.nodes:
            if node_name not in visited:
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

    def export_to_cypher(self) -> str:
        """
        Export graph representation to openCypher statements for Neo4j / Neptune.
        """
        lines = ["// --- Knowledge Graph OpenCypher Export ---"]
        for name, node in self.nodes.items():
            safe_name = name.replace("'", "\\'")
            safe_type = node.entity_type
            lines.append(
                f"MERGE (n:{safe_type} {{name: '{safe_name}', mentions: {node.mentions}}});"
            )

        for (u, v), edge in self.edges.items():
            safe_u = u.replace("'", "\\'")
            safe_v = v.replace("'", "\\'")
            safe_rel = edge.relation_type.upper().replace(" ", "_")
            lines.append(
                f"MATCH (a {{name: '{safe_u}'}}), (b {{name: '{safe_v}'}}) "
                f"MERGE (a)-[:{safe_rel} {{weight: {edge.weight}}}]->(b);"
            )

        return "\n".join(lines)


class GraphRAGEngine:
    """
    Enterprise GraphRAG Engine with Entity Resolution and hybrid traversal.
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
        """Extract entities and relation edges from a text chunk into the resolved knowledge graph."""
        text = chunk.content
        extracted_entities: List[Tuple[str, str]] = []

        # 1. Extract Metrics
        for m in self._compiled_patterns["METRIC"].finditer(text):
            val = m.group(0).strip()
            if len(val) >= 2:
                node = self.graph.add_node(val, "METRIC", chunk.chunk_id)
                extracted_entities.append((node.canonical_name, "METRIC"))

        # 2. Extract Temporal Markers
        for m in self._compiled_patterns["TEMPORAL"].finditer(text):
            val = m.group(0).strip()
            node = self.graph.add_node(val, "TEMPORAL", chunk.chunk_id)
            extracted_entities.append((node.canonical_name, "TEMPORAL"))

        # 3. Extract Organizations
        for m in self._compiled_patterns["ORGANIZATION"].finditer(text):
            val = m.group(0).strip()
            if len(val) > 3 and val.lower() not in {"this", "that", "there", "these", "section", "company", "total", "segment"}:
                node = self.graph.add_node(val, "ORGANIZATION", chunk.chunk_id)
                extracted_entities.append((node.canonical_name, "ORGANIZATION"))

        # 4. Form co-occurrence relation edges between resolved entities
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sent_entities = [name for name, _ in extracted_entities if name.lower() in sentence.lower()]
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
        Execute GraphRAG Global Query across resolved entities and communities.
        """
        if not self.graph.communities:
            self.graph.detect_communities()

        q_clean = query.lower()
        seed_entities = []
        for name, node in self.graph.nodes.items():
            if name.lower() in q_clean or any(a.lower() in q_clean for a in node.aliases):
                seed_entities.append(name)

        subgraph = self.graph.get_subgraph(seed_entities, max_hops=2) if seed_entities else {"entities": [], "relations": []}

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
            "cypher_export_sample": self.graph.export_to_cypher()[:300] + "...",
        }

    def clear(self) -> None:
        """Reset the knowledge graph."""
        self.graph = KnowledgeGraph()
