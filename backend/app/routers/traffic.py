"""Traffic management endpoints for roadblocks and traffic updates.

This router provides CRUD operations for:
- Roadblocks: Completely block roads (e.g., accidents, construction)
- Traffic Updates: Modify travel times due to congestion
"""

from datetime import datetime
from typing import List, Optional, Generator
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Roadblock, TrafficUpdate, Edge, Node

router = APIRouter()


# Dependency to get a DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Schemas -------------------- #

class RoadblockCreate(BaseModel):
    edge_id: int = Field(..., description="ID of the edge to block")
    reason: str = Field(..., description="Reason for the roadblock")
    end_time: Optional[datetime] = Field(None, description="When the roadblock ends (null = indefinite)")


class RoadblockOut(BaseModel):
    id: int
    edge_id: int
    from_node: int
    to_node: int
    reason: str
    start_time: datetime
    end_time: Optional[datetime]

    class Config:
        from_attributes = True


class TrafficUpdateCreate(BaseModel):
    edge_id: int = Field(..., description="ID of the edge to update")
    new_weight: float = Field(..., gt=0, description="New travel time in minutes")


class TrafficUpdateOut(BaseModel):
    id: int
    edge_id: int
    from_node: int
    to_node: int
    original_weight: float
    new_weight: float
    timestamp: datetime

    class Config:
        from_attributes = True


class EdgeInfo(BaseModel):
    id: int
    from_node: int
    to_node: int
    weight: float
    distance: Optional[float]
    is_active: bool

    class Config:
        from_attributes = True


# -------------------- Health Check -------------------- #

@router.get("/health")
def traffic_health_check():
    return {"status": "traffic router ready"}


# -------------------- Roadblock Endpoints -------------------- #

