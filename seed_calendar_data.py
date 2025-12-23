import random
from datetime import datetime, timedelta
from sqlmodel import Session, select
from core.db_engine import engine
from core.models import Appointment, Doctor, Clinic
import uuid

def seed_data():
    with Session(engine) as session:
        # Get Clinic and Doctors
        clinics = session.exec(select(Clinic)).all()
        if not clinics:
            print("No clinics found. Please seed clinics first.")
            return
        clinic = clinics[0]
        
        doctors = session.exec(select(Doctor).where(Doctor.clinic_id == clinic.id)).all()
        if not doctors:
            print("No doctors found. Creating dummy doctors...")
            doc_names = ["Smith", "Patel", "Garcia", "Lee"]
            doctors = []
            for name in doc_names:
                doc = Doctor(id=str(uuid.uuid4()), name=name, specialization="General", clinic_id=clinic.id, phone=f"+1555000{random.randint(1000,9999)}")
                session.add(doc)
                doctors.append(doc)
            session.commit()
            for d in doctors: session.refresh(d)

        print(f"Seeding data for clinic: {clinic.name}")
        
        # Generate appointments for Dec 2025
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2025, 12, 31)
        
        current = start_date
        while current <= end_date:
            # Random number of appointments per day (0 to 10)
            num_appts = random.randint(0, 10)
            
            # Make weekends busier?
            if current.weekday() >= 5: # Sat/Sun
                num_appts = random.randint(5, 15)
                
            for _ in range(num_appts):
                doc = random.choice(doctors)
                hour = random.randint(9, 17)
                minute = random.choice([0, 15, 30, 45])
                time_str = f"{hour:02d}:{minute:02d}"
                
                status = random.choice(['confirmed', 'completed', 'cancelled', 'scheduled'])
                type_ = random.choice(['Walk-in', 'Consultation'])
                
                appt = Appointment(
                    id=str(uuid.uuid4()),
                    clinic_id=clinic.id,
                    doctor_id=doc.id,
                    patient_name=f"Patient {random.randint(100, 999)}",
                    patient_phone=f"+1555{random.randint(100000, 999999)}",
                    date=current.strftime("%Y-%m-%d"),
                    time=time_str,
                    duration=15,
                    status=status,
                    type=type_,
                    token_number=random.randint(1, 50),
                    booking_source="DASHBOARD" if type_ == 'Walk-in' else "VOICE"
                )
                session.add(appt)
            
            current += timedelta(days=1)
        
        session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    seed_data()
