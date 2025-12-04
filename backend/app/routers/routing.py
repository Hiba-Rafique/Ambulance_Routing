"""Routing-related API endpoints.

This router exposes a high-level HTTP endpoint that connects the frontend
to the DSA-based routing core. Supports "auto-select hospital and create
emergency request" flow.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Generator

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Node
from app.core.routing.emergency_requests import create_emergency_request_auto
from app.core.routing.ambulance_assignment import create_assignment_for_request
from app.core.graph.debug_dijkstra import run_dijkstra_debug_for_request

router = APIRouter()


# Dependency to get a DB session per request
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Schemas -------------------- #

class AutoEmergencyRequestInput(BaseModel):
    city_id: int = Field(..., description="City in which the emergency occurs")
    latitude: float = Field(..., description="Patient/caller latitude")
    longitude: float = Field(..., description="Patient/caller longitude")
    caller_name: Optional[str] = Field(None, description="Name of the caller/patient")
    caller_phone: Optional[str] = Field(None, description="Contact number of the caller")


class RouteNodeOut(BaseModel):
    id: int
    lat: float
    lon: float


class AutoEmergencyRequestResponse(BaseModel):
    request_id: int
    source_node_id: int
    destination_hospital_node_id: int
    estimated_travel_time: Optional[float]
    distance_km: Optional[float] = None
    route_nodes: Optional[list[RouteNodeOut]] = None


class HospitalOut(BaseModel):
    id: int
    name: Optional[str]
    lat: float
    lon: float


class DebugDijkstraNode(BaseModel):
    id: int
    lat: float
    lon: float
    name: Optional[str]
    type: Optional[str]


class DebugDijkstraEdge(BaseModel):
    id: int
    from_node: int
    to_node: int
    weight: float
    adjusted_weight: Optional[float]
    distance: Optional[float]
    is_blocked: Optional[bool] = None
    has_traffic: Optional[bool] = None


class DebugDijkstraStep(BaseModel):
    current: Optional[int]
    distances: dict[int, float]
    visited: list[int]
    frontier: list[int]


class DebugDijkstraResponse(BaseModel):
    request_id: int
    source_node_id: int
    destination_node_id: int
    nodes: list[DebugDijkstraNode]
    edges: list[DebugDijkstraEdge]
    steps: list[DebugDijkstraStep]
    shortest_path: list[int]
    total_distance_km: Optional[float] = None


# -------------------- Endpoints -------------------- #

@router.post("/requests/auto", response_model=AutoEmergencyRequestResponse)
def create_emergency_request_auto_endpoint(
    payload: AutoEmergencyRequestInput,
    db: Session = Depends(get_db),
):
    # Step 1: Create emergency request
    emergency_request, error_message = create_emergency_request_auto(
        db=db,
        city_id=payload.city_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        caller_name=payload.caller_name,
        caller_phone=payload.caller_phone,
    )

    if error_message is not None or emergency_request is None:
        raise HTTPException(status_code=400, detail=error_message or "Unknown error")

    # Step 2: Re-run hospital selection to get ETA (minutes) and distance
    from app.core.routing.request_flow import auto_select_hospital_for_location
    selection_result = auto_select_hospital_for_location(
        db=db,
        city_id=payload.city_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    eta_minutes = selection_result.best_distance if selection_result else None
    distance_km = selection_result.distance_km if selection_result else None

    # Step 3: Create assignment for ambulance
    assignment_result = create_assignment_for_request(db, emergency_request.id)

    if assignment_result is None:
        # No ambulance available; return ETA only
        return AutoEmergencyRequestResponse(
            request_id=emergency_request.id,
            source_node_id=emergency_request.source_node,
            destination_hospital_node_id=emergency_request.destination_node,
            estimated_travel_time=eta_minutes,
            distance_km=distance_km,
        )

    # Unpack assignment tuple: (assignment, eta, route_node_ids)
    assignment, assigned_eta_minutes, route_node_ids = assignment_result

    # Build ordered route nodes for frontend map overlay (ambulance -> hospital)
    route_nodes: list[RouteNodeOut] = []
    if route_node_ids:
        db_nodes = db.query(Node).filter(Node.id.in_(route_node_ids)).all()
        node_map = {n.id: n for n in db_nodes}
        for nid in route_node_ids:
            node = node_map.get(nid)
            if node is not None:
                route_nodes.append(RouteNodeOut(id=node.id, lat=node.lat, lon=node.lon))

    # NOTE: Simulation is NOT started here anymore.
    # It will be started when the frontend connects to the WebSocket endpoint.
    # This ensures the client doesn't miss any ETA updates.

    # Return API response
    return AutoEmergencyRequestResponse(
        request_id=emergency_request.id,
        source_node_id=emergency_request.source_node,
        destination_hospital_node_id=emergency_request.destination_node,
        estimated_travel_time=assigned_eta_minutes,
        distance_km=distance_km,
        route_nodes=route_nodes or None,
    )


@router.get("/cities/{city_id}/hospitals", response_model=List[HospitalOut])
def list_hospitals_for_city(city_id: int, db: Session = Depends(get_db)):
    hospitals = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .filter(Node.type == "hospital")
        .all()
    )
    return [HospitalOut(id=h.id, name=h.name, lat=h.lat, lon=h.lon) for h in hospitals]


@router.get("/requests/{request_id}/debug/dijkstra", response_model=DebugDijkstraResponse)
def debug_dijkstra_for_request(request_id: int, db: Session = Depends(get_db)):
    """Return a debug view of Dijkstra for a specific emergency request.

    This does NOT affect normal routing; it just re-runs the algorithm on the
    same graph and captures internal steps so the frontend can visualize them.
    """

    try:
        emergency_request, nodes, edges, steps, path, total_distance_km = run_dijkstra_debug_for_request(
            db=db,
            request_id=request_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return DebugDijkstraResponse(
        request_id=emergency_request.id,
        source_node_id=emergency_request.source_node,
        destination_node_id=emergency_request.destination_node,
        nodes=[
            DebugDijkstraNode(
                id=n.id,
                lat=n.lat,
                lon=n.lon,
                name=n.name,
                type=n.type,
            )
            for n in nodes
        ],
        edges=[
            DebugDijkstraEdge(
                id=e.id,
                from_node=e.from_node,
                to_node=e.to_node,
                weight=e.weight,
                adjusted_weight=e.adjusted_weight,
                distance=e.distance,
                is_blocked=getattr(e, "_is_blocked", False),
                has_traffic=getattr(e, "_has_traffic", False),
            )
            for e in edges
        ],
        steps=[
            DebugDijkstraStep(
                current=s.current,
                distances=s.distances,
                visited=s.visited,
                frontier=s.frontier,
            )
            for s in steps
        ],
        shortest_path=path,
        total_distance_km=total_distance_km,
    )
