"""
Twilio WhatsApp Notification Service
Sends appointment confirmation messages via WhatsApp using templates
"""

import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = os.getenv("TWILIO_CONTENT_SID", "")


class WhatsAppService:
    """Send WhatsApp notifications via Twilio"""
    
    def __init__(self):
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured. WhatsApp notifications will be disabled.")
            self.client = None
        else:
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.from_number = TWILIO_WHATSAPP_FROM
        self.content_sid = TWILIO_CONTENT_SID
    
    def send_booking_confirmation(self, to_number: str, patient_name: str, token_number: int, estimated_time: str, date: str = None):
        """
        Sends a WhatsApp template message with appointment details.
        
        Args:
            to_number: Patient's phone number (e.g., "9381241869" or "+919381241869")
            patient_name: Patient's name (for logging)
            token_number: Token number assigned
            estimated_time: Estimated appointment time (e.g., "10:00 AM")
            date: Appointment date (e.g., "12/23" or "2024-12-23")
        
        Returns:
            True if message sent successfully, False otherwise
        """
        if not to_number:
            logger.warning("WhatsApp: No phone number provided.")
            return False
        
        if not self.client:
            logger.warning("WhatsApp: Twilio client not initialized. Skipping notification.")
            return False
        
        try:
            # Format phone number for WhatsApp
            phone = str(to_number).strip()
            if not phone.startswith("+"):
                # Assume Indian number if no country code
                phone = "+91" + phone.lstrip("0")
            whatsapp_to = f"whatsapp:{phone}"
            
            # Format date for template variable
            if date:
                # Use provided date
                display_date = date
            else:
                display_date = "your scheduled date"
            
            # Send template message using content_sid
            # Template: "Your appointment is coming up on {{1}} at {{2}}..."
            message = self.client.messages.create(
                from_=self.from_number,
                content_sid=self.content_sid,
                content_variables=f'{{"1":"{display_date}","2":"{estimated_time}"}}',
                to=whatsapp_to
            )
            
            logger.info(f"✓ WhatsApp sent to {whatsapp_to} | SID: {message.sid} | Status: {message.status}")
            logger.info(f"  Patient: {patient_name}, Token: {token_number}, Date: {display_date}, Time: {estimated_time}")
            return True
            
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False
