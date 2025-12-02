"""
Helpers for creating emergency requests using the routing engine.

This module provides the bridge between:
- The pure DSA routing logic (auto-selecting the best hospital), and
- The persistent data model (`EmergencyRequest` in the database).

There is still no HTTP/FastAPI code here. A web API layer can call these
functions to perform the actual work when a user clicks "Request
Ambulance (Auto Hospital)" on the frontend.

NOTE: Ambulance assignment is handled separately in routing.py to avoid
duplicate assignments. This module only creates the EmergencyRequest.
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy.orm import Session

# Routing: find nearest hospital
from app.core.routing.request_flow import auto_select_hospital_for_location

# DB models
from app.db.models import EmergencyRequest, Node


def create_emergency_request_auto(
    db: Session,
    city_id: int,
    latitude: float,
    longitude: float,
    caller_name: Optional[str] = None,
    caller_phone: Optional[str] = None,
) -> Tuple[Optional[EmergencyRequest], Optional[str]]:
    """
    Create an EmergencyRequest using auto-selected nearest hospital.
    
    NOTE: This function only creates the EmergencyRequest record.
    Ambulance assignment should be done by the caller (routing.py)
    to ensure it happens only once and the simulation can be started.
    """

    # Step 1: auto-select hospital
    selection_result = auto_select_hospital_for_location(
        db=db,
        city_id=city_id,
        latitude=latitude,
        longitude=longitude,
    )

    if selection_result is None:
        return None, "No routing data or hospitals available for this city."

    if selection_result.best_hospital_id is None:
        return None, "No reachable hospital from the caller location."

    best_hospital_node_id = selection_result.best_hospital_id

    # Step 2: compute nearest graph node for caller
    source_node = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .order_by(
            (Node.lat - latitude) * (Node.lat - latitude)
            + (Node.lon - longitude) * (Node.lon - longitude)
        )
        .first()
    )

    if source_node is None:
        return None, "Could not find a source node for the caller location."

    # Step 3: create request row
    emergency_request = EmergencyRequest(
        source_node=source_node.id,
        destination_node=best_hospital_node_id,
        caller_name=caller_name,
        caller_phone=caller_phone,
        status="pending",
    )

    db.add(emergency_request)
    db.commit()
    db.refresh(emergency_request)

    # Ambulance assignment is handled in routing.py to avoid duplicate assignments
    return emergency_request, None
