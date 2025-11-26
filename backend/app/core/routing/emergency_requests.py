"""Helpers for creating emergency requests using the routing engine.

This module provides the bridge between:
- The **pure DSA routing logic** (auto-selecting the best hospital), and
- The **persistent data model** (`EmergencyRequest` in the database).

There is still no HTTP/FastAPI code here. A web API layer can call these
functions to perform the actual work when a user clicks "Request
Ambulance (Auto Hospital)" on the frontend.
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..routing.request_flow import auto_select_hospital_for_location
from ...db.models import EmergencyRequest, Node


def create_emergency_request_auto(
    db: Session,
    city_id: int,
    latitude: float,
    longitude: float,
    caller_name: Optional[str] = None,
    caller_phone: Optional[str] = None,
) -> Tuple[Optional[EmergencyRequest], Optional[str]]:
    """Create an EmergencyRequest using auto-selected nearest hospital.

    Parameters
    ----------
    db:
        SQLAlchemy session used for both routing queries and inserting the
        new request.
    city_id:
        City in which the request is being made.
    latitude, longitude:
        Patient/caller location. These come from the frontend (map
        click, typed address converted to coordinates, or pin).
    caller_name, caller_phone:
        Optional metadata so operators can contact the caller if needed.

    Returns
    -------
    (EmergencyRequest | None, error_message | None)
        - On success: (EmergencyRequest instance, None)
        - On failure: (None, human-readable error message explaining what
          went wrong).

    High-level algorithm (easy to explain):
    1. Use the routing helper to auto-select the best hospital for this
       location.
    2. If no hospital can be found or reached, return an error message.
    3. If a hospital is found, create a new EmergencyRequest row that
       stores:
       - Source node (patient location node)
       - Destination node (hospital node)
       - Caller information
       - Initial status = "pending"
    """

    # Step 1: run the auto-selection pipeline.
    selection_result = auto_select_hospital_for_location(
        db=db,
        city_id=city_id,
        latitude=latitude,
        longitude=longitude,
    )

    if selection_result is None:
        # Either the city has no nodes or no hospitals.
        return None, "No routing data or hospitals available for this city."

    if selection_result.best_hospital_id is None:
        # Graph is disconnected or all paths to hospitals are blocked.
        return None, "No reachable hospital from the caller location."

    # At this point, we know which hospital node has the minimum travel
    # time according to Dijkstra.
    best_hospital_node_id = selection_result.best_hospital_id

    # We also need the *source* node used by the routing. The helper
    # `auto_select_hospital_for_location` internally chose the source
    # node via find_nearest_node_for_location, but it does not currently
    # expose that node id. For now, we will recompute it explicitly to
    # store it in the EmergencyRequest.
    #
    # NOTE: This keeps the responsibilities clear: routing focuses on
    # choosing the best hospital, while request creation ensures the
    # request row has both source and destination nodes recorded.
    source_node = (
        db.query(Node)
        .filter(Node.city_id == city_id)
        .order_by((Node.lat - latitude) * (Node.lat - latitude) + (Node.lon - longitude) * (Node.lon - longitude))
        .first()
    )

    if source_node is None:
        return None, "Could not find a source node for the caller location."

    # Step 3: create and persist the EmergencyRequest row.
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

    return emergency_request, None
