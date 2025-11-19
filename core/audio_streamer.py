"""
FINAL FIX: core/audio_streamer.py
- CONFIG: Set interruption_threshold = 0.018 (User Verified).
- FIXED: Audio Format Bug (Converts Float32 -> Int16). The model will hear you now.
- KEEPS: Smart Gain & Interruption logic.
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
        self.noise_floor = 0.005       # Approx noise floor
        self.silence_threshold = 0.01  # Silence below this
        self.interruption_threshold = 0.018 # <--- YOUR SWEET SPOT
        
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

                # 2. PROCESSING (Smart Amp -> Queue)
                # Boost volume nicely if it's speech, ignore if it's noise
                processed_chunk = self._smart_amp(chunk, rms)
                
                self.loop.call_soon_threadsafe(self.queue.put_nowait, (processed_chunk.copy(), rms))

    def _smart_amp(self, chunk, rms):
        """Boosts voice volume without distorting background noise."""
        # Only boost if it's louder than the noise floor (Speech)
        if rms > self.noise_floor:
            # Target RMS 0.15 is a good volume for Azure
            target = 0.15
            gain = min(target / (rms + 0.00001), 4.0) # Cap gain at 4x
            return np.clip(chunk * gain, -1.0, 1.0)
        return chunk

    async def _process_queue(self):
        """Async Logic: Converts to Int16 and Handles VAD."""
        while self.is_running:
            chunk_float, rms = await self.queue.get()

            # ---------------------------------------------------------
            # CRITICAL FIX: CONVERT FLOAT32 TO PCM16 BYTES
            # ---------------------------------------------------------
            # 1. Scale float (-1.0 to 1.0) to Int16 range (-32768 to 32767)
            # 2. Convert to bytes
            chunk_int16 = (chunk_float * 32767).astype(np.int16).tobytes()

            # SENDING (Noise Gate)
            if rms > 0.002:
                if self.on_audio_chunk: await self.on_audio_chunk(chunk_int16)

            # VAD LOGIC (Speech Detection)
            if rms > self.silence_threshold:
                if not self.user_has_spoken:
                    print("🗣️ Speaking...")
                self.user_has_spoken = True
                self.silence_counter = 0
            
            elif rms < self.silence_threshold:
                self.silence_counter += 1
                # 12 chunks = 0.5s silence
                if self.silence_counter >= 12: 
                    self.silence_counter = 0
                    if self.user_has_spoken:
                        print(">> Sending response...")
                        self.user_has_spoken = False
                        if self.on_silence_detected: await self.on_silence_detected(0.5)
            else:
                self.silence_counter = 0

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
            self.user_has_spoken = False 

class AudioStreamingEngine:
    def __init__(self, client, manager=None):
        self.client = client
        self.manager = manager
        self.streamer = None
        self.buffer = []
        self.playback_task = None

    async def start(self):
        while True:
            if await self.client.connect():
                if self.manager:
                    self.manager.add_audio_handler(self._on_audio, priority=5)
                    self.manager.add_response_done_handler(self._on_done, priority=5)
                
                self.streamer = AudioStreamer(
                    on_audio_chunk=self.client.send_audio,
                    on_silence_detected=self._on_silence,
                    on_interruption=self._on_interrupt
                )
                await self.streamer.start()
                await self.client.listen()
                await self.streamer.stop()
            
            print("⚠️ Reconnecting...")
            await asyncio.sleep(2)

    async def stop(self):
        if self.streamer: await self.streamer.stop()
        await self.client.disconnect()

    async def _on_silence(self, duration):
        await self.client.trigger_response()

    async def _on_interrupt(self):
        if self.playback_task: self.playback_task.cancel()
        await self.client.cancel_response()
        self.buffer = []
        await asyncio.sleep(0.1)
        if self.streamer: self.streamer.set_playing(False)

    async def _on_audio(self, data, **kwargs):
        self.buffer.append(data)

    async def _on_done(self, **kwargs):
        if not self.buffer: return
        
        full_audio = b''.join(self.buffer)
        self.buffer = []
        arr = np.frombuffer(full_audio, dtype=np.int16).astype(np.float32) / 32767.0
        
        if self.streamer: self.streamer.set_playing(True)
        sd.play(arr, samplerate=24000)
        
        duration = len(arr) / 24000
        try:
            self.playback_task = asyncio.create_task(asyncio.sleep(duration))
            await self.playback_task
        except asyncio.CancelledError:
            sd.stop()
        
        if self.streamer: self.streamer.set_playing(False)