@router.post("/roadblocks", response_model=RoadblockOut)
def create_roadblock(payload: RoadblockCreate, db: Session = Depends(get_db)):
    """Create a new roadblock on an edge."""
    # Verify edge exists
    edge = db.query(Edge).filter(Edge.id == payload.edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge {payload.edge_id} not found")
    
    # Check if roadblock already exists for this edge
    existing = db.query(Roadblock).filter(Roadblock.edge_id == payload.edge_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Roadblock already exists for edge {payload.edge_id}")
    
    roadblock = Roadblock(
        edge_id=payload.edge_id,
        reason=payload.reason,
        start_time=datetime.utcnow(),
        end_time=payload.end_time
    )
    db.add(roadblock)
    db.commit()
    db.refresh(roadblock)
    
    return RoadblockOut(
        id=roadblock.id,
        edge_id=roadblock.edge_id,
        from_node=edge.from_node,
        to_node=edge.to_node,
        reason=roadblock.reason,
        start_time=roadblock.start_time,
        end_time=roadblock.end_time
    )


@router.get("/roadblocks", response_model=List[RoadblockOut])
def list_roadblocks(city_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all active roadblocks, optionally filtered by city."""
    query = db.query(Roadblock).join(Roadblock.edge).join(Edge.from_node_rel)
    
    if city_id:
        query = query.filter(Node.city_id == city_id)
    
    roadblocks = query.all()
    
    result = []
    for rb in roadblocks:
        edge = rb.edge
        result.append(RoadblockOut(
            id=rb.id,
            edge_id=rb.edge_id,
            from_node=edge.from_node,
            to_node=edge.to_node,
            reason=rb.reason,
            start_time=rb.start_time,
            end_time=rb.end_time
        ))
    return result


@router.delete("/roadblocks/{roadblock_id}")
def delete_roadblock(roadblock_id: int, db: Session = Depends(get_db)):
    """Remove a roadblock (road is now open)."""
    roadblock = db.query(Roadblock).filter(Roadblock.id == roadblock_id).first()
    if not roadblock:
        raise HTTPException(status_code=404, detail=f"Roadblock {roadblock_id} not found")
    
    db.delete(roadblock)
    db.commit()
    return {"message": f"Roadblock {roadblock_id} removed successfully"}


@router.delete("/roadblocks/edge/{edge_id}")
def delete_roadblock_by_edge(edge_id: int, db: Session = Depends(get_db)):
    """Remove roadblock by edge ID."""
    roadblock = db.query(Roadblock).filter(Roadblock.edge_id == edge_id).first()
    if not roadblock:
        raise HTTPException(status_code=404, detail=f"No roadblock found for edge {edge_id}")
    
    db.delete(roadblock)
    db.commit()
    return {"message": f"Roadblock on edge {edge_id} removed successfully"}


# -------------------- Traffic Update Endpoints -------------------- #

@router.post("/traffic-updates", response_model=TrafficUpdateOut)
def create_traffic_update(payload: TrafficUpdateCreate, db: Session = Depends(get_db)):
    """Create or update traffic conditions on an edge."""
    # Verify edge exists
    edge = db.query(Edge).filter(Edge.id == payload.edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge {payload.edge_id} not found")
    
    # Check if traffic update already exists - update it instead of creating new
    existing = db.query(TrafficUpdate).filter(TrafficUpdate.edge_id == payload.edge_id).first()
    if existing:
        existing.new_weight = payload.new_weight
        existing.timestamp = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return TrafficUpdateOut(
            id=existing.id,
            edge_id=existing.edge_id,
            from_node=edge.from_node,
            to_node=edge.to_node,
            original_weight=edge.weight,
            new_weight=existing.new_weight,
            timestamp=existing.timestamp
        )
    
    traffic_update = TrafficUpdate(
        edge_id=payload.edge_id,
        new_weight=payload.new_weight,
        timestamp=datetime.utcnow()
    )
    db.add(traffic_update)
    db.commit()
    db.refresh(traffic_update)
    
    return TrafficUpdateOut(
        id=traffic_update.id,
        edge_id=traffic_update.edge_id,
        from_node=edge.from_node,
        to_node=edge.to_node,
        original_weight=edge.weight,
        new_weight=traffic_update.new_weight,
        timestamp=traffic_update.timestamp
    )


@router.get("/traffic-updates", response_model=List[TrafficUpdateOut])
def list_traffic_updates(city_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all traffic updates, optionally filtered by city."""
    query = db.query(TrafficUpdate).join(TrafficUpdate.edge).join(Edge.from_node_rel)
    
    if city_id:
        query = query.filter(Node.city_id == city_id)
    
    updates = query.all()
    
    result = []
    for tu in updates:
        edge = tu.edge
        result.append(TrafficUpdateOut(
            id=tu.id,
            edge_id=tu.edge_id,
            from_node=edge.from_node,
            to_node=edge.to_node,
            original_weight=edge.weight,
            new_weight=tu.new_weight,
            timestamp=tu.timestamp
        ))
    return result


@router.delete("/traffic-updates/{update_id}")
def delete_traffic_update(update_id: int, db: Session = Depends(get_db)):
    """Remove a traffic update (revert to normal traffic)."""
    traffic_update = db.query(TrafficUpdate).filter(TrafficUpdate.id == update_id).first()
    if not traffic_update:
        raise HTTPException(status_code=404, detail=f"Traffic update {update_id} not found")
    
    db.delete(traffic_update)
    db.commit()
    return {"message": f"Traffic update {update_id} removed successfully"}


@router.delete("/traffic-updates/edge/{edge_id}")
def delete_traffic_update_by_edge(edge_id: int, db: Session = Depends(get_db)):
    """Remove traffic update by edge ID."""
    traffic_update = db.query(TrafficUpdate).filter(TrafficUpdate.edge_id == edge_id).first()
    if not traffic_update:
        raise HTTPException(status_code=404, detail=f"No traffic update found for edge {edge_id}")
    
    db.delete(traffic_update)
    db.commit()
    return {"message": f"Traffic update on edge {edge_id} removed successfully"}


# -------------------- Edge Information -------------------- #

@router.get("/edges", response_model=List[EdgeInfo])
def list_edges(city_id: int, db: Session = Depends(get_db)):
    """List all edges for a city (useful for selecting which edges to block/update)."""
    edges = (
        db.query(Edge)
        .join(Edge.from_node_rel)
        .filter(Node.city_id == city_id)
        .all()
    )
    return [
        EdgeInfo(
            id=e.id,
            from_node=e.from_node,
            to_node=e.to_node,
            weight=e.weight,
            distance=e.distance,
            is_active=e.is_active
        )
        for e in edges
    ]


# -------------------- Clear All -------------------- #

@router.delete("/clear-all")
def clear_all_traffic_data(db: Session = Depends(get_db)):
    """Clear all roadblocks and traffic updates (reset to normal conditions)."""
    roadblocks_deleted = db.query(Roadblock).delete()
    traffic_updates_deleted = db.query(TrafficUpdate).delete()
    db.commit()
    return {
        "message": "All traffic data cleared",
        "roadblocks_deleted": roadblocks_deleted,
        "traffic_updates_deleted": traffic_updates_deleted
    }
