"""
Simple direct import of Health Plus Clinic - no fancy stuff
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ

# Load JSON
json_path = Path(__file__).parent.parent / "data" / "clinic_knowledge.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

phone = "+919876543210"

with Session(engine) as session:
    # Create clinic
    print("Creating Health Plus Clinic...")
    clinic = Clinic(
        id=uuid4(),
        name=data['clinic_info']['name'],
        clinic_type="Multi-Specialty",
        phone_primary=phone,
        email=data['clinic_info']['email'],
        # Required address fields
        address_line1="Health Plus Building, Jubilee Hills",
        city="Hyderabad",
        state="Telangana",
        postal_code="500033",
        # Required operational fields
        timezone="Asia/Kolkata",
        languages_spoken=json.dumps(["English", "Telugu", "Hindi"]),
        twilio_phone=phone,
        whatsapp_enabled=True
    )
    session.add(clinic)
    session.commit()
    session.refresh(clinic)
    
    print(f"✓ Clinic created: {clinic.name} ({clinic.id})")
    
    # Add providers
    print(f"\nAdding {len(data['doctors'])} doctors...")
    for doc in data['doctors']:
        provider = Provider(
            id=uuid4(),
            clinic_id=clinic.id,
            name=doc['name'],
            title="Dr.",
            specialty=doc['specialization'],
            qualifications=", ".join(doc['qualifications']),
            years_of_experience=doc['experience_years'],
            languages_spoken=json.dumps(doc['languages']),
            bio=doc.get('bio', ''),
            default_appointment_duration=30,
            is_active=True
        )
        session.add(provider)
        print(f"  ✓ {doc['name']}")
    
    session.commit()
    
    # Add services
    print(f"\nAdding {len(data['services'])} services...")
    for svc in data['services']:
        service = Service(
            id=uuid4(),
            clinic_id=clinic.id,
            name=svc['name'],
            description=f"Telugu: {svc.get('name_telugu', '')}",
            category="Medical",
            price=svc.get('cost', 500.0),
            duration_minutes=svc['duration_minutes'],
            is_active=True
        )
        session.add(service)
        print(f"  ✓ {svc['name']}")
    
    session.commit()
    
    # Add FAQs
    print(f"\nAdding {len(data['faqs'])} FAQs...")
    for faq_data in data['faqs']:
        faq = FAQ(
            id=uuid4(),
            clinic_id=clinic.id,
            category="General",
            question=faq_data['question'],
            answer_english=faq_data['answer'],
            answer_telugu=faq_data.get('question_telugu', ''),
            keywords=json.dumps(['parking', 'timing', 'reschedule']),
            is_active=True
        )
        session.add(faq)
        print(f"  ✓ {faq_data['question'][:40]}...")
    
    session.commit()
    
    print("\n" + "="*60)
    print(f"✓ SUCCESS! Imported Health Plus Clinic")
    print("="*60)
    print(f"Clinic: {clinic.name}")
    print(f"ID: {clinic.id}")
    print(f"Phone: {clinic.phone_primary}")
    print(f"Doctors: {len(data['doctors'])}")
    print(f"Services: {len(data['services'])}")
    print(f"FAQs: {len(data['faqs'])}")
