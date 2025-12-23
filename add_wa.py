with open('core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact line
target = 'self.token_service = TokenService()'
insert_after = '        self.whatsapp_service = WhatsAppService()\n'

if target in content and 'whatsapp_service' not in content:
    content = content.replace(target, target + '\n' + insert_after.rstrip())
    print('Inserted whatsapp_service')
    
    with open('core/database.py', 'w', encoding='utf-8') as f:
        f.write(content)
elif 'whatsapp_service' in content:
    print('Already has whatsapp_service')
else:
    print('Target not found')
    # Print context
    for i, line in enumerate(content.split('\n')[20:35], start=21):
        print(f'{i}: {repr(line)}')
