# test_completion.py
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import EmergencyRequest, Assignment, Ambulance, Node
from app.routers.ambulance import complete_emergency_request
from datetime import datetime

def main():
    db: Session = SessionLocal()
    try:
        print("--- Setting up test data ---")
        # 1. Ensure we have a city and nodes (assuming existing data or creating minimal)
        # For simplicity, let's pick an existing ambulance and request if possible, or create new ones.
        
        # Check for an ambulance
        ambulance = db.query(Ambulance).first()
        if not ambulance:
            print("No ambulance found. Creating one.")
            ambulance = Ambulance(name="Test Ambulance", status="available", speed=60.0)
            db.add(ambulance)
            db.commit()
            db.refresh(ambulance)
        
        # Ensure ambulance is available
        ambulance.status = "available"
        db.commit()
        print(f"Using Ambulance: {ambulance.name} (ID: {ambulance.id})")

        # Create a dummy emergency request
        req = EmergencyRequest(
            caller_name="Test Caller",
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        print(f"Created Emergency Request ID: {req.id}")

        # Create an assignment
        assignment = Assignment(
            ambulance_id=ambulance.id,
            emergency_request_id=req.id,
            eta=10.0,
            status="assigned"
        )
        db.add(assignment)
        
        # Update ambulance status to assigned
        ambulance.status = "assigned"
        
        db.commit()
        db.refresh(assignment)
        print(f"Created Assignment ID: {assignment.id} with status '{assignment.status}'")
        print(f"Ambulance status set to '{ambulance.status}'")

        print("\n--- Testing Completion Logic ---")
        # Call the completion function directly
        response = complete_emergency_request(ambulance_id=ambulance.id, db=db)
        print("Response:", response)

        print("\n--- Verifying Results ---")
        # Refresh objects
        db.refresh(req)
        db.refresh(ambulance)
        db.refresh(assignment)

        print(f"Request Status: {req.status}")
        print(f"Request Completed At: {req.completed_at}")
        print(f"Ambulance Status: {ambulance.status}")
        print(f"Assignment Status: {assignment.status}")

        if (req.status == "completed" and 
            req.completed_at is not None and 
            ambulance.status == "available" and 
            assignment.status == "completed"):
            print("\n[SUCCESS] Completion logic verified!")
        else:
            print("\n[FAILURE] Logic verification failed.")

    except Exception as e:
        print(f"\n[ERROR] Error during test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
