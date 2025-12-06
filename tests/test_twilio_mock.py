import asyncio
import websockets
import json
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestTwilio")

async def test_twilio_connection():
    uri = "ws://localhost:8000/stream/twilio"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to Server")
            
            # 1. Connected Event (Optional in test, but good practice)
            await websocket.send(json.dumps({
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }))

            # 2. Start Event
            await websocket.send(json.dumps({
                "event": "start",
                "start": {
                    "streamSid": "stream_12345",
                    "callSid": "call_12345",
                    "tracks": ["inbound"]
                }
            }))
            
            # 3. Media Event
            silence_chunk = b'\xff' * 160 
            payload = base64.b64encode(silence_chunk).decode('utf-8')
            
            await websocket.send(json.dumps({
                "event": "media",
                "streamSid": "stream_12345",
                "media": {
                    "payload": payload,
                    "track": "inbound",
                    "chunk": "1",
                    "timestamp": "1"
                }
            }))
            logger.info("Sent Media Chunk")
            
            # 4. Wait
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"Received: {response}")
            except asyncio.TimeoutError:
                logger.info("No immediate response")
            
            # 5. Stop
            await websocket.send(json.dumps({"event": "stop"}))
            logger.info("Sent Stop")

    except Exception as e:
        logger.error(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_twilio_connection())
