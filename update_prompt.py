import re

with open('core/realtime_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Task 1: Update end-call instructions
old_end_call = '5. If user says goodbye or is done, FIRST say a polite goodbye (e.g. "Thank you, have a nice day!"), THEN use the end_call tool immediately.'

new_end_call = '''5. BEFORE ending the call:
           - Ask: "Is there anything else I can help you with?" or "Inkemina help kavala?"
           - Wait for their response
           - ONLY after they confirm NO more queries, say goodbye and use end_call tool
           - Never hang up abruptly without asking if they need more help'''

if old_end_call in content:
    content = content.replace(old_end_call, new_end_call)
    print('Task 1: Updated end-call logic')
else:
    print('Task 1: Pattern not found for end-call')

# Task 2: Update booking process - no phone needed
old_booking = '2. Collect: doctor, date, time, patient name (in Latin script), phone'

new_booking = '''2. Collect: doctor, date, time, patient name (in Latin script)
        3. DO NOT ask for phone number - it is automatically captured from the call'''

if old_booking in content:
    content = content.replace(old_booking, new_booking)
    # Also need to update the numbering after this
    content = content.replace('3. BEFORE booking,', '4. BEFORE booking,')
    content = content.replace('4. ONLY after user says', '5. ONLY after user says')
    content = content.replace('5. BEFORE ending the call:', '6. BEFORE ending the call:')
    print('Task 2: Updated booking process - no phone required')
else:
    print('Task 2: Pattern not found for booking process')

# Task 3: Update book_appointment tool - remove phone requirement
old_phone_param = '"patient_phone": {"type": "string", "description": "Patient phone number"}'
new_phone_param = '"patient_phone": {"type": "string", "description": "Patient phone number (optional - auto-captured from call)"}'

if old_phone_param in content:
    content = content.replace(old_phone_param, new_phone_param)
    print('Task 3: Updated phone parameter description')
else:
    print('Task 3: Phone param pattern not found')

# Task 4: Remove phone from required list
old_required = '"required": ["doctor", "date", "time", "patient_name", "patient_phone"]'
new_required = '"required": ["doctor", "date", "time", "patient_name"]'

if old_required in content:
    content = content.replace(old_required, new_required)
    print('Task 4: Removed phone from required fields')
else:
    print('Task 4: Required pattern not found')

with open('core/realtime_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('File saved successfully!')
