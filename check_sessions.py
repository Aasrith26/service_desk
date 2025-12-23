from sqlmodel import Session, select
from core.database import engine
from core.models_sql import ClinicSession

with Session(engine) as session:
    sessions = session.exec(select(ClinicSession)).all()
    print(f"Total Sessions in DB: {len(sessions)}")
    for s in sessions:
        print(f" - {s.name}: {s.start_time} to {s.end_time} (Active: {s.is_active}) [ClinicID: {s.clinic_id}]")
