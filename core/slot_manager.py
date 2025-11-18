"""
Simple slot manager to extract appointment-related slots from model text.

This is a lightweight implementation: it looks for doctor names, dates, times,
and basic confirmations in the model's final text. It is not a full NLU but
is sufficient to demonstrate slot handling and can be extended later.
"""

import re
from typing import Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class SlotManager:
    def __init__(self):
        # Simple slot store
        self.slots: Dict[str, Optional[str]] = {
            'doctor': None,
            'date': None,
            'time': None,
            'patient_name': None,
            'confirmed': None,
        }

    def reset(self):
        for k in self.slots:
            self.slots[k] = None

    def update_from_text(self, text: str):
        """Try to extract slots from free text using simple heuristics."""
        t = text.lower()

        # Doctor names (from clinic data we have Kavya, Rajesh, Priya)
        if 'kavya' in t:
            self.slots['doctor'] = 'Dr. Kavya'
        if 'rajesh' in t:
            self.slots['doctor'] = 'Dr. Rajesh'
        if 'priya' in t:
            self.slots['doctor'] = 'Dr. Priya'

        # Dates - naive patterns: tomorrow, today, yyyy-mm-dd, dd/mm
        if 'tomorrow' in t:
            self.slots['date'] = 'tomorrow'
        if 'today' in t:
            self.slots['date'] = 'today'
        m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
        if m:
            self.slots['date'] = m.group(1)
        m2 = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", text)
        if m2:
            self.slots['date'] = m2.group(1)

        # Times - naive hh:mm or h am/pm
        m = re.search(r"(\d{1,2}:\d{2})", t)
        if m:
            self.slots['time'] = m.group(1)
        m2 = re.search(r"(\d{1,2}\s?(?:am|pm))", t)
        if m2:
            self.slots['time'] = m2.group(1)

        # Confirmations
        if any(w in t for w in ['yes', 'confirm', 'confirmed', 'ok', 'okay']):
            self.slots['confirmed'] = 'yes'
        if any(w in t for w in ['no', 'not', 'cancel']):
            self.slots['confirmed'] = 'no'

        logger.debug(f"Slots updated: {self.slots}")
        return self.slots

    def get_slots(self) -> Dict[str, Optional[str]]:
        return dict(self.slots)
