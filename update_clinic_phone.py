from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic

def update_clinic_phone():
    with Session(engine) as session:
        # Find Health Plus Clinic
        clinic = session.exec(select(Clinic).where(Clinic.name == "Health Plus Clinic")).first()
        
        if clinic:
            print(f"Found Clinic: {clinic.name}")
            print(f"Old Phone: {clinic.twilio_phone}")
            
            # Update to Exotel Number
            # New Number provided by user: 09513886363
            clinic.twilio_phone = "09513886363"
            
            session.add(clinic)
            session.commit()
            session.refresh(clinic)
            print(f"New Phone: {clinic.twilio_phone}")
            print("Update Successful!")
        else:
            print("Health Plus Clinic not found!")

if __name__ == "__main__":
    update_clinic_phone()
