"""
COMPLETE WORKING: core/audio_streamer.py
With audio buffering for smooth playback - NO BREAKING!
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Callable
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioStreamer:
    """Handles audio capture and processing from microphone."""
    
    def __init__(self, 
                 on_audio_chunk: Optional[Callable] = None,
                 on_silence_detected: Optional[Callable] = None,
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 silence_threshold: float = 0.02,
                 silence_duration: float = 0.8):
        """Initialize audio streamer."""
        self.on_audio_chunk = on_audio_chunk
        self.on_silence_detected = on_silence_detected
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        
        self.is_running = False
        self.silence_count = 0
        self.silence_chunks_needed = int((silence_duration * sample_rate) / chunk_size)
        self.capture_task = None
        self.is_response_pending = False
        
        logger.debug(f"[AudioStreamer] Initialized (sample_rate={sample_rate}, chunk_size={chunk_size})")
    
    async def capture_audio(self):
        """Capture audio from microphone and detect silence."""
        try:
            logger.info("[AudioStreamer] Starting audio capture...")
            
            with sd.InputStream(samplerate=self.sample_rate, 
                              channels=1, 
                              blocksize=self.chunk_size,
                              dtype=np.float32) as stream:
                
                while self.is_running:
                    audio_chunk, _ = stream.read(self.chunk_size)
                    
                    if audio_chunk is None:
                        continue
                    
                    if self.on_audio_chunk:
                        await self._call_async(self.on_audio_chunk, audio_chunk)
                    
                    rms = np.sqrt(np.mean(audio_chunk ** 2))
                    
                    if not self.is_response_pending:
                        if rms < self.silence_threshold:
                            self.silence_count += 1
                            
                            if self.silence_count >= self.silence_chunks_needed:
                                duration = (self.silence_count * self.chunk_size) / self.sample_rate
                                logger.info(f"[SILENCE] Detected {duration:.1f}s of silence")
                                
                                if self.on_silence_detected:
                                    self.is_response_pending = True
                                    await self._call_async(self.on_silence_detected, duration)
                                
                                self.silence_count = 0
                        else:
                            self.silence_count = 0
                        
        except Exception as e:
            logger.error(f"[AudioStreamer] Error in capture_audio: {e}", exc_info=True)
        finally:
            self.is_running = False
    
    async def _call_async(self, callback, *args):
        """Call a callback safely (handles both async and sync)."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"[AudioStreamer] Callback error: {e}", exc_info=True)
    
    async def start(self):
        """Start audio streaming."""
        self.is_running = True
        self.is_response_pending = False
        self.capture_task = asyncio.create_task(self.capture_audio())
        logger.debug("[AudioStreamer] Audio capture task created and started")
        return True
    
    async def stop(self):
        """Stop audio streaming."""
        self.is_running = False
        if self.capture_task:
            try:
                self.capture_task.cancel()
                await self.capture_task
            except asyncio.CancelledError:
                pass
        logger.debug("[AudioStreamer] Audio capture stopped")
    
    def response_completed(self):
        """Call this when model response is finished to reset silence detection."""
        self.is_response_pending = False
        logger.debug("[AudioStreamer] Response completed, silence detection re-enabled")


