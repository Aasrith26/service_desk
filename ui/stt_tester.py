"""
Simple STT tester UI

Features:
- Show microphone capture level (RMS) in real-time
- Record a short clip to `tmp_stt.wav`
- Playback recorded clip
- Send recorded clip to `RealtimeClient` for transcription (if Azure creds available)

This is a lightweight helper for debugging whether your microphone is capturing audio.
"""
import threading
import queue
import time
import wave
import json
import asyncio
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    raise

import numpy as np
import sounddevice as sd

from config import settings
from utils.logger import get_logger
from core.realtime_client import RealtimeClient

logger = get_logger(__name__)


class STTTesterUI:
    def __init__(self, master=None):
        self.master = master or tk.Tk()
        self.master.title("STT Tester - Microphone Monitor")

        self.frame = ttk.Frame(self.master, padding=10)
        self.frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # Device info
        self.devices_btn = ttk.Button(self.frame, text="Show Audio Devices", command=self.show_devices)
        self.devices_btn.grid(row=0, column=0, sticky=tk.W)

        # RMS label
        self.rms_var = tk.StringVar(value="RMS: 0.00")
        self.rms_label = ttk.Label(self.frame, textvariable=self.rms_var)
        self.rms_label.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))

        # Start/Stop monitor
        self.monitor_btn = ttk.Button(self.frame, text="Start Monitor", command=self.toggle_monitor)
        self.monitor_btn.grid(row=2, column=0, sticky=tk.W, pady=(8, 0))

        # Record / Play / Transcribe
        self.record_btn = ttk.Button(self.frame, text="Record 3s Clip", command=self.record_clip)
        self.record_btn.grid(row=3, column=0, sticky=tk.W, pady=(8, 0))

        self.play_btn = ttk.Button(self.frame, text="Play Clip", command=self.play_clip)
        self.play_btn.grid(row=4, column=0, sticky=tk.W, pady=(4, 0))

        self.transcribe_btn = ttk.Button(self.frame, text="Transcribe Clip (Azure)", command=self.transcribe_clip)
        self.transcribe_btn.grid(row=5, column=0, sticky=tk.W, pady=(4, 0))

        self.transcription_var = tk.StringVar(value="Transcription: ")
        self.transcription_label = ttk.Label(self.frame, textvariable=self.transcription_var, wraplength=480)
        self.transcription_label.grid(row=6, column=0, sticky=tk.W, pady=(8, 0))

        # State
        self.monitoring = False
        self._stream = None
        self._q = queue.Queue()
        self._rms_updater = None
        self.tmp_wav = Path(__file__).resolve().parent.joinpath('tmp_stt.wav')

    def show_devices(self):
        try:
            devs = sd.query_devices()
            txt = "\n".join([f"{i}: {d['name']}" for i, d in enumerate(devs)])
            top = tk.Toplevel(self.master)
            top.title("Audio Devices")
            txtw = tk.Text(top, width=80, height=20)
            txtw.pack(fill='both', expand=True)
            txtw.insert('1.0', txt)
        except Exception as e:
            logger.error(f"Failed to query devices: {e}")

    def toggle_monitor(self):
        if not self.monitoring:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        try:
            self.monitoring = True
            self.monitor_btn.config(text="Stop Monitor")

            # Open InputStream with callback
            self._stream = sd.InputStream(samplerate=settings.AUDIO_SAMPLE_RATE,
                                          channels=1,
                                          dtype='int16',
                                          blocksize=settings.AUDIO_CHUNK_SIZE,
                                          callback=self._audio_callback)
            self._stream.start()

            # Start GUI updater
            self._rms_updater = self.master.after(100, self._update_rms_label)
            logger.info("Monitor started")
        except Exception as e:
            logger.error(f"Failed to start monitor: {e}")
            self.monitoring = False

    def stop_monitor(self):
        try:
            self.monitoring = False
            self.monitor_btn.config(text="Start Monitor")
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            if self._rms_updater:
                self.master.after_cancel(self._rms_updater)
                self._rms_updater = None
            self.rms_var.set("RMS: 0.00")
            logger.info("Monitor stopped")
        except Exception as e:
            logger.error(f"Failed to stop monitor: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        try:
            # indata is int16, shape (frames, channels)
            samples = np.frombuffer(indata, dtype=np.int16)
            # compute RMS
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            # push to queue for GUI
            try:
                self._q.put_nowait(rms)
            except queue.Full:
                pass
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

    def _update_rms_label(self):
        try:
            vals = []
            while not self._q.empty():
                vals.append(self._q.get_nowait())
            if vals:
                rms = float(np.mean(vals))
                self.rms_var.set(f"RMS: {rms:.2f}")
            # schedule next
            self._rms_updater = self.master.after(100, self._update_rms_label)
        except Exception as e:
            logger.error(f"Error updating RMS label: {e}")

    def record_clip(self, seconds: float = 3.0):
        # Run recording in thread to avoid blocking UI
        threading.Thread(target=self._record_clip_thread, args=(seconds,), daemon=True).start()

    def _record_clip_thread(self, seconds: float):
        try:
            logger.info(f"Recording {seconds}s to {self.tmp_wav}")
            data = sd.rec(int(seconds * settings.AUDIO_SAMPLE_RATE), samplerate=settings.AUDIO_SAMPLE_RATE, channels=1, dtype='int16')
            sd.wait()
            # write WAV
            with wave.open(str(self.tmp_wav), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(settings.AUDIO_SAMPLE_RATE)
                wf.writeframes(data.tobytes())
            logger.info("Recording saved")
            self.transcription_var.set(f"Recorded {seconds}s to {self.tmp_wav}")
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            self.transcription_var.set(f"Recording failed: {e}")

    def play_clip(self):
        threading.Thread(target=self._play_clip_thread, daemon=True).start()

    def _play_clip_thread(self):
        try:
            if not self.tmp_wav.exists():
                self.transcription_var.set("No clip recorded yet")
                return
            with wave.open(str(self.tmp_wav), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                sd.play(audio, samplerate=wf.getframerate())
                sd.wait()
            logger.info("Playback finished")
        except Exception as e:
            logger.error(f"Playback failed: {e}")
            self.transcription_var.set(f"Playback failed: {e}")

    def transcribe_clip(self):
        # Send recorded clip to RealtimeClient for transcription in background thread
        threading.Thread(target=self._transcribe_thread, daemon=True).start()

    def _transcribe_thread(self):
        try:
            if not self.tmp_wav.exists():
                self.transcription_var.set("No clip recorded yet")
                return

            # run async transcription
            result = asyncio.run(self._transcribe_wav_async(str(self.tmp_wav)))
            if result:
                self.transcription_var.set(f"Transcription: {result}")
            else:
                self.transcription_var.set("No transcription received")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_var.set(f"Transcription failed: {e}")

    async def _transcribe_wav_async(self, path: str, timeout: float = 10.0):
        """Connect to RealtimeClient, stream the WAV file as input audio, commit and trigger a response that requests text.

        Returns final text or None.
        """
        client = RealtimeClient()
        final_text = {'value': None}

        async def _on_text(text, partial=False):
            if partial:
                # update partials in GUI
                self.transcription_var.set(f"Partial: {text}")
            else:
                final_text['value'] = text

        client.on_text_received = _on_text

        try:
            ok = await client.connect()
            if not ok:
                logger.error("RealtimeClient connect failed")
                return None

            # read file
            with wave.open(path, 'rb') as wf:
                assert wf.getsampwidth() == 2
                assert wf.getnchannels() == 1
                frames = wf.readframes(wf.getnframes())

            # send in chunks
            chunk_bytes = settings.AUDIO_CHUNK_SIZE * 2  # int16 bytes
            for i in range(0, len(frames), chunk_bytes):
                await client.send_audio(frames[i:i+chunk_bytes])
                await asyncio.sleep(0.01)

            # commit buffer
            try:
                await client.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            except Exception as e:
                logger.error(f"Failed to send commit event: {e}")

            # Trigger model response (request text modality)
            await client.trigger_response("")

            # wait for final text or timeout
            waited = 0.0
            interval = 0.2
            while waited < timeout:
                if final_text['value']:
                    break
                await asyncio.sleep(interval)
                waited += interval

            await client.disconnect()
            return final_text['value']

        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass
            return None


def main():
    print("Starting STT Tester UI...")
    try:
        root = tk.Tk()
    except Exception as e:
        print(f"Failed to initialize Tkinter: {e}")
        raise

    app = STTTesterUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
