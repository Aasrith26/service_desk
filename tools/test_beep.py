import sounddevice as sd
import numpy as np
import time

print('Default devices:', sd.default.device)
print('Default samplerate:', sd.default.samplerate)

try:
    fs = 24000
    duration = 1.0
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    beep = (np.sin(2 * np.pi * 880 * t) * 0.5).astype('float32')
    print('Playing 1s beep at 880Hz...')
    sd.play(beep, samplerate=fs)
    sd.wait()
    print('Beep played (done)')
except Exception as e:
    print('Error playing beep:', e)
