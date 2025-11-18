"""
Send a single text message to the Azure realtime model and print streaming text responses.

Usage (from project root):
    python -c "import sys, os; sys.path.insert(0, os.path.abspath('.')); from core.send_test_message import main; import asyncio; asyncio.run(main('Is Dr. Kavya available tomorrow?'))"

Or run directly (adjust sys.path is added when run directly):
    python core\send_test_message.py "Is Dr. Kavya available tomorrow?"

This script connects, sends the message, prints text deltas and final text, then disconnects.
"""

import sys
import asyncio
import os
import time
import wave
from typing import Optional

try:
    # Ensure project root is on sys.path when executed directly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
except Exception:
    pass

from core.realtime_client import RealtimeClient
from utils.logger import get_logger

logger = get_logger(__name__)


async def main(message: Optional[str] = None):
    if message is None:
        # get from argv
        if len(sys.argv) > 1:
            message = ' '.join(sys.argv[1:])
        else:
            message = "Hello from test script. Is Dr. Kavya available tomorrow?"

    loop = asyncio.get_event_loop()

    # Events
    text_done = asyncio.Event()

    # Buffer for audio bytes
    audio_buffer = bytearray()
    last_audio_ts = {'t': None}

    def on_text(text: str, partial: bool = False):
        prefix = '[partial]' if partial else '[final]'
        print(f"{prefix} {text}")
        if not partial:
            loop.call_soon_threadsafe(text_done.set)

    def on_audio(audio_bytes: bytes):
        # audio_bytes are raw PCM16 bytes
        audio_buffer.extend(audio_bytes)
        last_audio_ts['t'] = time.time()

    client = RealtimeClient(on_text_received=on_text, on_audio_received=on_audio)

    print("Connecting to realtime model...")
    ok = await client.connect()
    if not ok:
        print("Failed to connect")
        return 1

    print("Connected. Sending message:", message)
    # Start listening background task to receive streaming events
    listen_task = asyncio.create_task(client.listen())
    await client.send_message(message)

    # Wait for either text final or audio activity to finish
    start_wait = time.time()
    try:
        # Wait up to 25s for text; if audio arrives, we'll extend waiting until silence
        await asyncio.wait_for(text_done.wait(), timeout=15)
    except asyncio.TimeoutError:
        # No final text within timeout — wait for audio silence if audio received
        if last_audio_ts['t']:
            print("No final text; waiting for audio to finish...")
            # wait up to 10s after last audio chunk
            while True:
                await asyncio.sleep(0.5)
                if last_audio_ts['t'] and (time.time() - last_audio_ts['t'] > 2.0):
                    break
                # safety timeout
                if time.time() - start_wait > 35:
                    break
        else:
            print("Timed out waiting for model response")

    # At this point we either got text final or audio buffer filled (or timed out)
    if audio_buffer:
        wav_path = os.path.join(os.path.dirname(__file__), '..', 'tmp_model_response.wav')
        wav_path = os.path.abspath(wav_path)
        try:
            # Write PCM16 mono 24kHz WAV
            from config.settings import AUDIO_SAMPLE_RATE
        except Exception:
            AUDIO_SAMPLE_RATE = 24000

        try:
            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(AUDIO_SAMPLE_RATE)
                wf.writeframes(bytes(audio_buffer))
            print(f"Wrote audio response to: {wav_path}")
            # Try to play if sounddevice available
            try:
                import sounddevice as sd
                import numpy as np
                pcm = np.frombuffer(bytes(audio_buffer), dtype='int16')
                audio_float = pcm.astype('float32') / 32767.0
                print("Playing audio response...")
                sd.play(audio_float, samplerate=AUDIO_SAMPLE_RATE)
                sd.wait()
            except Exception as e:
                print(f"Could not play audio: {e}")
        except Exception as e:
            print(f"Failed to write WAV: {e}")

    # Cancel listen task if still running
    try:
        if listen_task and not listen_task.done():
            listen_task.cancel()
            await asyncio.sleep(0.1)
    except Exception:
        pass

    await client.disconnect()
    print("Disconnected")
    return 0


if __name__ == '__main__':
    msg = None
    if len(sys.argv) > 1:
        msg = ' '.join(sys.argv[1:])
    asyncio.run(main(msg))
