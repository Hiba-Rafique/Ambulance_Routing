# app/core/routing/ambulance_assignment.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from app.core.graph.graph_manager import build_graph_for_city, NodeId
from app.core.graph.shortest_path import shortest_path_and_distance
from app.core.routing.traffic_manager import apply_dynamic_traffic
from app.db.models import Ambulance, EmergencyRequest, Node, Assignment


@dataclass
class AmbulanceCandidate:
    """Represents one ambulance with its estimated time and route to the hospital."""
    ambulance: Ambulance
    eta_to_hospital: float
    route: List[int]


@dataclass
class AmbulanceAssignmentPlan:
    """Result of ambulance selection logic."""
    best_ambulance: Optional[Ambulance]
    best_eta: Optional[float]
    best_route: Optional[List[int]]
    candidates: List[AmbulanceCandidate]


def _compute_shortest_path_time(
    graph, source_node_id: int, target_node_id: int
) -> Optional[Tuple[float, List[int]]]:
    """Computes shortest path and ETA in minutes."""
    distance, route = shortest_path_and_distance(graph, source_node_id, target_node_id)
    if distance is None or not route:
        return None
    # Convert NodeId to int if necessary
    route_ids = [int(nid) for nid in route]
    return distance, route_ids


def select_best_ambulance_for_request(db: Session, request_id: int) -> AmbulanceAssignmentPlan:
    """Selects the best available ambulance for an emergency request."""
    emergency_request = db.query(EmergencyRequest).filter(EmergencyRequest.id == request_id).first()
    if not emergency_request or not emergency_request.destination_node:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, best_route=None, candidates=[])

    hospital_node = db.query(Node).filter(Node.id == emergency_request.destination_node).first()
    if not hospital_node or not hospital_node.city_id:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, best_route=None, candidates=[])

    city_id = hospital_node.city_id

    # Build city graph and apply traffic updates
    graph = build_graph_for_city(db, city_id)
    apply_dynamic_traffic(graph, db, city_id)

    # Fetch available ambulances in city
    ambulances = (
        db.query(Ambulance)
        .join(Node, Ambulance.current_node == Node.id)
        .filter(Ambulance.status == "available")
        .filter(Node.city_id == city_id)
        .all()
    )

    candidates: List[AmbulanceCandidate] = []

    for amb in ambulances:
        if amb.current_node is None:
            continue
        result = _compute_shortest_path_time(graph, amb.current_node, hospital_node.id)
        if result is None:
            continue
        eta, route = result
        candidates.append(AmbulanceCandidate(ambulance=amb, eta_to_hospital=eta, route=route))

    if not candidates:
        return AmbulanceAssignmentPlan(best_ambulance=None, best_eta=None, best_route=None, candidates=[])

    best_candidate = min(candidates, key=lambda c: c.eta_to_hospital)

    return AmbulanceAssignmentPlan(
        best_ambulance=best_candidate.ambulance,
        best_eta=best_candidate.eta_to_hospital,
        best_route=best_candidate.route,
        candidates=candidates
    )


def create_assignment_for_request(db: Session, request_id: int) -> Optional[Tuple[Assignment, float, List[int]]]:
    """
    Creates an assignment for the best ambulance and returns:
    (assignment, eta_minutes, route_node_ids)
    Returns None if no ambulance is available or if an assignment already exists.
    """
    # Check if an assignment already exists for this request to prevent duplicates
    existing_assignment = db.query(Assignment).filter(
        Assignment.emergency_request_id == request_id
    ).first()
    
    if existing_assignment:
        # Assignment already exists, do not create a duplicate
        return None
    
    plan = select_best_ambulance_for_request(db, request_id)
    if not plan.best_ambulance or not plan.best_eta or not plan.best_route:
        return None

    # Create assignment
    assignment = Assignment(
        ambulance_id=plan.best_ambulance.id,
        emergency_request_id=request_id,
        eta=plan.best_eta,
        status="assigned"
    )

    # Persist assignment and mark ambulance as assigned
    plan.best_ambulance.status = "assigned"

    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    db.refresh(plan.best_ambulance)

    return assignment, plan.best_eta, plan.best_route
