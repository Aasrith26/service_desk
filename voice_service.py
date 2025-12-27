# Fix Windows UTF-8 encoding - MUST be before any imports
import sys
import os

# FORCE UTF-8 for Windows Console to prevent logging crash on Telugu text
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Also set environment variable for child processes
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
import uvicorn

from fastapi import FastAPI, WebSocket, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Database & Config
from core.database import ClinicDatabase
from core.services.clinic_info_service import ClinicInfoService
from core.services.cached_clinic_service import CachedClinicService, preload_all_clinics

# Voice Core
# Voice Core
from core.exotel_bridge import ExotelCallHandler
# from core.twilio_bridge import TwilioCallHandler (Deprecated)

# Logging
# Logging
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        SafeStreamHandler(sys.stdout),
        logging.FileHandler("voice_debug.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("VoiceService")
logger.setLevel(logging.INFO)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload Clinic Data for Voice Agent Context
    logger.info("VOICE SERVICE STARTING - Loading context...")
    
    # Initialize DB (creates tables if needed)
    db = ClinicDatabase()
    db.initialize_db()
    
    preload_all_clinics()
    logger.info("✓ Voice Service Ready!")
    yield
    logger.info("Voice Service shutting down...")

app = FastAPI(lifespan=lifespan)

# Allow Twilio (and local checks)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Render/monitoring"""
    return {"status": "healthy", "service": "voice-service"}

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return "<h1>Voice Microservice Running</h1>"

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """
    Exotel Webhook (Optional):
    Exotel usually configures the flow in the dashboard, but if you need a dynamic response:
    You can return an applet response here. For now, we just log it.
    """
    logger.info(f"Incoming call signal received...")
    return Response(content="OK", media_type="text/plain")

@app.websocket("/stream/exotel")
async def websocket_endpoint(websocket: WebSocket, caller_id: str = None):
    """WebSocket endpoint for Exotel audio streaming."""
    # Extract caller_id from query params if provided
    if caller_id:
        logger.info(f"Caller ID from URL: {caller_id}")
    
    await websocket.accept()
    handler = ExotelCallHandler(websocket, caller_phone=caller_id)
    await handler.start()
    
    try:
        while True:
            message = await websocket.receive_text()
            await handler.handle_exotel_message(message)
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        await handler.close()

if __name__ == "__main__":
    # Run on PORT 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)

