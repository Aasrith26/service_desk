"""
MINIMAL TEST - Find the error
"""

import sys
import traceback

print("[TEST] Step 1: Starting imports...")

try:
    from core.realtime_client import RealtimeClient
    print("[TEST] ✓ RealtimeClient imported")
except Exception as e:
    print(f"[TEST] ✗ RealtimeClient import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from core.callback_manager import CallbackManager
    print("[TEST] ✓ CallbackManager imported")
except Exception as e:
    print(f"[TEST] ✗ CallbackManager import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from core.audio_streamer import AudioStreamingEngine
    print("[TEST] ✓ AudioStreamingEngine imported")
except Exception as e:
    print(f"[TEST] ✗ AudioStreamingEngine import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Step 2: Creating RealtimeClient...")
try:
    realtime_client = RealtimeClient()
    print("[TEST] ✓ RealtimeClient created")
except Exception as e:
    print(f"[TEST] ✗ RealtimeClient creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Step 3: Creating CallbackManager...")
try:
    callback_manager = CallbackManager(realtime_client)
    print("[TEST] ✓ CallbackManager created")
except Exception as e:
    print(f"[TEST] ✗ CallbackManager creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Step 4: Creating AudioStreamingEngine...")
try:
    engine = AudioStreamingEngine(realtime_client, callback_manager)
    print("[TEST] ✓ AudioStreamingEngine created")
except Exception as e:
    print(f"[TEST] ✗ AudioStreamingEngine creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Step 5: Testing async operations...")

import asyncio

async def test_async():
    print("[TEST] Inside async function")
    try:
        print("[TEST] Attempting to connect...")
        success = await realtime_client.connect()
        print(f"[TEST] Connect result: {success}")
    except Exception as e:
        print(f"[TEST] ✗ Async operation failed: {e}")
        traceback.print_exc()

try:
    print("[TEST] Running asyncio.run()...")
    asyncio.run(test_async())
    print("[TEST] ✓ Asyncio completed")
except Exception as e:
    print(f"[TEST] ✗ Asyncio.run failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[TEST] ✓✓✓ ALL TESTS PASSED ✓✓✓")
