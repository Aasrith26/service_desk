# Fix Windows UTF-8 encoding - MUST be before any imports
import sys
import os

# Create a wrapper to force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    # This reconfigures the underlying stream to use UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Also set environment variable for child processes
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
import uvicorn

# FORCE UTF-8 for Windows Console to prevent logging crash on Telugu text
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, WebSocket, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from core.routers import dashboard_router

# Import both for now, or just Twilio
from core.twilio_bridge import TwilioCallHandler
from core.services.cached_clinic_service import preload_all_clinics

# Setup Logging with UTF-8
# Setup Logging with UTF-8
# On Windows, we need to be careful. We already reconfigured sys.stdout to utf-8 above.
# But to be double safe, we can use a handler that handles encode errors gracefully if the console doesn't support it.

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Write with replacement if encoding fails
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # Fallback: encode to ascii with replacement, then decode
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
        logging.FileHandler("server_debug.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("Server")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("="*60)
    logger.info("SERVER STARTING - Preloading clinic knowledge...")
    logger.info("="*60)
    
    # Initialize Database (Verify tables & Seed data) - ONCE
    from core.database import ClinicDatabase
    db = ClinicDatabase()
    db.initialize_db()
    
    preload_all_clinics()
    logger.info("✓ Clinic knowledge cached - server ready!")
    logger.info("="*60)
    yield
    # Shutdown
    logger.info("Server shutting down...")

from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(dashboard_router.router)

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------
# API SERVER (DASHBOARD)
# -----------------

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/monitoring"""
    return {"status": "healthy", "service": "clinic-api"}

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return """
    <html>
        <head><title>Clinic API Server</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🏥 Clinic API Server Running</h1>
            <p>Dashboard API: <code>/dashboard</code></p>
            <p>Admin Dashboard: <a href="/static/admin.html">/static/admin.html</a></p>
            <p>Voice Service is separate on Port 8001</p>
        </body>
    </html>
    """
    
# NOTE: Voice logic (Twilio Webhook & WebSocket) has been moved to voice_service.py

if __name__ == "__main__":
    # Run on PORT 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
