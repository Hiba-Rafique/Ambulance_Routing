import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.core.routing.socket_manager import manager
from app.db.database import SessionLocal
from app.db.models import Ambulance, Assignment, EmergencyRequest, Node


async def simulate_ambulance_movement(request_id: int, route_nodes: List[Node], total_eta_minutes: float = 10.0):
    """
    Simulates ambulance movement along a route with real-time ETA updates.
    
    The simulation:
    - Broadcasts position and ETA updates every second via WebSocket
    - Decrements ETA in real-time as the ambulance progresses
    - Updates ambulance status: 'assigned' -> (in-transit during simulation) -> 'available'
    - Marks Assignment and EmergencyRequest as completed upon arrival
    
    Args:
        request_id: The emergency request ID being serviced
        route_nodes: List of Node objects representing the route path
        total_eta_minutes: Total estimated time in minutes for the journey
    """
    if not route_nodes:
        return

    db: Session = SessionLocal()
    try:
        assignment = db.query(Assignment).filter(
            Assignment.emergency_request_id == request_id,
            Assignment.status.in_(["assigned", "in-transit"])
        ).first()
        if not assignment:
            return

        ambulance_id = assignment.ambulance_id
        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            return

        # Mark assignment as in-transit (ambulance status remains 'assigned' during transit)
        assignment.status = "in-transit"
        db.commit()

        total_steps = max(1, len(route_nodes))
        # Total seconds to simulate the journey
        total_seconds = max(1, int(round(total_eta_minutes * 60)))
        
        # Calculate time to spend at each node
        seconds_per_step = total_seconds / total_steps
        
        # Track remaining ETA in seconds (starts at total, decrements each second)
        remaining_eta_seconds = total_seconds
        
        for i, node in enumerate(route_nodes):
            # Update ambulance location in DB
            ambulance.current_node = node.id
            db.commit()
            
            # Calculate how many seconds to spend at this node
            # For the last node, we spend any remaining time
            if i == total_steps - 1:
                node_duration = max(1, remaining_eta_seconds)
            else:
                node_duration = max(1, int(round(seconds_per_step)))
            
            # Broadcast updates every second while at this node
            for second in range(node_duration):
                # Calculate progress through entire route
                steps_completed = i + (second / node_duration) if node_duration > 0 else i
                progress = min(1.0, (steps_completed + 1) / total_steps)
                
                # Determine status based on remaining time
                is_arrived = (i == total_steps - 1) and (second == node_duration - 1)
                
                update_payload = {
                    "ambulance_id": ambulance_id,
                    "current_location": {"lat": node.lat, "lng": node.lon},
                    "status": "arrived" if is_arrived else "in-transit",
                    "progress": progress,
                    "node_index": i,
                    "eta_seconds": max(0, remaining_eta_seconds)
                }
                
                await manager.broadcast(update_payload, request_id)
                
                # Wait one second (real-time simulation)
                await asyncio.sleep(1)
                
                # Decrement ETA by 1 second
                remaining_eta_seconds = max(0, remaining_eta_seconds - 1)

        # Arrival — finalize DB state
        # Re-fetch all objects to ensure we have fresh references for the final update
        req = db.query(EmergencyRequest).filter(EmergencyRequest.id == request_id).first()
        assignment = db.query(Assignment).filter(
            Assignment.emergency_request_id == request_id,
            Assignment.ambulance_id == ambulance_id
        ).first()
        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        
        if req and assignment and ambulance:
            now = datetime.utcnow()
            
            # Update EmergencyRequest
            req.completed_at = now
            req.status = "completed"

            # Update Assignment status to completed
            assignment.status = "completed"
            
            # Update Ambulance status back to available
            ambulance.status = "available"
            
            db.commit()

            # Send final completion payload
            final_payload = {
                "ambulance_id": ambulance_id,
                "current_location": {"lat": route_nodes[-1].lat, "lng": route_nodes[-1].lon},
                "status": "completed",
                "completed_at": str(now),
                "eta_seconds": 0,
                "progress": 1.0
            }
            await manager.broadcast(final_payload, request_id)

    except Exception as e:
        print(f"Error in simulation: {e}")
    finally:
        db.close()
