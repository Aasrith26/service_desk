"""
Clinic Information Service
Retrieves comprehensive clinic data by phone number for voice AI
"""

from sqlmodel import Session, select
from core.models_sql import Clinic, Provider, Service, FAQ, SchedulingRule, Holiday
from core.db_engine import engine
from typing import Optional, Dict, List
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)


from core.services.token_service import TokenService

class ClinicInfoService:
    """Service to retrieve and manage clinic knowledge base"""
    
    @staticmethod
    def get_live_status(clinic_id_or_name: str) -> Dict:
        """
        Get live status (rush, wait time) for the voice agent.
        """
        try:
            with Session(engine) as session:
                if len(clinic_id_or_name) == 36: # UUID length
                    clinic_id = UUID(clinic_id_or_name)
                else:
                    # Search by name
                    stmt = select(Clinic).where(Clinic.name.ilike(f"%{clinic_id_or_name}%"))
                    clinic = session.exec(stmt).first()
                    if not clinic:
                        return {"error": "Clinic not found"}
                    clinic_id = clinic.id
            
            return TokenService.get_clinic_rush_info(clinic_id)
            
        except Exception as e:
            logger.error(f"Error getting live status: {e}")
            return {"error": "Could not determine status"}

    @staticmethod
    def get_clinic_by_phone(phone_number: str) -> Optional[Clinic]:
        """
        Retrieve clinic by incoming call phone number
        Matches against phone_primary or twilio_phone
        
        Args:
            phone_number: Phone number from incoming call
            
        Returns:
            Clinic object or None if not found
        """
        try:
            with Session(engine) as session:
                # Clean phone number (remove +, spaces, etc.)
                clean_phone = phone_number.replace("+", "").replace(" ", "").replace("-", "")
                
                stmt = select(Clinic).where(
                    (Clinic.phone_primary.contains(clean_phone)) |
                    (Clinic.twilio_phone.contains(clean_phone))
                )
                clinic = session.exec(stmt).first()
                
                if clinic:
                    logger.info(f"Found clinic: {clinic.name} for number {phone_number}")
                else:
                    logger.warning(f"No clinic found for number {phone_number}")
                
                return clinic
        except Exception as e:
            logger.error(f"Error retrieving clinic by phone: {e}")
            return None
    
    @staticmethod
    def get_clinic_knowledge(clinic_id: UUID) -> Dict:
        """
        Get complete clinic knowledge base for AI voice agent
        
        Args:
            clinic_id: UUID of the clinic
            
        Returns:
            Dictionary with all clinic information
        """
        try:
            with Session(engine) as session:
                # Get clinic
                clinic = session.get(Clinic, clinic_id)
                if not clinic:
                    return {}
                
                # Get active providers
                providers = session.exec(
                    select(Provider).where(
                        Provider.clinic_id == clinic_id,
                        Provider.is_active == True
                    )
                ).all()
                
                # Get active services
                services = session.exec(
                    select(Service).where(
                        Service.clinic_id == clinic_id,
                        Service.is_active == True
                    ).order_by(Service.display_order)
                ).all()
                
                # Get active FAQs
                faqs = session.exec(
                    select(FAQ).where(
                        FAQ.clinic_id == clinic_id,
                        FAQ.is_active == True
                    ).order_by(FAQ.display_order)
                ).all()
                
                # Get scheduling rules
                rules = session.exec(
                    select(SchedulingRule).where(
                        SchedulingRule.clinic_id == clinic_id
                    )
                ).first()
                
                # Get holidays
                holidays = session.exec(
                    select(Holiday).where(
                        Holiday.clinic_id == clinic_id
                    )
                ).all()
                
                return {
                    "clinic": clinic,
                    "providers": list(providers),
                    "services": list(services),
                    "faqs": list(faqs),
                    "scheduling_rules": rules,
                    "holidays": list(holidays)
                }
        except Exception as e:
            logger.error(f"Error retrieving clinic knowledge: {e}")
            return {}
    
    @staticmethod
    def get_clinic_hours_text(clinic_knowledge: Dict, language: str = "english") -> str:
        """
        Generate human-readable clinic hours text
        
        Args:
            clinic_knowledge: Dict from get_clinic_knowledge()
            language: "english", "telugu", or "hindi"
            
        Returns:
            Formatted hours string
        """
        clinic = clinic_knowledge.get("clinic")
        if not clinic:
            return ""
        
        # For now, basic format
        # TODO: Parse from FAQs or sessions
        return f"{clinic.name} is open Monday to Saturday, 9 AM to 1 PM and 6 PM to 9 PM"
    
    @staticmethod
    def get_faq_answer(clinic_knowledge: Dict, question: str, language: str = "english") -> Optional[str]:
        """
        Find FAQ answer matching the question
        
        Args:
            clinic_knowledge: Dict from get_clinic_knowledge()
            question: User's question
            language: Response language
            
        Returns:
            Answer string or None
        """
        faqs = clinic_knowledge.get("faqs", [])
        question_lower = question.lower()
        
        for faq in faqs:
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
            
            # Check question text
            if faq.question.lower() in question_lower:
                if language == "telugu" and faq.answer_telugu:
                    return faq.answer_telugu
                elif language == "hindi" and faq.answer_hindi:
                    return faq.answer_hindi
                else:
                    return faq.answer_english
        
        return None
    
    @staticmethod
    def get_services_list(clinic_knowledge: Dict) -> List[Dict]:
        """
        Get formatted services list with pricing
        
        Args:
            clinic_knowledge: Dict from get_clinic_knowledge()
            
        Returns:
            List of service dicts
        """
        services = clinic_knowledge.get("services", [])
        return [
            {
                "name": s.name,
                "description": s.description,
                "price": f"₹{s.price:.0f}",
                "duration": f"{s.duration_minutes} minutes",
                "category": s.category
            }
            for s in services
        ]
    
    @staticmethod
    def get_providers_list(clinic_knowledge: Dict) -> List[Dict]:
        """
        Get formatted providers list
        
        Args:
            clinic_knowledge: Dict from get_clinic_knowledge()
            
        Returns:
            List of provider dicts
        """
        providers = clinic_knowledge.get("providers", [])
        return [
            {
                "name": p.name,
                "title": p.title,
                "specialty": p.specialty,
                "qualifications": p.qualifications,
                "languages": json.loads(p.languages_spoken) if p.languages_spoken else [],
                "experience": f"{p.years_of_experience} years" if p.years_of_experience else None
            }
            for p in providers
        ]


# Convenience function for realtime voice client
def get_clinic_info_for_call(phone_number: str) -> Optional[Dict]:
    """
    Main function to get all clinic info when call is received
    
    Args:
        phone_number: Incoming call number
        
    Returns:
        Complete clinic knowledge dict or None
    """
    clinic = ClinicInfoService.get_clinic_by_phone(phone_number)
    if not clinic:
        return None
    
    return ClinicInfoService.get_clinic_knowledge(clinic.id)
