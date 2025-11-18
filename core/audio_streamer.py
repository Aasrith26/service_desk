"""
Audio Streamer - Handles microphone capture and speaker playback
Real-time bidirectional audio I/O with queue-based buffering
"""

import asyncio
import numpy as np
from collections import deque
from typing import Optional, Callable
import sounddevice as sd

from config.settings import (
    AUDIO_SAMPLE_RATE, 
    AUDIO_CHUNK_SIZE,
    AUDIO_CHANNELS,
    AUDIO_DTYPE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MIN_SPEECH_DURATION,
    SIMULATE_AUDIO
)
from config.settings import AUDIO_MAX_BUFFER_SECONDS
from utils.logger import get_logger
from utils.audio_utils import calculate_rms, AudioBuffer

logger = get_logger(__name__)


class AudioStreamer:
    """
    Manages microphone input and speaker output streams.
    
    Features:
    - Continuous microphone capture with silence detection
    - Queue-based speaker playback
    - Async/await compatible
    - Configurable silence thresholds
    """
    
    def __init__(self, 
                 on_audio_chunk: Optional[Callable] = None,
                 on_silence_detected: Optional[Callable] = None):
        """
        Initialize audio streamer.
        
        Args:
            on_audio_chunk: Callback when audio chunk received from mic
                           Should accept numpy array of audio samples
            on_silence_detected: Callback when silence is detected
                                Called with silence duration in seconds
        """
        self.on_audio_chunk = on_audio_chunk
        self.on_silence_detected = on_silence_detected
        
        # Streams
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        
        # Buffers and state
        self.output_queue = deque(maxlen=1000)  # Max ~40ms of audio at 24kHz
        self.output_buffer = AudioBuffer(max_size=AUDIO_SAMPLE_RATE * 5)  # 5 seconds
        self.is_streaming = False
        
        # Silence detection state
        self.silence_samples = 0
        self.speech_started = False
        self.speech_start_time = None
        self.silence_start_time = None
    
    async def start(self) -> bool:
        """
        Start microphone and speaker streams.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if SIMULATE_AUDIO:
                logger.warning("⚠️ AUDIO SIMULATION MODE - using generated sine wave instead of real mic")
                self.is_streaming = True
                return True
            
            # Start input stream (microphone)
            logger.info("Starting audio input stream...")
            self.input_stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype=AUDIO_DTYPE,
                blocksize=AUDIO_CHUNK_SIZE,
                latency='low'
            )
            self.input_stream.start()
            logger.info("[OK] Input stream started")
            
            # Start output stream (speaker)
            logger.info("Starting audio output stream...")
            self.output_stream = sd.OutputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='float32',
                blocksize=AUDIO_CHUNK_SIZE,
                latency='low'
            )
            self.output_stream.start()
            logger.info("[OK] Output stream started")
            
            self.is_streaming = True
            return True
        
        except Exception as e:
            logger.error(f"Failed to start audio streams: {e}")
            self.is_streaming = False
            return False
    
    async def stop(self):
        """Stop microphone and speaker streams."""
        self.is_streaming = False
        
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            logger.info("Input stream stopped")
        
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            logger.info("Output stream stopped")
    
    async def capture_audio(self):
        """
        Continuously capture audio from microphone.
        Runs in loop, calling on_audio_chunk callback for each frame.
        
        This should be run as an async task:
        asyncio.create_task(streamer.capture_audio())
        """
        if not self.is_streaming:
            logger.warning("Capture called but streaming not started")
            return
        
        logger.info("Audio capture loop started")
        frame_count = 0
        
        try:
            while self.is_streaming:
                if SIMULATE_AUDIO:
                    # Generate simulated audio (sine wave at 440 Hz)
                    await asyncio.sleep(0.02)  # Simulate frame duration
                    
                    if frame_count % 50 == 0:  # Generate every 50 frames
                        t = np.arange(AUDIO_CHUNK_SIZE) / AUDIO_SAMPLE_RATE
                        audio = (np.sin(2 * np.pi * 440 * t) * 32767 * 0.1).astype('int16')
                        frame_count += 1
                        
                        if self.on_audio_chunk:
                            await self._call_async(self.on_audio_chunk, audio)
                
                else:
                    # Read from microphone
                    try:
                        audio_data, _ = self.input_stream.read(AUDIO_CHUNK_SIZE)
                        audio = (audio_data[:, 0] * 32767).astype('int16')  # Convert to int16
                        
                        # Detect silence
                        await self._process_silence_detection(audio)
                        
                        # Call callback
                        if self.on_audio_chunk:
                            await self._call_async(self.on_audio_chunk, audio)
                        
                        frame_count += 1
                    
                    except sd.PortAudioError as e:
                        logger.error(f"Audio input error: {e}")
                        await asyncio.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
        finally:
            logger.info(f"Audio capture stopped after {frame_count} frames")
    
    async def _process_silence_detection(self, audio: np.ndarray):
        """
        Process audio frame for silence detection.
        
        Args:
            audio: Audio samples
        """
        rms = calculate_rms(audio)
        # Normalized RMS (0.0 - 1.0)
        try:
            rms_norm = rms / 32767.0
        except Exception:
            rms_norm = rms

        # Prefer fraction-based threshold if configured
        try:
            from config.settings import SILENCE_THRESHOLD_FRACTION
            is_silent = rms_norm < SILENCE_THRESHOLD_FRACTION
        except Exception:
            is_silent = rms < SILENCE_THRESHOLD

        logger.debug(f"Chunk RMS={rms:.1f}, norm={rms_norm:.4f}, is_silent={is_silent}")
        
        if is_silent:
            if not self.silence_start_time:
                self.silence_start_time = asyncio.get_event_loop().time()
                logger.info(f"[SILENCE START] silence timer started")
            
            silence_duration = asyncio.get_event_loop().time() - self.silence_start_time
            
            # Check if we've had enough silence to trigger response
            if (self.speech_started and 
                silence_duration >= SILENCE_DURATION):
                
                speech_duration = silence_duration  # Rough estimate
                if speech_duration >= MIN_SPEECH_DURATION:
                    logger.info(f"[SILENCE] Detected {silence_duration:.2f}s of silence. Triggering response.")
                    if self.on_silence_detected:
                        await self._call_async(self.on_silence_detected, silence_duration)
                    
                    self.speech_started = False
                    self.silence_start_time = None
        
        else:  # Speech detected
            if not self.speech_started:
                self.speech_started = True
                self.silence_start_time = None
                # mark when speech began
                try:
                    self.speech_start_time = asyncio.get_event_loop().time()
                except Exception:
                    self.speech_start_time = None
                logger.info(f"[SPEECH] Detected speech (rms={rms:.1f})")
                # play a short audible tick to indicate speech capture started
                try:
                    beep_duration = int(0.06 * AUDIO_SAMPLE_RATE)
                    t = np.arange(beep_duration) / AUDIO_SAMPLE_RATE
                    tick = (np.sin(2 * np.pi * 1200 * t) * 12000).astype('int16')
                    self.output_buffer.write(tick)
                except Exception:
                    pass
    
    def queue_audio_output(self, audio: np.ndarray):
        """
        Queue audio for playback.
        
        Args:
            audio: Audio samples to play
        """
        if not self.is_streaming:
            return
        
        try:
            # Add to buffer
            self.output_buffer.write(audio)
        except Exception as e:
            logger.error(f"Failed to queue audio: {e}")
    
    async def playback_audio(self):
        """
        Continuously play queued audio to speaker.
        
        This should be run as an async task:
        asyncio.create_task(streamer.playback_audio())
        """
        if not self.is_streaming:
            logger.warning("Playback called but streaming not started")
            return
        
        logger.info("Audio playback loop started")
        
        try:
            while self.is_streaming:
                # Read from output buffer
                available = self.output_buffer.available()
                
                if available >= AUDIO_CHUNK_SIZE:
                    audio_chunk = self.output_buffer.read(AUDIO_CHUNK_SIZE)
                    
                    if SIMULATE_AUDIO:
                        # In simulation mode, just sleep to simulate playback
                        await asyncio.sleep(AUDIO_CHUNK_SIZE / AUDIO_SAMPLE_RATE)
                    else:
                        # Write to speaker
                        try:
                            audio_float = audio_chunk.astype('float32') / 32767.0
                            self.output_stream.write(audio_float.reshape(-1, 1))
                        except sd.PortAudioError as e:
                            logger.error(f"Audio output error: {e}")
                else:
                    # Wait for more audio to buffer
                    await asyncio.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error in playback loop: {e}")
        finally:
            logger.info("Audio playback stopped")
    
    async def _call_async(self, callback: Callable, *args, **kwargs):
        """
        Call a callback that might be sync or async.
        
        Args:
            callback: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling callback: {e}")

    def get_audio_devices(self) -> dict:
        """
        Get available audio devices.
        
        Returns:
            Dictionary of available devices
        """
        devices = sd.query_devices()
        return devices


