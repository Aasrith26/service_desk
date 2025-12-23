
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.services.token_service import TokenService

def test_token_service_logic():
    print("Testing TokenService logic...")
    
    # Test cases for time parsing in get_session_for_time
    test_times = [
        ("10:00", "Valid Morning"),
        ("19:30", "Valid Evening"),
        ("14:00", "Valid Evening Boundary"),
        ("5 PM", "Invalid Format"), 
        ("10 AM", "Invalid Format")
    ]
    
    for time_str, desc in test_times:
        print(f"\nTesting: {time_str} ({desc})")
        try:
            # We are not testing DB connection here, just if it crashes before query
            # However, get_session_for_time connects to DB immediately.
            # We can rely on the fact that if it crashes on split(':'), it happens before DB query (mostly).
            # Wait, line 35: hour = int(requested_time.split(':')[0]) is INSIDE the try block but BEFORE query.
            
            # Since we can't easily mock the DB session context manager without setup, 
            # let's just see if we can trigger the error logic in TokenService.
            
            # We expect the real service to log an error for "5 PM" because it doesn't have ':'
            
            session = TokenService.get_session_for_time(time_str, "2025-12-16")
            print(f"Result: {session}")
            
        except Exception as e:
            print(f"CRASHED: {e}")

if __name__ == "__main__":
    test_token_service_logic()
