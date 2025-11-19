import asyncio
import json
import base64
import numpy as np
import sounddevice as sd
import websockets
import logging
import sys
from pathlib import Path

# --- CONFIGURATION ---
AZURE_ENDPOINT = "wss://shyam-mhvudwae-eastus2.services.ai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=gpt-4o-realtime-preview"
AZURE_API_KEY = "BhrrQpZqHtpdskVivvqgGDtxLs2QVuwFavleDwrCwwcGWFhZtvI6JQQ99BKACHYHv6XJ3w3AAAAACOGK5NWJ"

# Audio Settings
SAMPLE_RATE = 24000 # Azure prefers 24k
CHUNK_SIZE = 1024
SPEECH_THRESHOLD = 0.02  # Start talking volume
SILENCE_THRESHOLD = 0.01 # Stop talking volume
SILENCE_DURATION = 0.6   # Seconds of silence to trigger response

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Assistant")

class ClinicAssistant:
    def __init__(self):
        self.ws = None
        self.audio_buffer = [] # Buffer for microphone input
        self.response_audio_buffer = [] # Buffer for playing response
        self.is_speaking = False # Is the user speaking?
        self.is_playing = False  # Is the bot speaking?
        self.silence_chunks = 0
        self.playback_stream = None
        
        # Load Knowledge Base
        self.knowledge_base = self._load_knowledge()

    def _load_knowledge(self):
        """Loads clinic data into a simple string."""
        try:
            path = Path("data/clinic_knowledge.json")
            if not path.exists(): return "No info."
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Simple formatter
            text = "CLINIC DATA:\n"
            for d in data.get("doctors", []):
                text += f"- Dr. {d.get('name')} ({d.get('specialization')}). "
                text += f"Availability: {d.get('availability')}\n"
            return text
        except: return "Clinic data unavailable."

    async def connect(self):
        """Establishes WebSocket connection and sets Session."""
        headers = {"api-key": AZURE_API_KEY}
        try:
            self.ws = await websockets.connect(AZURE_ENDPOINT, additional_headers=headers)
            logger.info("✓ Connected to Azure")
            
            # 1. Send Session Update (The Brain)
            # We set the instructions ONCE.
            await self.ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": f"""
                    You are Sneha, a helpful receptionist at Health Plus Clinic.
                    Speak in TELUGU (Telugu script and pronunciation).
                    Keep answers short and polite.
                    
                    CONTEXT:
                    {self.knowledge_base}
                    """,
                    "voice": "shimmer",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": None, # WE CONTROL TURNS MANUALLY
                    "input_audio_transcription": {"model": "whisper-1"}
                }
            }))
            logger.info("✓ Session Configured")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            sys.exit(1)

    def pcm_to_base64(self, array):
        """Converts float32 audio chunk to PCM16 base64 string."""
        # Clip to avoid static
        array = np.clip(array, -1.0, 1.0)
        # Convert to 16-bit PCM
        pcm_data = (array * 32767).astype(np.int16).tobytes()
        return base64.b64encode(pcm_data).decode('utf-8')

    async def audio_loop(self):
        """Main Loop: Captures Mic -> VAD Logic -> Sends to Azure."""
        logger.info("🎤 Listening...")
        
        loop = asyncio.get_event_loop()
        input_queue = asyncio.Queue()

        def callback(indata, frames, time, status):
            loop.call_soon_threadsafe(input_queue.put_nowait, indata.copy())

        # Start Mic Stream
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE, callback=callback):
            while True:
                chunk = await input_queue.get()
                rms = np.sqrt(np.mean(chunk**2))

                # --- 1. INTERRUPTION LOGIC ---
                # If bot is playing and we hear loud sound -> KILL PLAYBACK
                if self.is_playing and rms > SPEECH_THRESHOLD:
                    logger.warning("⚡ INTERRUPTION DETECTED")
                    sd.stop() # Hardware stop
                    self.is_playing = False
                    self.response_audio_buffer = [] # Clear buffer
                    # Tell Azure to shut up
                    await self.ws.send(json.dumps({"type": "response.cancel"}))
                    # Clear current input buffer so we don't send the interruption noise
                    self.audio_buffer = []
                    self.is_speaking = True 
                    continue

                # --- 2. USER SPEECH DETECTION ---
                if rms > SPEECH_THRESHOLD:
                    self.is_speaking = True
                    self.silence_chunks = 0
                    self.audio_buffer.append(chunk) # Keep recording
                
                elif self.is_speaking and rms < SILENCE_THRESHOLD:
                    self.silence_chunks += 1
                    self.audio_buffer.append(chunk) # Keep recording silence (natural pause)
                    
                    # If silence persists for 0.6s, user is done.
                    chunks_needed = int(SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE)
                    if self.silence_chunks > chunks_needed:
                        logger.info(f"🗣️ Speech Ended. Sending {len(self.audio_buffer)} chunks...")
                        await self.process_user_input()
                        self.is_speaking = False
                        self.silence_chunks = 0
                        self.audio_buffer = [] # Reset buffer
                
                elif self.is_speaking:
                    # User paused briefly, keep recording
                    self.audio_buffer.append(chunk)

    async def process_user_input(self):
        """Sends collected audio buffer to Azure and requests response."""
        if not self.audio_buffer: return

        # 1. Combine all chunks
        full_audio = np.concatenate(self.audio_buffer)
        
        # 2. Convert to Base64
        b64_audio = self.pcm_to_base64(full_audio)
        
        # 3. Send APPEND event
        await self.ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": b64_audio
        }))
        
        # 4. Send COMMIT (I am done speaking)
        await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        
        # 5. Send CREATE RESPONSE (Please answer now)
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def receive_loop(self):
        """Listens for Audio/Text from Azure."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                event_type = data.get("type")

                if event_type == "response.audio.delta":
                    # Decode audio
                    b64_delta = data.get("delta")
                    if b64_delta:
                        pcm_bytes = base64.b64decode(b64_delta)
                        audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                        self.response_audio_buffer.append(audio_np)
                        
                        # Start playback if not already playing
                        if not self.is_playing:
                            asyncio.create_task(self.play_response())

                elif event_type == "response.audio_transcript.done":
                    print(f"🤖 Bot: {data.get('transcript')}")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    print(f"You: {data.get('transcript')}")
                    
                elif event_type == "error":
                    logger.error(f"API Error: {data}")

        except websockets.ConnectionClosed:
            logger.warning("Connection closed.")

    async def play_response(self):
        """Plays audio from the buffer continuously."""
        self.is_playing = True
        
        # Small buffer to ensure smoothness
        while self.is_playing:
            if self.response_audio_buffer:
                # Get next chunk
                chunk = self.response_audio_buffer.pop(0)
                # Play blocking (short duration) - allows interruption check in main loop
                sd.play(chunk, samplerate=SAMPLE_RATE)
                sd.wait() 
            else:
                # Buffer empty? Wait a bit, if still empty, stop.
                await asyncio.sleep(0.1)
                if not self.response_audio_buffer:
                    self.is_playing = False
                    break

    async def run(self):
        await self.connect()
        # Run Audio Input and Network Receiver in parallel
        await asyncio.gather(
            self.receive_loop(),
            self.audio_loop()
        )



if __name__ == "__main__":
    # 1. Verify Settings exists
    if "AZURE_API_KEY" not in globals() or "<YOUR_API_KEY>" in AZURE_API_KEY:
        print("❌ ERROR: You forgot to set your API Key and Endpoint at the top of the file!")
        sys.exit(1)

    print("🚀 Starting Clinic Assistant...")
    
    try:
        assistant = ClinicAssistant()
        # This actually starts the loop
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")