class AudioStreamingEngine:
    """
    High-level engine combining RealtimeClient and AudioStreamer.
    Manages the full bidirectional audio pipeline.
    """
    
    def __init__(self, realtime_client):
        """
        Initialize streaming engine.
        
        Args:
            realtime_client: RealtimeClient instance
        """
        self.realtime_client = realtime_client
        self.streamer = AudioStreamer(
            on_audio_chunk=self._on_audio_chunk,
            on_silence_detected=self._on_silence_detected
        )
        self.is_running = False
        self.current_user_text = ""
        # Silence prompter task
        self._silence_prompt_task = None
        self._silence_prompt_last_prompt = 0
    
    async def _on_audio_chunk(self, audio: np.ndarray):
        """Callback when audio chunk captured from mic."""
        try:
            # Log outgoing audio chunk size
            try:
                logger.debug(f"[AUDIO_CHUNK] captured {len(audio)} samples, sending {audio.nbytes} bytes")
            except Exception:
                pass
            await self.realtime_client.send_audio(audio.tobytes())
        except Exception as e:
            logger.error(f"Error in _on_audio_chunk: {e}")
    
    async def _on_silence_detected(self, duration: float):
        """Callback when silence is detected."""
        logger.info(f"✓ [USER SPEECH ENDED] Silence detected after {duration:.1f}s")
        logger.info(f"🎤 Processing your request... Sending to Azure model")

        # Play a simple beep to confirm speech was heard
        try:
            # Generate a 440Hz beep (0.35 seconds, louder)
            beep_duration = int(0.35 * AUDIO_SAMPLE_RATE)
            t = np.arange(beep_duration) / AUDIO_SAMPLE_RATE
            beep = (np.sin(2 * np.pi * 440 * t) * 16000).astype('int16')
            self.streamer.queue_audio_output(beep)
            logger.info("🔊 [BEEP] Confirmation tone played")
        except Exception as e:
            logger.debug(f"Could not play beep: {e}")
        
        await self.realtime_client.trigger_response(self.current_user_text)

    async def _silence_prompt_loop(self):
        """Background loop: when long continuous silence is detected, prompt user every 3s up to 18s and disconnect.

        Behaviour:
        - Checks streamer's silence_start_time when there is no active speech
        - Every 3 seconds of continuous silence logs a prompt so user knows the system is idle
        - After 18 seconds of continuous silence, stops the engine and disconnects
        """
        try:
            logger.debug("Silence prompter loop started")
            while self.is_running:
                await asyncio.sleep(0.5)

                # Only consider when streamer is active and not currently in a speech segment
                silence_start = getattr(self.streamer, 'silence_start_time', None)
                speech_started = getattr(self.streamer, 'speech_started', False)

                # If there is no silence AND no speech, skip prompting
                if silence_start is None and not speech_started:
                    # reset last prompt counter
                    self._silence_prompt_last_prompt = 0
                    continue

                # If silence_start is None, skip computing elapsed and reset prompt counter
                if silence_start is None:
                    self._silence_prompt_last_prompt = 0
                    continue

                # safe to compute elapsed now
                try:
                    elapsed = asyncio.get_event_loop().time() - silence_start
                except Exception:
                    self._silence_prompt_last_prompt = 0
                    continue

                # compute how many 3-second prompts should have been emitted
                prompt_count = int(elapsed // 3)

                # emit any missed prompts
                while prompt_count > self._silence_prompt_last_prompt and self._silence_prompt_last_prompt * 3 < 18:
                    self._silence_prompt_last_prompt += 1
                    secs = self._silence_prompt_last_prompt * 3
                    # Console + log prompt
                    logger.info(f"🔔 Silence detected for {secs}s — please speak so the model can capture your audio")
                    # also play a short low-volume beep to give audible feedback (non-blocking)
                    try:
                        # short prompt beep (0.2s, louder)
                        beep_duration = int(0.2 * AUDIO_SAMPLE_RATE)
                        t = np.arange(beep_duration) / AUDIO_SAMPLE_RATE
                        beep = (np.sin(2 * np.pi * 600 * t) * 16000).astype('int16')
                        self.streamer.queue_audio_output(beep)
                    except Exception:
                        pass

                    # If we've reached 18s, dismantle connection
                    if secs >= 18:
                        logger.info("⚠️  18s of continuous silence reached — stopping engine and disconnecting")
                        # Stop engine and disconnect gracefully
                        try:
                            await self.stop()
                        except Exception as e:
                            logger.error(f"Error stopping engine after silence timeout: {e}")
                        return

                    # Safety fallback: if the realtime client has accumulated a large
                    # amount of appended audio (e.g. > AUDIO_MAX_BUFFER_SECONDS), force a trigger
                    try:
                        max_bytes = int(AUDIO_MAX_BUFFER_SECONDS * AUDIO_SAMPLE_RATE * 2)
                        appended = getattr(self.realtime_client, '_audio_appended_bytes', 0)
                        if appended >= max_bytes:
                            logger.warning(f"[FORCED COMMIT] Audio buffer exceeded {AUDIO_MAX_BUFFER_SECONDS}s ({appended} bytes) — forcing commit/trigger")
                            try:
                                await self.realtime_client.trigger_response(self.current_user_text)
                            except Exception as e:
                                logger.error(f"Error during forced commit trigger: {e}")
                            # Debounce to avoid repeated forced triggers
                            await asyncio.sleep(1.0)
                    except Exception:
                        pass

                # If user spoke but no silence detected for a while, force a trigger as a fallback
                try:
                    speech_start = getattr(self.streamer, 'speech_start_time', None)
                    if speech_start and not silence_start:
                        elapsed_since_speech = asyncio.get_event_loop().time() - speech_start
                        if elapsed_since_speech >= 5:
                            logger.info(f"[FORCED TRIGGER] No silence detected after {elapsed_since_speech:.1f}s — forcing model trigger")
                            try:
                                await self.realtime_client.trigger_response(self.current_user_text)
                            except Exception as e:
                                logger.error(f"Error during forced trigger: {e}")
                            # avoid spamming forced triggers
                            await asyncio.sleep(1)
                except Exception:
                    pass

        except asyncio.CancelledError:
            logger.debug("Silence prompter loop cancelled")
        except Exception as e:
            logger.error(f"Silence prompter loop error: {e}")
    
    async def _on_model_audio(self, audio_bytes: bytes):
        """Callback when audio received from model."""
        audio = np.frombuffer(audio_bytes, dtype='int16')
        self.streamer.queue_audio_output(audio)
    
    async def start(self) -> bool:
        """Start the full streaming engine."""
        try:
            # Connect to Azure
            if not await self.realtime_client.connect():
                return False
            
            # Set model audio callback
            self.realtime_client.on_audio_received = self._on_model_audio
            
            # Start audio I/O
            if not await self.streamer.start():
                return False
            
            self.is_running = True
            logger.info("[OK] Audio Streaming Engine started")
            # start silence prompter background task
            if not self._silence_prompt_task:
                self._silence_prompt_task = asyncio.create_task(self._silence_prompt_loop())
            return True
        
        except Exception as e:
            logger.error(f"Failed to start streaming engine: {e}")
            return False
    
    async def stop(self):
        """Stop the streaming engine."""
        self.is_running = False
        # cancel silence prompter
        try:
            if self._silence_prompt_task:
                self._silence_prompt_task.cancel()
                self._silence_prompt_task = None
        except Exception:
            pass

        await self.streamer.stop()
        await self.realtime_client.disconnect()
        logger.info("Audio Streaming Engine stopped")
    
    async def run(self):
        """Run the main event loop."""
        try:
            # Create concurrent tasks
            tasks = [
                self.streamer.capture_audio(),
                self.streamer.playback_audio(),
                self.realtime_client.listen()
            ]
            
            await asyncio.gather(*tasks)
        
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
        finally:
            await self.stop()
