"""
Properly migrate Health Plus Clinic from clinic_knowledge.json to PostgreSQL
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ, ClinicSession, SchedulingRule
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_health_plus_clinic():
    """Import Health Plus Clinic from JSON"""
    
    # Load JSON
    json_path = Path(__file__).parent.parent / "data" / "clinic_knowledge.json"
    logger.info(f"Loading {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    clinic_info = data['clinic_info']
    phone = "+919876543210"  # Standard phone number
    
    with Session(engine) as session:
        # Check if Health Plus Clinic exists
        stmt = select(Clinic).where(Clinic.name == clinic_info['name'])
        existing = session.exec(stmt).first()
        
        if existing:
            logger.info(f"Clinic '{clinic_info['name']}' already exists with ID {existing.id}")
            logger.info("Deleting old data to reimport...")
            
            # Delete old related data
            for p in session.exec(select(Provider).where(Provider.clinic_id == existing.id)).all():
                session.delete(p)
            for s in session.exec(select(Service).where(Service.clinic_id == existing.id)).all():
                session.delete(s)
            for f in session.exec(select(FAQ).where(FAQ.clinic_id == existing.id)).all():
                session.delete(f)
            session.commit()
            
            clinic = existing
        else:
            logger.info(f"Creating new clinic: {clinic_info['name']}")
            clinic = Clinic(
                id=uuid4(),
                name=clinic_info['name'],
                clinic_type="Multi-Specialty",
                specialties=json.dumps(["General Medicine", "Cardiology", "Pediatrics"]),
                phone_primary=phone,
                email=clinic_info['email'],
                address_line1="Health Plus Building, Jubilee Hills",
                address_line2="",
                city="Hyderabad",
                state="Telangana",
                postal_code="500033",
                timezone=clinic_info['timezone'],
                languages_spoken=json.dumps(clinic_info['languages_supported']),
                parking_info="Free parking available",
                accepts_walkins=True,
                twilio_phone=phone,
                whatsapp_enabled=True
            )
            session.add(clinic)
            session.commit()
            session.refresh(clinic)
        
        logger.info(f"Clinic ID: {clinic.id}")
        
        # Import Doctors -> Providers
        logger.info(f"\nImporting {len(data['doctors'])} doctors...")
        for doc in data['doctors']:
            # Parse availability
            working_days = []
            working_hours = {}
            
            for day, hours in doc['availability'].items():
                if hours != "closed":
                    working_days.append(day)
                    if isinstance(hours, list) and len(hours) > 0:
                        # Parse time ranges like "09:00-12:00"
                        morning = hours[0].split('-')
                        working_hours[day] = {
                            "start": morning[0],
                            "end": morning[1]
                        }
                        if len(hours) > 1:
                            evening = hours[1].split('-')
                            working_hours[day]["evening_start"] = evening[0]
                            working_hours[day]["evening_end"] = evening[1]
            
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
                working_days=json.dumps(working_days),
                working_hours=json.dumps(working_hours),
                default_appointment_duration=30,
                is_active=True
            )
            session.add(provider)
            logger.info(f"  ✓ {doc['name']} - {doc['specialization']}")
        
        # Import Services
        logger.info(f"\nImporting {len(data['services'])} services...")
        for idx, svc in enumerate(data['services'], 1):
            service = Service(
                id=uuid4(),
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
            logger.info(f"  ✓ {svc['name']} - {svc['duration_minutes']} min")
        
        # Import FAQs
        logger.info(f"\nImporting {len(data['faqs'])} FAQs...")
        for idx, faq_data in enumerate(data['faqs'], 1):
            # Extract keywords from question
            keywords = [word.lower() for word in faq_data['question'].split() if len(word) > 3]
            
            faq = FAQ(
                id=uuid4(),
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
            logger.info(f"  ✓ {faq_data['question'][:50]}...")
        
        # Add scheduling rules if not exist
        stmt = select(SchedulingRule).where(SchedulingRule.clinic_id == clinic.id)
        if not session.exec(stmt).first():
            logger.info("\nCreating scheduling rules...")
            rules = SchedulingRule(
                id=uuid4(),
                clinic_id=clinic.id,
                advance_booking_days=30,
                same_day_cutoff_hour=12,
                send_confirmation=True,
                confirmation_methods=json.dumps(["whatsapp"]),
                cancellation_hours=24,
                allow_reschedule=True
            )
            session.add(rules)
            logger.info("  ✓ Default scheduling rules")
        
        # Add clinic sessions if not exist
        stmt = select(ClinicSession).where(ClinicSession.clinic_id == clinic.id)
        if len(session.exec(stmt).all()) == 0:
            logger.info("\nCreating clinic sessions...")
            sessions = [
                ClinicSession(
                    id=uuid4(),
                    clinic_id=clinic.id,
                    name="MORNING",
                    start_time="08:00",
                    end_time="13:00",
                    max_tokens=25,
                    buffer_minutes=10,
                    days_of_week=json.dumps(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]),
                    is_active=True
                ),
                ClinicSession(
                    id=uuid4(),
                    clinic_id=clinic.id,
                    name="AFTERNOON",
                    start_time="14:00",
                    end_time="19:00",
                    max_tokens=20,
                    buffer_minutes=10,
                    days_of_week=json.dumps(["monday", "tuesday", "wednesday", "thursday", "friday"]),
                    is_active=True
                )
            ]
            for sess in sessions:
                session.add(sess)
            logger.info("  ✓ 2 clinic sessions (Morning, Afternoon)")
        
        # Commit everything
        session.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ SUCCESS! Health Plus Clinic imported")
        logger.info(f"{'='*60}")
        logger.info(f"Clinic ID: {clinic.id}")
        logger.info(f"Name: {clinic.name}")
        logger.info(f"Phone: {clinic.phone_primary}")
        logger.info(f"Providers: {len(data['doctors'])}")
        logger.info(f"Services: {len(data['services'])}")
        logger.info(f"FAQs: {len(data['faqs'])}")
        
        return clinic.id


if __name__ == "__main__":
    try:
        clinic_id = import_health_plus_clinic()
        print(f"\n✓ Migration complete! Clinic ID: {clinic_id}")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
