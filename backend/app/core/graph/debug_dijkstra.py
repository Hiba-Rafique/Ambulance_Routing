from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import EmergencyRequest, Node, Edge, Roadblock, TrafficUpdate
from app.core.graph.graph_manager import GraphManager, NodeId, EdgeId, build_graph_for_city
from app.core.routing.traffic_manager import apply_dynamic_traffic


@dataclass
class DebugStep:
    current: Optional[NodeId]
    distances: Dict[NodeId, float]
    visited: List[NodeId]
    frontier: List[NodeId]


def run_dijkstra_debug_for_request(
    db: Session,
    request_id: int,
) -> Tuple[
    EmergencyRequest,
    List[Node],
    List[Edge],
    List[DebugStep],
    List[NodeId],
    Optional[float],
]:
    """Run Dijkstra for a given emergency request and capture debug steps.

    Returns
    -------
    emergency_request: EmergencyRequest DB row
    nodes: all Node rows for the request's city
    edges: all Edge rows used in the GraphManager for that city
    steps: list of DebugStep capturing algorithm state after each pop
    shortest_path: list of node IDs from source to destination (may be empty)
    """

    emergency_request = db.query(EmergencyRequest).get(request_id)
    if emergency_request is None:
        raise ValueError(f"EmergencyRequest {request_id} not found")

    source = emergency_request.source_node
    target = emergency_request.destination_node

    if source is None or target is None:
        raise ValueError("EmergencyRequest is missing source or destination node")

    # infer city from source node
    source_node = db.query(Node).get(source)
    if source_node is None or source_node.city_id is None:
        raise ValueError("Source node or its city_id not found")

    city_id = source_node.city_id

    # build graph and apply the same dynamic traffic/roadblocks as normal routing
    graph: GraphManager = build_graph_for_city(db, city_id)
    apply_dynamic_traffic(graph, db, city_id)

    # collect nodes and edges actually used in this city view
    nodes = db.query(Node).filter(Node.city_id == city_id).all()
    # edges are stored inside GraphManager.edges
    edges = list(graph.edges.values())

    # Mark edges that currently have roadblocks or traffic updates so the
    # visualizer can highlight them.
    from datetime import datetime
    now = datetime.utcnow()

    # Active roadblocks (same logic as traffic_manager)
    active_rbs = (
        db.query(Roadblock)
        .join(Roadblock.edge)
        .filter(Roadblock.start_time <= now)
        .filter((Roadblock.end_time.is_(None)) | (Roadblock.end_time >= now))
        .all()
    )
    blocked_edge_ids = {rb.edge_id for rb in active_rbs}

    # Traffic updates active in current peak hours (reuse same peak_hours set)
    peak_hours = {7, 8, 9, 16, 17, 18}
    if now.hour in peak_hours:
        active_tu = db.query(TrafficUpdate).all()
        traffic_edge_ids = {tu.edge_id for tu in active_tu}
    else:
        traffic_edge_ids = set()

    for e in edges:
        # annotate edge objects (not persisted) so router can pick up flags
        setattr(e, "_is_blocked", e.id in blocked_edge_ids)
        setattr(e, "_has_traffic", e.id in traffic_edge_ids)

    # classical Dijkstra, but record per-pop state for visualization
    dist: Dict[NodeId, float] = {source: 0.0}
    prev: Dict[NodeId, NodeId] = {}
    visited: List[NodeId] = []
    steps: List[DebugStep] = []

    import heapq

    heap: List[Tuple[float, NodeId]] = [(0.0, source)]
    visited_set = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited_set:
            continue
        visited_set.add(u)
        visited.append(u)

        # frontier = neighbors of u that are not yet visited
        frontier: List[NodeId] = []
        for v, w, _eid in graph.neighbors(u):
            if v not in visited_set:
                frontier.append(v)

        # snapshot BEFORE relaxing neighbors so distances correspond
        steps.append(
            DebugStep(
                current=u,
                distances=dict(dist),
                visited=list(visited),
                frontier=list(frontier),
            )
        )
        # We do NOT break when u == target; we want to continue
        # exploring to show the full behavior of the algorithm.

        for v, w, _eid in graph.neighbors(u):
            if w is None:
                continue
            alt = d + w
            if v not in dist or alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    # reconstruct path if reachable, and compute total distance in km using edge.distance
    path: List[NodeId] = []
    total_distance_km: Optional[float] = None
    if target in dist:
        cur = target
        while cur != source:
            path.append(cur)
            cur = prev.get(cur)
            if cur is None:
                path = []
                break
        if path:
            path.append(source)
            path.reverse()

            # compute total distance along this path using the stored Edge objects
            total_meters = 0.0
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                # graph.edges is a dict[EdgeId, Edge]; we need to look up the
                # specific edge connecting u -> v.
                for neighbor_id, _w, edge_id in graph.neighbors(u):
                    if neighbor_id == v:
                        edge_obj = graph.edges.get(edge_id)
                        if edge_obj is not None and edge_obj.distance is not None:
                            total_meters += edge_obj.distance
                        break
            if total_meters > 0:
                total_distance_km = total_meters / 1000.0

    # final step (no more nodes or unreachable target)
    steps.append(
        DebugStep(
            current=None,
            distances=dict(dist),
            visited=list(visited),
            frontier=[],
        )
    )

    return emergency_request, nodes, edges, steps, path, total_distance_km
