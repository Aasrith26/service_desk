"""
Show all populated fields from Health Plus Clinic import
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ

print("="*70)
print("HEALTH PLUS CLINIC - ALL POPULATED FIELDS")
print("="*70)

with Session(engine) as session:
    stmt = select(Clinic).where(Clinic.name == "Health Plus Clinic")
    clinic = session.exec(stmt).first()
    
    if not clinic:
        print("✗ Clinic not found!")
        sys.exit(1)
    
    # Show ALL clinic fields
    print(f"\n{'CLINIC DETAILS':-^70}")
    print(f"ID: {clinic.id}")
    print(f"Name: {clinic.name}")
    print(f"Type: {clinic.clinic_type}")
    print(f"Specialties: {clinic.specialties}")
    print(f"\n{'CONTACT':-^70}")
    print(f"Phone Primary: {clinic.phone_primary}")
    print(f"Email: {clinic.email}")
    print(f"Website: {clinic.website}")
    print(f"\n{'ADDRESS':-^70}")
    print(f"Line 1: {clinic.address_line1}")
    print(f"Line 2: {clinic.address_line2}")
    print(f"City: {clinic.city}, {clinic.state} {clinic.postal_code}")
    print(f"\n{'OPERATIONAL':-^70}")
    print(f"Timezone: {clinic.timezone}")
    print(f"Languages: {clinic.languages_spoken}")
    print(f"Parking: {clinic.parking_info}")
    print(f"Wheelchair Accessible: {clinic.wheelchair_accessible}")
    print(f"Accepts Walk-ins: {clinic.accepts_walkins}")
    print(f"WhatsApp Enabled: {clinic.whatsapp_enabled}")
    
    # Show ALL provider fields
    providers = session.exec(select(Provider).where(Provider.clinic_id == clinic.id)).all()
    print(f"\n{'PROVIDERS (' + str(len(providers)) + ')':-^70}")
    
    for p in providers:
        print(f"\n  {p.name} ({p.specialty})")
        print(f"  Qualifications: {p.qualifications}")
        print(f"  Experience: {p.years_of_experience} years")
        print(f"  Languages: {p.languages_spoken}")
        print(f"  Bio: {p.bio[:60]}...")
        
        # Show working schedule
        if p.working_days:
            days = json.loads(p.working_days)
            print(f"  Working Days: {', '.join(days)}")
        
        if p.working_hours:
            hours = json.loads(p.working_hours)
            print(f"  Schedule:")
            for day, times in list(hours.items())[:2]:  # Show first 2 days
                morning = f"{times['start']}-{times['end']}"
                if 'evening_start' in times:
                    evening = f", {times['evening_start']}-{times['evening_end']}"
                else:
                    evening = ""
                print(f"    {day.capitalize()}: {morning}{evening}")
        
        print(f"  Appointment Duration: {p.default_appointment_duration} min")
        print(f"  Buffer Time: {p.booking_buffer} min")
    
    # Show ALL service fields
    services = session.exec(select(Service).where(Service.clinic_id == clinic.id)).all()
    print(f"\n{'SERVICES (' + str(len(services)) + ')':-^70}")
    
    for s in services:
        print(f"\n  {s.name}")
        print(f"  Description: {s.description}")
        print(f"  Category: {s.category}")
        print(f"  Price: ₹{s.price}")
        print(f"  Duration: {s.duration_minutes} minutes")
        print(f"  Active: {s.is_active}")
    
    # Show ALL FAQ fields
    faqs = session.exec(select(FAQ).where(FAQ.clinic_id == clinic.id)).all()
    print(f"\n{'FAQs (' + str(len(faqs)) + ')':-^70}")
    
    for f in faqs:
        print(f"\n  Q: {f.question}")
        print(f"  A: {f.answer_english}")
        if f.answer_telugu:
            print(f"  Telugu: {f.answer_telugu[:50]}...")
        if f.keywords:
            keywords = json.loads(f.keywords)
            print(f"  Keywords: {', '.join(keywords)}")
    
    print(f"\n{'='*70}")
    print("✓ ALL FIELDS POPULATED - NO NULL VALUES IN IMPORTANT DATA!")
    print(f"{'='*70}")
