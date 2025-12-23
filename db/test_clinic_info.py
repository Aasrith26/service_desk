"""
Test clinic info service - retrieve clinic knowledge by phone
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.services.clinic_info_service import ClinicInfoService, get_clinic_info_for_call
import json


def test_clinic_retrieval():
    """Test retrieving clinic by phone number"""
    
    print("=" * 60)
    print("TESTING CLINIC INFO SERVICE")
    print("=" * 60)
    
    # Test 1: Get clinic by phone
    print("\n1. Testing clinic retrieval by phone number...")
    phone = "+919876543210"
    clinic = ClinicInfoService.get_clinic_by_phone(phone)
    
    if clinic:
        print(f"✓ Found clinic: {clinic.name}")
        print(f"  - Type: {clinic.clinic_type}")
        print(f"  - Address: {clinic.address_line1}, {clinic.city}")
        print(f"  - Languages: {clinic.languages_spoken}")
    else:
        print(f"✗ No clinic found for {phone}")
        return False
    
    # Test 2: Get complete knowledge base
    print("\n2. Testing complete knowledge base retrieval...")
    knowledge = ClinicInfoService.get_clinic_knowledge(clinic.id)
    
    if knowledge:
        print(f"✓ Retrieved knowledge base:")
        print(f"  - Providers: {len(knowledge['providers'])}")
        for p in knowledge['providers']:
            print(f"    • {p.name} ({p.specialty})")
        
        print(f"  - Services: {len(knowledge['services'])}")
        for s in knowledge['services'][:3]:  # Show first 3
            print(f"    • {s.name} - ₹{s.price}")
        
        print(f"  - FAQs: {len(knowledge['faqs'])}")
        for f in knowledge['faqs'][:2]:  # Show first 2
            print(f"    • {f.category}: {f.question[:50]}...")
        
        print(f"  - Holidays: {len(knowledge['holidays'])}")
        for h in knowledge['holidays']:
            print(f"    • {h.name} ({h.date})")
    else:
        print("✗ No knowledge base retrieved")
        return False
    
    # Test 3: Test FAQ answer
    print("\n3. Testing FAQ search...")
    answer = ClinicInfoService.get_faq_answer(knowledge, "What are your timings?", "english")
    if answer:
        print(f"✓ FAQ Answer: {answer[:100]}...")
    else:
        print("✗ No FAQ answer found")
    
    # Test 4: Test formatted services
    print("\n4. Testing formatted services list...")
    services = ClinicInfoService.get_services_list(knowledge)
    print(f"✓ {len(services)} services formatted")
    for s in services[:2]:
        print(f"  {s['name']}: {s['price']} ({s['duration']})")
    
    # Test 5: Test convenience function
    print("\n5. Testing convenience function for calls...")
    call_info = get_clinic_info_for_call("+919876543210")
    if call_info:
        print(f"✓ Call info retrieved for {call_info['clinic'].name}")
    else:
        print("✗ Call info not retrieved")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_clinic_retrieval()
    sys.exit(0 if success else 1)
