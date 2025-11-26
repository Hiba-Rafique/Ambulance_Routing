"""Placeholder router for ambulance-related endpoints.

You can later add endpoints for listing ambulances, updating their
positions, etc. For now we keep it simple so that imports work.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def ambulance_health_check():
    return {"status": "ambulance router ready"}
