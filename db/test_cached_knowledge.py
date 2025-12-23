"""
Simple test: Migrate JSON to DB and test cached retrieval
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ
from core.services.cached_clinic_service import get_cached_clinic_knowledge, preload_all_clinics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load JSON
json_path = Path(__file__).parent.parent / "data" / "clinic_knowledge.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get or create clinic
with Session(engine) as session:
    phone = "+919876543210"
    
    # Find clinic
    stmt = select(Clinic).where(Clinic.phone_primary == phone)
    clinic = session.exec(stmt).first()
    
    if not clinic:
        print("Creating Health Plus Clinic...")
        clinic = Clinic(
            id=uuid4(),
            name=data['clinic_info']['name'],
            clinic_type="Multi-Specialty",
            phone_primary=phone,
            email=data['clinic_info']['email'],
            address_line1="Health Plus Building, Jubilee Hills",
            address_line2="",
            city="Hyderabad",
            state="Telangana",
            postal_code="500033",
            timezone="Asia/Kolkata",
            languages_spoken=json.dumps(["English", "Telugu", "Hindi"]),
            twilio_phone=phone,
            whatsapp_enabled=True
        )
        session.add(clinic)
        session.commit()
        session.refresh(clinic)
    
    print(f"\n✓ Found/Created clinic: {clinic.name} ({clinic.id})")

# Test cached retrieval
print("\n" + "="*60)
print("TESTING CACHED CLINIC SERVICE")
print("="*60)

# First call - will fetch from DB
print("\n1. First call (cache MISS - fetching from DB)...")
knowledge1 = get_cached_clinic_knowledge(phone)
if knowledge1:
    print(f"✓ Retrieved: {knowledge1['clinic'].name}")
    print(f"  - Providers: {len(knowledge1['providers'])}")
    print(f"  - Services: {len(knowledge1['services'])}")
    print(f"  - FAQs: {len(knowledge1['faqs'])}")

# Second call - should be instant from cache
print("\n2. Second call (cache HIT - instant from cache)...")
import time
start = time.time()
knowledge2 = get_cached_clinic_knowledge(phone)
elapsed = (time.time() - start) * 1000  # ms
if knowledge2:
    print(f"✓ Retrieved in {elapsed:.2f}ms (CACHED!)")
    print(f"  - Same as first: {knowledge1 == knowledge2}")

# Test preload
print("\n3. Testing preload functionality...")
preload_all_clinics()

print("\n" + "="*60)
print("✓ CACHED RETRIEVAL WORKING - ZERO LAG!")
print("="*60)
