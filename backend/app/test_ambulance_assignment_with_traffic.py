# test_ambulance_assignment_with_traffic.py

from sqlalchemy.orm import Session
from db.database import SessionLocal
from core.routing.ambulance_assignment import select_best_ambulance_for_request, create_assignment_for_request
from pprint import pprint

def main():
    db: Session = SessionLocal()
    
    try:
        # Choose an existing emergency request ID
        request_id = 1  # adjust as needed for your DB

        # Step 1: Run ambulance selection WITH traffic applied
        assignment_plan = select_best_ambulance_for_request(db, request_id)

        if assignment_plan.best_ambulance:
            print(f"Best ambulance: {assignment_plan.best_ambulance.name}")
            print(f"ETA to hospital: {assignment_plan.best_eta:.2f} minutes")
        else:
            print("No reachable ambulance found.")

        print("\nAll candidate ambulances with ETA:")
        for candidate in assignment_plan.candidates:
            print(f"{candidate.ambulance.name} -> ETA: {candidate.eta_to_hospital:.2f} minutes")

        # Step 2: Create the assignment row
        assignment = create_assignment_for_request(db, request_id)
        if assignment:
            print(f"\n✅ Assignment created successfully! ID: {assignment.id}")
            print(f"Ambulance: {assignment.ambulance.name}, Status: {assignment.status}, ETA: {assignment.eta}")
        else:
            print("\n❌ No assignment could be created (no available ambulances)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
