"""
Configuration settings for Clinic Voice Assistant
Handles Azure credentials, audio constants, and runtime parameters
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# AZURE GPT-REALTIME CONFIGURATION
# ============================================================================
# Preferred: provide a full wss:// endpoint via AZURE_REALTIME_ENDPOINT in your .env
AZURE_REALTIME_ENDPOINT = os.getenv(
    "AZURE_REALTIME_ENDPOINT",
    ""
)

# Fallback: construct endpoint from host/region/deployment env vars when full endpoint isn't provided
AZURE_HOST = os.getenv("AZURE_HOST", "shyam-mhvudwae-eastus2.openai.azure.com")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT", "gpt-realtime")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-10-01-preview")

if not AZURE_REALTIME_ENDPOINT:
    # Auto-correct hostname if it uses the internal/services domain which might be unreachable
    if "services.ai.azure.com" in AZURE_HOST:
        AZURE_HOST = AZURE_HOST.replace("services.ai.azure.com", "openai.azure.com")
        
    # Ensure we use wss:// scheme for WebSocket realtime API
    AZURE_REALTIME_ENDPOINT = (
        f"wss://{AZURE_HOST}/openai/realtime?api-version={AZURE_API_VERSION}&deployment={AZURE_DEPLOYMENT}"
    )

# API key must be supplied via env (.env). No hardcoded secrets.
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "")

# ============================================================================
# AUDIO CONFIGURATION
# ============================================================================
AUDIO_SAMPLE_RATE = 24000  # 24kHz required by Azure GPT-Realtime
AUDIO_FORMAT = "audio/pcm"  # PCM format
AUDIO_CHANNELS = 1  # Mono
AUDIO_CHUNK_SIZE = 512  # Samples per frame (21ms at 24kHz)
AUDIO_DTYPE = "int16"  # 16-bit PCM

# ============================================================================
# LANGUAGE CONFIGURATION
# ============================================================================
SUPPORTED_LANGUAGES = ["en", "te"]  # English, Telugu
DEFAULT_LANGUAGE = "en"
LANGUAGE_CODES = {
    "english": "en",
    "telugu": "te",
    "en": "en",
    "te": "te",
}

# ============================================================================
# AUDIO PROCESSING
# ============================================================================
SILENCE_THRESHOLD = 100  # RMS threshold for silence detection (very sensitive)
SILENCE_DURATION = 0.5  # Seconds of silence to trigger response (reduced for faster response)
MIN_SPEECH_DURATION = 0.2  # Minimum speech duration to recognize (seconds)
# Normalized silence threshold (fraction of full-scale). Use when numeric RMS scales vary between devices.
SILENCE_THRESHOLD_FRACTION = float(os.getenv('SILENCE_THRESHOLD_FRACTION', '0.02'))  # ~2% of full scale

# ============================================================================
# SYSTEM PROMPT FOR MULTILINGUAL CLINIC ASSISTANT
# ============================================================================
SYSTEM_PROMPT_TEMPLATE = """You are a multilingual clinic receptionist assistant for a healthcare facility. 

IMPORTANT INSTRUCTIONS:
1. You MUST respond in the same language(s) the user uses. If they speak Telugu, respond in Telugu. If English, respond in English. If they mix both, you can mix both.
2. You are helpful, professional, and empathetic when discussing medical appointments and healthcare.
3. Use the provided clinic context to answer questions about doctors, specializations, availability, and appointment slots.
4. Always confirm details before booking appointments.
5. If you don't know something not in the provided context, say so honestly.
6. Speak naturally and conversationally - you're having a voice conversation.

CLINIC CONTEXT:
{context}

Always be accurate about doctor availability and appointment slots."""

# ============================================================================
# STREAMING CONFIGURATION
# ============================================================================
WEBSOCKET_TIMEOUT = 30  # seconds
WEBSOCKET_RECONNECT_ATTEMPTS = 3
WEBSOCKET_RECONNECT_DELAY = 2  # seconds

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "clinic_voice_assistant.log"

# ============================================================================
# DATA FILES
# ============================================================================
CLINIC_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "clinic_knowledge.json")
SLOTS_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "slots.xlsx")

# ============================================================================
# DEBUG / TESTING
# ============================================================================
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
SIMULATE_AUDIO = os.getenv("SIMULATE_AUDIO", "false").lower() == "true"  # Simulate audio for testing without mic
# Safety: if more than this many seconds of audio are buffered without a trigger,
# force a commit/trigger to avoid endlessly sending audio with no response.
AUDIO_MAX_BUFFER_SECONDS = float(os.getenv('AUDIO_MAX_BUFFER_SECONDS', '5.0'))
