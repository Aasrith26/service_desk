with open('core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import for WhatsApp service
old_import = 'from core.services.token_service import TokenService'
new_import = '''from core.services.token_service import TokenService
from core.services.whatsapp_service import WhatsAppService'''

if old_import in content and 'WhatsAppService' not in content:
    content = content.replace(old_import, new_import)
    print('Added WhatsApp import')
else:
    print('Import already exists or not found')

# Add WhatsApp service to __init__
old_init = 'self.token_service = TokenService()'
new_init = '''self.token_service = TokenService()
        self.whatsapp_service = WhatsAppService()'''

if old_init in content and 'whatsapp_service' not in content:
    content = content.replace(old_init, new_init)
    print('Added WhatsApp service to __init__')
else:
    print('WhatsApp service already in init or pattern not found')

# Add WhatsApp notification after successful booking
old_success = '''if result["success"]:
            logger.info(f"✓ Booked Token {result['token_number']} for {patient_name} on {date} at {result['estimated_time']}")
            return {
                "success": True,
                "token": result["token_number"],
                "est_time": result["estimated_time"],
                "patient_name": patient_name,
                "appointment_id": result.get("appointment_id")
            }'''

new_success = '''if result["success"]:
            logger.info(f"✓ Booked Token {result['token_number']} for {patient_name} on {date} at {result['estimated_time']}")
            
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
                logger.warning(f"WhatsApp notification failed (booking still succeeded): {e}")
            
            return {
                "success": True,
                "token": result["token_number"],
                "est_time": result["estimated_time"],
                "patient_name": patient_name,
                "appointment_id": result.get("appointment_id")
            }'''

if 'whatsapp_service.send_booking_confirmation' not in content:
    if old_success in content:
        content = content.replace(old_success, new_success)
        print('Added WhatsApp notification after booking')
    else:
        print('Success pattern not found - may have different formatting')
else:
    print('WhatsApp notification already added')

with open('core/database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
