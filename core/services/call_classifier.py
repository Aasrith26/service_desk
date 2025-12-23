"""
Call Classification Service
Classifies calls based on transcript analysis and booking outcomes.
"""

import logging
import re
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CallClassifier:
    """Classify calls into predefined categories"""
    
    # Call classification categories
    ENQUIRY = "enquiry"  # General information
    APPOINTMENT_BOOKING = "appointment_booking"  # Successfully booked
    SCHEDULING = "scheduling"  # Asked for slots but didn't book
    CANCELLED = "cancelled"  # Cancelled existing appointment
    WAIT_TIME = "wait_time"  # Asked about queue/waiting
    REVISIT = "revisit"  # Existing patient calling again
    OTHER = "other"  # Miscellaneous
    
    # Keywords for each category (Telugu and English)
    PATTERNS = {
        ENQUIRY: [
            r'\b(information|details|timings|location|address|charges|fees|cost|price|where)\b',
            r'\b(emundi|address|charges|fees|kharchu|ekkada|timing)\b',
            r'\b(open|close|working hours)\b'
        ],
        APPOINTMENT_BOOKING: [
            r'\b(book|booked|appointment|token|confirmed|confirm|reservation)\b',
            r'\b(book|chesanu|appointment|token|confirm|kavalani)\b',
        ],
        SCHEDULING: [
            r'\b(available|slots|when|time|availability|schedule|free)\b',
            r'\b(available|slots|eppudu|time|khali|unnaya)\b',
        ],
        CANCELLED: [
            r'\b(cancel|cancelled|cancellation|not coming|drop)\b',
            r'\b(cancel|raanu|ralekapothunna|oddu)\b',
        ],
        WAIT_TIME: [
            r'\b(wait|waiting|queue|how long|delay|crowd)\b',
            r'\b(wait|waiting|entha sepu|delay|janam)\b',
        ],
        REVISIT: [
            r'\b(again|followup|follow-up|second visit|revisit|came before)\b',
            r'\b(malli|followup|second visit|vachanu)\b',
        ]
    }
    
    @classmethod
    def classify(
        cls,
        transcript: str,
        booking_made: bool = False,
        appointment_cancelled: bool = False
    ) -> str:
        """
        Classify a call based on transcript and outcome.
        
        Args:
            transcript: Full conversation transcript
            booking_made: Whether a booking was successfully made
            appointment_cancelled: Whether an appointment was cancelled
            
        Returns:
            Classification category string
        """
        if not transcript:
            return cls.OTHER
        
        transcript_lower = transcript.lower()
        
        # Priority-based classification
        
        # 1. If booking was made, it's appointment_booking
        if booking_made:
            return cls.APPOINTMENT_BOOKING
        
        # 2. If appointment was cancelled
        if appointment_cancelled:
            return cls.CANCELLED
        
        # 3. Check for wait time queries
        if cls._matches_pattern(transcript_lower, cls.PATTERNS[cls.WAIT_TIME]):
            return cls.WAIT_TIME
        
        # 4. Check for cancellation intent (even if not completed)
        if cls._matches_pattern(transcript_lower, cls.PATTERNS[cls.CANCELLED]):
            return cls.CANCELLED
        
        # 5. Check for scheduling queries
        if cls._matches_pattern(transcript_lower, cls.PATTERNS[cls.SCHEDULING]):
            return cls.SCHEDULING
        
        # 6. Check for general enquiry
        if cls._matches_pattern(transcript_lower, cls.PATTERNS[cls.ENQUIRY]):
            return cls.ENQUIRY
        
        # 7. Check for revisit
        if cls._matches_pattern(transcript_lower, cls.PATTERNS[cls.REVISIT]):
            return cls.REVISIT
        
        # 8. Default to OTHER
        return cls.OTHER
    
    @staticmethod
    def _matches_pattern(text: str, patterns: list) -> bool:
        """Check if text matches any pattern in the list"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def get_classification_stats(cls, classifications: list) -> Dict:
        """
        Generate statistics from a list of classifications.
        
        Args:
            classifications: List of classification strings
            
        Returns:
            Dict with counts for each category
        """
        stats = {
            cls.ENQUIRY: 0,
            cls.APPOINTMENT_BOOKING: 0,
            cls.SCHEDULING: 0,
            cls.CANCELLED: 0,
            cls.WAIT_TIME: 0,
            cls.REVISIT: 0,
            cls.OTHER: 0
        }
        
        for classification in classifications:
            if classification in stats:
                stats[classification] += 1
        
        return stats
