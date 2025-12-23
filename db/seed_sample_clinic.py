"""
Seed sample clinic data for testing
Creates a complete clinic with providers, services, FAQs, etc.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime, date
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db_engine import engine
from core.models_sql import (
    Clinic, Provider, Service, VisitType, FAQ, 
    SchedulingRule, Holiday, ClinicSession, Doctor
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_sample_clinic():
    """Create a complete sample clinic"""
    
    with Session(engine) as session:
        # Check if clinic already exists
        existing = session.query(Clinic).filter(
            Clinic.phone_primary == "+919876543210"
        ).first()
        
        if existing:
            logger.info(f"Clinic '{existing.name}' already exists.")
            clinic = existing
            # Check if providers exist
            providers = session.exec(select(Provider).where(Provider.clinic_id == clinic.id)).all()
            if not providers:
                logger.info("Clone exists but PROVIDERS MISSING. Adding providers...")
                # Continue execution to add providers...
            else:
                logger.info("Providers already exist. Skipping seed.")
                return existing.id
        else:
            logger.info("Creating sample clinic...")
            # 1. Create Clinic
            clinic = Clinic(
                id=uuid4(),
                name="Sri Lakshmi Clinic",
                clinic_type="General Practice",
                specialties=json.dumps(["General Medicine", "Pediatrics", "ENT"]),
                
                # Contact
                phone_primary="+919876543210",
                phone_secondary="+919876543211",
                email="contact@srilakshmiclinic.com",
                website="https://srilakshmiclinic.com",
                
                # Address
                address_line1="123, MG Road",
                address_line2="Near City Hospital",
                city="Hyderabad",
                state="Telangana",
                postal_code="500001",
                
                # Operational
                timezone="Asia/Kolkata",
                languages_spoken=json.dumps(["Telugu", "English", "Hindi"]),
                parking_info="Free parking available in basement",
                wheelchair_accessible=True,
                accepts_walkins=True,
                
                # Integration
                twilio_phone="+919876543210",
                whatsapp_enabled=True
            )
            session.add(clinic)
            session.commit() # Commit clinic first to get ID if needed, but we used uuid4 so ok.
        
        # 2. Create Providers
        logger.info("Creating providers...")
        
        dr_rajesh = Provider(
            id=uuid4(),
            clinic_id=clinic.id,
            name="Dr. Rajesh Patel",
            title="Dr.",
            specialty="General Physician",
            qualifications="MBBS, MD",
            years_of_experience=15,
            languages_spoken=json.dumps(["Telugu", "English", "Hindi"]),
            bio="Dr. Rajesh has 15 years of experience in general medicine and family healthcare.",
            working_days=json.dumps(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]),
            working_hours=json.dumps({
                "monday": {"start": "09:00", "end": "13:00", "evening_start": "18:00", "evening_end": "21:00"},
                "tuesday": {"start": "09:00", "end": "13:00", "evening_start": "18:00", "evening_end": "21:00"},
                "wednesday": {"start": "09:00", "end": "13:00", "evening_start": "18:00", "evening_end": "21:00"},
                "thursday": {"start": "09:00", "end": "13:00", "evening_start": "18:00", "evening_end": "21:00"},
                "friday": {"start": "09:00", "end": "13:00", "evening_start": "18:00", "evening_end": "21:00"},
                "saturday": {"start": "09:00", "end": "13:00"}
            }),
            default_appointment_duration=15,
            booking_buffer=5
        )
        session.add(dr_rajesh)
        
        dr_priya = Provider(
            id=uuid4(),
            clinic_id=clinic.id,
            name="Dr. Priya Sharma",
            title="Dr.",
            specialty="Pediatrician",
            qualifications="MBBS, DCH",
            years_of_experience=10,
            languages_spoken=json.dumps(["Telugu", "English"]),
            bio="Dr. Priya specializes in child healthcare and vaccination.",
            working_days=json.dumps(["monday", "wednesday", "friday", "saturday"]),
            default_appointment_duration=20
        )
        session.add(dr_priya)

        # 2.1 Mirror to Legacy Doctor Table (for TokenService compatibility)
        logger.info("Mirroring to legacy Doctor table...")
        legacy_doctors = session.exec(select(Doctor).where(Doctor.clinic_id == clinic.id)).all()
        if not legacy_doctors:
            doc_rajesh = Doctor(
                id=dr_rajesh.id, # keep IDs same if possible, or new. Let's keep same UUID for consistency
                clinic_id=clinic.id,
                name=dr_rajesh.name,
                specialization=dr_rajesh.specialty,
                is_active=True
            )
            session.add(doc_rajesh)
            
            doc_priya = Doctor(
                id=dr_priya.id,
                clinic_id=clinic.id,
                name=dr_priya.name,
                specialization=dr_priya.specialty,
                is_active=True
            )
            session.add(doc_priya)
            logger.info("Legacy Doctors added.")
        
        # 3. Create Services
        logger.info("Creating services...")
        
        services = [
            Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name="General Consultation",
                description="Routine check-up and diagnosis",
                category="Consultation",
                price=500.0,
                duration_minutes=15,
                display_order=1
            ),
            Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name="Pediatric Consultation",
                description="Child health check-up",
                category="Consultation",
                price=600.0,
                duration_minutes=20,
                display_order=2
            ),
            Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name="Blood Test",
                description="Complete blood count and basic tests",
                category="Diagnostic",
                price=800.0,
                duration_minutes=10,
                display_order=3
            ),
            Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name="ECG",
                description="Electrocardiogram test",
                category="Diagnostic",
                price=400.0,
                duration_minutes=15,
                display_order=4
            ),
            Service(
                id=uuid4(),
                clinic_id=clinic.id,
                name="Vaccination",
                description="Child vaccination",
                category="Procedure",
                price=300.0,
                duration_minutes=10,
                display_order=5
            )
        ]
        for service in services:
            session.add(service)
        
        # 4. Create FAQs
        logger.info("Creating FAQs...")
        
        faqs = [
            FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="Hours",
                question="What are your clinic timings?",
                answer_english="We are open Monday to Saturday. Morning session: 9 AM to 1 PM, Evening session: 6 PM to 9 PM. Sunday closed.",
                answer_telugu="మేము సోమవారం నుండి శనివారం వరకు తెరిచి ఉంటాము. ఉదయం 9 నుండి 1 వరకు, సాయంత్రం 6 నుండి 9 వరకు. ఆదివారం సెలవు.",
                keywords=json.dumps(["timings", "hours", "open", "close", "schedule", "time"]),
                display_order=1
            ),
            FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="Location",
                question="Where is the clinic located?",
                answer_english="We are located at 123 MG Road, near City Hospital, Hyderabad 500001. Free parking available.",
                answer_telugu="మేము హైదరాబాద్ 500001, సిటీ హాస్పిటల్ దగ్గర, 123 ఎం.జి రోడ్ వద్ద ఉన్నాము. ఉచిత పార్కింగ్ అందుబాటులో ఉంది.",
                keywords=json.dumps(["location", "address", "where", "parking"]),
                display_order=2
            ),
            FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="Services",
                question="What services do you provide?",
                answer_english="We provide general consultations, pediatric care, blood tests, ECG, vaccinations, and more. Consult our doctors for specific treatments.",
                answer_telugu="మేము సాధారణ పరీక్షలు, పిల్లల వైద్యం, రక్త పరీక్షలు, ఈసీజీ, టీకాలు మరియు మరిన్ని సేవలను అందిస్తాము.",
                keywords=json.dumps(["services", "treatment", "what", "provide", "offer"]),
                display_order=3
            ),
            FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="Fees",
                question="What are the consultation charges?",
                answer_english="General consultation is ₹500, Pediatric consultation is ₹600. Diagnostic tests have separate charges.",
                answer_telugu="సాధారణ కన్సల్టేషన్ ₹500, పిల్లల కన్సల్టేషన్ ₹600. పరీక్షలకు వేరు ఛార్జీలు.",
                keywords=json.dumps(["fees", "charges", "cost", "price", "how much"]),
                display_order=4
            ),
            FAQ(
                id=uuid4(),
                clinic_id=clinic.id,
                category="Walk-in",
                question="Do you accept walk-in patients?",
                answer_english="Yes, we accept walk-in patients. However, we recommend booking an appointment to avoid waiting time.",
                answer_telugu="అవును, మేము వాక్-ఇన్ రోగులను అంగీకరిస్తాము. కానీ వేచి ఉండకుండా ముందుగానే అపాయింట్మెంట్ తీసుకోవడం మంచిది.",
                keywords=json.dumps(["walk-in", "walkin", "without appointment", "direct"]),
                display_order=5
            )
        ]
        for faq in faqs:
            session.add(faq)
        
        # 5. Create Scheduling Rules
        logger.info("Creating scheduling rules...")
        
        rules = SchedulingRule(
            id=uuid4(),
            clinic_id=clinic.id,
            advance_booking_days=30,
            same_day_cutoff_hour=12,  # No same-day booking after noon
            requires_manual_approval=False,
            send_confirmation=True,
            confirmation_methods=json.dumps(["whatsapp", "sms"]),
            cancellation_hours=24,
            cancellation_fee_percent=0.0,
            no_show_fee=200.0,
            allow_reschedule=True,
            reschedule_hours=24
        )
        session.add(rules)
        
        # 6. Create Holidays
        logger.info("Creating holidays...")
        
        holidays = [
            Holiday(
                id=uuid4(),
                clinic_id=clinic.id,
                date=date(2025, 1, 26),
                name="Republic Day",
                is_recurring=True,
                affects_all_providers=True
            ),
            Holiday(
                id=uuid4(),
                clinic_id=clinic.id,
                date=date(2025, 8, 15),
                name="Independence Day",
                is_recurring=True,
                affects_all_providers=True
            ),
            Holiday(
                id=uuid4(),
                clinic_id=clinic.id,
                date=date(2025, 10, 2),
                name="Gandhi Jayanti",
                is_recurring=True,
                affects_all_providers=True
            )
        ]
        for holiday in holidays:
            session.add(holiday)
        
        # 7. Create Sessions (for token system)
        logger.info("Creating clinic sessions...")
        
        sessions = [
            ClinicSession(
                id=uuid4(),
                clinic_id=clinic.id,
                name="MORNING",
                start_time="09:00",
                end_time="13:00",
                max_tokens=20,
                buffer_minutes=10,
                days_of_week=json.dumps(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]),
                is_active=True
            ),
            ClinicSession(
                id=uuid4(),
                clinic_id=clinic.id,
                name="EVENING",
                start_time="18:00",
                end_time="21:00",
                max_tokens=15,
                buffer_minutes=10,
                days_of_week=json.dumps(["monday", "tuesday", "wednesday", "thursday", "friday"]),
                is_active=True
            )
        ]
        for sess in sessions:
            session.add(sess)
        
        # Commit all
        logger.info("Committing to database...")
        session.commit()
        logger.info(f"✓ Sample clinic '{clinic.name}' created successfully!")
        
        return clinic.id


if __name__ == "__main__":
    try:
        clinic_id = create_sample_clinic()
        logger.info(f"\n✓ Seed completed! Clinic ID: {clinic_id}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
