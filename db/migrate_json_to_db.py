"""
Migrate clinic_knowledge.json to PostgreSQL database
Imports existing clinic data into comprehensive schema
"""

import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import Clinic, Provider, Service, FAQ, ClinicSession, SchedulingRule

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate_json_to_db():
    """Migrate clinic_knowledge.json to database"""
    
    # Load JSON file
    json_path = Path(__file__).parent.parent / "data" / "clinic_knowledge.json"
    logger.info(f"Loading {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with Session(engine) as session:
        # Check if clinic already exists
        clinic_info = data['clinic_info']
        phone = "+919876543210"  # Use standard format
        
        stmt = select(Clinic).where(Clinic.name == clinic_info['name'])
        existing = session.exec(stmt).first()
        
        if existing:
            logger.info(f"Clinic '{existing.name}' already exists, updating...")
            clinic = existing
        else:
            logger.info(f"Creating new clinic: {clinic_info['name']}...")
            
            # Create Clinic
            clinic = Clinic(
                id=uuid4(),
                name=clinic_info['name'],
                clinic_type="Multi-Specialty",
                specialties=json.dumps(["General Medicine", "Cardiology", "Pediatrics"]),
                
                # Contact
                phone_primary=phone,
                email=clinic_info['email'],
                
                # Address (from location)
                address_line1="Health Plus Building",
                address_line2="Jubilee Hills",
                city="Hyderabad",
                state="Telangana",
                postal_code="500033",
                
                # Operational
                timezone=clinic_info['timezone'],
                languages_spoken=json.dumps(clinic_info['languages_supported']),
                accepts_walkins=True,
                
                # Integration
                twilio_phone=phone,
                whatsapp_enabled=True
            )
            session.add(clinic)
            session.flush()  # Get clinic ID
        
        # Clear existing providers, services, FAQs for this clinic
        logger.info("Clearing old data...")
        for provider in session.exec(select(Provider).where(Provider.clinic_id == clinic.id)).all():
            session.delete(provider)
        for service in session.exec(select(Service).where(Service.clinic_id == clinic.id)).all():
            session.delete(service)
        for faq in session.exec(select(FAQ).where(FAQ.clinic_id == clinic.id)).all():
            session.delete(faq)
        
        # Migrate Doctors -> Providers
        logger.info(f"Migrating {len(data['doctors'])} doctors...")
        for doc in data['doctors']:
            # Convert availability to working_days and working_hours
            working_days = [day for day, hours in doc['availability'].items() 
                          if hours != "closed"]
            
            working_hours = {}
            for day, hours in doc['availability'].items():
                if hours != "closed" and isinstance(hours, list):
                    if len(hours) >= 1:
                        times = hours[0].split('-')
                        working_hours[day] = {"start": times[0], "end": times[1]}
                        if len(hours) > 1:
                            evening_times = hours[1].split('-')
                            working_hours[day]["evening_start"] = evening_times[0]
                            working_hours[day]["evening_end"] = evening_times[1]
            
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
                default_appointment_duration=30,  # From services
                is_active=True
            )
            session.add(provider)
        
        # Migrate Services
        logger.info(f"Migrating {len(data['services'])} services...")
        for idx, svc in enumerate(data['services'], 1):
            service = Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name=svc['name'],
                description=f"Telugu: {svc.get('name_telugu', '')}",
                category="Consultation",
                price=svc.get('cost', 500.0),  # Default if not specified
                duration_minutes=svc['duration_minutes'],
                display_order=idx,
                is_active=True
            )
            session.add(service)
        
        # Migrate FAQs
        logger.info(f"Migrating {len(data['faqs'])} FAQs...")
        for idx, faq_data in enumerate(data['faqs'], 1):
            faq = FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="General",
                question=faq_data['question'],
                answer_english=faq_data['answer'],
                answer_telugu=faq_data.get('question_telugu', ''),  # Store Telugu question
                keywords=json.dumps([
                    word.lower() for word in faq_data['question'].split() 
                    if len(word) > 3
                ]),
                display_order=idx,
                is_active=True
            )
            session.add(faq)
        
        # Add default scheduling rules if not exists
        stmt = select(SchedulingRule).where(SchedulingRule.clinic_id == clinic.id)
        existing_rules = session.exec(stmt).first()
        
        if not existing_rules:
            logger.info("Creating default scheduling rules...")
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
        
        # Add clinic sessions for token system
        stmt = select(ClinicSession).where(ClinicSession.clinic_id == clinic.id)
        existing_sessions = len(session.exec(stmt).all())
        
        if existing_sessions == 0:
            logger.info("Creating clinic sessions...")
            sessions_data = [
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
            for sess in sessions_data:
                session.add(sess)
        
        # Commit all changes
        logger.info("Committing to database...")
        session.commit()
        
        logger.info(f"\n✓ Migration complete for '{clinic.name}'!")
        logger.info(f"  - Clinic ID: {clinic.id}")
        logger.info(f"  - Phone: {clinic.phone_primary}")
        
        return clinic.id


if __name__ == "__main__":
    try:
        clinic_id = migrate_json_to_db()
        logger.info(f"\n✓ JSON data successfully migrated to PostgreSQL!")
        logger.info(f"  Clinic ID: {clinic_id}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
