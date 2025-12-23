"""
UPDATED: core/realtime_client.py
- LOGIC: Server-side VAD with strict booking confirmation
"""

import asyncio
import json
import websockets
from config.settings import AZURE_REALTIME_ENDPOINT, AZURE_API_KEY
from utils.logger import get_logger
from utils.audio_utils import pcm_to_base64, base64_to_pcm
from core.context_retriever import ContextRetriever

logger = get_logger(__name__)

class RealtimeClient:
    def __init__(self, on_audio_received=None, on_text_received=None, on_response_done=None, on_call_ended=None, on_interruption=None, caller_phone=None):
        self.ws = None
        self.is_connected = False
        self.caller_phone = caller_phone or "Unknown"  # Auto-captured from Exotel
        self.on_audio_received = on_audio_received
        self.on_text_received = on_text_received
        self.on_response_done = on_response_done
        self.on_call_ended = on_call_ended
        self.on_interruption = on_interruption
        self.ignore_audio = False 
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
            logger.info("Session initialized. Ready for voice input...")
            return True
        except Exception as e:
            logger.error(f"Connect Error: {e}")
            return False

    async def _init_session(self):
        context = self.context_retriever.get_context()

        instructions = f"""
        ROLE: You are Sneha, a warm receptionist at Health Plus Clinic,Help pateints with all sorts of clinic information.
        Always be kind and helpful.
        LANGUAGE: Speak naturally in Telugu/Hinglish mix.
        Examples: "Okay sir, check చేస్తాను", "Name ఏమిటి?", "Slot available ఉందా చూద్దాం"
        
        AVAILABLE TOOLS:
        You have 3 tools to help with bookings:
        1. **check_slot_availability**: Check if a specific slot is free (use BEFORE confirming!)
        2. **book_appointment**: Book after getting confirmation from patient
        3. **get_available_slots**: Get all available slots for a doctor/date
        
        BOOKING PROCESS:
        1. When user requests appointment, use get_available_slots or check_slot_availability
        2. Collect: doctor, date, time, patient name (in Latin script)
        3. DO NOT ask for phone number - it is automatically captured from the call
        4. BEFORE booking, confirm ALL details with user
        5. ONLY after user says "yes/OK/సరే", call book_appointment tool
        6. ENDING THE CALL (FOLLOW THIS EXACTLY):
           - First ask: "Inkemina help kavala?" or "Is there anything else?"
           - Wait for their response
           - When they say no/bye/done:
             1. Say a warm goodbye: "Thank you for calling! Have a great day!" 
             2. THEN call the end_call tool
           - NEVER hang up without saying goodbye first!
        
        TIME FORMAT (VERY IMPORTANT):
        - NEVER say times in 24-hour format like "nineteen hundred" or "1900"
        - ALWAYS use 12-hour format with AM/PM: "7 PM", "10 AM", "3:30 PM"
        - Say times naturally: "evening 7 PM", "morning 10 AM"
        - WRONG: "19:00", "1900", "nineteen hundred"
        - CORRECT: "7 PM", "evening 7 o'clock"
        
        PRONUNCIATION:
        - Say "appointment" clearly, NOT "appoint"
        - Pronounce all words completely
        
        STYLE:
        - Keep responses SHORT - this is a phone call!
        - Mix Telugu and English naturally
        - Always check availability with tools before confirming
        - Don't make up availability - use the tools!
        
        {context}
        """
        
        tools = [
            {
                "type": "function",
                "name": "check_slot_availability",
                "description": "Check if a specific appointment slot is available in real-time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor": {"type": "string", "description": "Doctor name (e.g., 'Dr. Rajesh Patel')"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Time in HH:MM format"}
                    },
                    "required": ["doctor", "date", "time"]
                }
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Book an appointment after confirming all details with patient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor": {"type": "string", "description": "Doctor name"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Time in HH:MM format"},
                        "patient_name": {"type": "string", "description": "Patient name in Latin script"},
                        "patient_phone": {"type": "string", "description": "Patient phone number (optional - auto-captured from call)"}
                    },
                    "required": ["doctor", "date", "time", "patient_name"]
                }
            },
            {
                "type": "function",
                "name": "get_available_slots",
                "description": "Get list of available slots for a specific doctor and date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor": {"type": "string", "description": "Doctor name (optional)"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional)"}
                    }
                }
            },
            {
                    "type": "function",
                    "name": "end_call",
                    "description": "Call this AFTER you have spoken your final goodbye message. This will disconnect the phone.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
            }
        ]
        
        await self.ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": instructions,
                "voice": "shimmer", 
                "input_audio_format": "pcm16", 
                "output_audio_format": "pcm16",
                "tools": tools,
                "tool_choice": "auto",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 1500
                },
                "temperature": 0.6
            }
        }))

    async def send_audio(self, audio_data: bytes):
        if self.ws:
            try:
                await self.ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": pcm_to_base64(audio_data)
                }))
            except Exception as e:
                logger.error(f"Send audio error: {e}")

    async def listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                
                # DEBUG: Log all event types
                event_type = data.get('type', 'unknown')
                logger.info(f"Event: {event_type}")
                
                # HANDLING SERVER EVENTS
                if event_type == 'input_audio_buffer.speech_started':
                    logger.info("Interruption detected! Cancelling response...")
                    self.ignore_audio = True  # GATE: Block audio immediately
                    await self.cancel_response()
                    if self.on_interruption:
                         await self._call(self.on_interruption)

                elif event_type == 'response.created':
                    logger.info("New response started. Unblocking audio.")
                    self.ignore_audio = False # GATE: Open gate for new response

                elif event_type == 'response.audio.delta' and self.on_audio_received:
                    if self.ignore_audio:
                        # logger.debug("Dropped stale audio packet")
                        pass
                    else:
                        await self._call(self.on_audio_received, base64_to_pcm(data['delta']))
                
                # AUDIO TRANSCRIPT EVENTS
                elif data['type'] == 'response.audio_transcript.delta':
                    text_chunk = data.get('delta', '')
                    logger.debug(f"Transcript Delta: {text_chunk}")
                
                elif data['type'] == 'response.audio_transcript.done':
                    text_full = data.get('transcript', '')
                    logger.info(f"TRANSCRIPT: {text_full}")
                    if self.on_text_received and text_full:
                        await self._call(self.on_text_received, text_full)
                
                # FUNCTION CALL HANDLING
                elif data['type'] == 'response.function_call_arguments.done':
                    call_id = data.get('call_id')
                    function_name = data.get('name')
                    arguments_str = data.get('arguments', '{}')
                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError as e:
                        logger.warning(f'Function call interrupted - incomplete JSON: {e}')
                        continue
                    
                    logger.info(f"Function called: {function_name} with {arguments}")
                    
                    # Execute function and get result
                    result = await self._execute_function(function_name, arguments)
                    
                    # Send result back to model
                    await self.ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result)
                        }
                    }))
                    
                    # Trigger response with function result
                    await self.ws.send(json.dumps({"type": "response.create"}))
                
                elif data['type'] == 'response.done' and self.on_response_done:
                    await self._call(self.on_response_done)
                    
                # Input Transcript
                elif data['type'] == 'conversation.item.input_audio_transcription.completed':
                    logger.info(f"User said: {data.get('transcript', '')}")
                    
        except Exception as e:
            logger.error(f"Listen error: {e}")
        finally: 
            self.is_connected = False

    async def _call(self, cb, *args):
        if asyncio.iscoroutinefunction(cb): 
            await cb(*args)
        else: 
            cb(*args)
    
    async def trigger_response(self):
        """Manually trigger model response (used for local VAD - currently disabled)"""
        if self.ws:
            await self.ws.send(json.dumps({
                "type": "response.create"
            }))

    async def cancel_response(self):
        """Cancel ongoing response (used for interruption)"""
        if self.ws:
            await self.ws.send(json.dumps({
                "type": "response.cancel"
            }))
    
    async def _execute_function(self, function_name, arguments):
        """Execute a function call and return the result"""
        try:
            if function_name == "check_slot_availability":
                doctor = arguments.get("doctor")
                date = arguments.get("date")
                time = arguments.get("time")
                
                is_available = self.context_retriever.db.is_slot_available(doctor, date, time)
                return {
                    "available": is_available,
                    "doctor": doctor,
                    "date": date,
                    "time": time,
                    "message": f"Slot is {'available' if is_available else 'already booked'}"
                }
            
            elif function_name == "book_appointment":
                doctor = arguments.get("doctor")
                date = arguments.get("date")
                time = arguments.get("time")
                patient_name = arguments.get("patient_name")
                # Use auto-captured phone from Exotel if not provided
                patient_phone = arguments.get("patient_phone") or self.caller_phone
                
                success = self.context_retriever.db.book_slot(doctor, date, time, patient_name, patient_phone)
                return {
                    "success": success,
                    "message": f"{'Successfully booked' if success else 'Failed - slot not available'} appointment for {patient_name}"
                }
            
            elif function_name == "get_available_slots":
                doctor = arguments.get("doctor")
                date = arguments.get("date")
                
                all_slots = self.context_retriever.db.get_available_slots()
                
                # Filter by doctor and/or date if provided
                result_slots = {}
                for doc, dates in all_slots.items():
                    if doctor and doctor not in doc:
                        continue
                    result_slots[doc] = {}
                    for dt, times in dates.items():
                        if date and date != dt:
                            continue
                        result_slots[doc][dt] = times
                
                return {
                    "available_slots": result_slots,
                    "message": f"Found {sum(len(times) for dates in result_slots.values() for times in dates.values())} available slots"
                }
            
            elif function_name == "end_call":
                if self.on_call_ended:
                    # We can schedule the disconnect
                    asyncio.create_task(self._call(self.on_call_ended))
                return {"message": "Call ended"}
            
            else:
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Function execution error: {e}")
            return {"error": str(e)}

    async def disconnect(self):
        if self.ws: 
            await self.ws.close()