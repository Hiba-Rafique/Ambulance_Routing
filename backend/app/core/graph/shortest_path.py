# app/core/graph/shortest_path.py
"""Dijkstra shortest path + path reconstruction for GraphManager.

Returns (distance_in_minutes, path_node_id_list) or (None, []) if unreachable.
"""
from __future__ import annotations
import heapq
from typing import List, Optional, Tuple

from ..graph.graph_manager import GraphManager, NodeId


def shortest_path_and_distance(graph: GraphManager, source: NodeId, target: NodeId) -> Tuple[Optional[float], List[NodeId]]:
    if not graph.has_node(source) or not graph.has_node(target):
        return None, []

    # dist and predecessor maps
    dist = {source: 0.0}
    prev: dict[int, int] = {}

    heap: List[tuple[float, int]] = [(0.0, source)]
    visited: set[int] = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u == target:
            break

        for neighbor_id, weight, _edge_id in graph.neighbors(u):
            # skip neighbors that are not usable (weight is None or inf)
            if weight is None:
                continue
            new_d = d + weight
            if neighbor_id not in dist or new_d < dist[neighbor_id]:
                dist[neighbor_id] = new_d
                prev[neighbor_id] = u
                heapq.heappush(heap, (new_d, neighbor_id))

    if target not in dist:
        return None, []

    # reconstruct path
    path: List[int] = []
    cur = target
    while cur != source:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            # path broken (shouldn't happen), bail out
            return None, []
    path.append(source)
    path.reverse()

    return dist[target], path
