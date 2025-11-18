"""
Audio utilities for PCM conversion, buffering, and format handling
"""

import base64
import numpy as np
from typing import Tuple, List
from utils.logger import get_logger

logger = get_logger(__name__)


def pcm_to_base64(pcm_data: bytes) -> str:
    """
    Convert raw PCM audio bytes to base64 string.
    
    Args:
        pcm_data: Raw PCM16 audio bytes
    
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(pcm_data).decode('utf-8')


def base64_to_pcm(b64_data: str) -> bytes:
    """
    Convert base64 string back to raw PCM audio bytes.
    
    Args:
        b64_data: Base64 encoded audio string
    
    Returns:
        Raw PCM16 audio bytes
    """
    return base64.b64decode(b64_data.encode('utf-8'))


def bytes_to_numpy(pcm_bytes: bytes, dtype: str = 'int16') -> np.ndarray:
    """
    Convert PCM bytes to numpy array.
    
    Args:
        pcm_bytes: Raw PCM audio bytes
        dtype: Data type (default: 'int16' for PCM16)
    
    Returns:
        Numpy array of audio samples
    """
    return np.frombuffer(pcm_bytes, dtype=dtype)


def numpy_to_bytes(audio_array: np.ndarray, dtype: str = 'int16') -> bytes:
    """
    Convert numpy array to PCM bytes.
    
    Args:
        audio_array: Numpy array of audio samples
        dtype: Data type (default: 'int16' for PCM16)
    
    Returns:
        Raw PCM audio bytes
    """
    return audio_array.astype(dtype).tobytes()


def calculate_rms(audio_data: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) energy of audio.
    Used for silence detection.
    
    Args:
        audio_data: Numpy array of audio samples
    
    Returns:
        RMS value
    """
    if len(audio_data) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_data.astype(float)))))


def detect_silence(audio_data: np.ndarray, threshold: float = 500) -> bool:
    """
    Detect if audio chunk contains silence.
    
    Args:
        audio_data: Numpy array of audio samples
        threshold: RMS threshold below which is considered silence
    
    Returns:
        True if silent, False if contains speech
    """
    rms = calculate_rms(audio_data)
    return rms < threshold


class AudioBuffer:
    """
    Circular buffer for smooth audio streaming.
    Helps manage variable-sized audio chunks.
    """
    
    def __init__(self, max_size: int = 48000):
        """
        Initialize audio buffer.
        
        Args:
            max_size: Maximum number of samples to store
        """
        self.max_size = max_size
        self.buffer = np.zeros(max_size, dtype='int16')
        self.write_pos = 0
        self.read_pos = 0
        self.logger = get_logger(__name__)
    
    def write(self, data: np.ndarray) -> bool:
        """
        Write audio data to buffer.
        
        Args:
            data: Audio samples to write
        
        Returns:
            True if successful, False if buffer overflow
        """
        data_len = len(data)
        available = (self.read_pos - self.write_pos - 1) % self.max_size
        
        if data_len > available:
            self.logger.warning(f"Audio buffer overflow: need {data_len}, have {available}")
            return False
        
        # Handle wrap-around
        if self.write_pos + data_len <= self.max_size:
            self.buffer[self.write_pos:self.write_pos + data_len] = data
        else:
            split = self.max_size - self.write_pos
            self.buffer[self.write_pos:] = data[:split]
            self.buffer[:data_len - split] = data[split:]
        
        self.write_pos = (self.write_pos + data_len) % self.max_size
        return True
    
    def read(self, size: int) -> np.ndarray:
        """
        Read audio data from buffer.
        
        Args:
            size: Number of samples to read
        
        Returns:
            Audio samples (may be shorter if buffer has less data)
        """
        available = (self.write_pos - self.read_pos) % self.max_size
        size = min(size, available)
        
        if size == 0:
            return np.array([], dtype='int16')
        
        # Handle wrap-around
        if self.read_pos + size <= self.max_size:
            data = self.buffer[self.read_pos:self.read_pos + size].copy()
        else:
            split = self.max_size - self.read_pos
            data = np.concatenate([
                self.buffer[self.read_pos:],
                self.buffer[:size - split]
            ])
        
        self.read_pos = (self.read_pos + size) % self.max_size
        return data
    
    def available(self) -> int:
        """Get number of samples available to read."""
        return (self.write_pos - self.read_pos) % self.max_size
    
    def clear(self):
        """Clear the buffer."""
        self.buffer.fill(0)
        self.write_pos = 0
        self.read_pos = 0


def mix_audio(audio1: np.ndarray, audio2: np.ndarray, gain1: float = 0.5, gain2: float = 0.5) -> np.ndarray:
    """
    Mix two audio streams together.
    
    Args:
        audio1: First audio array
        audio2: Second audio array
        gain1: Gain for first audio (0.0-1.0)
        gain2: Gain for second audio (0.0-1.0)
    
    Returns:
        Mixed audio array (clipped to prevent overflow)
    """
    min_len = min(len(audio1), len(audio2))
    mixed = (audio1[:min_len].astype(float) * gain1 + 
             audio2[:min_len].astype(float) * gain2)
    
    # Clip to int16 range to prevent overflow
    mixed = np.clip(mixed, -32768, 32767)
    return mixed.astype('int16')
