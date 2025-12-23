"""
Minimal test - create clinic with absolute minimum fields
"""

import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from core.db_engine import engine
from core.models_sql import Clinic

try:
    with Session(engine) as session:
        print("Creating minimal clinic...")
        clinic = Clinic(
            # Absolutely required fields only
            name="Test Clinic",
            phone_primary="+919999999999",
            address_line1="Test Address",
            city="Test City",
            state="Test State",
            postal_code="123456",
            twilio_phone="+919999999999"
        )
        
        session.add(clinic)
        session.commit()
        session.refresh(clinic)
        
        print(f"✓ SUCCESS! Created clinic: {clinic.name} ({clinic.id})")
        
        # Clean up
        session.delete(clinic)
        session.commit()
        print("✓ Test clinic deleted")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
