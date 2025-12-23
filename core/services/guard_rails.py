"""
Guard Rails System
Manages conversation flow and prevents time-wasting calls.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GuardRails:
    """Conversation flow management and abuse prevention"""
    
    # Configuration (can be loaded from config file)
    MAX_CALL_DURATION = 300  # 5 minutes
    MAX_CLARIFICATION_ATTEMPTS = 2
    MAX_IRRELEVANT_DURATION = 30  # 30 seconds
    BOOKING_INTENT_TIMEOUT = 180  # 3 minutes without booking intent
    
    def __init__(self):
        """Initialize guard rails"""
        self.conversation_state = {}
    
    def init_conversation(self, call_sid: str):
        """Initialize tracking for a new conversation"""
        self.conversation_state[call_sid] = {
            "start_time": datetime.now(),
            "booking_intent_detected": False,
            "clarification_attempts": 0,
            "irrelevant_start": None,
            "last_relevant_time": datetime.now(),
            "turn_count": 0
        }
        logger.info(f"Initialized guard rails for call {call_sid}")
    
    def update_state(
        self,
        call_sid: str,
        booking_intent: bool = False,
        clarification_needed: bool = False,
        is_relevant: bool = True
    ):
        """
        Update conversation state.
        
        Args:
            call_sid: Unique call identifier
            booking_intent: Whether booking intent was detected
            clarification_needed: Whether AI needed to ask for clarification
            is_relevant: Whether user's response was relevant to clinic
        """
        if call_sid not in self.conversation_state:
            self.init_conversation(call_sid)
        
        state = self.conversation_state[call_sid]
        state["turn_count"] += 1
        
        # Update booking intent
        if booking_intent:
            state["booking_intent_detected"] = True
            logger.info(f"Booking intent detected for {call_sid}")
        
        # Update clarification attempts
        if clarification_needed:
            state["clarification_attempts"] += 1
            logger.warning(f"Clarification attempt {state['clarification_attempts']} for {call_sid}")
        
        # Track relevance
        if is_relevant:
            state["last_relevant_time"] = datetime.now()
            state["irrelevant_start"] = None
        else:
            if state["irrelevant_start"] is None:
                state["irrelevant_start"] = datetime.now()
    
    def should_terminate_call(self, call_sid: str) -> Tuple[bool, Optional[str]]:
        """
        Check if call should be terminated based on guard rails.
        
        Returns:
            (should_terminate, reason)
            
        Reasons:
            - "timeout_no_intent": Call too long without booking intent
            - "clarification_failure": Too many failed clarification attempts
            - "off_topic": User speaking irrelevant topics too long
            - "max_duration": Exceeded maximum call duration
        """
        if call_sid not in self.conversation_state:
            return (False, None)
        
        state = self.conversation_state[call_sid]
        current_time = datetime.now()
        duration = (current_time - state["start_time"]).total_seconds()
        
        # 1. Check max call duration
        if duration > self.MAX_CALL_DURATION:
            logger.warning(f"Call {call_sid} exceeded max duration ({duration}s)")
            return (True, "max_duration")
        
        # 2. Check clarification failures
        if state["clarification_attempts"] >= self.MAX_CLARIFICATION_ATTEMPTS:
            logger.warning(f"Call {call_sid} exceeded clarification attempts")
            return (True, "clarification_failure")
        
        # 3. Check irrelevant topic duration
        if state["irrelevant_start"]:
            irrelevant_duration = (current_time - state["irrelevant_start"]).total_seconds()
            if irrelevant_duration > self.MAX_IRRELEVANT_DURATION:
                logger.warning(f"Call {call_sid} off-topic for {irrelevant_duration}s")
                return (True, "off_topic")
        
        # 4. Check booking intent timeout
        if not state["booking_intent_detected"] and duration > self.BOOKING_INTENT_TIMEOUT:
            logger.warning(f"Call {call_sid} no booking intent after {duration}s")
            return (True, "timeout_no_intent")
        
        return (False, None)
    
    def get_termination_message(self, reason: str, language: str = "telugu") -> str:
        """
        Get polite termination message based on reason.
        
        Args:
            reason: Termination reason
            language: "telugu" or "english"
            
        Returns:
            Polite goodbye message
        """
        messages = {
            "telugu": {
                "timeout_no_intent": (
                    "Thank you for calling. Meeku inko help kavali ante "
                    "please call back cheyyandi. Thank you!"
                ),
                "clarification_failure": (
                    "Sorry andi, nenu clear ga vinalekapothunna. "
                    "Please call back chesthe better ga assist chesthanu. Thank you!"
                ),
                "off_topic": (
                    "Thank you for your time. Clinic appointment kosam meeru "
                    "call back cheyandi. Have a good day!"
                ),
                "max_duration": (
                    "Thank you for calling. Meeku appointment book cheyali ante "
                    "please call back cheyyandi. Thank you!"
                ),
                "completed": (
                    "Your appointment is confirmed. Thank you for calling. "
                    "Have a good day!"
                )
            },
            "english": {
                "timeout_no_intent": (
                    "Thank you for calling. If you need any assistance, "
                    "please call back. Have a good day!"
                ),
                "clarification_failure": (
                    "I'm sorry, I'm having trouble understanding. "
                    "Please call back and I'll assist you better. Thank you!"
                ),
                "off_topic": (
                    "Thank you for your time. For clinic appointments, "
                    "please call back. Have a good day!"
                ),
                "max_duration": (
                    "Thank you for calling. To book an appointment, "
                    "please call back. Have a good day!"
                ),
                "completed": (
                    "Your appointment is confirmed. Thank you for calling. "
                    "Have a good day!"
                )
            }
        }
        
        lang_messages = messages.get(language, messages["telugu"])
        return lang_messages.get(reason, lang_messages["completed"])
    
    def close_conversation(self, call_sid: str):
        """Clean up conversation state"""
        if call_sid in self.conversation_state:
            del self.conversation_state[call_sid]
            logger.info(f"Closed conversation {call_sid}")
    
    def get_conversation_duration(self, call_sid: str) -> float:
        """Get current conversation duration in seconds"""
        if call_sid not in self.conversation_state:
            return 0.0
        
        state = self.conversation_state[call_sid]
        duration = (datetime.now() - state["start_time"]).total_seconds()
        return duration
