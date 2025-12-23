"""
UPDATED: core/context_retriever.py
NOW USES: PostgreSQL database with cached clinic knowledge (zero lag!)
- STATIC DATA (Clinic info, doctors, FAQs) - Preloaded in memory cache
- DYNAMIC DATA (Slot availability) - Fetched real-time from database
"""

import json
from datetime import datetime
from core.database import ClinicDatabase
from core.services.cached_clinic_service import get_cached_clinic_knowledge

class ContextRetriever:
    def __init__(self, twilio_phone="+16203509655"):
        """
        Initialize with Twilio phone number to identify clinic
        
        Args:
            twilio_phone: The Twilio number receiving the call (identifies which clinic)
        """
        self.db = ClinicDatabase()
        self.twilio_phone = twilio_phone
        
        # PRELOAD clinic knowledge (cached - instant access!)
        self.clinic_knowledge = get_cached_clinic_knowledge(twilio_phone)
        
        if not self.clinic_knowledge:
            raise ValueError(f"No clinic found for phone {twilio_phone}")
        
        self.clinic = self.clinic_knowledge['clinic']
        self.providers = self.clinic_knowledge['providers']
        self.services = self.clinic_knowledge['services']
        self.faqs = self.clinic_knowledge['faqs']

    def get_context(self, user_text=None):
        """
        Generate context for AI:
        - Static data from CACHE (instant - no DB query)
        - Dynamic slot data from DATABASE (real-time query)
        """
        try:
            # Get current date/time for temporal awareness
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            day_name = now.strftime("%A")
            
            # Format current time in 12-hour for AI clarity
            hour_12 = int(now.strftime("%I"))
            am_pm = now.strftime("%p")
            current_time_12h = f"{hour_12}:{now.strftime('%M')} {am_pm}"
            
            text = f"**CURRENT TIME CONTEXT:**\n"
            text += f"Today is {day_name}, {current_date}. Current time is {current_time_12h}.\n"
            text += f"CRITICAL RULES:\n"
            text += f"- If booking for TODAY, slots must be AFTER {current_time_12h}\n"
            text += f"- Do NOT book past times like 7:30 PM if current time is 10:00 PM\n"
            text += f"- Check CLINIC HOURS section below for actual closing time\n\n"
            
            # 1. CLINIC INFO (from cached database - instant!)
            text += f"**CLINIC INFO:**\n"
            text += f"Name: {self.clinic.name}\n"
            text += f"Location: {self.clinic.address_line1}, {self.clinic.city}\n"
            languages = json.loads(self.clinic.languages_spoken) if self.clinic.languages_spoken else []
            text += f"Languages: {', '.join(languages)}\n\n"
            
            # 2. CLINIC HOURS (CRITICAL FOR SMART SLOT VALIDATION!)
            text += "**CLINIC HOURS (MEMORIZE THIS!):**\n"
            text += "You MUST check these hours BEFORE using tools!\n"
            text += "- Morning Session: 9:00 AM - 1:00 PM\n"
            text += "- Closed: 1:00 PM - 6:00 PM (Lunch Break)\n"
            text += "- Evening Session: 6:00 PM - 10:00 PM\n"
            text += "- Sunday: CLOSED (all day)\n"
            text += "\n"
            text += "EXAMPLES:\n"
            text += "- Patient asks \"12 PM slot?\" → YOU respond: \"Sorry andi, 12 PM ki clinic undadhu. Evening 6 nunchi open\"\n"
            text += "- Patient asks \"3 PM slot?\" → YOU respond: \"3 PM ki clinic undadhu. Evening 6 PM nunchi open avthundhi\"\n"
            text += "- Patient asks \"7 PM slot?\" → YOU respond: \"Chusi chepthanu\" → Then check DB\n"
            text += "- Patient asks \"Sunday slot?\" → YOU respond: \"Sunday ki clinic undadhu andi. Monday nunchi open\"\n"
            text += "\n"
            
            # 3. DOCTORS INFO (from cached database - instant!)
            text += "**DOCTORS:**\n"
            for provider in self.providers:
                name = provider.name
                spec = provider.specialty
                years = provider.years_of_experience
                text += f"- {name} ({spec}, {years} years experience)\n"
            text += "\n"
            
            # 3. SERVICES & PRICING (from cached database - instant!)
            text += "**SERVICES & FEES:**\n"
            for service in self.services:
                text += f"- {service.name}: ₹{service.price} ({service.duration_minutes} min)\n"
            text += "\n"
            
            # 4. FAQs (from cached database - instant!)
            text += "**COMMON QUESTIONS:**\n"
            for faq in self.faqs[:3]:  # First 3 FAQs
                text += f"Q: {faq.question}\n"
                text += f"A: {faq.answer_english}\n\n"
            
            # 5. DYNAMIC SLOT AVAILABILITY (fetched real-time from DB)
            # This is queried on-demand, not cached
            slots = self.db.get_available_slots()
            
            if slots:
                text += "**AVAILABILITY SUMMARY (Real-time from database):**\n"
                for doctor, dates in slots.items():
                    text += f" - {doctor}:\n"
                    for date, times in dates.items():
                        # Check if times are in HH:MM format
                        if times and ":" in times[0]:
                            # Group into Morning/Afternoon
                            morn = [t for t in times if int(t.split(':')[0]) < 12]
                            aft = [t for t in times if int(t.split(':')[0]) >= 12]
                            
                            summary_parts = []
                            if morn: summary_parts.append(f"Morning ({', '.join(morn)})")
                            if aft: summary_parts.append(f"Afternoon ({', '.join(aft)})")
                            text += f"   * {date}: {', '.join(summary_parts)}\n"
                        else:
                            # Just list the session names
                            text += f"   * {date}: {', '.join(times)}\n"
            else:
                text += "   (No slots available. Apologize to user.)\n"

            return text
            
        except Exception as e:
            return f"Error loading data: {e}"
    
    def answer_faq(self, question: str, language: str = "english") -> str:
        """
        Answer FAQ from cached knowledge (instant!)
        
        Args:
            question: User's question
            language: "english", "telugu", or "hindi"
            
        Returns:
            Answer string or None
        """
        question_lower = question.lower()
        
        for faq in self.faqs:
            # Check keywords
            if faq.keywords:
                keywords = json.loads(faq.keywords)
                if any(keyword.lower() in question_lower for keyword in keywords):
                    if language == "telugu" and faq.answer_telugu:
                        return faq.answer_telugu
                    elif language == "hindi" and faq.answer_hindi:
                        return faq.answer_hindi
                    else:
                        return faq.answer_english
        
        return None