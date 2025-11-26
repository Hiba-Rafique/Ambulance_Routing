"""High-level routing helpers for the emergency request flow.

This module connects the smaller DSA building blocks into the concrete
operation we need in the app flow:

    1. Caller provides a location in a given city (latitude, longitude).
    2. System auto-selects the nearest hospital based on *travel time*,
       not just straight-line distance.

It does this by combining:
- nearest_node.find_nearest_node_for_location  → maps (lat, lon) to a graph node
- graph_manager.build_graph_for_city           → builds adjacency list for that city
- hospital_select.find_nearest_hospital        → runs Dijkstra to pick the best hospital

This is still **pure backend logic** with no knowledge of HTTP/JSON. A
FastAPI route or any other interface can simply call the functions in
this module.
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
from ...db.models import Node


def auto_select_hospital_for_location(
    db: Session,
    city_id: int,
    latitude: float,
    longitude: float,
) -> Optional[HospitalSelectionResult]:
    """End-to-end helper to choose the best hospital for a caller location.

    Parameters
    ----------
    db:
        SQLAlchemy session for querying nodes/edges.
    city_id:
        City in which we are operating. We only consider nodes/edges
        that belong to this city.
    latitude, longitude:
        Approximate location of the patient/caller.

    Returns
    -------
    Optional[HospitalSelectionResult]
        - A `HospitalSelectionResult` object if at least one hospital is
          reachable in this city's graph.
        - None if we cannot even map the caller to a graph node or there
          are no hospital nodes in this city.

    High-level explanation (good to mention in a viva):
    1. Map the caller's (lat, lon) to the nearest graph node. This makes
       the problem purely graph-based.
    2. Build the adjacency-list representation for this city's road
       network using `GraphManager`.
    3. Fetch all nodes that are tagged as hospitals.
    4. Run Dijkstra via `find_nearest_hospital` to select the hospital
       with the minimum travel time from the caller node.
    """

    # Step 1: map (lat, lon) → nearest node in this city.
    source_node_id = find_nearest_node_for_location(
        db=db,
        city_id=city_id,
        latitude=latitude,
        longitude=longitude,
    )

    if source_node_id is None:
        # City has no nodes at all; nothing we can do.
        return None

    # Step 2: build an in-memory graph for this city.
    graph = build_graph_for_city(db, city_id)

    # Step 3: gather all hospital nodes in this city.
    hospital_nodes: List[Node] = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .filter(Node.type == "hospital")
        .all()
    )

    hospital_ids = [node.id for node in hospital_nodes]
    if not hospital_ids:
        # No hospitals defined for this city.
        return None

    # Step 4: run Dijkstra to find the nearest hospital by travel time.
    result = find_nearest_hospital(
        graph=graph,
        source_node_id=source_node_id,
        hospital_node_ids=hospital_ids,
    )

    # If best_hospital_id is None, it means there is no path from the
    # caller node to any hospital in the graph (disconnected components
    # or all paths blocked). We still return the result object so the
    # caller can inspect distances if needed.
    return result
