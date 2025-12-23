import asyncio
import json
from sqlmodel import SQLModel, create_engine, Session, select
from core.models_sql import Clinic, Doctor, KnowledgeBase

# Database Setup
DATABASE_URL = "sqlite:///./clinic.db" 
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def seed_data():
    with Session(engine) as session:
        # Check if clinic already exists
        existing_clinic = session.exec(select(Clinic)).first()
        if existing_clinic:
            print("Clinic already exists. Skipping seed.")
            return

        # 1. Create Clinic with Cal.com Config
        clinic = Clinic(
            name="HealthFlo Clinic",
            cal_com_api_key="cal_live_22d355f481409ed31cb37d890cc088ab",
            cal_com_event_type_id=1,  # 15 Min Meeting
            twilio_phone="+15550100", 
            # Store as JSON strings
            whatsapp_config=json.dumps({"provider": "mock"}), 
            ai_config=json.dumps({"model": "gpt-4o"})
        )
        session.add(clinic)
        session.commit()
        session.refresh(clinic)
        
        print(f"Created Clinic: {clinic.name} (ID: {clinic.id})")

        # 2. Create Doctors
        doc1 = Doctor(
            name="Dr. Aasrith",
            clinic_id=clinic.id,
            cal_com_user_id=1,
            is_active=True,
            specialization="General Physician"
        )
        session.add(doc1)
        
        # 3. Create Basic Knowledge Base
        kb1 = KnowledgeBase(
            clinic_id=clinic.id,
            category="timings", 
            content="We are open from 9 AM to 5 PM, Monday to Saturday." 
        )
        kb2 = KnowledgeBase(
            clinic_id=clinic.id,
            category="location", 
            content="We are located at 123 Health Street, Tech City." 
        )
        session.add(kb1)
        session.add(kb2)
        
        session.commit()
        print("Seeded Doctors and Knowledge Base.")

if __name__ == "__main__":
    create_db_and_tables()
    seed_data()
