import re

# Update realtime_client.py - book_appointment to use self.caller_phone
with open('core/realtime_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and update the book_appointment execution to use caller_phone if not provided
old_booking = '''elif function_name == "book_appointment":
                doctor = arguments.get("doctor")
                date = arguments.get("date")
                time = arguments.get("time")
                patient_name = arguments.get("patient_name")
                patient_phone = arguments.get("patient_phone")'''

new_booking = '''elif function_name == "book_appointment":
                doctor = arguments.get("doctor")
                date = arguments.get("date")
                time = arguments.get("time")
                patient_name = arguments.get("patient_name")
                # Use auto-captured phone from Exotel if not provided
                patient_phone = arguments.get("patient_phone") or self.caller_phone'''

if old_booking in content:
    content = content.replace(old_booking, new_booking)
    print('Updated book_appointment to use auto-captured phone')
else:
    print('book_appointment pattern not found')

with open('core/realtime_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('realtime_client.py saved!')

# Update exotel_bridge.py - pass caller_phone to RealtimeClient
with open('core/exotel_bridge.py', 'r', encoding='utf-8') as f:
    exo_content = f.read()

old_realtime = '''self.azure_client = RealtimeClient(
            on_audio_received=self.handle_ai_audio,'''

new_realtime = '''self.azure_client = RealtimeClient(
            caller_phone=self.caller_phone,  # Pass caller phone from Exotel
            on_audio_received=self.handle_ai_audio,'''

if old_realtime in exo_content:
    exo_content = exo_content.replace(old_realtime, new_realtime)
    print('Updated exotel_bridge to pass caller_phone')
else:
    print('exotel_bridge pattern not found')

with open('core/exotel_bridge.py', 'w', encoding='utf-8') as f:
    f.write(exo_content)
print('exotel_bridge.py saved!')
