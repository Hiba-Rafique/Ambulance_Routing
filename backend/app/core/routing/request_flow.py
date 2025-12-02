"""
High-level routing helpers for the emergency request flow.

This module connects the smaller DSA building blocks into the concrete
operation we need in the app flow:

1. Caller provides a location in a given city (latitude, longitude).
2. System auto-selects the nearest hospital based on *travel time*.
"""

from __future__ import annotations
from typing import List, Optional

from sqlalchemy.orm import Session

from ..graph.graph_manager import build_graph_for_city
from ..graph.nearest_node import find_nearest_node_for_location
from ..routing.hospital_select import (
    HospitalSelectionResult,
    find_nearest_hospital,
)
from ..routing.traffic_manager import apply_dynamic_traffic
from ...db.models import Node


def auto_select_hospital_for_location(
    db: Session,
    city_id: int,
    latitude: float,
    longitude: float,
) -> Optional[HospitalSelectionResult]:
    """
    End-to-end routing:
    - Convert (lat, lon) → nearest node
    - Build graph
    - APPLY traffic updates + roadblocks   ← (IMPORTANT FIX)
    - Run Dijkstra
    """

    # -----------------------------------------
    # Step 1 — map location to nearest node
    # -----------------------------------------
    source_node_id = find_nearest_node_for_location(
        db=db,
        city_id=city_id,
        latitude=latitude,
        longitude=longitude,
    )

    if source_node_id is None:
        return None

    # -----------------------------------------
    # Step 2 — build base graph for this city
    # -----------------------------------------
    graph = build_graph_for_city(db, city_id)

    # -----------------------------------------
    # Step 3 — APPLY TRAFFIC & ROADBLOCKS
    # -----------------------------------------
    try:
        apply_dynamic_traffic(graph, db, city_id)
    except Exception as e:
        print("ERROR: Traffic update failed:", e)

    # -----------------------------------------
    # Step 4 — gather hospital nodes
    # -----------------------------------------
    hospital_nodes: List[Node] = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .filter(Node.type == "hospital")
        .all()
    )

    hospital_ids = [node.id for node in hospital_nodes]

    if not hospital_ids:
        return None

    # -----------------------------------------
    # Step 5 — DIJKSTRA: find nearest hospital
    # -----------------------------------------
    result = find_nearest_hospital(
        graph=graph,
        source_node_id=source_node_id,
        hospital_node_ids=hospital_ids,
    )

    # Result is a HospitalSelectionResult with:
    # - best_hospital_id
    # - best_distance (ETA)
    # - full path list
    return result
