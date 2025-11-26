"""Placeholder router for traffic-related endpoints.

Currently kept minimal so that `main.py` can include it without errors.
You can later add endpoints here for simulating or updating traffic.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def traffic_health_check():
    return {"status": "traffic router ready"}
