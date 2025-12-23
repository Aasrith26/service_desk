import sys
import os
sys.path.append(os.getcwd())

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, ClinicSession, Doctor

def check_db():
    with Session(engine) as session:
        print("\n--- CLINICS ---")
        clinics = session.exec(select(Clinic)).all()
        for c in clinics:
            print(f"ID: {c.id} | Name: {c.name} | Phone: {c.twilio_phone}")
            
        print("\n--- DOCTORS ---")
        doctors = session.exec(select(Doctor)).all()
        for d in doctors:
            print(f"ID: {d.id} | Name: {d.name} | Spec: {d.specialization}")

        print("\n--- SESSIONS ---")
        sessions = session.exec(select(ClinicSession)).all()
        for s in sessions:
            print(f"ID: {s.id} | Name: {s.name} | Time: {s.start_time}-{s.end_time} | Active: {s.is_active}")

if __name__ == "__main__":
    check_db()
