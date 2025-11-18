"""
config/__init__.py
This file makes config a package and exports all configuration variables
Place this file in: config/__init__.py
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# AZURE CONFIGURATION
# ============================================================================

AZURE_DEPLOYMENT_URL = os.getenv(
    'AZURE_DEPLOYMENT_URL',
    ''
)

AZURE_API_KEY = os.getenv(
    'AZURE_API_KEY',
    ''
)

MODEL_NAME = os.getenv(
    'MODEL_NAME',
    'gpt-4-realtime-preview'
)

VOICE_NAME = os.getenv(
    'VOICE_NAME',
    'alloy'
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'True').lower() in ('true', '1', 'yes')

LOG_FILE_PATH = os.getenv(
    'LOG_FILE_PATH',
    'logs/voice_assistant.log'
)

# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() in ('true', '1', 'yes')

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate that all required configuration is set."""
    errors = []
    
    if not AZURE_DEPLOYMENT_URL:
        errors.append("❌ AZURE_DEPLOYMENT_URL is not set in .env file")
    
    if not AZURE_API_KEY:
        errors.append("❌ AZURE_API_KEY is not set in .env file")
    
    if errors:
        print("\n⚠️  CONFIGURATION ERRORS:\n")
        for error in errors:
            print(f"   {error}\n")
        print("Please set these variables in your .env file and try again.\n")
        return False
    
    return True


# ============================================================================
# EXPORT ALL VARIABLES
# ============================================================================

__all__ = [
    'AZURE_DEPLOYMENT_URL',
    'AZURE_API_KEY',
    'MODEL_NAME',
    'VOICE_NAME',
    'ENABLE_LOGGING',
    'LOG_FILE_PATH',
    'DEBUG_MODE',
    'validate_config',
]