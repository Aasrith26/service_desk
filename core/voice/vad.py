
import logging

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    def __init__(self, mode=3):
        """
        Initialize VAD.
        mode: 0 (Least aggressive) to 3 (Most aggressive).
        3 is best for "Gatekeeper" to avoid false positives (noise sent as speech).
        """
        self.vad = None
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(mode)
            logger.info(f"Local VAD initialized in mode {mode}.")
        except ImportError:
            logger.warning("webrtcvad library not found. Local VAD disabled (falling back to always-speech).")
            self.vad = None
        
        self.sample_rate = 8000 # Twilio/Mulaw standard

    def is_speech(self, audio_frame: bytes) -> bool:
        """
        Returns True if speech is detected, or if VAD is disabled.
        audio_frame: Must be 16-bit PCM bytes.
        """
        if not self.vad:
            return True
            
        try:
            # Twilio chunks are usually 20ms (160 samples * 2 bytes = 320 bytes)
            # webrtcvad supports 10, 20, 30ms.
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except Exception as e:
            # If frame size is wrong, log warning and let it pass (safe fallback)
            # logger.warning(f"VAD Error: {e}")
            return True 
