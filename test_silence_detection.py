"""
Simple silence/speech detection tester.
Records continuously and shows RMS + speech/silence state.
Helps debug why silence detection isn't triggering in main.
"""
import sounddevice as sd
import numpy as np
from config.settings import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE, SILENCE_THRESHOLD, SILENCE_DURATION
from utils.audio_utils import calculate_rms
import time

print(f"Silence Detection Tester")
print(f"  Threshold: {SILENCE_THRESHOLD}")
print(f"  Duration:  {SILENCE_DURATION}s")
print(f"\nRecording... speak and then pause for {SILENCE_DURATION}s\n")

stream = sd.InputStream(samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, blocksize=AUDIO_CHUNK_SIZE)
stream.start()

speech_started = False
silence_start_time = None
frame_count = 0

try:
    while frame_count < 1000:  # ~20 seconds
        audio_data, _ = stream.read(AUDIO_CHUNK_SIZE)
        audio = (audio_data[:, 0] * 32767).astype('int16')
        rms = calculate_rms(audio)
        
        is_silent = rms < SILENCE_THRESHOLD
        
        if is_silent:
            if not silence_start_time:
                silence_start_time = time.time()
            silence_duration = time.time() - silence_start_time
            state = f"SILENCE ({silence_duration:.1f}s)"
            
            if speech_started and silence_duration >= SILENCE_DURATION:
                print(f"\n>>> TRIGGER: Silence detected for {silence_duration:.1f}s after speech!")
                speech_started = False
                silence_start_time = None
        else:
            if not speech_started:
                speech_started = True
                silence_start_time = None
                state = "SPEECH START"
                print(f"\n>>> Speech started")
            else:
                state = "SPEECH"
        
        # Print status every 10 frames to avoid spam
        if frame_count % 10 == 0:
            marker = "[SILENCE]" if is_silent else "[SPEECH ]"
            print(f"{marker} RMS={rms:7.1f} | {state}")
        
        frame_count += 1

except KeyboardInterrupt:
    pass
finally:
    stream.stop()
    stream.close()
    print("\nDone.")
