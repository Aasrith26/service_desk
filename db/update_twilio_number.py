"""
Update Health Plus Clinic with Twilio number
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic

twilio_number = "+16203509655"

with Session(engine) as session:
    stmt = select(Clinic).where(Clinic.name == "Health Plus Clinic")
    clinic = session.exec(stmt).first()
    
    if not clinic:
        print("✗ Health Plus Clinic not found!")
        sys.exit(1)
    
    print(f"Updating Health Plus Clinic...")
    print(f"  Old Twilio: {clinic.twilio_phone}")
    print(f"  New Twilio: {twilio_number}")
    
    # Update both phone fields
    clinic.twilio_phone = twilio_number
    clinic.phone_primary = twilio_number
    
    session.add(clinic)
    session.commit()
    session.refresh(clinic)
    
    print(f"\n✓ SUCCESS!")
    print(f"Clinic: {clinic.name}")
    print(f"Twilio Phone: {clinic.twilio_phone}")
    print(f"\nWhen calls come to {twilio_number}, Health Plus Clinic data will be loaded!")
