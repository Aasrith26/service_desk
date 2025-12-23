import json
import logging
import base64
import asyncio
from fastapi import WebSocket
from core.realtime_client import RealtimeClient
from utils import g711

logger = logging.getLogger(__name__)

def pcm24k_to_pcm8k(pcm24k_bytes):
    """Convert 24kHz PCM16 bytes -> 8kHz PCM16 bytes (Exotel format)"""
    try:
        return g711.resample_down_3x(pcm24k_bytes)
    except Exception as e:
        logger.error(f"Resample Error: {e}")
        return b''

def pcm8k_to_pcm24k(pcm8k_bytes):
    """Convert 8kHz PCM16 bytes -> 24kHz PCM16 bytes (Azure format)"""
    try:
        return g711.resample_up_3x(pcm8k_bytes)
    except Exception as e:
        logger.error(f"Resample Error: {e}")
        return b'\x00' * 320

class ExotelCallHandler:
    def __init__(self, websocket: WebSocket, caller_phone: str = None):
        self.websocket = websocket
        self.caller_phone = caller_phone or "Unknown"
        self.call_sid = None
        self.stream_sid = None
        self.azure_client = None
        self.is_active = False
        self.listen_task = None
        # Audio buffer for meeting Exotel's minimum chunk size (3200 bytes)
        self.audio_buffer = b''
        self.MIN_CHUNK_SIZE = 3200  # 100ms at 8kHz 16-bit mono

    async def start(self):
        self.is_active = True
        self.azure_client = RealtimeClient(
            caller_phone=self.caller_phone,  # Pass caller phone from Exotel
            on_audio_received=self.handle_ai_audio,
            on_text_received=lambda text: logger.info(f"AI: {text.encode('ascii', 'replace').decode('ascii') if text else ''}"),
            on_response_done=self._on_response_done,
            on_call_ended=self.handle_call_ended,
            on_interruption=self.handle_interruption
        )
        
        if await self.azure_client.connect():
            self.listen_task = asyncio.create_task(self.azure_client.listen())
            logger.info("AI Client Connected")

    async def _on_response_done(self):
        """Called when AI finishes a response - flush any remaining audio"""
        logger.info("Response Done - flushing audio buffer")
        if self.audio_buffer:
            await self._send_to_exotel(self.audio_buffer)
            self.audio_buffer = b''

    async def handle_exotel_message(self, message: str):
        """Handle WebSocket messages from Exotel."""
        try:
            data = json.loads(message)
            event = data.get('event')

            if event == 'connected':
                logger.info("Exotel: WebSocket Connected")

            elif event == 'start':
                # Debug: Log full start event to understand Exotel's data structure
                logger.info(f"Exotel START event data: {data}")
                
                self.stream_sid = data.get('stream_sid', 'unknown_stream')
                self.call_sid = data.get('call_sid', 'unknown_call')
                
                # Exotel sends caller phone in data['start']['from']
                start_data = data.get('start', {})
                self.caller_phone = (
                    start_data.get('from') or  # Primary: from start.from
                    self.caller_phone or  # Keep URL-provided phone if available
                    "Unknown"
                )
                logger.info(f"Exotel Stream Started: {self.stream_sid} | Caller: {self.caller_phone}")
                
                # Update azure_client with actual caller phone
                if self.azure_client:
                    self.azure_client.caller_phone = self.caller_phone
                    logger.info(f"Updated RealtimeClient caller_phone: {self.caller_phone}")
                
                # Now that we have stream_sid, trigger the greeting
                await self._trigger_greeting()

            elif event == 'media':
                # Exotel sends 8kHz PCM16, convert to 24kHz for Azure
                payload = data['media']['payload']
                chunk = base64.b64decode(payload)
                pcm24 = pcm8k_to_pcm24k(chunk)
                if self.azure_client:
                    await self.azure_client.send_audio(pcm24)

            elif event == 'stop':
                logger.info("Exotel Stream Stopped")
                await self.close()

        except Exception as e:
            logger.error(f"Exotel Handler Error: {e}")

    async def handle_ai_audio(self, pcm_24k_chunk: bytes):
        """Receive audio from AI (24kHz PCM16), resample to 8kHz PCM16, buffer and send."""
        if not self.is_active:
            return

        # Resample 24kHz -> 8kHz
        chunk_8k = pcm24k_to_pcm8k(pcm_24k_chunk)
        if not chunk_8k:
            return

        # Add to buffer
        self.audio_buffer += chunk_8k

        # Send when we have at least MIN_CHUNK_SIZE bytes
        while len(self.audio_buffer) >= self.MIN_CHUNK_SIZE:
            # Take exactly MIN_CHUNK_SIZE bytes (which is a multiple of 320)
            to_send = self.audio_buffer[:self.MIN_CHUNK_SIZE]
            self.audio_buffer = self.audio_buffer[self.MIN_CHUNK_SIZE:]
            await self._send_to_exotel(to_send)

    async def _send_to_exotel(self, audio_bytes):
        """Send audio chunk to Exotel."""
        if not self.is_active or not audio_bytes:
            return
            
        # Ensure chunk is multiple of 320 bytes
        remainder = len(audio_bytes) % 320
        if remainder != 0:
            # Pad to next multiple of 320
            audio_bytes += b'\x00' * (320 - remainder)
        
        logger.info(f">>> SENDING {len(audio_bytes)} bytes to Exotel (PCM16 8kHz)")
        payload = base64.b64encode(audio_bytes).decode('utf-8')
        
        msg = {
            "event": "media",
            "stream_sid": self.stream_sid,
            "media": {
                "payload": payload
            }
        }
        try:
            await self.websocket.send_text(json.dumps(msg))
        except Exception as e:
            logger.error(f"Error sending to Exotel: {e}")

    async def handle_interruption(self):
        """Clear Exotel's audio buffer if user interrupts."""
        logger.info("Clearing Exotel Buffer...")
        self.audio_buffer = b''  # Clear our buffer too
        msg = {
            "event": "clear",
            "stream_sid": self.stream_sid
        }
        await self.websocket.send_text(json.dumps(msg))

    async def handle_call_ended(self):
        """AI requested to end the call."""
        logger.info("AI requested hangup. Waiting for audio to drain...")
        await asyncio.sleep(2.0)
        await self.close()

    async def close(self):
        self.is_active = False
        if self.listen_task:
            self.listen_task.cancel()
        
        try:
            await self.websocket.close()
            logger.info("Exotel WebSocket Closed")
        except:
            pass
        
        if self.azure_client:
            await self.azure_client.disconnect()

    async def _trigger_greeting(self):
        """Force AI to speak first with a greeting (within Exotel's 10-sec timeout)."""
        if self.azure_client and self.azure_client.ws:
            msg = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Call connected. Greet the caller warmly: 'Namaste! Health Plus Clinic. Ela help cheyagalanu?'"
                        }
                    ]
                }
            }
            await self.azure_client.ws.send(json.dumps(msg))
            await self.azure_client.ws.send(json.dumps({"type": "response.create"}))
            logger.info("Greeting triggered")