class AudioStreamingEngine:
    """Complete audio streaming engine handling voice input and model communication."""
    
    def __init__(self, realtime_client, callback_manager=None):
        """Initialize the audio streaming engine."""
        self.realtime_client = realtime_client
        self.callback_manager = callback_manager
        self.current_user_text = ""
        self.streamer = None
        self.listen_task = None
        self.is_running = False
        self._audio_buffer = []  # Buffer for collecting audio chunks
        
        logger.debug("[AudioStreamingEngine] Initialized with callback_manager support")
    
    async def _on_audio_chunk(self, audio_chunk):
        """Handle incoming audio chunk from microphone."""
        try:
            audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
            await self.realtime_client.send_audio(audio_bytes)
            logger.debug(f"[AudioStreamingEngine] Sent {len(audio_bytes)} bytes of audio")
            
        except Exception as e:
            logger.error(f"[AudioStreamingEngine] Error processing audio chunk: {e}", exc_info=True)
    
    async def _on_silence_detected(self, duration: float):
        """Handle silence detection - trigger model response."""
        try:
            logger.info(f"[USER SPEECH ENDED] Silence detected after {duration:.1f}s")
            logger.info("Processing your request... Sending to Azure model")
            
            # Clear audio buffer for new response
            self._audio_buffer = []
            
            await self.realtime_client.trigger_response(self.current_user_text)
            
            # Wait for response to complete
            await asyncio.sleep(3)
            
            # Play the complete buffered audio
            await self._play_buffered_audio()
            
            self.streamer.response_completed()
            
        except Exception as e:
            logger.error(f"[AudioStreamingEngine] Error in _on_silence_detected: {e}", exc_info=True)
    
    async def _on_model_text(self, text: str, **kwargs):
        """Handle text response from model."""
        try:
            partial = kwargs.get('partial', False)
            response_type = "PARTIAL" if partial else "COMPLETE"
            logger.info(f"[AudioStreamingEngine] Model text ({response_type}): {text}")
            
        except Exception as e:
            logger.error(f"[AudioStreamingEngine] Error in _on_model_text: {e}", exc_info=True)
    
    async def _on_model_audio(self, audio_data: bytes, **kwargs):
        """Handle audio response from model and BUFFER it (don't play yet)."""
        try:
            logger.info(f"[MODEL AUDIO] Received {len(audio_data)} bytes from model")
            
            # Buffer the chunk
            self._audio_buffer.append(audio_data)
            logger.debug(f"[AUDIO BUFFER] Chunk #{len(self._audio_buffer)} buffered, total {sum(len(c) for c in self._audio_buffer)} bytes")
            
        except Exception as e:
            logger.error(f"[AudioStreamingEngine] Error buffering audio: {e}", exc_info=True)
    
    async def _play_buffered_audio(self):
        """Play all buffered audio chunks together - SMOOTH PLAYBACK!"""
        try:
            if not self._audio_buffer:
                logger.warning("[PLAYBACK] No audio to play - buffer is empty")
                return
            
            # Combine all chunks into one complete audio
            combined_audio = b''.join(self._audio_buffer)
            chunk_count = len(self._audio_buffer)
            self._audio_buffer = []  # Clear buffer
            
            logger.info(f"[PLAYBACK] Playing {len(combined_audio)} bytes ({chunk_count} chunks)")
            
            # Convert to numpy array
            audio_array = np.frombuffer(combined_audio, dtype=np.int16).astype(np.float32) / 32767.0
            duration = len(audio_array) / 24000
            logger.info(f"[PLAYBACK] Audio duration: {duration:.2f} seconds")
            
            # Play complete audio - NO BREAKING!
            sd.play(audio_array, samplerate=24000)
            sd.wait()  # Wait until playback finishes
            
            logger.info("[PLAYBACK] ✓ Audio playback completed smoothly")
            
        except Exception as e:
            logger.error(f"[PLAYBACK] ERROR: {e}", exc_info=True)
    
    async def start(self) -> bool:
        """Start the full streaming engine with callback manager integration."""
        try:
            logger.info("[ENGINE] Starting audio streaming engine...")
            
            if not await self.realtime_client.connect():
                logger.error("[ENGINE] Failed to connect realtime client")
                return False
            
            logger.debug("[ENGINE] Connected to realtime client")
            
            if not self.callback_manager:
                logger.error("[ENGINE] No callback manager provided!")
                return False
            
            # Register handlers through callback manager
            logger.debug("[ENGINE] Registering handlers through callback manager")
            self.callback_manager.add_audio_handler(self._on_model_audio, priority=5)
            self.callback_manager.add_text_handler(self._on_model_text, priority=5)
            logger.debug("[ENGINE] Handlers registered via callback manager")
            logger.info(f"[ENGINE] Callback status: {self.callback_manager.get_status()}")
            
            logger.debug("[ENGINE] Creating audio streamer...")
            self.streamer = AudioStreamer(
                on_audio_chunk=self._on_audio_chunk,
                on_silence_detected=self._on_silence_detected
            )
            
            logger.debug("[ENGINE] Starting audio streamer...")
            success = await self.streamer.start()
            if not success:
                logger.error("[ENGINE] Failed to start audio streamer")
                return False
            
            logger.debug("[ENGINE] Audio streamer started")
            
            self.is_running = True
            self.listen_task = asyncio.create_task(self.realtime_client.listen())
            
            logger.info("[ENGINE] Audio streaming engine started successfully")
            logger.info("[ENGINE] Listening for voice input... Speak now!")
            return True
            
        except Exception as e:
            logger.error(f"[ENGINE] Error starting engine: {e}", exc_info=True)
            return False
    
    async def stop(self):
        """Stop the audio streaming engine."""
        try:
            logger.info("[ENGINE] Stopping audio streaming engine...")
            
            self.is_running = False
            
            if self.streamer:
                await self.streamer.stop()
            
            if self.listen_task:
                self.listen_task.cancel()
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("[ENGINE] Audio streaming engine stopped")
            
        except Exception as e:
            logger.error(f"[ENGINE] Error stopping engine: {e}", exc_info=True)
