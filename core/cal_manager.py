"""
core/cal_manager.py
Handles Cal.com webhooks and syncs them to the CSV database.
"""
import logging
from datetime import datetime
import dateutil.parser
from core.database import ClinicDatabase

logger = logging.getLogger(__name__)

class CalWebhookHandler:
    def __init__(self):
        self.db = ClinicDatabase()

    async def process_webhook(self, data: dict):
        """
        Main entry point for generic Cal.com webhook payloads.
        """
        try:
            trigger = data.get("triggerEvent")
            payload = data.get("payload", {})
            
            logger.info(f"Received Cal.com Webhook: {trigger}")
            
            if trigger == "BOOKING_CREATED":
                return self._handle_booking_created(payload)
            elif trigger == "BOOKING_CANCELLED":
                return self._handle_booking_cancelled(payload)
            elif trigger == "BOOKING_RESCHEDULED":
                # Reschedule is often Cancel + Create, but let's handle if specific
                # For now, treat as create (which upserts)
                 return self._handle_booking_created(payload)
            else:
                logger.warning(f"Unhandled trigger event: {trigger}")
                return False

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

    def _handle_booking_created(self, payload):
        # Extract details
        # Organizer = Doctor
        doctor_name = payload.get("organizer", {}).get("name", "Unknown Doctor")
        
        # Time - Cal.com sends UTC ISO format usually, e.g. "2025-12-07T10:00:00.000Z"
        start_time_str = payload.get("startTime")
        
        if not start_time_str:
            logger.error("No startTime in payload")
            return False

        # Convert to local format for CSV
        # Assuming CSV expects YYYY-MM-DD and HH:MM
        dt = dateutil.parser.parse(start_time_str)
        
        # Convert to local time (Server time)
        # If the server is running in IST, astimezone() will convert to IST
        dt_local = dt.astimezone() 
        
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%H:%M")
        
        # Patient Info
        attendees = payload.get("attendees", [])
        patient_name = ""
        patient_phone = ""
        if attendees:
            first_attendee = attendees[0]
            patient_name = first_attendee.get("name", "")
            patient_phone = first_attendee.get("phoneNumber", "")
            
        success = self.db.upsert_slot(
            doctor=doctor_name,
            date=date_str,
            time=time_str,
            status="booked",
            patient_name=patient_name,
            patient_phone=patient_phone
        )
        return success

    def _handle_booking_cancelled(self, payload):
        doctor_name = payload.get("organizer", {}).get("name", "Unknown Doctor")
        start_time_str = payload.get("startTime")
        
        if not start_time_str:
            return False

        dt = dateutil.parser.parse(start_time_str)
        dt_local = dt.astimezone()
        
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%H:%M")
        
        # Set status back to available
        success = self.db.upsert_slot(
            doctor=doctor_name,
            date=date_str,
            time=time_str,
            status="available",
            patient_name="",
            patient_phone=""
        )
        return success
