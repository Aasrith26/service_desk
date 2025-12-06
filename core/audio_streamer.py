"""
FINAL FIX: core/audio_streamer.py
- CONFIG: Set interruption_threshold = 0.012 (User Verified).
- FIXED: Audio Format Bug (Converts Float32 -> Int16). The model will hear you now.
- KEEPS: Smart Gain & Interruption logic.
- IMPROVED: Uses OutputStream for smooth playback.
- UPDATED: Noise Gate to 0.02 to block background noise.
"""

import asyncio
import logging
import threading
import numpy as np
import sounddevice as sd
import time

logger = logging.getLogger(__name__)

class AudioStreamer:
    def __init__(self, on_audio_chunk=None, on_silence_detected=None, on_interruption=None):
        self.on_audio_chunk = on_audio_chunk
        self.on_silence_detected = on_silence_detected
        self.on_interruption = on_interruption
        
        # AUDIO SETTINGS
        self.sample_rate = 24000 
        self.chunk_size = 1024
        
        # THRESHOLDS (User Tuned)
        self.noise_floor = 0.003       # Lowered - 0.02 was blocking all audio
        self.silence_threshold = 0.01  # Silence below this
        self.interruption_threshold = 0.012 # Lowered for better sensitivity
        
        self.is_running = False
        self.is_playing = False
        self.silence_counter = 0
        self.speech_counter = 0
        self.user_has_spoken = False
        
        self.queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.input_thread = None

    def _capture_loop(self):
        """Hardware thread: Captures audio."""
        with sd.InputStream(samplerate=self.sample_rate, channels=1, blocksize=self.chunk_size, dtype=np.float32) as stream:
            while self.is_running:
                chunk, _ = stream.read(self.chunk_size)
                rms = np.sqrt(np.mean(chunk**2))
                
                # Debug: Visual RMS Meter
                # print(f"RMS: {rms:.5f} | {'VN' if rms > self.noise_floor else '..'} ", end="\r")

                # 1. INTERRUPTION (Hardware Kill)
                if self.is_playing:
                    if rms > self.interruption_threshold:
                        self.speech_counter += 1
                        # 3 chunks = ~60ms confirmation
                        if self.speech_counter >= 3:
                            sd.stop() 
                            self.is_playing = False
                            self.speech_counter = 0
                            print(f"⚡ INTERRUPT (RMS: {rms:.4f})")
                            self.loop.call_soon_threadsafe(
                                asyncio.create_task, 
                                self._safe_callback(self.on_interruption)
                            )
                    else:
                        self.speech_counter = 0
                    continue 

                # 2. PROCESSING (Raw Audio -> Queue)
                self.loop.call_soon_threadsafe(self.queue.put_nowait, (chunk.copy(), rms))

    async def _process_queue(self):
        """Async Logic: Converts to Int16 and Sends to Server."""
        counter = 0
        while self.is_running:
            chunk_float, rms = await self.queue.get()
            counter += 1

            # 1. Convert to PCM16
            chunk_int16 = (chunk_float * 32767).astype(np.int16).tobytes()

            # 2. NOISE GATE / SILENCE INJECTION
            is_silence = False
            if rms < self.noise_floor: 
                chunk_int16 = b'\x00' * len(chunk_int16)
                is_silence = True
            
            # Visual Feedback (DISABLED - for diagnostics only)
            # if counter % 25 == 0:
            #     status = "🔇 SILENCE" if is_silence else "🔊 AUDIO"
            #     print(f"[VAD] {status} | RMS: {rms:.4f} | Threshold: {self.noise_floor}", flush=True)

            # 3. Send to Server
            if self.on_audio_chunk: 
                await self.on_audio_chunk(chunk_int16)

    async def _safe_callback(self, cb):
        if cb: await cb()

    async def start(self):
        self.is_running = True
        self.input_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.input_thread.start()
        asyncio.create_task(self._process_queue())

    async def stop(self):
        self.is_running = False
        if self.input_thread: self.input_thread.join(1.0)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if playing: 
            self.speech_counter = 0

class AudioStreamingEngine:
    def __init__(self, client, manager=None):
        self.client = client
        self.manager = manager
        self.streamer = None
        self.output_stream = None
        self.playback_queue = asyncio.Queue()
        self.is_playing = False
        
        # Metrics
        self.metrics = {
            "sent_chunks": 0,
            "received_chunks": 0,
            "received_bytes": 0
        }

    async def start(self):
        # Start Playback Loop
        asyncio.create_task(self._playback_loop())
        
        while True:
            if await self.client.connect():
                if self.manager:
                    self.manager.add_audio_handler(self._on_audio, priority=5)
                    self.manager.add_response_done_handler(self._on_done, priority=5)
                
                self.streamer = AudioStreamer(
                    on_audio_chunk=self._on_input_audio,
                    on_interruption=self._on_interrupt
                )
                await self.streamer.start()
                await self.client.listen()
                await self.streamer.stop()
            
            print("⚠️ Reconnecting...")
            await asyncio.sleep(2)

    async def _playback_loop(self):
        """Continuous playback loop using OutputStream."""
        # Create OutputStream
        # Blocksize=512 (approx 21ms) for low latency
        with sd.OutputStream(samplerate=24000, channels=1, dtype='float32', blocksize=512) as stream:
            while True:
                chunk = await self.playback_queue.get()
                stream.write(chunk)

    async def stop(self):
        if self.streamer: await self.streamer.stop()
        await self.client.disconnect()

    async def _on_interrupt(self):
        # Local Interruption detected (User spoke while assistant was talking)
        # 1. Stop Playback immediately
        while not self.playback_queue.empty():
            try: self.playback_queue.get_nowait()
            except: pass
        if self.streamer: self.streamer.set_playing(False)
        
        # 2. Tell Server to STOP generating response
        await self.client.cancel_response()

    async def _on_input_audio(self, chunk_int16):
        self.metrics["sent_chunks"] += 1
        await self.client.send_audio(chunk_int16)

    async def _on_audio(self, data, **kwargs):
        """
        LOWER LATENCY: Push chunks to playback queue.
        """
        # Metrics
        self.metrics["received_chunks"] += 1
        self.metrics["received_bytes"] += len(data)
        
        if self.metrics["received_chunks"] % 50 == 0:
            logger.info(f"📊 METRICS: Sent={self.metrics['sent_chunks']} | Recv={self.metrics['received_chunks']} ({self.metrics['received_bytes']} bytes)")

        # Convert base64/bytes -> float32 array
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        
        if self.streamer: 
            self.streamer.set_playing(True)
        
        # Push to queue for the playback loop
        await self.playback_queue.put(arr)

    async def _on_done(self, **kwargs):
        if self.streamer: 
            # Allow a small buffer drain time
            await asyncio.sleep(0.5)
            self.streamer.set_playing(False)