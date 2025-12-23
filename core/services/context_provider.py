from typing import Optional, Dict
from sqlmodel import Session, select
from core.models_sql import Clinic, KnowledgeBase, Doctor

class ContextProvider:
    """
    Service to fetch clinic-specific context for the Voice Agent.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_clinic_by_phone(self, phone_number: str) -> Optional[Clinic]:
        statement = select(Clinic).where(Clinic.twilio_phone == phone_number)
        result = self.db.exec(statement).first()
        return result

    def get_system_prompt_context(self, clinic_id: str) -> str:
        """
        Builds the text block to inject into the LLM System Prompt.
        Includes: Knowledge Base, Doctors List.
        """
        # 1. Fetch Knowledge Base
        kb_stmt = select(KnowledgeBase).where(KnowledgeBase.clinic_id == clinic_id)
        kb_entries = self.db.exec(kb_stmt).all()
        
        kb_text = "**CLINIC KNOWLEDGE BASE:**\n"
        for entry in kb_entries:
            kb_text += f"- {entry.category.upper()}: {entry.content}\n"
            
        # 2. Fetch Doctors
        doc_stmt = select(Doctor).where(Doctor.clinic_id == clinic_id)
        doctors = self.db.exec(doc_stmt).all()
        
        doc_text = "**DOCTORS AVAILABLE:**\n"
        for doc in doctors:
            status = "Active" if doc.is_active else "On Leave"
            doc_text += f"- {doc.name} ({doc.specialization}) - {status}\n"
            
        return f"{kb_text}\n{doc_text}"

    def get_llm_config(self, clinic: Clinic) -> Dict:
        """
        Returns the specific config for the AI (Voice ID, Language).
        Defaults if missing.
        """
        defaults = {
            "voice": "alloy",
            "language": "en-US",
            "model": "gpt-4o"
        }
        if clinic.ai_config:
            return {**defaults, **clinic.ai_config}
        return defaults
