"""
WhatsApp Service for sending booking notifications
"""
import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """WhatsApp notification service (stub implementation)"""
    
    def __init__(self):
        self.enabled = False  # Set to True when configured with actual credentials
    
    def send_booking_confirmation(
        self,
        to_number: str,
        patient_name: str,
        token_number: int,
        estimated_time: str,
        date: str
    ) -> bool:
        """
        Send a booking confirmation message via WhatsApp.
        
        Args:
            to_number: Patient's phone number
            patient_name: Name of the patient
            token_number: Assigned token number
            estimated_time: Estimated appointment time
            date: Appointment date
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"WhatsApp disabled - would send confirmation to {to_number}")
            return True
            
        try:
            message = f"""
Hello {patient_name},

Your appointment is confirmed!
Token Number: {token_number}
Date: {date}
Estimated Time: {estimated_time}

Please arrive 10 minutes early.

- Health Plus Clinic
"""
            logger.info(f"WhatsApp confirmation sent to {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False
    
    def send_reminder(
        self,
        to_number: str,
        patient_name: str,
        token_number: int,
        estimated_time: str
    ) -> bool:
        """Send appointment reminder"""
        if not self.enabled:
            logger.info(f"WhatsApp disabled - would send reminder to {to_number}")
            return True
            
        try:
            logger.info(f"WhatsApp reminder sent to {to_number}")
            return True
        except Exception as e:
            logger.error(f"WhatsApp reminder failed: {e}")
            return False
