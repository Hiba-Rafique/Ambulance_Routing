# app/core/routing/traffic_manager.py
"""
Applies dynamic traffic updates & roadblocks to the in-memory graph.

The graph uses adjacency lists where:
    graph.adjacency[from_node] = List[Tuple[to_node, weight, edge_id]]

This module modifies the in-memory graph to reflect:
1. ROADBLOCKS: Completely removes edges (road is impassable)
2. TRAFFIC UPDATES: Modifies edge weights (increased travel time)
"""

from typing import List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import TrafficUpdate, Roadblock, Edge, Node


def apply_dynamic_traffic(graph, db: Session, city_id: int):
    """
    Apply real-time traffic + roadblocks to the routing graph.

    The graph structure is:
        graph.adjacency[from_node] = List[Tuple[to_node, weight, edge_id]]
    
    This function:
    1. Removes edges that have active roadblocks
    2. Updates weights for edges with traffic updates
    """

    now = datetime.utcnow()

    # -------------------------------
    # 1. ROADBLOCKS → REMOVE edges
    # -------------------------------
    # Collect all edge_ids that are currently blocked (start_time <= now <= end_time or end_time is NULL)
    active_roadblocks = (
        db.query(Roadblock)
        .join(Roadblock.edge)
        .join(Edge.from_node_rel)
        .filter(Node.city_id == city_id)
        .filter(Roadblock.start_time <= now)
        .filter((Roadblock.end_time.is_(None)) | (Roadblock.end_time >= now))
        .all()
    )

    blocked_edges = set()
    for rb in active_roadblocks:
        edge = rb.edge
        if edge:
            blocked_edges.add((edge.from_node, edge.to_node))

    # Remove blocked edges from adjacency list
    for from_node in graph.adjacency:
        # Filter out edges that are blocked
        # Each entry is (to_node, weight, edge_id)
        graph.adjacency[from_node] = [
            entry for entry in graph.adjacency[from_node]
            if (from_node, entry[0]) not in blocked_edges
        ]

    # -------------------------------
    # 2. TRAFFIC UPDATES → MODIFY weight
    # -------------------------------
    # Simple time-of-day model using current UTC hour. During peak hours we
    # apply traffic updates; outside those hours we ignore them.
    peak_hours = {7, 8, 9, 16, 17, 18}  # configurable: morning & evening rush

    if now.hour in peak_hours:
        traffic_updates = (
            db.query(TrafficUpdate)
            .join(TrafficUpdate.edge)
            .join(Edge.from_node_rel)
            .filter(Node.city_id == city_id)
            .all()
        )
    else:
        traffic_updates = []

    # Build a lookup: (from_node, to_node) -> new_weight
    traffic_weights = {}
    for tu in traffic_updates:
        edge = tu.edge
        if edge:
            traffic_weights[(edge.from_node, edge.to_node)] = tu.new_weight

    # Update weights in adjacency list
    for from_node in graph.adjacency:
        updated_entries: List[Tuple[int, float, int]] = []
        for to_node, weight, edge_id in graph.adjacency[from_node]:
            # Check if there's a traffic update for this edge
            if (from_node, to_node) in traffic_weights:
                new_weight = traffic_weights[(from_node, to_node)]
                updated_entries.append((to_node, new_weight, edge_id))
            else:
                updated_entries.append((to_node, weight, edge_id))
        graph.adjacency[from_node] = updated_entries
