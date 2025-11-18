"""
Main entry point for Clinic Voice Assistant
Orchestrates the full bidirectional audio streaming pipeline
"""

import asyncio
import sys
import json
from typing import Optional
from pathlib import Path

from config.settings import DEBUG_MODE
from utils.logger import get_logger
from core.realtime_client import RealtimeClient
from core.audio_streamer import AudioStreamingEngine
from core.slot_manager import SlotManager
import sounddevice as sd

logger = get_logger(__name__)


class ClinicVoiceAssistant:
    """Main application class with debug-heavy tracing and slot persistence.

    Behaviour:
    - Starts audio capture and realtime client
    - Streams microphone audio to Azure
    - Receives streaming text (partial/final) and audio from the model
    - Updates slots from final text and persists confirmed appointments to disk
    - Emits debug logs for nearly every important event
    """

    APPOINTMENTS_FILE = Path(__file__).resolve().parent.joinpath('data', 'appointments.json')

    def __init__(self):
        """Initialize the voice assistant and wire callbacks."""
        logger.debug("Initializing ClinicVoiceAssistant")
        self.realtime_client = RealtimeClient()
        self.engine = AudioStreamingEngine(self.realtime_client)
        self.slot_manager = SlotManager()

        # Wire callbacks
        self.realtime_client.on_text_received = self._on_model_text
        # audio callback is used by engine, but add a log wrapper here as well
        orig_audio_cb = getattr(self.realtime_client, 'on_audio_received', None)
        self.realtime_client.on_audio_received = self._on_model_audio

        # ensure appointments file exists
        self.APPOINTMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not self.APPOINTMENTS_FILE.exists():
            self._write_json(self.APPOINTMENTS_FILE, [])

    def _write_json(self, path: Path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Wrote JSON to {path}")
        except Exception as e:
            logger.error(f"Failed to write JSON to {path}: {e}")

    def _read_json(self, path: Path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def _persist_appointment(self, slots: dict):
        try:
            logger.info("Persisting appointment to disk")
            appointments = self._read_json(self.APPOINTMENTS_FILE)
            appointments.append(slots)
            self._write_json(self.APPOINTMENTS_FILE, appointments)
            logger.info("Appointment saved")
        except Exception as e:
            logger.error(f"Failed to persist appointment: {e}")

    async def run(self):
        """Run the voice assistant in continuous loop.

        This method starts the streaming engine and monitors connection state.
        """
        logger.info("=" * 60)
        logger.info("CLINIC VOICE ASSISTANT - Starting (debug mode: %s)" % (DEBUG_MODE,))
        logger.info("=" * 60)

        # Clear instructions for user
        logger.info("")
        logger.info("📋 INSTRUCTIONS:")
        logger.info("  1️⃣  Speak clearly when you see '🎤 Listening for your voice input'")
        logger.info("  2️⃣  After speaking, wait 1-2 seconds (do NOT press Ctrl+C)")
        logger.info("  3️⃣  You will hear a beep (🔊) when speech is recognized")
        logger.info("  4️⃣  The model will respond - watch for '[MODEL RESPONSE]' in logs")
        logger.info("  5️⃣  Press Ctrl+C to exit gracefully")
        logger.info("")

        try:
            # Start the streaming engine
            logger.debug("Starting AudioStreamingEngine.start()")
            if not await self.engine.start():
                logger.error("Failed to start streaming engine")
                return False

            logger.info("[OK] Ready for conversation")
            logger.info("🎤 Listening for your voice input... (Press Ctrl+C to stop)")

            # Extra debug: report audio device and input stream status so user knows mic capture started
            try:
                # Log default input/output device indices and names
                try:
                    default_in, default_out = sd.default.device
                    devs = sd.query_devices()
                    din = devs[default_in]['name'] if isinstance(devs[default_in], dict) else str(devs[default_in])
                    dout = devs[default_out]['name'] if isinstance(devs[default_out], dict) else str(devs[default_out])
                    logger.info(f"Default devices - input: {default_in} ({din}), output: {default_out} ({dout})")
                except Exception:
                    logger.debug("Could not determine default sounddevice device names")
                devices = self.engine.streamer.get_audio_devices()
                logger.info(f"Audio devices detected: {len(devices)}")
                # Log first 3 device names for quick inspection
                for i, d in enumerate(devices[:3]):
                    # d may be a dict with 'name'
                    name = d.get('name') if isinstance(d, dict) else str(d)
                    logger.info(f"  device[{i}]: {name}")
            except Exception as e:
                logger.debug(f"Could not query audio devices: {e}")

            if getattr(self.engine.streamer, 'input_stream', None):
                logger.info("✓ Microphone input stream appears active")
            else:
                logger.warning("⚠️  Microphone input stream not active — check device/permissions")

            logger.info("✓ (All systems ready. Awaiting your voice input...)")
            logger.info("🎤 Listening for your voice input... (Press Ctrl+C to stop)")

            # Run engine (capture, playback, listen) concurrently
            await self.engine.run()

        except KeyboardInterrupt:
            logger.info("👋 Shutdown requested by user")
        except Exception as e:
            logger.error(f"ERROR in main loop: {e}")
            if DEBUG_MODE:
                import traceback
                traceback.print_exc()
        finally:
            logger.debug("Stopping engine and disconnecting")
            await self.engine.stop()
            logger.info("✓ Clinic Voice Assistant stopped")

    async def test_connection(self) -> bool:
        """Test connection to Azure GPT-Realtime API with verbose debug logs."""
        logger.info("Testing Azure connection...")

        try:
            logger.debug("Calling realtime_client.connect()")
            if not await self.realtime_client.connect():
                logger.error("[FAIL] Connection test failed")
                return False

            logger.info("[OK] Connected successfully")
            logger.debug("Sending test message to model")
            await self.realtime_client.send_message("Hello, this is a debug test message.")

            # Allow some time for streaming responses (text/audio)
            await asyncio.sleep(3)

            logger.debug("Disconnecting after test")
            await self.realtime_client.disconnect()
            logger.info("[OK] Test successful")
            return True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False

    async def _on_model_audio(self, audio_bytes: bytes):
        """Receive raw audio bytes from the model and log details.

        The engine already queues these for playback; this handler adds debugging.
        """
        try:
            logger.debug(f"Model audio received: {len(audio_bytes)} bytes")
            # Do not duplicate playback; engine handles it. But keep for debug.
        except Exception as e:
            logger.error(f"Error in _on_model_audio: {e}")

    async def _on_model_text(self, text: str, partial: bool = False):
        """Handle model text (partial and final). Update slot manager on final text.

        This function is intentionally verbose to aid debugging of ASR/MTL flows.
        """
        try:
            if partial:
                # Silently ignore partials to reduce log noise
                return

            # final text - this is the model's response to the user
            logger.info(f"[MODEL RESPONSE] {text}")

            # Update slots with final text
            slots = self.slot_manager.update_from_text(text)

            # If user confirmed, persist appointment
            if slots.get('confirmed') == 'yes' and slots.get('doctor') and slots.get('date') and slots.get('time'):
                logger.info("Slots confirmed by user, persisting appointment")
                self._persist_appointment(slots)

        except Exception as e:
            logger.error(f"Error handling model text: {e}")


async def main():
    """Main entry point."""
    # Check for command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            # Run connection test
            assistant = ClinicVoiceAssistant()
            success = await assistant.test_connection()
            sys.exit(0 if success else 1)
        
        elif sys.argv[1] == '--help':
            print("""
Clinic Voice Assistant - Interactive Medical Appointment Booking

Usage:
    python main.py                  Run the assistant in full mode
    python main.py --test           Test Azure connection only
    python main.py --help           Show this help message

Features:
    - Real-time voice conversation with Azure GPT-Realtime
    - Telugu + English support
    - Doctor availability and appointment booking
    - Clinic information queries
    - Completely hands-free operation

Requirements:
    - Azure API key (from Azure AI Foundry)
    - Microphone and speakers
    - Internet connection

Environment Variables:
    AZURE_API_KEY               Your Azure OpenAI API key
    LOG_LEVEL                   Logging level (DEBUG, INFO, WARNING, ERROR)
    DEBUG_MODE                  Enable debug logging (true/false)
    SIMULATE_AUDIO              Use simulated audio instead of real mic (true/false)
            """)
            sys.exit(0)
    
    # Run normal mode
    assistant = ClinicVoiceAssistant()
    await assistant.run()


if __name__ == "__main__":
    asyncio.run(main())
