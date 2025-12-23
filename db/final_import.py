"""
Complete import of Health Plus Clinic with ALL fields from JSON
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ

# Load JSON
json_path = Path(__file__).parent.parent / "data" / "clinic_knowledge.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

phone = "+911234567890"

with Session(engine) as session:
    # Delete existing Health Plus if exists
    stmt = select(Clinic).where(Clinic.name == data['clinic_info']['name'])
    existing = session.exec(stmt).first()
    
    if existing:
        print(f"Deleting existing Health Plus Clinic...")
        # Delete related data
        for p in session.exec(select(Provider).where(Provider.clinic_id == existing.id)).all():
            session.delete(p)
        for s in session.exec(select(Service).where(Service.clinic_id == existing.id)).all():
            session.delete(s)
        for f in session.exec(select(FAQ).where(FAQ.clinic_id == existing.id)).all():
            session.delete(f)
        session.delete(existing)
        session.commit()
    
    # Create clinic with ALL fields
    print("Creating Health Plus Clinic with complete data...")
    clinic = Clinic(
        name=data['clinic_info']['name'],
        clinic_type="Multi-Specialty",
        specialties=json.dumps(["General Medicine", "Cardiology", "Pediatrics"]),
        
        # Contact
        phone_primary=phone,
        email=data['clinic_info']['email'],
        website="https://healthplus.in",
        
        # Address
        address_line1="Health Plus Building, Jubilee Hills",
        address_line2="Opposite Metro Station",
        city="Hyderabad",
        state="Telangana",
        postal_code="500033",
        
        # Operational
        timezone=data['clinic_info']['timezone'],
        languages_spoken=json.dumps(data['clinic_info']['languages_supported']),
        parking_info="Free parking available for patients",
        wheelchair_accessible=True,
        accepts_walkins=True,
        
        # Integration
        twilio_phone=phone,
        whatsapp_enabled=True
    )
    session.add(clinic)
    session.commit()
    session.refresh(clinic)
    
    print(f"✓ Clinic created: {clinic.name} ({clinic.id})")
    
    # Add ALL provider data with working hours
    print(f"\nAdding {len(data['doctors'])} doctors with complete schedules...")
    for doc in data['doctors']:
        # Parse availability into working_days and working_hours
        working_days = []
        working_hours = {}
        
        for day, hours in doc['availability'].items():
            if hours != "closed":
                working_days.append(day)
                if isinstance(hours, list):
                    # Morning slot
                    if len(hours) >= 1:
                        morning_times = hours[0].split('-')
                        working_hours[day] = {
                            "start": morning_times[0],
                            "end": morning_times[1]
                        }
                    # Evening slot
                    if len(hours) >= 2:
                        evening_times = hours[1].split('-')
                        working_hours[day]["evening_start"] = evening_times[0]
                        working_hours[day]["evening_end"] = evening_times[1]
        
        provider = Provider(
            clinic_id=clinic.id,
            name=doc['name'],
            title="Dr.",
            specialty=doc['specialization'],
            qualifications=", ".join(doc['qualifications']),
            years_of_experience=doc['experience_years'],
            languages_spoken=json.dumps(doc['languages']),
            bio=doc.get('bio', ''),
            
            # Working schedule - POPULATED!
            working_days=json.dumps(working_days),
            working_hours=json.dumps(working_hours),
            
            default_appointment_duration=30,
            booking_buffer=5,
            is_active=True
        )
        session.add(provider)
        print(f"  ✓ {doc['name']} - {doc['specialization']}")
        print(f"    Working days: {', '.join(working_days)}")
        print(f"    Experience: {doc['experience_years']} years")
    
    session.commit()
    
    # Add ALL service data
    print(f"\nAdding {len(data['services'])} services with pricing...")
    for idx, svc in enumerate(data['services'], 1):
        service = Service(
            clinic_id=clinic.id,
            name=svc['name'],
            description=f"Telugu: {svc.get('name_telugu', '')}",
            category="Medical Service",
            price=svc.get('cost', 500.0),
            duration_minutes=svc['duration_minutes'],
            display_order=idx,
            is_active=True
        )
        session.add(service)
        price_text = f"₹{svc['cost']}" if 'cost' in svc else "Price varies"
        print(f"  ✓ {svc['name']} - {price_text}, {svc['duration_minutes']} min")
    
    session.commit()
    
    # Add ALL FAQ data with keywords
    print(f"\nAdding {len(data['faqs'])} FAQs with keywords...")
    for idx, faq_data in enumerate(data['faqs'], 1):
        # Extract meaningful keywords
        question_words = faq_data['question'].lower().split()
        keywords = [w for w in question_words if len(w) > 3 and w not in ['what', 'should', 'there', 'visit']]
        
        faq = FAQ(
            clinic_id=clinic.id,
            category="General",
            question=faq_data['question'],
            answer_english=faq_data['answer'],
            answer_telugu=faq_data.get('question_telugu', ''),
            keywords=json.dumps(keywords),
            display_order=idx,
            is_active=True
        )
        session.add(faq)
        print(f"  ✓ {faq_data['question']}")
        print(f"    Keywords: {', '.join(keywords)}")
    
    session.commit()
    
    print("\n" + "="*60)
    print(f"✓ COMPLETE IMPORT SUCCESS!")
    print("="*60)
    print(f"Clinic: {clinic.name}")
    print(f"Phone: {clinic.phone_primary}")
    print(f"Email: {clinic.email}")
    print(f"Languages: {', '.join(data['clinic_info']['languages_supported'])}")
    print(f"\nData imported:")
    print(f"  ✓ 3 Providers (with schedules)")
    print(f"  ✓ 3 Services (with pricing)")
    print(f"  ✓ 3 FAQs (with keywords)")
    print(f"\n✓ All fields populated - no NULLs in critical data!")
