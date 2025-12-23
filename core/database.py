
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from core.models_sql import Clinic, ClinicSession, Doctor, Appointment, CallLog, SQLModel
from core.services.token_service import TokenService
from core.services.whatsapp_service import WhatsAppService
from core.services.call_classifier import CallClassifier
from core.db_engine import engine

logger = logging.getLogger(__name__)

class ClinicDatabase:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClinicDatabase, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.token_service = TokenService()
        self.whatsapp_service = WhatsAppService()
        self.call_classifier = CallClassifier()
        self.initialized = True

    def initialize_db(self):
        """Explicitly create tables and seed data - call this ONCE at startup"""
        self._create_tables()
        self._seed_defaults()

    def _create_tables(self):
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables verified.")

    def _seed_defaults(self):
        """Ensure default Clinic, Sessions, Doctor, and Users exist"""
        from core.models_sql import ClinicUser
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        def get_password_hash(password):
            return pwd_context.hash(password)

        with Session(engine) as session:
            # 1. Ensure Health Plus Clinic Exists
            hp_clinic = session.exec(select(Clinic).where(Clinic.name == "Health Plus Clinic")).first()
            if not hp_clinic:
                logger.info("Seeding Health Plus Clinic...")
                hp_clinic = Clinic(name="Health Plus Clinic", twilio_phone="+1234567890")
                session.add(hp_clinic)
                session.commit()
                session.refresh(hp_clinic)
                
                # Sessions
                s1 = ClinicSession(
                    clinic_id=hp_clinic.id, 
                    name="MORNING", 
                    start_time="09:00", 
                    end_time="13:00",
                    max_tokens=20,
                    buffer_minutes=10,
                    days_of_week='["monday","tuesday","wednesday","thursday","friday","saturday"]',
                    is_active=True
                )
                s2 = ClinicSession(
                    clinic_id=hp_clinic.id, 
                    name="EVENING", 
                    start_time="18:00", 
                    end_time="21:00",
                    max_tokens=15,
                    buffer_minutes=10,
                    days_of_week='["monday","tuesday","wednesday","thursday","friday","saturday"]',
                    is_active=True
                )
                session.add(s1); session.add(s2); session.commit()
            
            # 2. Ensure Doctor Exists for Health Plus
            if not session.exec(select(Doctor).where(Doctor.clinic_id == hp_clinic.id)).first():
                logger.info("Seeding Health Plus Doctor...")
                # We reuse the existing logic or create new
                doc = Doctor(clinic_id=hp_clinic.id, name="Dr. Rajesh Patel", specialization="General Physician")
                session.add(doc)
                session.commit()

            # 3. Ensure User for Health Plus
            if not session.exec(select(ClinicUser).where(ClinicUser.username == "health_plus")).first():
                 logger.info("Seeding Health Plus Admin User...")
                 user = ClinicUser(
                     clinic_id=hp_clinic.id,
                     username="health_plus",
                     password_hash=get_password_hash("aarambh_ai"),
                     full_name="Health Plus Admin"
                 )
                 session.add(user)
                 session.commit()

            # 4. Ensure Sri Lakshmi Clinic Exists (Second Clinic)
            sl_clinic = session.exec(select(Clinic).where(Clinic.name == "Sri Lakshmi Clinic")).first()
            if not sl_clinic:
                logger.info("Seeding Sri Lakshmi Clinic...")
                sl_clinic = Clinic(name="Sri Lakshmi Clinic", twilio_phone="+0987654321")
                session.add(sl_clinic)
                session.commit()
                session.refresh(sl_clinic)

            # 5. Ensure User for Sri Lakshmi
            if not session.exec(select(ClinicUser).where(ClinicUser.username == "sri_lakshmi")).first():
                 logger.info("Seeding Sri Lakshmi Admin User...")
                 user = ClinicUser(
                     clinic_id=sl_clinic.id,
                     username="sri_lakshmi",
                     password_hash=get_password_hash("aarambh_ai"),
                     full_name="Sri Lakshmi Admin"
                 )
                 session.add(user)
                 session.commit()


    def get_available_slots(self):
        """
        Legacy support: Returns available SESSIONS/Tokens rather than time slots.
        """
        return {"Dr. Rajesh Patel": {"Today": ["Morning Session", "Evening Session"]}}

    def is_slot_available(self, doctor: str, date: str, time: str) -> bool:
        """
        Checks if the SESSION implied by 'time' is available.
        Now uses TokenService for proper capacity checking.
        """
        session = self.token_service.get_session_for_time(time, date)
        if not session:
            return False
        
        has_capacity, current, maximum = self.token_service.check_session_capacity(session, date)
        return has_capacity

    def book_slot(self, doctor: str, date: str, time: str, patient_name: str, patient_phone: str):
        """
        Generates a TOKEN for the appropriate session using TokenService.
        """
        doctor_id = None
        if doctor:
            with Session(engine) as session:
                # Try to find doctor by name (case-insensitive partial match)
                # Remove "Dr." prefix if present for better matching
                clean_name = doctor.replace("Dr.", "").strip()
                doc_obj = session.exec(select(Doctor).where(Doctor.name.ilike(f"%{clean_name}%"))).first()
                if doc_obj:
                    doctor_id = doc_obj.id
                    logger.info(f"Resolved doctor '{doctor}' to ID: {doctor_id}")
                else:
                    logger.warning(f"Could not resolve doctor '{doctor}', will use default.")

        result = self.token_service.generate_token(
            patient_name=patient_name,
            patient_phone=patient_phone,
            date=date,
            requested_time=time,
            doctor_id=doctor_id,
            source="PHONE",
            created_by="ai"
        )
        
        if result["success"]:
            logger.info(f"✓ Booked Token {result['token_number']} for {patient_name} on {date} at {result['estimated_time']}")
            
            # Send WhatsApp confirmation
            try:
                self.whatsapp_service.send_booking_confirmation(
                    to_number=patient_phone,
                    patient_name=patient_name,
                    token_number=result["token_number"],
                    estimated_time=result["estimated_time"],
                    date=date
                )
            except Exception as e:
                logger.warning(f"WhatsApp notification failed (booking still succeeded): {e}")
            
            return {
                "success": True,
                "token": result["token_number"],
                "est_time": result["estimated_time"],
                "patient_name": patient_name,
                "appointment_id": result.get("appointment_id")
            }
        else:
            logger.error(f"Booking failed: {result.get('error')}")
            return {"success": False, "error": result.get('error')}

    def log_call(
        self,
        call_sid: str,
        caller_phone: str,
        start_time: datetime,
        duration: int,
        transcript: str,
        booking_made: bool = False,
        appointment_cancelled: bool = False,
        was_successful: bool = False,
        termination_reason: str = "completed",
        appointment_id: Optional[str] = None,
        clinic_id: Optional[str] = None
    ):
        """
        Enhanced call logging with classification and analytics.
        """
        try:
            # Classify the call
            classification = self.call_classifier.classify(
                transcript=transcript,
                booking_made=booking_made,
                appointment_cancelled=appointment_cancelled
            )
            
            with Session(engine) as session:
                log = CallLog(
                    clinic_id=clinic_id,
                    twilio_call_sid=call_sid,
                    caller_phone=caller_phone,
                    start_time=start_time,
                    end_time=start_time + timedelta(seconds=duration) if duration else None,
                    duration_seconds=duration,
                    classification=classification,
                    transcript=transcript,
                    was_successful=was_successful,
                    termination_reason=termination_reason,
                    appointment_id=appointment_id
                )
                session.add(log)
                session.commit()
                
                logger.info(f"✓ Call logged: {call_sid} - Classification: {classification}")
                
        except Exception as e:
            logger.error(f"Log Error: {e}", exc_info=True)
    
    def get_call_analytics(self, start_date: str, end_date: str) -> Dict:
        """Get call analytics for a date range"""
        try:
            with Session(engine) as session:
                stmt = select(CallLog).where(
                    CallLog.start_time >= datetime.fromisoformat(start_date),
                    CallLog.start_time <= datetime.fromisoformat(end_date)
                )
                calls = session.exec(stmt).all()
                
                classifications = [call.classification for call in calls if call.classification]
                stats = self.call_classifier.get_classification_stats(classifications)
                
                return {
                    "total_calls": len(calls),
                    "successful_calls": sum(1 for c in calls if c.was_successful),
                    "classifications": stats,
                    "avg_duration": sum(c.duration_seconds for c in calls if c.duration_seconds) / len(calls) if calls else 0
                }
                
        except Exception as e:
            logger.error(f"Analytics Error: {e}")
            return {}
