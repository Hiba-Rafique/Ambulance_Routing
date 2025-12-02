# test_ambulance_assignment.py
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.core.routing.ambulance_assignment import (
    select_best_ambulance_for_request,
    create_assignment_for_request
)

def main():
    # Step 1: create a database session
    db: Session = SessionLocal()

    try:
        # Step 2: specify the emergency request ID
        request_id = 1  # change if you want to test another request

        # Step 3: run the ambulance selection logic
        assignment_plan = select_best_ambulance_for_request(db, request_id)

        # Step 4: print the best ambulance
        if assignment_plan.best_ambulance:
            print(f"Best ambulance: {assignment_plan.best_ambulance.name}")
            print(f"ETA to hospital: {assignment_plan.best_eta} minutes")
        else:
            print("No reachable ambulance found.")

        # Step 5: print all candidate ambulances
        print("\nAll candidate ambulances and their ETAs:")
        for candidate in assignment_plan.candidates:
            print(f"{candidate.ambulance.name} -> ETA: {candidate.eta_to_hospital} minutes")

        # Step 6: actually create the assignment in the database
        assignment = create_assignment_for_request(db, request_id)
        if assignment:
            print(f"\n✅ Assignment created successfully! Assignment ID: {assignment.id}")
            print(f"Ambulance {assignment.ambulance.name} assigned to request {assignment.emergency_request_id} with ETA {assignment.eta} minutes")
        else:
            print("\n⚠️ Assignment could not be created (no available ambulance).")

    finally:
        # Step 7: close the DB session
        db.close()

if __name__ == "__main__":
    main()
