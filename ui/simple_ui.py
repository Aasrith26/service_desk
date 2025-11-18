"""
Simple Tkinter UI to simulate microphone input.

Features:
- Type a query and press Send
- Shows response text in the history pane
- Optionally speaks the response using local TTS (pyttsx3) if available

Run from project root:
    python -c "import sys, os; sys.path.insert(0, os.path.abspath('.')); from ui.simple_ui import run_ui; run_ui()"

"""

import sys
import os
import threading
try:
    import tkinter as tk
    from tkinter import scrolledtext, messagebox
except Exception:
    raise

import asyncio
from core.query_answering import QueryAnsweringEngine
from core.realtime_client import RealtimeClient
from utils.logger import get_logger

logger = get_logger(__name__)


def _safely_import_tts():
    try:
        import pyttsx3
        engine = pyttsx3.init()
        return engine
    except Exception:
        return None


class SimpleUI:
    def __init__(self, root):
        self.root = root
        root.title("Clinic Voice Assistant - Simulated UI")
        self.engine = QueryAnsweringEngine()
        self.tts = _safely_import_tts()
        
        # Live realtime client (runs in background asyncio loop)
        self.realtime = None
        self.realtime_loop = None
        self._live_text_buffer = ""
        self._start_realtime_client()

        # Input frame
        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=8, pady=6)

        self.entry = tk.Entry(input_frame, width=80)
        self.entry.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        self.entry.bind('<Return>', lambda e: self._on_send())

        send_btn = tk.Button(input_frame, text="Send", command=self._on_send)
        send_btn.pack(side=tk.LEFT)

        self.tts_var = tk.BooleanVar(value=bool(self.tts))
        tts_check = tk.Checkbutton(input_frame, text="Speak response", variable=self.tts_var)
        tts_check.pack(side=tk.LEFT, padx=(8, 0))

        # History pane
        self.history = scrolledtext.ScrolledText(root, state='disabled', width=100, height=20)
        self.history.pack(padx=8, pady=(0,8), fill=tk.BOTH, expand=True)

        # Footer
        footer = tk.Frame(root)
        footer.pack(fill=tk.X, padx=8, pady=(0,8))
        # Connection status (realtime)
        self.conn_status_label = tk.Label(footer, text="Realtime: connecting...")
        self.conn_status_label.pack(side=tk.LEFT, padx=(0,12))

        # Force offline checkbox
        self.force_offline = tk.BooleanVar(value=False)
        force_chk = tk.Checkbutton(footer, text="Force offline", variable=self.force_offline)
        force_chk.pack(side=tk.LEFT, padx=(0,12))

        self.status_label = tk.Label(footer, text="Ready")
        self.status_label.pack(side=tk.LEFT)

        # Start periodic UI updates (connection status)
        self.root.after(1000, self._update_connection_status)

    def _append_history(self, text: str):
        self.history.configure(state='normal')
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.configure(state='disabled')

    def _on_send(self):
        query = self.entry.get().strip()
        if not query:
            return
        self.entry.delete(0, tk.END)
        self._append_history(f"You: {query}")
        self.status_label.config(text="Processing...")
        # If realtime client connected, send to Azure model; otherwise use offline engine
        if not self.force_offline.get() and self.realtime and getattr(self.realtime, 'is_connected', False) and self.realtime_loop:
            try:
                # Schedule send_message in the realtime event loop
                asyncio.run_coroutine_threadsafe(self.realtime.send_message(query), self.realtime_loop)
                # Show that we're waiting for live model
                self._append_history("Assistant (live): (waiting for response...)")
            except Exception as e:
                logger.error(f"Failed to send to realtime client: {e}")
                # Fallback to offline
                threading.Thread(target=self._process_query, args=(query,), daemon=True).start()
        else:
            # Run processing in background thread to avoid blocking UI
            threading.Thread(target=self._process_query, args=(query,), daemon=True).start()

    def _process_query(self, query: str):
        try:
            resp = self.engine.answer_query(query)
            out = f"Assistant ({resp.language}): {resp.response_text}"
            logger.info(f"UI response: {out}")
            self.root.after(0, lambda: self._append_history(out))
            # TTS if requested and available
            if self.tts_var.get() and self.tts:
                try:
                    self.tts.say(resp.response_text)
                    self.tts.runAndWait()
                except Exception as e:
                    logger.error(f"TTS error: {e}")
                    self.root.after(0, lambda: messagebox.showerror("TTS Error", str(e)))
        finally:
            self.root.after(0, lambda: self.status_label.config(text="Ready"))

    # ---------------- Realtime client management ----------------
    def _start_realtime_client(self):
        """Start the RealtimeClient in a background thread with its own asyncio loop."""
        def _run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.realtime_loop = loop
            # Create client with text callback
            self.realtime = RealtimeClient(on_text_received=self._on_realtime_text)

            async def _runner():
                try:
                    await self.realtime.connect()
                    # start listen loop (will run until disconnected)
                    await self.realtime.listen()
                except Exception as e:
                    logger.error(f"Realtime client loop error: {e}")

            try:
                loop.run_until_complete(_runner())
            finally:
                loop.close()

        t = threading.Thread(target=_run_loop, daemon=True)
        t.start()

    def _on_realtime_text(self, text: str, partial: bool = False):
        """Callback invoked from realtime client thread when text arrives.
        We schedule UI updates via root.after.
        """
        try:
            if partial:
                # update live buffer and display/update last live line
                self._live_text_buffer = text
                self.root.after(0, lambda: self._update_last_live_line(f"Assistant (live, partial): {self._live_text_buffer}"))
            else:
                final = text
                self._live_text_buffer = ""
                self.root.after(0, lambda: self._append_history(f"Assistant (live): {final}"))
                # Optionally speak
                if self.tts_var.get() and self.tts:
                    try:
                        self.tts.say(final)
                        self.tts.runAndWait()
                    except Exception as e:
                        logger.error(f"TTS error (live): {e}")
        finally:
            self.root.after(0, lambda: self.status_label.config(text="Ready"))

    def _update_last_live_line(self, text: str):
        # Remove last line if it begins with 'Assistant (live' and append new
        try:
            self.history.configure(state='normal')
            lines = self.history.get('1.0', tk.END).rstrip('\n').split('\n')
            if lines and lines[-1].startswith('Assistant (live'):
                # replace last line
                lines[-1] = text
                self.history.delete('1.0', tk.END)
                self.history.insert(tk.END, '\n'.join(lines) + '\n')
            else:
                self.history.insert(tk.END, text + '\n')
            self.history.see(tk.END)
            self.history.configure(state='disabled')
        except Exception as e:
            logger.error(f"Error updating live line: {e}")

    def _update_connection_status(self):
        """Periodic update of realtime connection status shown in the UI."""
        try:
            status = "Disconnected"
            if self.realtime is None:
                status = "starting"
            else:
                if getattr(self.realtime, 'is_connected', False):
                    status = "connected"
                else:
                    status = "disconnected"

            text = f"Realtime: {status}"
            if self.force_offline.get():
                text += " (forced offline)"
            self.conn_status_label.config(text=text)
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
        finally:
            # schedule next update
            self.root.after(1000, self._update_connection_status)


def run_ui():
    root = tk.Tk()
    app = SimpleUI(root)
    root.mainloop()


if __name__ == '__main__':
    # Ensure project root is on sys.path when run directly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    run_ui()
