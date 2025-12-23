import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Provider, Doctor

def seed_doctors():
    with Session(engine) as session:
        providers = session.exec(select(Provider)).all()
        print(f"Found {len(providers)} providers.")
        
        count = 0
        for p in providers:
            # Check if doctor exists by ID
            doc = session.get(Doctor, p.id) 
            if not doc:
                # Check by name
                existing_name = session.exec(select(Doctor).where(Doctor.name == p.name)).first()
                if existing_name:
                    print(f"Doctor {p.name} already exists (ID: {existing_name.id}). Skipping.")
                    continue

                print(f"Creating Doctor for {p.name}")
                new_doc = Doctor(
                    id=p.id,
                    clinic_id=p.clinic_id,
                    name=p.name,
                    specialization=p.specialty,
                    is_active=True
                )
                session.add(new_doc)
                count += 1
            else:
                print(f"Doctor {p.name} already exists (ID match).")
        
        session.commit()
        print(f"Added {count} doctors.")

if __name__ == "__main__":
    seed_doctors()
