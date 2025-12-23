# Stop voice_service.py first (Ctrl+C)

from utils.audio_utils import base64_to_pcm
import base64

# Test audio decoding
test_audio = base64.b64encode(b'\x00\x01\x02\x03').decode()
result = base64_to_pcm(test_audio)
print(f'base64_to_pcm works: {len(result)} bytes')

# Test the whole import chain
from core.realtime_client import RealtimeClient
print('RealtimeClient imports OK')

# Check if callback is set correctly
def test_callback(data):
    print(f'Callback received: {len(data)} bytes')

client = RealtimeClient(on_audio_received=test_callback)
print(f'on_audio_received is set: {client.on_audio_received is not None}')
