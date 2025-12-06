import asyncio
import websockets
import json
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestClient")

async def test_exotel_connection():
    uri = "ws://localhost:8000/stream/test_call_123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to Server")
            
            # 1. Send Connected Event
            await websocket.send(json.dumps({
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }))
            
            # 2. Send Start Event
            await websocket.send(json.dumps({
                "event": "start",
                "stream_sid": "stream_12345",
                "start": {
                    "media_format": {
                        "encoding": "audio/x-mulaw",
                        "sample_rate": 8000,
                        "channels": 1
                    }
                }
            }))
            
            # 3. Send Mock Media (Silence Mulaw)
            # Mulaw silence is 0xFF (negative zero) or 0x7F (positive zero) roughly.
            silence_chunk = b'\xff' * 160 # 20ms of 8kHz
            payload = base64.b64encode(silence_chunk).decode('utf-8')
            
            await websocket.send(json.dumps({
                "event": "media",
                "stream_sid": "stream_12345",
                "media": {
                    "payload": payload,
                    "track": "inbound",
                    "chunk": "1",
                    "timestamp": "1"
                }
            }))
            logger.info("Sent Media Chunk")
            
            # 4. Wait for response (Might not get one immediately if VAD doesn't trigger)
            # But we just want to ensure no crash
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                logger.info(f"Received: {response}")
            except asyncio.TimeoutError:
                logger.info("No immediate response (Expected, if VAD is silent)")
            
            # 5. Stop
            await websocket.send(json.dumps({"event": "stop"}))
            logger.info("Sent Stop")

    except Exception as e:
        logger.error(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_exotel_connection())
