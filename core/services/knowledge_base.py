"""
Clinic Knowledge Base Service
Provides instant responses to common queries without database lookups.
"""

import logging
import re
from typing import Optional, Dict
from datetime import datetime, time as datetime_time

logger = logging.getLogger(__name__)


class ClinicKnowledgeBase:
    """Pre-loaded knowledge about clinic operations"""
    
    def __init__(self):
        """Initialize with clinic configuration"""
        # TODO: Load from database or config file
        self.clinic_name = "Health Plus Clinic"
        
        # Session timings
        self.sessions = {
            "MORNING": {
                "start": "09:00",
                "end": "13:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            },
            "EVENING": {
                "start": "18:00",
                "end": "21:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            }
        }
        
        # Holidays (can be loaded from DB)
        self.holidays = [
            # "2025-12-25",  # Example
        ]
    
    def is_clinic_open_now(self, current_time: datetime) -> tuple[bool, Optional[str]]:
        """
        Check if clinic is currently open.
        
        Returns:
            (is_open, session_name or reason)
        """
        current_day = current_time.strftime("%A").lower()
        current_time_str = current_time.strftime("%H:%M")
        date_str = current_time.strftime("%Y-%m-%d")
        
        # Check if holiday
        if date_str in self.holidays:
            return (False, "holiday")
        
        # Check each session
        for session_name, session_info in self.sessions.items():
            if current_day not in session_info["days"]:
                continue
            
            if session_info["start"] <= current_time_str <= session_info["end"]:
                return (True, session_name)
        
        return (False, "closed")
    
    def get_next_opening_time(self, current_time: datetime) -> Optional[str]:
        """Get next opening time from current time"""
        current_day = current_time.strftime("%A").lower()
        current_time_str = current_time.strftime("%H:%M")
        
        # Check if evening session is still today
        evening = self.sessions["EVENING"]
        if current_day in evening["days"] and current_time_str < evening["start"]:
            return evening["start"]
        
        # Otherwise, next morning
        return self.sessions["MORNING"]["start"]
    
    def should_use_knowledge_base(self, user_query: str) -> bool:
        """
        Check if query can be answered from knowledge base.
        
        Returns True for:
        - Clinic hours/timings
        - Location/address
        - General information
        
        Returns False for:
        - Specific slot availability (needs DB check)
        - Booking requests
        """
        query_lower = user_query.lower()
        
        # Patterns that indicate KB can answer
        kb_patterns = [
            r'\b(timing|time|hours|open|close|eppudu|\bkalu\b)\b',
            r'\b(location|address|ekkada|where)\b',
            r'\b(morning|evening|session)\b',
            r'\b(holiday|sunday|off day)\b',
        ]
        
        # Patterns that indicate DB needed
        db_patterns = [
            r'\b(available|book|appointment|token|slot)\b',
            r'\b(kavala|book|appointment|token)\b',
        ]
        
        # Check if DB needed first (higher priority)
        for pattern in db_patterns:
            if re.search(pattern, query_lower):
                return False
        
        # Check if KB can answer
        for pattern in kb_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def get_response_for_query(self, user_query: str, current_time: datetime, language: str = "telugu") -> Optional[str]:
        """
        Generate appropriate response for common queries.
        
        Args:
            user_query: User's question
            current_time: Current datetime
            language: "telugu" or "english"
            
        Returns:
            Pre-formulated response or None if can't answer
        """
        query_lower = user_query.lower()
        is_open, status = self.is_clinic_open_now(current_time)
        
        # Query about clinic hours/timings
        if re.search(r'\b(timing|time|hours|open|close|eppudu)\b', query_lower):
            if language == "telugu":
                return (
                    f"Clinic timings: Morning 9 AM to 1 PM, Evening 6 PM to 9 PM. "
                    f"Monday to Saturday open. Sunday off."
                )
            else:
                return (
                    f"Clinic timings: Morning 9 AM to 1 PM, Evening 6 PM to 9 PM. "
                    f"Open Monday to Saturday. Closed on Sundays."
                )
        
        # Query about current availability
        if re.search(r'\b(open|available now|ippudu)\b', query_lower):
            if is_open:
                if language == "telugu":
                    return f"Avunu, clinic ippudu open undi. {status.title()} session nadusthundi."
                else:
                    return f"Yes, the clinic is currently open. {status.title()} session is running."
            else:
                next_time = self.get_next_opening_time(current_time)
                if language == "telugu":
                    return f"Ledu andi, ippudu clinic close undi. Next {next_time} ki open avthundi."
                else:
                    return f"Sorry, the clinic is currently closed. We open at {next_time}."
        
        return None
    
    def get_closed_session_response(self, requested_time: str, current_time: datetime, language: str = "telugu") -> Optional[str]:
        """
        Generate response when user asks for slot during closed hours.
        
        Args:
            requested_time: Time user requested (e.g., "12:00", "14:30")
            current_time: Current datetime
            language: Response language
            
        Returns:
            Appropriate response or None
        """
        try:
            hour = int(requested_time.split(':')[0])
            
            # Check if time falls in closed period (13:00-18:00)
            if 13 <= hour < 18:
                next_session_start = self.sessions["EVENING"]["start"]
                
                if language == "telugu":
                    return (
                        f"Sorry andi, {requested_time} ki clinic undadhu. "
                        f"Clinic evening {next_session_start} ki open avthundi. "
                        f"Evening session ki slots kavala?"
                    )
                else:
                    return (
                        f"Sorry, the clinic is closed at {requested_time}. "
                        f"We open in the evening at {next_session_start}. "
                        f"Would you like a slot in the evening session?"
                    )
            
            # Before morning session starts (before 9 AM)
            if hour < 9:
                morning_start = self.sessions["MORNING"]["start"]
                if language == "telugu":
                    return (
                        f"Morning session {morning_start} nunchi start avthundi. "
                        f"{morning_start} tarvatha slot kavala?"
                    )
                else:
                    return f"Morning session starts at {morning_start}. Would you like a slot after that?"
            
            # After evening session ends (after 9 PM)
            if hour >= 21:
                if language == "telugu":
                    return "Evening session 9 PM varaku. Repu slot book cheyamantara?"
                else:
                    return "Evening session ends at 9 PM. Shall I book for tomorrow?"
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating closed session response: {e}")
            return None
    
    def get_session_for_time(self, time_str: str) -> Optional[str]:
        """Determine which session a time belongs to"""
        try:
            hour = int(time_str.split(':')[0])
            
            # Morning: 9-13
            if 9 <= hour < 13:
                return "MORNING"
            
            # Evening: 18-21
            if 18 <= hour < 21:
                return "EVENING"
            
            return None
            
        except Exception:
            return None
