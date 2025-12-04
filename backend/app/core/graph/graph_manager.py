"""Graph management utilities for the Ambulance Routing system.

This module is intentionally **DSA-focused**:
- It is responsible for building and maintaining an *in-memory graph* representation
  of the road network stored in the database (nodes + edges tables).
- The graph is represented using **adjacency lists**, which are efficient for sparse graphs
  and work well with shortest-path algorithms like Dijkstra.

IMPORTANT DESIGN CHOICES (you should be able to explain these):
1. We use a *directed* adjacency list: each Edge(from_node, to_node, weight) becomes
   one entry in the adjacency list of `from_node`.
   - If the real-world road is two-way, we will store two edges in the DB (A->B and B->A).
2. For routing, we use the **effective weight** of an edge:
   - If `adjusted_weight` is present and the road is active, we use that.
   - Otherwise, we fall back to the base `weight` column.
3. We filter out edges where `is_active = False` so closed roads are not used.

This module does **NOT** know anything about HTTP, FastAPI, or requests.
It only talks to the database session and returns plain Python structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import Node, Edge


# Type aliases for clarity when explaining the DSA side
NodeId = int
EdgeId = int
# (neighbor_node_id, effective_weight, edge_id)
AdjacencyEntry = Tuple[NodeId, float, EdgeId]


@dataclass
class GraphManager:
    """In-memory graph wrapper built from the database.

    Core responsibilities:
    - Store an adjacency list: for every node, which neighbors are reachable and
      with what *effective* travel time.
    - Provide helper methods that routing algorithms (Dijkstra, A*, etc.) can use
      without having to know anything about SQLAlchemy or the database.
    """

    # adjacency list: node_id -> list of (neighbor_node_id, weight, edge_id)
    adjacency: Dict[NodeId, List[AdjacencyEntry]]
    # edge_id -> Edge object for distance lookup
    edges: Dict[EdgeId, Edge]

    def __post_init__(self):
        if not hasattr(self, 'adjacency'):
            self.adjacency = {}
        if not hasattr(self, 'edges'):
            self.edges = {}

    def get_edge(self, from_node: NodeId, to_node: NodeId) -> Optional[Edge]:
        """Get the edge object between two nodes if it exists."""
        if from_node not in self.adjacency:
            return None
            
        for neighbor, _, edge_id in self.adjacency[from_node]:
            if neighbor == to_node:
                return self.edges.get(edge_id)
        return None

    def neighbors(self, node_id: NodeId) -> List[AdjacencyEntry]:
        """Return all outgoing edges from a node.

        Time complexity: O(k) where k is the out-degree of the node.
        This is exactly why adjacency lists are preferred for sparse graphs:
        we only touch the edges that actually leave this node.
        """

        return self.adjacency.get(node_id, [])

    def has_node(self, node_id: NodeId) -> bool:
        """Check whether a node exists in the current graph view."""

        return node_id in self.adjacency


def _compute_effective_weight(edge: Edge) -> Optional[float]:
    """Compute the weight used for routing for a given edge.

    Rules:
    - If the edge is not active (`is_active == False`), we return None so
      the caller can skip this edge.
    - If `adjusted_weight` is set (not None), we prefer that because it
      includes traffic effects.
    - Otherwise, we fall back to the base `weight` from the database.
    """

    if edge.is_active is False:
        return None

    if edge.adjusted_weight is not None:
        return edge.adjusted_weight

    return edge.weight


def build_graph_for_city(db: Session, city_id: int) -> GraphManager:
    """Build a GraphManager for all nodes/edges belonging to a given city.

    This function performs **one database read** and converts the relational
    representation into an adjacency-list graph that is convenient for DSA
    algorithms.

    Steps:
    1. Load all nodes for the given city (to know which node IDs belong).
    2. Load all edges where both endpoints are in those nodes.
    3. For each edge, compute its effective weight and insert it into
       the adjacency list of `from_node`.
    4. Store the edge objects for distance lookup.
    """
    # Step 1: load nodes of this city and collect their IDs.
    nodes: Iterable[Node] = (
        db.query(Node).filter(Node.city_id == city_id).all()
    )
    node_ids = {node.id for node in nodes}

    # 2. Create empty adjacency list for each node
    graph = GraphManager(adjacency={node.id: [] for node in nodes}, edges={})

    # 3. Load all edges where both endpoints are in this city
    edges = (
        db.query(Edge)
        .filter(Edge.from_node.in_(node_ids))
        .filter(Edge.to_node.in_(node_ids))
        .all()
    )

    # 4. Populate the adjacency list with edges that have valid weights
    for edge in edges:
        weight = _compute_effective_weight(edge)
        if weight is not None:
            graph.adjacency[edge.from_node].append((edge.to_node, weight, edge.id))
            graph.edges[edge.id] = edge

    return graph
