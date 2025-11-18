"""
Simple auth check for Azure GPT-Realtime WebSocket endpoint.

Run this from the project root (it uses the same settings as the app).
It will try to open a websocket and report HTTP status codes and suggestions.
"""

import asyncio
import json
import sys
from config import settings
import websockets
from websockets.exceptions import InvalidStatusCode, WebSocketException


async def run_check():
    endpoint = settings.AZURE_REALTIME_ENDPOINT
    api_key = settings.AZURE_API_KEY

    print(f"Endpoint: {endpoint}")
    print(f"API key present: {len(api_key) > 0}")

    headers = {
        "api-key": api_key,
    }

    try:
        print("Attempting WebSocket connection...")
        async with websockets.connect(endpoint, additional_headers=headers, subprotocols=["realtime"]) as ws:
            print("Connected successfully (unexpected). Server sent:")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                print(msg)
            except asyncio.TimeoutError:
                print("No initial message received (connection open).")
            return 0

    except InvalidStatusCode as exc:
        code = exc.status_code
        print(f"Connection rejected with HTTP status: {code}")
        if code == 401:
            print("401 Unauthorized - API key invalid or deployment not configured. Check AZURE_API_KEY and ensure deployment name in endpoint is correct.")
        elif code == 403:
            print("403 Forbidden - API key lacks permissions or is blocked.")
        elif code == 404:
            print("404 Not Found - endpoint or deployment name incorrect.")
        else:
            print("Unhandled HTTP status. Verify endpoint and key.")
        return 1
    except WebSocketException as exc:
        print(f"WebSocket exception: {exc}")
        return 2
    except Exception as exc:
        print(f"General error: {exc}")
        return 3


if __name__ == '__main__':
    code = asyncio.run(run_check())
    sys.exit(code)
