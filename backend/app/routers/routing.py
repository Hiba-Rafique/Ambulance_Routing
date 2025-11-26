"""Routing-related API endpoints.

This router exposes a high-level HTTP endpoint that connects the
frontend to the DSA-based routing core. For now we only implement the
"auto-select hospital and create emergency request" flow.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.db.database import SessionLocal
from sqlalchemy.orm import Session

from app.core.routing.emergency_requests import create_emergency_request_auto
from app.db.models import Node


router = APIRouter()


# Dependency to get a DB session per request
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AutoEmergencyRequestInput(BaseModel):
    """Input schema for auto-hospital emergency request.

    This represents what the frontend should send when the user clicks
    "Request Ambulance" in auto-select mode.
    """

    city_id: int = Field(..., description="City in which the emergency occurs")
    latitude: float = Field(..., description="Patient/caller latitude")
    longitude: float = Field(..., description="Patient/caller longitude")
    caller_name: Optional[str] = Field(None, description="Name of the caller/patient")
    caller_phone: Optional[str] = Field(None, description="Contact number of the caller")


class AutoEmergencyRequestResponse(BaseModel):
    """What we return after creating an emergency request using auto mode."""

    request_id: int
    source_node_id: int
    destination_hospital_node_id: int
    estimated_travel_time: Optional[float]


class HospitalOut(BaseModel):
  """Hospital representation returned to the frontend.

  This is directly based on the `nodes` table where type == "hospital".
  For now we only expose the minimal fields the frontend needs.
  """

  id: int
  name: Optional[str]
  lat: float
  lon: float


@router.post("/requests/auto", response_model=AutoEmergencyRequestResponse)
def create_emergency_request_auto_endpoint(
    payload: AutoEmergencyRequestInput,
    db: Session = Depends(get_db),
):
    """Create an emergency request using auto-selected nearest hospital.

    Flow:
    1. Call the core helper `create_emergency_request_auto` which:
       - Maps (lat, lon) → nearest node
       - Builds the graph for the city
       - Runs Dijkstra to find the best hospital
       - Inserts an EmergencyRequest row
    2. If anything fails (no hospitals / no path), return HTTP 400 with
       a clear error message.
    3. On success, return the new request ID, source node, destination
       hospital node and the Dijkstra distance (travel time estimate).
    """

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

    # For now we re-run the routing helper to fetch the estimated travel
    # time. This keeps the API response informative for the frontend
    # without storing distances directly in the request table.
    from app.core.routing.request_flow import auto_select_hospital_for_location

    selection_result = auto_select_hospital_for_location(
        db=db,
        city_id=payload.city_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    eta = selection_result.best_distance if selection_result else None

    return AutoEmergencyRequestResponse(
        request_id=emergency_request.id,
        source_node_id=emergency_request.source_node,
        destination_hospital_node_id=emergency_request.destination_node,
        estimated_travel_time=eta,
    )


@router.get("/cities/{city_id}/hospitals", response_model=List[HospitalOut])
def list_hospitals_for_city(city_id: int, db: Session = Depends(get_db)):
    """Return all hospital nodes for a given city.

    The frontend can use this to:
    - Populate the hospital selection list for a city.
    - Plot hospital markers on the map using their latitude/longitude.
    """

    hospitals = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .filter(Node.type == "hospital")
        .all()
    )

    return [
        HospitalOut(id=h.id, name=h.name, lat=h.lat, lon=h.lon)
        for h in hospitals
    ]
