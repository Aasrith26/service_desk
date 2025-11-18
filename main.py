"""
Service Desk Voice Assistant - Main Application
Handles voice input, processes through Azure OpenAI Realtime API, and returns responses
FIXED: Matches actual RealtimeClient signature + Auto-creates logs directory
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.realtime_client import RealtimeClient
from core.audio_streamer import AudioStreamingEngine
from core.slot_manager import SlotManager
from core.callback_manager import CallbackManager
from config import (
    ENABLE_LOGGING,
    LOG_FILE_PATH,
)

# Create logs directory if it doesn't exist
if LOG_FILE_PATH:
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        print(f"[INFO] Created logs directory: {log_dir}")

# Configure logging with UTF-8 encoding for Windows emoji support
logging.basicConfig(
    level=logging.DEBUG if ENABLE_LOGGING else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8') if LOG_FILE_PATH else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClinicVoiceAssistant:
    """Main voice assistant for clinic/hospital service desk."""
    
    def __init__(self):
        """Initialize the voice assistant with callback chain management."""
        logger.info("=" * 80)
        logger.info("INITIALIZING CLINIC VOICE ASSISTANT")
        logger.info("=" * 80)
        
        try:
            logger.debug("[INIT] Creating RealtimeClient...")
            # RealtimeClient takes optional callbacks in __init__
            self.realtime_client = RealtimeClient(
                on_audio_received=None,  # Will be set via callback manager
                on_text_received=None    # Will be set via callback manager
            )
            logger.debug("[INIT] ✓ RealtimeClient created")
            
            logger.debug("[INIT] Setting up callback manager...")
            self.callback_manager = CallbackManager(self.realtime_client)
            logger.debug("[INIT] ✓ Callback manager initialized")
            
            logger.debug("[INIT] Registering main.py handlers...")
            self.callback_manager.add_text_handler(self._on_model_text, priority=10)
            self.callback_manager.add_audio_handler(self._on_model_audio, priority=10)
            logger.debug("[INIT] ✓ Main.py handlers registered")
            
            logger.debug("[INIT] Creating AudioStreamingEngine...")
            self.engine = AudioStreamingEngine(
                self.realtime_client,
                callback_manager=self.callback_manager
            )
            logger.debug("[INIT] ✓ AudioStreamingEngine created")
            
            logger.debug("[INIT] Creating SlotManager...")
            self.slot_manager = SlotManager()
            logger.debug("[INIT] ✓ SlotManager created")
            
            callback_status = self.callback_manager.get_status()
            logger.info(f"[INIT] Callback Chain Status: {callback_status}")
            
            logger.info("[INIT] ✓ ClinicVoiceAssistant initialized successfully")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"[INIT] ✗ Failed to initialize ClinicVoiceAssistant: {e}", exc_info=True)
            raise
    
    async def _on_model_text(self, text: str, partial: bool = False):
        """Handle text response from model.
        
        Args:
            text: Text response from the model
            partial: Whether this is a partial response
        """
        try:
            response_type = "PARTIAL" if partial else "COMPLETE"
            logger.info(f"[MODEL TEXT] {response_type}: {text}")
            
            if not partial:
                logger.info(f"[RESPONSE] Assistant: {text}")
                
                if "appointment" in text.lower():
                    logger.info("[APPOINTMENT] Appointment confirmation detected")
                    
        except Exception as e:
            logger.error(f"[MODEL TEXT] Error processing text: {e}", exc_info=True)
    
    async def _on_model_audio(self, audio_data: bytes, **kwargs):
        """Handle audio response from model.
        
        Args:
            audio_data: Audio bytes from the model
            **kwargs: Additional arguments
        """
        try:
            logger.debug(f"[MODEL AUDIO] Received {len(audio_data)} bytes of audio")
            logger.info(f"[AUDIO] Audio playback initiated ({len(audio_data)} bytes)")
            
        except Exception as e:
            logger.error(f"[MODEL AUDIO] Error processing audio: {e}", exc_info=True)
    
    async def start(self):
        """Start the voice assistant."""
        try:
            logger.info("Starting voice assistant...")
            logger.info("Ready to receive voice input")
            logger.info("Listening for speech...")
            
            success = await self.engine.start()
            
            if not success:
                logger.error("[START] ✗ Failed to start engine")
                return False
            
            logger.info("[START] ✓ Voice assistant started successfully")
            return True
            
        except Exception as e:
            logger.error(f"[START] ✗ Error starting voice assistant: {e}", exc_info=True)
            return False
    
    async def stop(self):
        """Stop the voice assistant."""
        try:
            logger.info("Stopping voice assistant...")
            
            await self.engine.stop()
            await self.realtime_client.disconnect()
            
            logger.info("[STOP] ✓ Voice assistant stopped")
            
        except Exception as e:
            logger.error(f"[STOP] ✗ Error stopping voice assistant: {e}", exc_info=True)
    
    async def run(self):
        """Run the voice assistant."""
        try:
            if not await self.start():
                logger.error("[RUN] Failed to start voice assistant")
                return
            
            logger.info("[RUN] Voice assistant running... Press Ctrl+C to stop")
            
            try:
                while True:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("[RUN] Received interrupt signal")
                
        except Exception as e:
            logger.error(f"[RUN] ✗ Error in run loop: {e}", exc_info=True)
            
        finally:
            await self.stop()


async def main():
    """Main entry point."""
    try:
        logger.info("Starting Clinic Voice Assistant...")
        
        assistant = ClinicVoiceAssistant()
        
        await assistant.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
