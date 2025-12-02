from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.routing.socket_manager import manager
from app.core.routing.simulation import simulate_ambulance_movement
from app.db.database import SessionLocal
from app.db.models import EmergencyRequest, Assignment, Node, Ambulance
import asyncio

router = APIRouter()


@router.websocket("/ws/tracking/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: int):
    await manager.connect(websocket, request_id)
    try:
        # Check if simulation needs to start (only if not already running)
        # This prevents duplicate simulations when multiple clients connect
        should_start_simulation = manager.start_simulation(request_id)
        
        if should_start_simulation:
            # We need a new DB session for this check
            db = SessionLocal()
            try:
                req = db.query(EmergencyRequest).filter(EmergencyRequest.id == request_id).first()
                assignment = db.query(Assignment).filter(
                    Assignment.emergency_request_id == request_id,
                    Assignment.status.in_(["assigned", "in-transit"])
                ).first()
                
                if req and assignment and req.status != "completed":
                    # Get the ambulance and hospital info
                    ambulance = db.query(Ambulance).filter(Ambulance.id == assignment.ambulance_id).first()
                    hospital_node = db.query(Node).filter(Node.id == req.destination_node).first()
                    
                    if ambulance and ambulance.current_node and hospital_node:
                        # Get current node object
                        current_node = db.query(Node).filter(Node.id == ambulance.current_node).first()
                        
                        # Calculate shortest path using Dijkstra
                        from app.core.graph.graph_manager import build_graph_for_city
                        from app.core.graph.shortest_path import shortest_path_and_distance
                        from app.core.routing.traffic_manager import apply_dynamic_traffic
                        
                        graph = build_graph_for_city(db, hospital_node.city_id)
                        apply_dynamic_traffic(graph, db, hospital_node.city_id)
                        
                        distance, path_node_ids = shortest_path_and_distance(graph, current_node.id, hospital_node.id)
                        
                        if path_node_ids:
                            route_nodes = db.query(Node).filter(Node.id.in_(path_node_ids)).all()
                            # Sort them to match path order
                            node_map = {n.id: n for n in route_nodes}
                            ordered_nodes = [node_map[nid] for nid in path_node_ids if nid in node_map]
                            
                            # Start simulation in background
                            # Use the calculated distance (minutes) as total ETA
                            asyncio.create_task(
                                simulate_ambulance_movement(
                                    request_id, 
                                    ordered_nodes, 
                                    total_eta_minutes=distance or 10.0
                                )
                            )
                        else:
                            # No path found, end simulation tracking
                            manager.end_simulation(request_id)
                    else:
                        manager.end_simulation(request_id)
                else:
                    # Request already completed or no assignment
                    manager.end_simulation(request_id)
                        
            finally:
                db.close()

        while True:
            # Keep connection alive and listen for any client messages (optional)
            data = await websocket.receive_text()
            # We could handle "ping" or other commands here
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, request_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, request_id)
