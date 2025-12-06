import logging
import uvicorn
from fastapi import FastAPI, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
import sys
import os

# Import both for now, or just Twilio
from core.twilio_bridge import TwilioCallHandler

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Server")

app = FastAPI()

# Store active calls
active_calls = {}

@app.get("/")
async def root():
    return {"status": "online", "service": "Clinic Voice Assistant (Twilio)"}

@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    """
    Twilio Webhook. Returns TwiML to start the WebSocket stream.
    """
    # Get the host url (ngrok url) to build the websocket url
    form_data = await request.form()
    logger.info(f"Incoming call from: {form_data.get('From')}")
    
    host = request.headers.get("host") # e.g. 1234.ngrok.app
    
    # TwiML Response
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting to AI Assistant.</Say>
    <Connect>
        <Stream url="wss://{host}/stream/twilio" />
    </Connect>
</Response>
"""
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/stream/twilio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New Twilio Connection")
    
    handler = TwilioCallHandler(websocket)
    await handler.start()
    
    try:
        while True:
            message = await websocket.receive_text()
            await handler.handle_twilio_message(message)
            
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        logger.info("Connection closed")
        await handler.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
