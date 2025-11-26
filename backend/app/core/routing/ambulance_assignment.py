"""Ambulance selection (assignment) logic using the routing engine.

This module implements the next step in the app flow after an emergency
request has been created and a destination hospital has been chosen:

    "From all available ambulances, pick the one that can reach the
    hospital in the **minimum travel time**."

This is again **DSA-centric** logic that:
- Reuses the existing GraphManager (adjacency list) for the city.
- Uses Dijkstra's algorithm to compute shortest-path distances from
  each ambulance's current location to the hospital node.
- Selects the ambulance with the smallest estimated travel time (ETA).

We keep this module independent of HTTP; it only talks to the database
models and the graph/routing helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..graph.graph_manager import build_graph_for_city, NodeId
from ..routing.hospital_select import HospitalSelectionResult, find_nearest_hospital
from ...db.models import Ambulance, EmergencyRequest, Node


@dataclass
class AmbulanceCandidate:
    """Represents one ambulance with its estimated time to reach the hospital."""

    ambulance: Ambulance
    eta_to_hospital: float  # in minutes, based on shortest-path distance


@dataclass
class AmbulanceAssignmentPlan:
    """Result of running the ambulance selection logic.

    Attributes
    ----------
    best_ambulance:
        The ambulance object that should be assigned, or None if no
        reachable ambulance exists.
    best_eta:
        The ETA in minutes for `best_ambulance` to reach the hospital.
    candidates:
        List of all candidate ambulances (with their ETAs) that were
        considered during the selection.
    """

    best_ambulance: Optional[Ambulance]
    best_eta: Optional[float]
    candidates: List[AmbulanceCandidate]


def _compute_shortest_path_time(
    graph, source_node_id: NodeId, target_node_id: NodeId
) -> Optional[float]:
    """Helper: run Dijkstra from one source to get distance to one target.

    Instead of re-implementing Dijkstra here, we reuse the existing
    `find_nearest_hospital` function by treating the *target* as a
    "hospital" in the sense of "set of destinations".

    We pass a list containing only `target_node_id` as the set of
    hospital_node_ids; the function will run full Dijkstra from the
    source and then pick the best among that single-node set, which is
    exactly the distance we want.
    """

    # We reuse the structure of HospitalSelectionResult, but conceptually
    # we are just interested in the distance from source to target.
    selection_result: HospitalSelectionResult = find_nearest_hospital(
        graph=graph,
        source_node_id=source_node_id,
        hospital_node_ids=[target_node_id],
    )

    if selection_result.best_hospital_id is None:
        return None

    return selection_result.best_distance


def select_best_ambulance_for_request(
    db: Session,
    request_id: int,
) -> AmbulanceAssignmentPlan:
    """Select the best ambulance for a given emergency request.

    The logic assumes that the emergency request already has a
    source_node (patient location) and a destination_node (hospital).

    Steps (how to explain it):
    1. Load the EmergencyRequest and its destination (hospital node).
    2. Determine the city (through the hospital node's city_id).
    3. Build the graph for that city using GraphManager.
    4. Query all ambulances that are currently "available" and located
       at some node in that city.
    5. For each candidate ambulance:
         - Run shortest-path computation from ambulance.current_node
           to the hospital node to get ETA.
    6. Pick the ambulance with the minimum ETA.

    The function returns an AmbulanceAssignmentPlan summarizing the
    decision. It does **not** create an Assignment row yet; that will be
    handled by a higher-level helper.
    """

    # Step 1: load the emergency request.
    emergency_request = db.query(EmergencyRequest).filter(EmergencyRequest.id == request_id).first()
    if emergency_request is None:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, candidates=[])

    if emergency_request.destination_node is None:
        # Without a destination hospital we cannot compute ETAs.
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, candidates=[])

    # Step 2: find the city via the hospital node.
    hospital_node: Node = db.query(Node).filter(Node.id == emergency_request.destination_node).first()
    if hospital_node is None or hospital_node.city_id is None:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, candidates=[])

    city_id = hospital_node.city_id

    # Step 3: build the graph for this city.
    graph = build_graph_for_city(db, city_id)

    # Step 4: fetch all available ambulances in this city.
    ambulances: List[Ambulance] = (
        db.query(Ambulance)
        .join(Node, Ambulance.current_node == Node.id)
        .filter(Ambulance.status == "available")
        .filter(Node.city_id == city_id)
        .all()
    )

    candidates: List[AmbulanceCandidate] = []

    # Step 5: compute ETA for each ambulance.
    for amb in ambulances:
        if amb.current_node is None:
            continue

        eta = _compute_shortest_path_time(
            graph=graph,
            source_node_id=amb.current_node,
            target_node_id=hospital_node.id,
        )

        if eta is None:
            # No path from this ambulance to the hospital.
            continue

        candidates.append(AmbulanceCandidate(ambulance=amb, eta_to_hospital=eta))

    # Step 6: select the ambulance with minimum ETA.
    if not candidates:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, candidates=[])

    best = min(candidates, key=lambda c: c.eta_to_hospital)

    return AmbulanceAssignmentPlan(
        best_ambulance=best.ambulance,
        best_eta=best.eta_to_hospital,
        candidates=candidates,
    )
