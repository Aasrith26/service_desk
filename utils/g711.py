"""
G.711 Mu-Law Codec & Resampling Utilities
Replaces deprecated 'audioop' module for Python 3.13+ compatibility.
"""

import numpy as np

# ==========================================
# G.711 MU-LAW LOOKUP TABLES
# ==========================================

# Mu-law to Linear (PCM16) Lookup Table
# Generated based on G.711 standard
_MU_LAW_DECODE_TABLE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364,  -9852,  -9340,  -8828,  -8316,
     -7932,  -7676,  -7420,  -7164,  -6908,  -6652,  -6396,  -6140,
     -5884,  -5628,  -5372,  -5116,  -4860,  -4604,  -4348,  -4092,
     -3900,  -3772,  -3644,  -3516,  -3388,  -3260,  -3132,  -3004,
     -2876,  -2748,  -2620,  -2492,  -2364,  -2236,  -2108,  -1980,
     -1884,  -1820,  -1756,  -1692,  -1628,  -1564,  -1500,  -1436,
     -1372,  -1308,  -1244,  -1180,  -1116,  -1052,   -988,   -924,
      -876,   -844,   -812,   -780,   -748,   -716,   -684,   -652,
      -620,   -588,   -556,   -524,   -492,   -460,   -428,   -396,
      -372,   -356,   -340,   -324,   -308,   -292,   -276,   -260,
      -244,   -228,   -212,   -196,   -180,   -164,   -148,   -132,
      -120,   -112,   -104,    -96,    -88,    -80,    -72,    -64,
       -56,    -48,    -40,    -32,    -24,    -16,     -8,      0,
     32124,  31100,  30076,  29052,  28028,  27004,  25980,  24956,
     23932,  22908,  21884,  20860,  19836,  18812,  17788,  16764,
     15996,  15484,  14972,  14460,  13948,  13436,  12924,  12412,
     11900,  11388,  10876,  10364,   9852,   9340,   8828,   8316,
      7932,   7676,   7420,   7164,   6908,   6652,   6396,   6140,
      5884,   5628,   5372,   5116,   4860,   4604,   4348,   4092,
      3900,   3772,   3644,   3516,   3388,   3260,   3132,   3004,
      2876,   2748,   2620,   2492,   2364,   2236,   2108,   1980,
      1884,   1820,   1756,   1692,   1628,   1564,   1500,   1436,
      1372,   1308,   1244,   1180,   1116,   1052,    988,    924,
       876,    844,    812,    780,    748,    716,    684,    652,
       620,    588,    556,    524,    492,    460,    428,    396,
       372,    356,    340,    324,    308,    292,    276,    260,
       244,    228,    212,    196,    180,    164,    148,    132,
       120,    112,    104,     96,     88,     80,     72,     64,
        56,     48,     40,     32,     24,     16,      8,      0
]

# Pre-convert to numpy array for fast indexing
_DECODE_LUT = np.array(_MU_LAW_DECODE_TABLE, dtype=np.int16)

# Linear to Mu-law encoding logic
# (It's often clearer to use a function or a very large LUT. 
# A 64KB LUT is trivial for modern RAM and fastest).
def _generate_encode_lut():
    lut = np.zeros(65536, dtype=np.uint8)
    for i in range(65536):
        # Convert unsigned index back to signed 16-bit
        pcm_val = i - 65536 if i >= 32768 else i
        pcm_val = max(-32768, min(32767, pcm_val))
        
        # Encoding logic (G.711)
        sign = 0x80 if pcm_val < 0 else 0
        if pcm_val < 0: pcm_val = -pcm_val
        pcm_val += 0x84
        if pcm_val > 0x7FFF: pcm_val = 0x7FFF
        
        exponent = 7
        for exp in range(7, -1, -1):
            if pcm_val & (1 << (exp + 7)):
                exponent = exp
                break
        
        mantissa = (pcm_val >> (exponent + 3)) & 0x0F
        mulaw = ~(sign | (exponent << 4) | mantissa)
        lut[i] = mulaw & 0xFF
    return lut

_ENCODE_LUT = _generate_encode_lut()


def ulaw2lin(mulaw_bytes: bytes) -> bytes:
    """Decode Mu-law bytes to PCM16 bytes using Lookup Table."""
    indices = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    # Direct LUT lookup
    pcm16 = _DECODE_LUT[indices]
    return pcm16.tobytes()

def lin2ulaw(pcm16_bytes: bytes) -> bytes:
    """Encode PCM16 bytes to Mu-law bytes using Lookup Table."""
    samples = np.frombuffer(pcm16_bytes, dtype=np.uint16) # Use uint16 to index directly into 64k LUT
    mulaw = _ENCODE_LUT[samples]
    return mulaw.tobytes()


# ==========================================
# RESAMPLING UTILITIES (3x Factor)
# ==========================================

def resample_up_3x(pcm8k_bytes: bytes) -> bytes:
    """
    Resample 8kHz -> 24kHz (Factor 3).
    Method: Linear Interpolation for smoothness (better than simple repeat).
    """
    if not pcm8k_bytes: return b''
    
    samples = np.frombuffer(pcm8k_bytes, dtype=np.int16)
    n = len(samples)
    
    # Linear Interpolation
    # We want 3x samples.
    # Original indices: 0, 1, 2...
    # Target indices: 0, 0.33, 0.66, 1, 1.33...
    
    # High-performance numpy interp
    x_old = np.arange(n)
    x_new = np.linspace(0, n - 1, n * 3)
    
    new_samples = np.interp(x_new, x_old, samples).astype(np.int16)
    return new_samples.tobytes()


def resample_down_3x(pcm24k_bytes: bytes) -> bytes:
    """
    Resample 24kHz -> 8kHz (Factor 1/3).
    Method: Simple averaging (Boxcar filter) to prevent aliasing + Decimation.
    """
    if not pcm24k_bytes: return b''
    
    samples = np.frombuffer(pcm24k_bytes, dtype=np.int16)
    
    # We need to reshape to (N/3, 3) to average every 3 samples
    # Truncate if not divisible by 3
    n_keep = (len(samples) // 3) * 3
    if n_keep == 0: return b''
    
    reshaped = samples[:n_keep].reshape(-1, 3)
    
    # Average along axis 1 (approximate low-pass filter)
    downsampled = np.mean(reshaped, axis=1).astype(np.int16)
    
    return downsampled.tobytes()
