import json
from pathlib import Path

class ContextRetriever:
    def get_context(self, user_text=None):
        try:
            path = Path("data/clinic_knowledge.json")
            if not path.exists(): return "No info."
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            text = "CLINIC INFO:\n"
            if "doctors" in data:
                for d in data["doctors"]:
                    text += f"- Dr. {d.get('name')} ({d.get('specialization')})\n"
            return text
        except: return "Error loading data."