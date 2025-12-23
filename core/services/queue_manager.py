import logging
from datetime import datetime, timedelta
from typing import List
from sqlmodel import Session, select
from core.models_sql import Appointment, Clinic
from core.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Manages the Appointment Queue, specifically Delays and Broadcasts.
    """
    def __init__(self, db_session: Session, whatsapp_svc: WhatsAppService):
        self.db = db_session
        self.whatsapp = whatsapp_svc

    async def broadcast_delay(self, clinic_id: str, delay_minutes: int):
        """
        1. Updates 'estimated_time' for all ACTIVE, FUTURE appointments for this clinic.
        2. Triggers WhatsApp broadcasts to those patients.
        """
        # 1. Get all active bookings for today/future
        now = datetime.utcnow()
        statement = select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status == "BOOKED",
            Appointment.start_time >= now
        )
        appointments = self.db.exec(statement).all()
        
        updated_count = 0
        
        for appt in appointments:
            # Calculate new estimated time
            # Logic: If estimated_time exists, add to it. If not, add to start_time.
            base_time = appt.estimated_time or appt.start_time
            new_est_time = base_time + timedelta(minutes=delay_minutes)
            
            appt.estimated_time = new_est_time
            self.db.add(appt)
            
            # Format time for message (e.g. "10:30 AM")
            # Note: In prod, handle Timezones properly (store UTC, display IST/ClinicTZ)
            time_str = new_est_time.strftime("%I:%M %p")
            
            # Notifications should be async/background task in prod!
            await self.whatsapp.send_delay_alert(
                patient_phone=appt.patient_phone,
                token_number=appt.token_number,
                new_time_str=time_str,
                delay_minutes=delay_minutes
            )
            updated_count += 1
            
        self.db.commit()
        logger.info(f"Broadcasted {delay_minutes}min delay to {updated_count} patients.")
        return updated_count

    async def get_queue_status(self, clinic_id: str) -> List[Appointment]:
        """
        Returns the simplified live queue for the Admin Dashboard.
        """
        # Sort by estimated time (or start time)
        statement = select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_(["BOOKED", "CHECKED_IN"])
        ).order_by(Appointment.start_time)
        return self.db.exec(statement).all()
