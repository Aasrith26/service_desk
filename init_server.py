"""
Server startup script - Preload clinic knowledge for zero lag!
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.cached_clinic_service import preload_all_clinics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_server():
    """Call this when your server starts"""
    logger.info("="*60)
    logger.info("INITIALIZING VOICE ASSISTANT SERVER")
    logger.info("="*60)
    
    # Preload all clinic knowledge into cache
    logger.info("\nPreloading clinic knowledge...")
    preload_all_clinics()
    
    logger.info("\n✓ Server initialization complete!")
    logger.info("✓ Clinic knowledge cached - ready for calls!")
    logger.info("="*60)

if __name__ == "__main__":
    initialize_server()
