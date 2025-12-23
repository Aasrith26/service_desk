"""
EXAMPLE: How to use cached clinic knowledge in your voice assistant
Replace JSON file access with database fetch (cached for zero lag)
"""

# OLD WAY (JSON file)
# import json
# with open('data/clinic_knowledge.json') as f:
#     clinic_data = json.load(f)

# NEW WAY (PostgreSQL with cache - ZERO LAG!)
from core.services.cached_clinic_service import get_cached_clinic_knowledge, preload_all_clinics

# ✓ STEP 1: Preload on server startup (optional but recommended)
# Add this to your server.py or main initialization
def on_server_start():
    """Call this when your server/app starts"""
    preload_all_clinics()  # Loads all clinics into memory cache
    print("✓ Clinic knowledge preloaded - ready for calls!")

# ✓ STEP 2: Get clinic knowledge when call is received
def handle_incoming_call(from_phone: str):
    """Call this when a patient calls"""
    
    # Get clinic knowledge (instant if preloaded, fast if not)
    clinic_knowledge = get_cached_clinic_knowledge(from_phone)
    
    if not clinic_knowledge:
        print(f"Error: No clinic found for {from_phone}")
        return
    
    # Access clinic information
    clinic = clinic_knowledge['clinic']
    providers = clinic_knowledge['providers']
    services = clinic_knowledge['services']
    faqs = clinic_knowledge['faqs']
    rules = clinic_knowledge['scheduling_rules']
    holidays = clinic_knowledge['holidays']
    
    # Example: Print clinic info
    print(f"Call received for: {clinic.name}")
    print(f"Languages: {clinic.languages_spoken}")
    print(f"Available providers: {len(providers)}")
    
    # Example: Get doctor information
    for provider in providers:
        print(f"  - {provider.name} ({provider.specialty})")
    
    # Example: Answer FAQ
    patient_question = "what are your timings"
    for faq in faqs:
        if any(keyword in patient_question.lower() for keyword in ['timing', 'hours', 'time']):
            print(f"Answer: {faq.answer_english}")
            break
    
    # Example: Get service pricing
    for service in services:
        print(f"Service: {service.name} - ₹{service.price}")
    
    return clinic_knowledge


# ✓ EXAMPLE USAGE IN REALTIME CLIENT
"""
# In your realtime_client.py or voice handler:

from core.services.cached_clinic_service import get_cached_clinic_knowledge

class RealtimeClient:
    def __init__(self, incoming_phone_number):
        self.phone = incoming_phone_number
        
        # Get clinic knowledge (cached, instant!)
        self.clinic_knowledge = get_cached_clinic_knowledge(incoming_phone_number)
        
        if not self.clinic_knowledge:
            raise ValueError(f"No clinic found for {incoming_phone_number}")
        
        self.clinic = self.clinic_knowledge['clinic']
        self.providers = self.clinic_knowledge['providers']
        self.faqs = self.clinic_knowledge['faqs']
        
        print(f"✓ Loaded {self.clinic.name} knowledge (cached)")
    
    def get_clinic_info(self):
        return {
            "name": self.clinic.name,
            "address": f"{self.clinic.address_line1}, {self.clinic.city}",
            "languages": json.loads(self.clinic.languages_spoken)
        }
    
    def answer_faq(self, question: str, language: str = "english"):
        for faq in self.faqs:
            # Simple keyword matching
            keywords = json.loads(faq.keywords) if faq.keywords else []
            if any(kw in question.lower() for kw in keywords):
                if language == "telugu" and faq.answer_telugu:
                    return faq.answer_telugu
                return faq.answer_english
        return None
"""

# ✓ CACHE BENEFITS:
# - First call: ~50-100ms (database query)
# - Subsequent calls: <1ms (in-memory cache)
# - Cache TTL: 5 minutes (refresh automatically)
# - Zero patient-facing lag!

print("✓ Integration example ready - see comments above!")
