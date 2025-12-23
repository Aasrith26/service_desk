import re

with open('core/realtime_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the __init__ to accept caller_phone
old_init = '''def __init__(self, on_audio_received=None, on_text_received=None, on_response_done=None, on_call_ended=None, on_interruption=None):
        self.ws = None
        self.is_connected = False
        self.on_audio_received = on_audio_received'''

new_init = '''def __init__(self, on_audio_received=None, on_text_received=None, on_response_done=None, on_call_ended=None, on_interruption=None, caller_phone=None):
        self.ws = None
        self.is_connected = False
        self.caller_phone = caller_phone or "Unknown"  # Auto-captured from Exotel
        self.on_audio_received = on_audio_received'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print('Updated __init__ with caller_phone parameter')
else:
    print('Init pattern not found')

with open('core/realtime_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('File saved!')
