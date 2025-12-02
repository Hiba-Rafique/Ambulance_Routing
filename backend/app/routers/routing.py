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


class AutoEmergencyRequestResponse(BaseModel):
    request_id: int
    source_node_id: int
    destination_hospital_node_id: int
    estimated_travel_time: Optional[float]


class HospitalOut(BaseModel):
    id: int
    name: Optional[str]
    lat: float
    lon: float


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

    # Step 2: Re-run hospital selection to get ETA (minutes)
    from app.core.routing.request_flow import auto_select_hospital_for_location
    selection_result = auto_select_hospital_for_location(
        db=db,
        city_id=payload.city_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    eta_minutes = selection_result.best_distance if selection_result else None

    # Step 3: Create assignment for ambulance
    assignment_result = create_assignment_for_request(db, emergency_request.id)

    if assignment_result is None:
        # No ambulance available; return ETA only
        return AutoEmergencyRequestResponse(
            request_id=emergency_request.id,
            source_node_id=emergency_request.source_node,
            destination_hospital_node_id=emergency_request.destination_node,
            estimated_travel_time=eta_minutes,
        )

    # Unpack assignment tuple: (assignment, eta, route_node_ids)
    assignment, assigned_eta_minutes, route_node_ids = assignment_result

    # NOTE: Simulation is NOT started here anymore.
    # It will be started when the frontend connects to the WebSocket endpoint.
    # This ensures the client doesn't miss any ETA updates.

    # Return API response
    return AutoEmergencyRequestResponse(
        request_id=emergency_request.id,
        source_node_id=emergency_request.source_node,
        destination_hospital_node_id=emergency_request.destination_node,
        estimated_travel_time=assigned_eta_minutes,
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
