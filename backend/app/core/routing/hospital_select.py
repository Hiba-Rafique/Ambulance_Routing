"""Hospital selection logic using Dijkstra's shortest path algorithm.

This module is also **DSA-focused** and does not know anything about HTTP
or FastAPI. It only depends on the in-memory graph representation provided
by `GraphManager`.

Goal for now:
- Given a source node (patient location) and a set of hospital node IDs
  in the same city, find the hospital that can be reached with the
  *minimum travel time* according to the graph edge weights.

We use **Dijkstra's algorithm** because:
- Edge weights are non-negative (they represent travel times).
- We care about the *shortest path distance* from a single source to many
  possible destinations (all hospitals).
- Dijkstra's algorithm gives us the shortest distance from the source
  to *every* reachable node in O((V + E) log V) time when implemented
  with a min-heap (priority queue).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from ..graph.graph_manager import GraphManager, NodeId, AdjacencyEntry
from ...db.models import Node
from ...core.utils.geo import haversine_distance


@dataclass
class HospitalSelectionResult:
    """Result of running Dijkstra from the patient to hospitals.

    Attributes
    ----------
    best_hospital_id:
        The node_id of the hospital with the minimum travel time, or None
        if no hospital is reachable from the patient node.
    best_distance:
        The travel time (sum of edge weights) to reach `best_hospital_id`.
        If `best_hospital_id` is None, this will also be None.
    distance_km:
        The actual distance in kilometers to the best hospital, if known.
    distances:
        A dictionary mapping *all* visited node_ids to their shortest known
        distance from the source. This is useful if later we want to
        reconstruct paths or inspect distances to all hospitals.
    """

    best_hospital_id: Optional[NodeId]
    best_distance: Optional[float]
    distances: Dict[NodeId, float]
    distance_km: Optional[float] = None


def find_nearest_hospital(
    graph: GraphManager,
    source_node_id: NodeId,
    hospital_node_ids: List[NodeId],
    db: Optional[Session] = None,
) -> HospitalSelectionResult:
    """Run Dijkstra from `source_node_id` and pick the nearest hospital.

    Parameters
    ----------
    graph:
        An instance of GraphManager containing the adjacency list for the
        relevant city.
    source_node_id:
        The node where the patient is located.
    hospital_node_ids:
        List of node_ids that represent hospitals in this city.

    Returns
    -------
    HospitalSelectionResult
        Contains the ID and distance of the nearest reachable hospital,
        as well as the full distance map produced by Dijkstra.

    High-level algorithm (explainable in an interview):
    1. Initialize all distances to infinity, except the source which is 0.
    2. Push the source into a min-heap (priority queue) keyed by distance.
    3. Repeatedly pop the node with the smallest tentative distance.
       - If we have already finalized this node, skip.
       - For each outgoing edge, try to relax the distance to the neighbor.
    4. At the end, check among all hospital nodes which has the
       smallest distance value.
    """

    if not graph.has_node(source_node_id):
        # Source is not part of this city's graph view.
        return HospitalSelectionResult(
            best_hospital_id=None, best_distance=None, distances={}
        )

    # Convert hospitals to a set for O(1) membership checks.
    hospital_set: Set[NodeId] = set(hospital_node_ids)

    # Distance map: node_id -> shortest known distance from source.
    distances: Dict[NodeId, float] = {}

    # Previous-node map for path reconstruction: child -> parent.
    previous: Dict[NodeId, Optional[NodeId]] = {source_node_id: None}

    # Min-heap of (distance_from_source, node_id).
    # We may push multiple entries for the same node, but only the first
    # time we pop a node do we finalize its distance.
    heap: List[Tuple[float, NodeId]] = []

    # Initialization: source distance is 0.
    distances[source_node_id] = 0.0
    heapq.heappush(heap, (0.0, source_node_id))

    # Visited set to mark nodes whose shortest distance is finalized.
    visited: Set[NodeId] = set()

    while heap:
        current_dist, node_id = heapq.heappop(heap)

        if node_id in visited:
            # We have already processed this node with a shorter distance.
            continue

        visited.add(node_id)

        # Optional micro-optimization (not required but nice to explain):
        # If this node is a hospital and we are only interested in the
        # *single* nearest hospital, we *could* break here when we pop the
        # first hospital, because Dijkstra guarantees it is optimal.
        # For clarity and flexibility, we do not break and instead compute
        # full distances, then pick the best hospital at the end.

        # Relax edges out of this node.
        for neighbor_id, weight, _edge_id in graph.neighbors(node_id):
            new_dist = current_dist + weight

            # If this path to neighbor is better, update and push to heap.
            if neighbor_id not in distances or new_dist < distances[neighbor_id]:
                distances[neighbor_id] = new_dist
                previous[neighbor_id] = node_id
                heapq.heappush(heap, (new_dist, neighbor_id))

    # After Dijkstra finishes, we select the hospital with the
    # minimum distance among those we reached.
    best_hospital_id: Optional[NodeId] = None
    best_distance: Optional[float] = None
    distance_km: Optional[float] = None

    for hospital_id in hospital_set:
        d = distances.get(hospital_id)
        if d is None:
            # This hospital is not reachable; skip.
            continue

        if best_distance is None or d < best_distance:
            best_distance = d
            best_hospital_id = hospital_id

    # Calculate actual path distance in kilometers using edge distances.
    # If that fails or yields 0, fall back to haversine based on node coordinates.
    if best_hospital_id is not None:
        try:
            # Reconstruct path from source to best hospital using `previous` map.
            path: List[NodeId] = []
            cur: Optional[NodeId] = best_hospital_id
            # Guard against missing previous entries (should not normally happen).
            while cur is not None and cur in previous:
                path.append(cur)
                cur = previous.get(cur)
            path.reverse()

            # Sum edge distances along the path.
            total_meters: float = 0.0
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                edge = graph.get_edge(u, v)
                if edge is not None and edge.distance is not None:
                    total_meters += edge.distance

            if total_meters > 0:
                distance_km = total_meters / 1000.0
        except Exception as e:
            print(f"Error calculating path distance from edges: {e}")

        # Final safety net: if we still don't have a positive distance and we
        # have DB access, fall back to haversine straight-line distance.
        if (distance_km is None or distance_km == 0) and db is not None:
            try:
                source_node = db.query(Node).get(source_node_id)
                dest_node = db.query(Node).get(best_hospital_id)
                if source_node and dest_node:
                    distance_km = haversine_distance(
                        source_node.lat,
                        source_node.lon,
                        dest_node.lat,
                        dest_node.lon,
                    )
            except Exception as e:
                print(f"Error calculating haversine fallback distance: {e}")

    return HospitalSelectionResult(
        best_hospital_id=best_hospital_id,
        best_distance=best_distance,
        distances=distances,
        distance_km=distance_km,
    )
