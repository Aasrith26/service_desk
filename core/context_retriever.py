"""
UPDATED: core/context_retriever.py
- FEATURE: Uses ClinicDatabase (CSV).
- LOGIC: Filters out 'booked' slots so the model never offers them.
"""
import json
from pathlib import Path
from datetime import datetime
from core.database import ClinicDatabase

class ContextRetriever:
    def __init__(self):
        self.db = ClinicDatabase()

    def get_context(self, user_text=None):
        try:
            # Get current date/time for temporal awareness
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            day_name = now.strftime("%A")
            
            # File Paths
            kb_path = Path("data/clinic_knowledge.json")
            
            text = f"**CURRENT TIME CONTEXT:**\n"
            text += f"Today is {day_name}, {current_date}. Current time is {current_time}.\n"
            text += f"CRITICAL: Do NOT suggest slots before current time if booking for today!\n\n"
            text += "**CLINIC INFO:**\n"
            
            # 1. Static Info (Doctors & Fees)
            if kb_path.exists():
                with open(kb_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "doctors" in data:
                        text += "Doctors:\n"
                        for d in data["doctors"]:
                            name = d.get("name_telugu", d["name"])
                            spec = d.get("specialization_telugu", d["specialization"])
                            text += f"- {name} ({spec})\n"

            # 2. Dynamic Slots (Summarized for Natural Conversation)
            slots = self.db.get_available_slots()
            
            if slots:
                text += "\n **AVAILABILITY SUMMARY (Use this to answer queries):**\n"
                for doctor, dates in slots.items():
                    text += f" - {doctor}:\n"
                    for date, times in dates.items():
                        # Group into Morning/Afternoon
                        morn = [t for t in times if int(t.split(':')[0]) < 12]
                        aft = [t for t in times if int(t.split(':')[0]) >= 12]
                        
                        summary_parts = []
                        if morn: summary_parts.append(f"Morning ({', '.join(morn)})")
                        if aft: summary_parts.append(f"Afternoon ({', '.join(aft)})")
                        
                        text += f"   * {date}: {', '.join(summary_parts)}\n"
            else:
                text += "   ( No slots available. Apologize to user.)\n"

            return text
        except Exception as e:
            return f"Error loading data: {e}"