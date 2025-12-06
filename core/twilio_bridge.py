import json
import logging
import base64
import numpy as np
import scipy.signal
from fastapi import WebSocket

from core.realtime_client import RealtimeClient

logger = logging.getLogger(__name__)

# --- AUDIO HELPERS (Shared Logic) ---
# reusing the same efficient conversion as Exotel since formats are identical (Mulaw 8k)

from utils import g711

def mulaw_to_pcm16(mulaw_bytes):
    try:
        # 1. Decode Mu-law (8kHz)
        pcm_8k = g711.ulaw2lin(mulaw_bytes)
        # 2. Resample 8kHz -> 24kHz
        return g711.resample_up_3x(pcm_8k)
    except Exception as e:
        logger.error(f"Decode Error: {e}")
        return b'\x00' * 320

def pcm16_to_mulaw(pcm16_bytes):
    try:
        # 1. Resample 24kHz -> 8kHz
        pcm_8k = g711.resample_down_3x(pcm16_bytes)
        # 2. Encode Mu-law
        return g711.lin2ulaw(pcm_8k)
    except Exception as e:
        logger.error(f"Encode Error: {e}")
        return b''

import asyncio

# ... imports ...

class TwilioCallHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.azure_client = None
        self.stream_sid = None
        self.is_active = False
        self.call_sid = None
        self.listen_task = None

    async def start(self):
        self.is_active = True
        self.azure_client = RealtimeClient(
            on_audio_received=self.handle_azure_audio,
            on_text_received=lambda text: logger.info(f"Azure: {text}"),
            on_response_done=lambda: logger.info("Response Done"),
            on_call_ended=self.handle_call_ended,
            on_interruption=self.handle_interruption
        )
        if await self.azure_client.connect():
            # Start listening loop in background
            self.listen_task = asyncio.create_task(self.azure_client.listen())
            logger.info("Azure Listener Started")

    async def handle_twilio_message(self, message: str):
        try:
            data = json.loads(message)
            event = data.get('event')

            if event == 'start':
                self.stream_sid = data['start']['streamSid']
                self.call_sid = data['start']['callSid']
                logger.info(f"Twilio Stream Started: {self.stream_sid}")
            
            elif event == 'media':
                # Twilio sends base64 mulaw payload
                payload = data['media']['payload']
                chunk = base64.b64decode(payload)
                
                # Transcode and send to Azure
                pcm24 = mulaw_to_pcm16(chunk)
                
                # DEBUG: Check if audio is silent
                # Simple RMS check (approx) -> using numpy directly to avoid circular import if needed
                # But we can just use np here.
                if np.random.random() < 0.05: # Log 5% of packets
                    y = np.frombuffer(pcm24, dtype=np.int16)
                    rms = np.sqrt(np.mean(y.astype(float)**2))
                    logger.info(f"Mic Level (RMS): {rms:.2f} (Zeros? {np.all(y==0)})")

                await self.azure_client.send_audio(pcm24)
            
            elif event == 'stop':
                logger.info("Twilio Stream Stopped")
                await self.close()

        except Exception as e:
            logger.error(f"Twilio Handler Error: {e}")

    async def handle_azure_audio(self, pcm_24k_chunk: bytes):
        if not self.is_active or not self.stream_sid: return
        
        # Transcode PCM24 -> Mulaw
        chunk_mulaw = pcm16_to_mulaw(pcm_24k_chunk)
        if not chunk_mulaw: return
        
        # Send to Twilio
        payload = base64.b64encode(chunk_mulaw).decode('utf-8')
        
        msg = {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {
                "payload": payload
            }
        }
        await self.websocket.send_text(json.dumps(msg))

    async def handle_call_ended(self):
        """Callback for when AI ends the call"""
        logger.info("AI requested end of call. Waiting for audio to drain...")
        # Give 2 seconds for the "Goodbye" audio to play out before cutting connection
        await asyncio.sleep(2.0)
        logger.info("Hanging up now.")
        await self.close()

    async def handle_interruption(self):
        """Callback for when user interrupts - Clear Twilio Buffer"""
        logger.info("Clearing Twilio Buffer...")
        if self.stream_sid:
            msg = { 
                "event": "clear",
                "streamSid": self.stream_sid,
            }
            await self.websocket.send_text(json.dumps(msg))

    async def close(self):
        self.is_active = False
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        if self.azure_client:
            await self.azure_client.disconnect()
