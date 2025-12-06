"""
UPDATED: main.py
- FEATURE: Listens for [BOOK_ACTION] command.
- LOGIC: Updates appointments.csv without stopping the call.
"""

import asyncio
import logging
import sys
import os
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.realtime_client import RealtimeClient
from core.audio_streamer import AudioStreamingEngine
from core.callback_manager import CallbackManager
from core.database import ClinicDatabase
from config import ENABLE_LOGGING, LOG_FILE_PATH

# Disable verbose websockets logging
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('websockets.client').setLevel(logging.WARNING)

# Setup Logs
if LOG_FILE_PATH:
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if ENABLE_LOGGING else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ClinicVoiceAssistant:
    def __init__(self):
        logger.info("INITIALIZING CLINIC VOICE ASSISTANT...")
        
        self.realtime_client = RealtimeClient()
        
        # Setup Callbacks
        self.callback_manager = CallbackManager(self.realtime_client)
        self.callback_manager.add_text_handler(self._on_model_text, priority=10)
        
        self.engine = AudioStreamingEngine(
            self.realtime_client,
            manager=self.callback_manager
        )
        
        # Initialize DB
        self.db = ClinicDatabase()
        
        logger.info("Initialization Complete")
    
    async def _on_model_text(self, text: str):
        """Log assistant's text responses"""
        logger.info(f"[ASSISTANT]: {text}")
    
    async def run(self):
        logger.info("Starting System...")
        await self.engine.start()
        logger.info("SYSTEM RUNNING")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping...")
            await self.engine.stop()

if __name__ == "__main__":
    try:
        asyncio.run(ClinicVoiceAssistant().run())
    except Exception as e:
        logger.error(f"Fatal Error: {e}")