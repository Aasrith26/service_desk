import re

# Read file
with open('core/database.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

modified = False
new_lines = []

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Add whatsapp_service after token_service
    if 'self.token_service = TokenService()' in line:
        # Check if next line already has whatsapp
        if i + 1 < len(lines) and 'whatsapp_service' not in lines[i + 1]:
            new_lines.append('        self.whatsapp_service = WhatsAppService()\n')
            print(f'Added whatsapp_service init after line {i + 1}')
            modified = True

# Write back
if modified or 'self.whatsapp_service.send_booking_confirmation' not in ''.join(new_lines):
    with open('core/database.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('File saved')
else:
    print('No changes needed')

# Now add the WhatsApp call in book_slot
with open('core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the success block and add WhatsApp call
if 'self.whatsapp_service.send_booking_confirmation' not in content:
    # Pattern: after "logger.info(f"✓ Booked Token..."
    old_pattern = 'logger.info(f"✓ Booked Token {result[\\'token_number\\']} for {patient_name} on {date} at {result[\\'estimated_time\\']}")'
    
    whatsapp_block = '''logger.info(f"✓ Booked Token {result['token_number']} for {patient_name} on {date} at {result['estimated_time']}")
            
            # Send WhatsApp confirmation
            try:
                self.whatsapp_service.send_booking_confirmation(
                    to_number=patient_phone,
                    patient_name=patient_name,
                    token_number=result["token_number"],
                    estimated_time=result["estimated_time"],
                    date=date
                )
            except Exception as e:
                logger.warning(f"WhatsApp notification failed (booking still succeeded): {e}")'''
    
    # Try to find the pattern
    if 'Booked Token' in content:
        # Find the exact line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '✓ Booked Token' in line and 'whatsapp' not in lines[min(i+5, len(lines)-1)].lower():
                print(f'Found booking log at line {i+1}: {line[:60]}...')
                # Insert after this line
                lines.insert(i + 1, '''            
            # Send WhatsApp confirmation
            try:
                self.whatsapp_service.send_booking_confirmation(
                    to_number=patient_phone,
                    patient_name=patient_name,
                    token_number=result["token_number"],
                    estimated_time=result["estimated_time"],
                    date=date
                )
            except Exception as e:
                logger.warning(f"WhatsApp notification failed (booking still succeeded): {e}")''')
                content = '\n'.join(lines)
                print('Added WhatsApp call')
                break

    with open('core/database.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Saved with WhatsApp call')
else:
    print('WhatsApp call already exists')
