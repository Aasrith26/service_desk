import sounddevice as sd
import numpy as np
from config.settings import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

print("Recording 2 seconds from default input device...")
print("SPEAK INTO YOUR MIC NOW!")

# Record 2 seconds
data = sd.rec(int(2 * AUDIO_SAMPLE_RATE), samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, dtype='int16')
sd.wait()

print("Recording complete.")

# Compute RMS for each chunk
chunk_size = 512
rmses = []
for i in range(0, len(data), chunk_size):
    chunk = data[i:i+chunk_size]
    if len(chunk) > 0:
        rms = float(np.sqrt((chunk.astype('float32') ** 2).mean()))
        rmses.append(rms)

if rmses:
    min_rms = min(rmses)
    max_rms = max(rmses)
    avg_rms = np.mean(rmses)
    print(f"\nRMS Stats (from {len(rmses)} chunks):")
    print(f"  Min RMS: {min_rms:.2f}")
    print(f"  Max RMS: {max_rms:.2f}")
    print(f"  Avg RMS: {avg_rms:.2f}")
    print(f"\nThreshold used by app: 500")
    
    if max_rms > 500:
        print("VERDICT: Microphone is working! Audio is being captured.")
    else:
        print("VERDICT: Microphone is NOT picking up audio (RMS too low).")
        print("  - Check if mic is muted or disconnected")
        print("  - Check Windows privacy settings (allow app access to microphone)")
        print("  - Try a different microphone device")
else:
    print("ERROR: No audio data recorded!")
