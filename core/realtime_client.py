"""
Azure GPT-Realtime WebSocket Client
Handles bidirectional audio streaming with Azure OpenAI's GPT-Realtime API
FIXED: Proper callback chain integration for audio playback
"""

import asyncio
import json
import base64
from typing import Callable, Optional, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol

from config.settings import (
    AZURE_REALTIME_ENDPOINT, 
    AZURE_API_KEY, 
    AUDIO_SAMPLE_RATE, 
    SYSTEM_PROMPT_TEMPLATE,
    WEBSOCKET_TIMEOUT,
    WEBSOCKET_RECONNECT_ATTEMPTS,
    WEBSOCKET_RECONNECT_DELAY
)
from utils.logger import get_logger
from utils.audio_utils import pcm_to_base64, base64_to_pcm
from core.context_retriever import ContextRetriever

logger = get_logger(__name__)


class RealtimeClient:
    """
    Client for Azure GPT-Realtime API with bidirectional audio streaming.
    
    Handles:
    - WebSocket connection management
    - Audio event streaming (input_audio_buffer.append)
    - Response generation (response.create)
    - Audio response reception (response.audio.delta)
    - Error handling and reconnection
    """
    
    def __init__(self, on_audio_received: Optional[Callable] = None, on_text_received: Optional[Callable] = None):
        """
        Initialize Realtime client.
        
        Args:
            on_audio_received: Callback function called when audio is received from model
                              Should accept bytes of audio data
            on_text_received: Callback function called when text is received from model
        """
        self.ws: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.on_audio_received = on_audio_received
        self.on_text_received = on_text_received
        self.context_retriever = ContextRetriever()
        self.last_user_input = ""

        # Session tracking
        self.session_id = None
        self.response_count = 0
        self._audio_appended_bytes = 0
        self._last_response_had_text = False
        self._text_followup_requested_for = None
    
    async def connect(self) -> bool:
        """
        Connect to Azure GPT-Realtime WebSocket endpoint.
        
        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(WEBSOCKET_RECONNECT_ATTEMPTS):
            try:
                logger.info(f"Connecting to Azure GPT-Realtime... (attempt {attempt + 1})")
                
                headers = {
                    "api-key": AZURE_API_KEY,
                }
                
                self.ws = await asyncio.wait_for(
                    websockets.connect(
                        AZURE_REALTIME_ENDPOINT,
                        additional_headers=headers,
                        subprotocols=["realtime"]
                    ),
                    timeout=WEBSOCKET_TIMEOUT
                )
                
                self.is_connected = True
                logger.info("[OK] Connected to Azure GPT-Realtime API")
                
                await self._initialize_session()
                return True
            
            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout (attempt {attempt + 1}/{WEBSOCKET_RECONNECT_ATTEMPTS})")
            except Exception as e:
                logger.error(f"Connection failed: {e} (attempt {attempt + 1}/{WEBSOCKET_RECONNECT_ATTEMPTS})")
            
            if attempt < WEBSOCKET_RECONNECT_ATTEMPTS - 1:
                await asyncio.sleep(WEBSOCKET_RECONNECT_DELAY)
        
        logger.error("Failed to connect after all retry attempts")
        self.is_connected = False
        return False
    
    async def _initialize_session(self):
        """Initialize the realtime session with configuration."""
        try:
            logger.info("Waiting for session.created event...")
            
            try:
                response = await asyncio.wait_for(self.ws.recv(), timeout=5)
                data = json.loads(response)
                logger.debug(f"Received: {data.get('type', 'unknown')}")
                
                if data.get('type') == 'session.created':
                    self.session_id = data.get('session', {}).get('id')
                    logger.info(f"Session created: {self.session_id}")
                    
                    session_config = {
                        "type": "session.update",
                        "session": {
                            "modalities": ["text", "audio"],
                            "instructions": "You are a helpful multilingual clinic assistant.",
                            "voice": "alloy",
                            "input_audio_format": "pcm16",
                            "output_audio_format": "pcm16",
                            "temperature": 0.6
                        }
                    }
                    
                    await self.ws.send(json.dumps(session_config))
                    logger.info("Session configured")
            
            except asyncio.TimeoutError:
                logger.warning("No session.created event received, proceeding anyway")
        
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise
    
    async def send_audio(self, audio_data: bytes):
        """Send raw PCM audio bytes to the realtime WebSocket as base64."""
        if not self.is_connected or not self.ws:
            logger.warning("Not connected, cannot send audio")
            return

        try:
            audio_b64 = pcm_to_base64(audio_data)
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            await self.ws.send(json.dumps(event))
            try:
                self._audio_appended_bytes += len(audio_data)
            except Exception:
                self._audio_appended_bytes = self._audio_appended_bytes if hasattr(self, '_audio_appended_bytes') else 0

            logger.info(f"[AUDIO SENT] Sent {len(audio_data)} bytes (base64 {len(audio_b64)} chars) to realtime endpoint; total_buffered_bytes={self._audio_appended_bytes}")
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
    
    async def trigger_response(self, user_text: str = "", modalities: Optional[list] = None):
        """
        Trigger the model to generate a response.
        
        Args:
            user_text: Optional user transcription text for context
            modalities: List of modalities for response
        """
        if not self.is_connected or not self.ws:
            logger.warning("Not connected, cannot trigger response")
            return
        
        try:
            logger.info("[TRIGGER] Sending request to model...")
            self.last_user_input = user_text
            
            context = self.context_retriever.get_context(user_text)
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
            
            try:
                min_bytes = int(0.1 * AUDIO_SAMPLE_RATE * 2)
                if getattr(self, '_audio_appended_bytes', 0) >= min_bytes:
                    commit_event = {"type": "input_audio_buffer.commit"}
                    await self.ws.send(json.dumps(commit_event))
                    logger.info("[AUDIO COMMIT] Sent input_audio_buffer.commit to server")
                    try:
                        self._audio_appended_bytes = 0
                    except Exception:
                        pass
                else:
                    logger.info(f"[AUDIO COMMIT] Skipping commit - only {getattr(self, '_audio_appended_bytes', 0)} bytes buffered (<{min_bytes})")
            except Exception as e:
                logger.debug(f"[TRIGGER] Failed to send commit: {e}")

            if modalities is None:
                modalities = ["audio", "text"]

            response_event = {
                "type": "response.create",
                "response": {
                    "modalities": modalities,
                    "instructions": system_prompt,
                    "voice": "alloy",
                    "temperature": 0.6
                }
            }

            await self.ws.send(json.dumps(response_event))
            logger.debug("Sent response.create event")
            self.response_count += 1
            logger.info(f"[TRIGGER] Response #{self.response_count} sent to server. Waiting for model response...")
        
        except Exception as e:
            logger.error(f"[TRIGGER] Failed to trigger response: {e}")
            import traceback
            traceback.print_exc()
    
    async def listen(self):
        """
        Listen for incoming messages from the model.
        Processes audio and other events.
        """
        if not self.is_connected or not self.ws:
            logger.warning("Not connected, cannot listen")
            return
        logger.info("[LISTEN] Starting message loop (recv timeout=5s)...")
        try:
            while self.is_connected and self.ws:
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    logger.debug("[LISTEN] recv timeout — still waiting for messages...")
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("[LISTEN] WebSocket connection closed")
                    self.is_connected = False
                    break

                try:
                    try:
                        logger.debug(f"[RAW MESSAGE] {message[:100]}...")
                    except Exception:
                        pass
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"[LISTEN] Error handling message: {e}")

        except Exception as e:
            logger.error(f"[LISTEN] Unexpected error in listen loop: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: str):
        """
        Process incoming WebSocket message.
        
        Args:
            message: JSON message from Azure GPT-Realtime API
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            logger.debug(f"[MESSAGE] Received: {msg_type}")
            
            # Handle different message types
            if msg_type == 'response.audio.delta':
                # Receive audio chunk from model
                audio_b64 = data.get('delta')
                if audio_b64:
                    audio_bytes = base64_to_pcm(audio_b64)
                    logger.info(f"[MODEL AUDIO] Received {len(audio_bytes)} bytes from model")
                    if self.on_audio_received:
                        await self._call_async(self.on_audio_received, audio_bytes)
            
            elif msg_type == 'response.text.delta':
                # Receive text chunk from model
                text = data.get('delta', '')
                logger.debug(f"Model text: {text}")
                try:
                    self._last_response_had_text = True
                except Exception:
                    pass
                if self.on_text_received:
                    await self._call_async(self.on_text_received, text, partial=True)
            
            elif msg_type == 'response.text.done':
                # Full text response received
                text = data.get('text', '')
                logger.info(f"Response complete: {text}")
                try:
                    self._last_response_had_text = True
                except Exception:
                    pass
                if self.on_text_received:
                    await self._call_async(self.on_text_received, text, partial=False)
            
            elif msg_type == 'input_audio_buffer.committed':
                # Acknowledge: audio buffer committed for processing
                logger.debug("Audio buffer committed")
            
            elif msg_type == 'conversation.item.created':
                # New conversation item created
                item_type = data.get('item', {}).get('type')
                logger.debug(f"Conversation item created: {item_type}")
            
            elif msg_type == 'response.done':
                # Response generation complete
                status = data.get('response', {}).get('status')
                logger.info(f"Response generation complete: {status}")
                try:
                    current_resp = self.response_count
                    if not self._last_response_had_text and self._text_followup_requested_for != current_resp:
                        logger.info("[FOLLOWUP] No text received for response — requesting text-only follow-up")
                        self._text_followup_requested_for = current_resp
                        followup_event = {
                            "type": "response.create",
                            "response": {
                                "modalities": ["text"],
                                "instructions": "Please provide a concise text transcript of the last audio response.",
                                "temperature": 0.0
                            }
                        }
                        await self.ws.send(json.dumps(followup_event))
                        logger.info("[FOLLOWUP] Text-only follow-up sent")
                except Exception as e:
                    logger.debug(f"Failed to send text follow-up: {e}")
                finally:
                    try:
                        self._last_response_had_text = False
                    except Exception:
                        pass
            
            elif msg_type == 'error':
                # Error message from API
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"API Error: {error_msg}")
            
            else:
                # Log other message types for debugging
                logger.debug(f"Received message type: {msg_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _call_async(self, callback: Callable, *args, **kwargs):
        """
        Call a callback that might be sync or async.
        
        Args:
            callback: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            logger.info("Disconnected from Azure GPT-Realtime API")
    
    async def send_message(self, text: str):
        """
        Send a text message to the model.
        
        Args:
            text: Text message to send
        """
        if not self.is_connected or not self.ws:
            logger.warning("Not connected, cannot send message")
            return
        
        try:
            event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            
            await self.ws.send(json.dumps(event))
            logger.debug(f"Sent text message: {text}")

            await self.trigger_response(text, modalities=["text"])
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
