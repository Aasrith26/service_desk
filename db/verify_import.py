"""
Verify Health Plus Clinic import and test cached retrieval
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ
from core.services.cached_clinic_service import get_cached_clinic_knowledge

print("="*60)
print("VERIFYING HEALTH PLUS CLINIC IMPORT")
print("="*60)

# 1. Verify data in database
with Session(engine) as session:
    stmt = select(Clinic).where(Clinic.name == "Health Plus Clinic")
    clinic = session.exec(stmt).first()
    
    if not clinic:
        print("✗ Health Plus Clinic not found in database!")
        sys.exit(1)
    
    print(f"\n✓ Found clinic: {clinic.name}")
    print(f"  ID: {clinic.id}")
    print(f"  Phone: {clinic.phone_primary}")
    print(f"  Email: {clinic.email}")
    print(f"  Address: {clinic.address_line1}, {clinic.city}")
    
    # Count related data
    providers = session.exec(select(Provider).where(Provider.clinic_id == clinic.id)).all()
    services = session.exec(select(Service).where(Service.clinic_id == clinic.id)).all()
    faqs = session.exec(select(FAQ).where(FAQ.clinic_id == clinic.id)).all()
    
    print(f"\n✓ Related data:")
    print(f"  Providers: {len(providers)}")
    for p in providers:
        print(f"    - {p.name} ({p.specialty})")
    
    print(f"  Services: {len(services)}")
    for s in services:
        print(f"    - {s.name} (₹{s.price}, {s.duration_minutes} min)")
    
    print(f"  FAQs: {len(faqs)}")
    for f in faqs:
        print(f"    - {f.question[:50]}...")

# 2. Test cached retrieval
print("\n" + "="*60)
print("TESTING CACHED RETRIEVAL")
print("="*60)

knowledge = get_cached_clinic_knowledge(clinic.phone_primary)

if knowledge:
    print(f"\n✓ Cached retrieval working!")
    print(f"  Clinic: {knowledge['clinic'].name}")
    print(f"  Providers: {len(knowledge['providers'])}")
    print(f"  Services: {len(knowledge['services'])}")
    print(f"  FAQs: {len(knowledge['faqs'])}")
    
    # Test second call (should be from cache)
    import time
    start = time.time()
    knowledge2 = get_cached_clinic_knowledge(clinic.phone_primary)
    elapsed = (time.time() - start) * 1000
    
    print(f"\n✓ Second call (cached): {elapsed:.2f}ms")
else:
    print("\n✗ Cached retrieval failed!")
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL TESTS PASSED!")
print("="*60)
print(f"\nHealth Plus Clinic is now in PostgreSQL and cached!")
print(f"Use this phone to retrieve: {clinic.phone_primary}")
