"""
Context Retriever - Extracts relevant clinic information for conversation context
Supports fuzzy matching on doctor names, specializations, and availability queries
"""

import json
import re
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from utils.logger import get_logger
from config.settings import CLINIC_DATA_FILE

logger = get_logger(__name__)


class ContextRetriever:
    """Manages clinic data and provides intelligent context extraction."""
    
    def __init__(self, data_file: str = CLINIC_DATA_FILE):
        """
        Initialize context retriever with clinic data.
        
        Args:
            data_file: Path to clinic_knowledge.json file
        """
        self.data_file = data_file
        self.clinic_data = {}
        self.doctors_by_name = {}
        self.doctors_by_specialization = {}
        
        self._load_clinic_data()
    
    def _load_clinic_data(self):
        """Load clinic data from JSON file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.clinic_data = json.load(f)
            
            # Build indices for faster lookups
            for doctor in self.clinic_data.get('doctors', []):
                # Index by name (both English and Telugu)
                self.doctors_by_name[doctor['name'].lower()] = doctor
                self.doctors_by_name[doctor.get('name_telugu', '').lower()] = doctor
                
                # Index by specialization
                spec = doctor['specialization'].lower()
                if spec not in self.doctors_by_specialization:
                    self.doctors_by_specialization[spec] = []
                self.doctors_by_specialization[spec].append(doctor)
            
            logger.info(f"Loaded clinic data with {len(self.clinic_data.get('doctors', []))} doctors")
        
        except FileNotFoundError:
            logger.error(f"Clinic data file not found: {self.data_file}")
            self.clinic_data = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse clinic data: {e}")
            self.clinic_data = {}
    
    def _fuzzy_match(self, query: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
        """
        Find best fuzzy match from candidates.
        
        Args:
            query: Search query
            candidates: List of candidate strings
            threshold: Minimum match ratio (0.0-1.0)
        
        Returns:
            Best matching candidate or None
        """
        best_match = None
        best_ratio = threshold
        
        for candidate in candidates:
            ratio = SequenceMatcher(None, query.lower(), candidate.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        return best_match
    
    def find_doctor(self, name_or_spec: str) -> Optional[Dict[str, Any]]:
        """
        Find a doctor by name or specialization with fuzzy matching.
        
        Args:
            name_or_spec: Doctor name or specialization (supports Telugu and English)
        
        Returns:
            Doctor info dict or None if not found
        """
        name_or_spec_lower = name_or_spec.lower()
        
        # Direct match in name index
        if name_or_spec_lower in self.doctors_by_name:
            return self.doctors_by_name[name_or_spec_lower]
        
        # Direct match in specialization index
        if name_or_spec_lower in self.doctors_by_specialization:
            return self.doctors_by_specialization[name_or_spec_lower]
        
        # Fuzzy match on names
        best_name = self._fuzzy_match(
            name_or_spec, 
            list(self.doctors_by_name.keys()) + 
            [d['name'] for d in self.clinic_data.get('doctors', [])]
        )
        if best_name:
            return self.doctors_by_name.get(best_name.lower())
        
        # Fuzzy match on specializations
        best_spec = self._fuzzy_match(
            name_or_spec,
            list(self.doctors_by_specialization.keys()) +
            [d['specialization'].lower() for d in self.clinic_data.get('doctors', [])]
        )
        if best_spec and best_spec.lower() in self.doctors_by_specialization:
            # Return first doctor with this specialization
            return self.doctors_by_specialization[best_spec.lower()][0]
        
        return None
    
    def find_all_doctors_by_specialization(self, specialization: str) -> List[Dict[str, Any]]:
        """
        Find all doctors with a given specialization.
        
        Args:
            specialization: Medical specialization (supports fuzzy matching)
        
        Returns:
            List of doctor info dicts
        """
        spec_lower = specialization.lower()
        
        if spec_lower in self.doctors_by_specialization:
            return self.doctors_by_specialization[spec_lower]
        
        # Try fuzzy matching
        best_spec = self._fuzzy_match(
            specialization,
            list(self.doctors_by_specialization.keys())
        )
        if best_spec:
            return self.doctors_by_specialization[best_spec.lower()]
        
        return []
    
    def format_doctor_info(self, doctor: Dict[str, Any], include_availability: bool = True) -> str:
        """
        Format doctor information into readable text.
        
        Args:
            doctor: Doctor info dict
            include_availability: Whether to include availability details
        
        Returns:
            Formatted doctor information string
        """
        lines = [
            f"Name: {doctor['name']} ({doctor.get('name_telugu', 'N/A')})",
            f"Specialization: {doctor['specialization']} ({doctor.get('specialization_telugu', 'N/A')})",
            f"Experience: {doctor['experience_years']} years",
            f"Qualifications: {', '.join(doctor['qualifications'])}",
            f"Languages: {', '.join(doctor['languages'])}",
            f"Consultation Fee: ₹{doctor['consultation_fee']}",
        ]
        
        if include_availability:
            lines.append("Availability:")
            for day, timings in doctor['availability'].items():
                if timings == "closed":
                    lines.append(f"  {day.capitalize()}: Closed")
                else:
                    times_str = ", ".join(timings) if isinstance(timings, list) else timings
                    lines.append(f"  {day.capitalize()}: {times_str}")
        
        return "\n".join(lines)
    
    def get_context(self, user_input: str) -> str:
        """
        Extract relevant context from clinic data based on user input.
        This is the main method called before each API response.
        
        Args:
            user_input: User's spoken or typed input
        
        Returns:
            Formatted context string to include in system prompt
        """
        context_parts = [
            f"=== CLINIC INFORMATION ===",
            f"Clinic: {self.clinic_data.get('clinic_info', {}).get('name', 'Health Plus Clinic')}",
            f"Location: {self.clinic_data.get('clinic_info', {}).get('location', 'Hyderabad')}",
            f"",
        ]
        
        # Extract potential doctor mentions or specialization queries
        user_lower = user_input.lower()
        
        # Look for doctor name queries
        for doctor in self.clinic_data.get('doctors', []):
            if any(name in user_lower for name in 
                   [doctor['name'].lower(), doctor.get('name_telugu', '').lower()]):
                context_parts.append("RELEVANT DOCTOR INFO:")
                context_parts.append(self.format_doctor_info(doctor))
                context_parts.append("")
                break
        
        # Look for specialization queries
        specialization_keywords = {
            'cardio': 'Cardiology',
            'heart': 'Cardiology',
            'chest': 'Cardiology',
            'pediatric': 'Pediatrics',
            'kids': 'Pediatrics',
            'child': 'Pediatrics',
            'general': 'General Medicine',
        }
        
        for keyword, spec in specialization_keywords.items():
            if keyword in user_lower:
                doctors = self.find_all_doctors_by_specialization(spec)
                if doctors:
                    context_parts.append(f"=== DOCTORS IN {spec.upper()} ===")
                    for doctor in doctors:
                        context_parts.append(self.format_doctor_info(doctor, include_availability=True))
                        context_parts.append("")
                break
        
        # If no specific doctor or specialization mentioned, provide general clinic overview
        if "doctor" in user_lower or "appointment" in user_lower or "booking" in user_lower:
            if not any("RELEVANT DOCTOR" in part or "DOCTORS IN" in part for part in context_parts):
                context_parts.append("=== ALL AVAILABLE DOCTORS ===")
                for doctor in self.clinic_data.get('doctors', [])[:3]:  # Limit to first 3
                    context_parts.append(f"• {doctor['name']} ({doctor['specialization']}) - ₹{doctor['consultation_fee']}")
                context_parts.append("")
        
        # Add FAQ if relevant
        user_words = set(user_input.lower().split())
        for faq in self.clinic_data.get('faqs', [])[:2]:
            faq_words = set(faq.get('question', '').lower().split())
            if len(faq_words & user_words) > 2:  # At least 2 words in common
                context_parts.append("RELEVANT FAQ:")
                context_parts.append(f"Q: {faq['question']}")
                context_parts.append(f"A: {faq['answer']}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_all_doctors(self) -> List[Dict[str, Any]]:
        """Get list of all doctors."""
        return self.clinic_data.get('doctors', [])
    
    def get_clinic_info(self) -> Dict[str, Any]:
        """Get general clinic information."""
        return self.clinic_data.get('clinic_info', {})
