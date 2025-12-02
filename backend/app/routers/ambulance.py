"""Ambulance-related API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Ambulance, Assignment, EmergencyRequest

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def ambulance_health_check():
    return {"status": "ambulance router ready"}


@router.post("/{ambulance_id}/complete")
def complete_emergency_request(ambulance_id: int, db: Session = Depends(get_db)):
    """
    Mark the current assignment for the ambulance as completed.
    Updates:
    - EmergencyRequest.completed_at
    - Ambulance.status -> 'available'
    - Assignment.status -> 'completed'
    """
    # 1. Find the active assignment for this ambulance
    # Check for both 'assigned' and 'in-transit' as active statuses
    assignment = (
        db.query(Assignment)
        .filter(Assignment.ambulance_id == ambulance_id)
        .filter(Assignment.status.in_(["assigned", "in-transit"]))
        .first()
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="No active assignment found for this ambulance")

    # 2. Get the associated emergency request
    emergency_request = (
        db.query(EmergencyRequest)
        .filter(EmergencyRequest.id == assignment.emergency_request_id)
        .first()
    )

    if not emergency_request:
        raise HTTPException(status_code=404, detail="Emergency request not found")

    # 3. Update timestamps and statuses
    now = datetime.utcnow()
    emergency_request.completed_at = now
    emergency_request.status = "completed"

    assignment.status = "completed"
    
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if ambulance:
        ambulance.status = "available"

    db.commit()

    return {
        "message": "Emergency request completed successfully",
        "completed_at": now,
        "ambulance_id": ambulance_id,
        "request_id": emergency_request.id
    }
