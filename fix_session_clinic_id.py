from sqlmodel import Session, select
from core.database import engine
from core.models_sql import ClinicSession
from uuid import UUID

# The ID seen in the logs for "Health Plus Clinic"
TARGET_CLINIC_ID = UUID("5ed9bf9a-9506-4081-95c2-2ac39e4e1516")

with Session(engine) as session:
    sessions = session.exec(select(ClinicSession)).all()
    count = 0
    for s in sessions:
        print(f"Updating session '{s.name}' from {s.clinic_id} to {TARGET_CLINIC_ID}")
        s.clinic_id = TARGET_CLINIC_ID
        session.add(s)
        count += 1
    
    session.commit()
    print(f"Updated {count} sessions successfully.")
