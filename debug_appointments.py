from sqlmodel import Session, select
from core.db_engine import engine
from core.models import Appointment

def list_appointments():
    with Session(engine) as session:
        appointments = session.exec(select(Appointment)).all()
        print(f"Total Appointments: {len(appointments)}")
        for appt in appointments:
            print(f"ID: {appt.id}, Date: {appt.date}, Status: {appt.status}, Clinic: {appt.clinic_id}")

if __name__ == "__main__":
    list_appointments()
