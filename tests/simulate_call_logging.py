
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.twilio_bridge import TwilioCallHandler
from core.models_sql import CallLog
from core.database import ClinicDatabase
from sqlmodel import select, Session
from core.db_engine import engine

async def test_call_logging():
    print("TEST: Simulating Call Logging Flow...")
    
    # 1. Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.close = AsyncMock()
    
    # 2. Init Handler
    handler = TwilioCallHandler(mock_ws, caller_phone="+919999988888")
    
    # Mock Azure Client inside handler (since we don't want real connection)
    handler.azure_client = AsyncMock()
    handler.azure_client.connect.return_value = True
    
    # But we want to test the REAL save_call_log logic, so we need a real RealtimeClient?
    # Or we can just import RealtimeClient and patch its connect/listen methods.
    
    from core.realtime_client import RealtimeClient
    real_client = RealtimeClient()
    real_client.ws = AsyncMock() # Fake WS
    real_client.connect = AsyncMock(return_value=True)
    real_client.listen = AsyncMock()
    real_client.disconnect = AsyncMock()
    
    # Inject real client logic into handler
    handler.azure_client = real_client
    
    import uuid
    # FETCH REAL CLINIC ID (to satisfy foreign key)
    with Session(engine) as session:
        from core.models_sql import Clinic
        db_clinic = session.exec(select(Clinic)).first()
        if not db_clinic:
            # Seed one if missing
            db_clinic = Clinic(name="Test Clinic", phone_primary="+919999999999", twilio_phone="+1234567890", address_line1="Test St", city="Test City", state="TS", postal_code="500001", country="India")
            session.add(db_clinic)
            session.commit()
            session.refresh(db_clinic)
        
    mock_clinic_id = db_clinic.id
    real_client.context_retriever.clinic = MagicMock()
    real_client.context_retriever.clinic.id = mock_clinic_id
    
    # Simulate Call Start
    unique_sid = f"TEST_SID_{uuid.uuid4().hex[:8]}"
    print(f"-> Call Starting (SID: {unique_sid})...")
    
    handler.call_sid = unique_sid
    handler.stream_sid = "STREAM_SID_123"
    handler.is_active = True
    
    # Simulate accumulating transcript
    real_client.transcript_parts.append("User: I want to book an appointment for tomorrow")
    real_client.transcript_parts.append("AI: Sure, I have a slot at 10 AM. Shall I book it?")
    real_client.transcript_parts.append("User: Yes please")
    
    # SIMULATE TOOL SUCCESS
    real_client.was_booking_made = True
    
    # Simulate Stop Event (which should trigger logging)
    print("-> Call Ending (Stop Event)...")
    await handler.handle_twilio_message('{"event": "stop"}')
    
    # Verify DB
    print("-> Verifying Database Entry...")
    with Session(engine) as session:
        statement = select(CallLog).where(CallLog.twilio_call_sid == unique_sid)
        log = session.exec(statement).first()
        
        if log:
            print("[OK] SUCCESS: Call Log Found!")
            print(f"  - SIP: {log.twilio_call_sid}")
            print(f"  - Classification: {log.classification}")
            print(f"  - Clinic ID: {log.clinic_id}")
            
            if log.classification == "appointment_booking":
                print("  [OK] Classification Correct!")
            else:
                print(f"  [FAIL] Classification Failed: Expected 'appointment_booking', got '{log.classification}'")
                
            if str(log.clinic_id) == str(mock_clinic_id):
                 print("  [OK] Clinic ID Correct!")
            else:
                 print(f"  [FAIL] Clinic ID Mismatch: Expected {mock_clinic_id}, got {log.clinic_id}")

        else:
            print("[FAIL] FAILURE: No log found in DB.")

if __name__ == "__main__":
    asyncio.run(test_call_logging())
