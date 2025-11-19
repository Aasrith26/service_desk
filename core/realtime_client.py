import asyncio
import json
import websockets
from config.settings import AZURE_REALTIME_ENDPOINT, AZURE_API_KEY
from utils.audio_utils import pcm_to_base64, base64_to_pcm
from core.context_retriever import ContextRetriever

class RealtimeClient:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.on_audio_received = None
        self.on_text_received = None
        self.on_response_done = None
        self.context_retriever = ContextRetriever()

    async def connect(self):
        try:
            headers = { "api-key": AZURE_API_KEY }
            self.ws = await asyncio.wait_for(
                websockets.connect(AZURE_REALTIME_ENDPOINT, additional_headers=headers, subprotocols=["realtime"], ping_interval=None),
                timeout=10
            )
            self.is_connected = True
            await self._init_session()
            return True
        except Exception as e:
            print(f"Connect Error: {e}")
            return False

    async def _init_session(self):
        kb = self.context_retriever.get_context()
        
        instructions = f'''
        You are "Sneha", a receptionist at Health Plus Clinic.
        Speak primarily in TELUGU.
        
        CONTEXT:
        {kb}
        
        INSTRUCTIONS:
        1. Be warm and human-like.
        2. If interrupted, stop speaking immediately.
        3. Only answer questions related to the clinic.
        '''
        
        await self.ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "instructions": instructions,
                "voice": "shimmer", 
                # Azure defaults to 24kHz for pcm16
                "input_audio_format": "pcm16", 
                "output_audio_format": "pcm16",
                "turn_detection": None
            }
        }))

    async def send_audio(self, audio_data: bytes):
        if self.ws:
            try:
                await self.ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": pcm_to_base64(audio_data)
                }))
            except: pass

    async def trigger_response(self):
        if self.ws:
            await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            await self.ws.send(json.dumps({"type": "response.create"}))

    async def cancel_response(self):
        if self.ws: 
            await self.ws.send(json.dumps({"type": "response.cancel"}))
            # Clear server buffer to prevent old audio from processing
            await self.ws.send(json.dumps({"type": "input_audio_buffer.clear"}))

    async def listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                if data['type'] == 'response.audio.delta' and self.on_audio_received:
                    await self._call(self.on_audio_received, base64_to_pcm(data['delta']))
                elif data['type'] == 'response.text.delta' and self.on_text_received:
                    await self._call(self.on_text_received, data['delta'], True)
                elif data['type'] == 'response.done' and self.on_response_done:
                    await self._call(self.on_response_done)
        except: pass
        finally: self.is_connected = False

    async def _call(self, cb, *args):
        if asyncio.iscoroutinefunction(cb): await cb(*args)
        else: cb(*args)
    
    async def disconnect(self):
        if self.ws: await self.ws.close()