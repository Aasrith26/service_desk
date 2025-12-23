with open('core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add WhatsApp service to __init__
old_init = '''self.token_service = TokenService()
        self.call_classifier = CallClassifier()
        self.initialized = True'''

new_init = '''self.token_service = TokenService()
        self.whatsapp_service = WhatsAppService()
        self.call_classifier = CallClassifier()
        self.initialized = True'''

if 'whatsapp_service' not in content:
    if old_init in content:
        content = content.replace(old_init, new_init)
        print('Added whatsapp_service to __init__')
    else:
        # Try with different spacing
        alt_old = 'self.token_service = TokenService()'
        if alt_old in content:
            content = content.replace(alt_old, alt_old + '\n        self.whatsapp_service = WhatsAppService()')
            print('Added whatsapp_service after token_service')
        else:
            print('Could not find init pattern')
else:
    print('whatsapp_service already exists')

with open('core/database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
