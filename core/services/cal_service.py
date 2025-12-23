import os
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class CalService:
    """
    Wrapper for Cal.com v1/v2 API.
    Handles Booking, Slot Checking, Booking Cancellation, and Rescheduling.
    """
    def __init__(self, api_key: str, event_type_id: int):
        self.api_key = api_key
        self.event_type_id = event_type_id
        self.base_url = "https://api.cal.com/v1" 

    async def get_available_slots(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetches available slots from Cal.com for the given range.
        start_date, end_date: ISO 8601 strings (YYYY-MM-DD)
        """
        params = {
            "apiKey": self.api_key,
            "eventTypeId": self.event_type_id,
            "startTime": start_date,
            "endTime": end_date
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Note: Endpoint structure varies based on Cal.com version, assuming /slots here
                # In v2 typically: /slots?eventTypeId=...
                url = f"{self.base_url}/slots"
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("slots", {})
                    else:
                        logger.error(f"Cal.com Slots Error: {resp.status} - {await resp.text()}")
                        return []
            except Exception as e:
                logger.error(f"Cal.com Connection Error: {e}")
                return []

    async def create_booking(self, 
                             name: str, 
                             email: str, 
                             start_time: str, 
                             phone: str = "",
                             metadata: Dict = {}) -> Optional[int]:
        """
        Creates a booking on Cal.com.
        Returns the external booking_id if successful.
        """
        payload = {
            "eventTypeId": self.event_type_id,
            "start": start_time,
            "responses": {
                "name": name,
                "email": email,
                "phone": phone,
                **metadata
            },
            "metadata": metadata,
            "timeZone": "Asia/Kolkata", # TODO: Make dynamic
            "language": "en"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/bookings?apiKey={self.api_key}"
                async with session.post(url, json=payload) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        return data.get("id") # The Booking ID
                    else:
                        logger.error(f"Cal.com Booking Error: {resp.status} - {await resp.text()}")
                        return None
            except Exception as e:
                logger.error(f"Cal.com Create Error: {e}")
                return None

    async def cancel_booking(self, booking_id: int, reason: str = "User requested cancellation") -> bool:
        """
        Cancels a booking by ID.
        """
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/bookings/{booking_id}/cancel?apiKey={self.api_key}"
                payload = {"cancellationReason": reason}
                async with session.delete(url, json=payload) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        logger.error(f"Cal.com Cancel Error: {resp.status} - {await resp.text()}")
                        return False
            except Exception as e:
                logger.error(f"Cal.com Cancel Exception: {e}")
                return False

    async def reschedule_booking(self, booking_id: int, new_start_time: str) -> bool:
        """
        Reschedules a booking. 
        Cal.com uses PATCH /bookings/{id} with new start time.
        """
        payload = {
            "start": new_start_time
        }
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/bookings/{booking_id}?apiKey={self.api_key}"
                async with session.patch(url, json=payload) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        logger.error(f"Cal.com Reschedule Error: {resp.status} - {await resp.text()}")
                        return False
            except Exception as e:
                logger.error(f"Cal.com Reschedule Exception: {e}")
                return False
