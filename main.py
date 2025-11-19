import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.realtime_client import RealtimeClient
from core.audio_streamer import AudioStreamingEngine
from core.callback_manager import CallbackManager
from core.slot_manager import SlotManager
from config import ENABLE_LOGGING, LOG_FILE_PATH

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
        
        # 1. Create Client
        self.realtime_client = RealtimeClient()
        
        # 2. Create Callback Manager
        self.callback_manager = CallbackManager(self.realtime_client)
        self.callback_manager.add_text_handler(self._on_model_text, priority=10)
        
        # 3. Create Engine
        # FIXED: Argument name is 'manager', not 'callback_manager'
        self.engine = AudioStreamingEngine(
            self.realtime_client,
            manager=self.callback_manager
        )
        
        logger.info("✓ Initialization Complete")
    
    async def _on_model_text(self, text: str, partial: bool = False):
        if not partial:
            logger.info(f"[ASSISTANT]: {text}")
    
    async def run(self):
        logger.info("Starting System...")
        await self.engine.start()
        logger.info("✓ SYSTEM RUNNING. Press Ctrl+C to stop.")
        
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
        logger.error(f"Fatal Error: {e}", exc_info=True)