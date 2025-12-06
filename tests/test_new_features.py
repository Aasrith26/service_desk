import unittest
import os
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import ClinicDatabase
import re

class TestClinicSystem(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for testing
        self.test_db_path = "data/test_appointments.csv"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = ClinicDatabase(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_database_initialization(self):
        self.assertTrue(os.path.exists(self.test_db_path))
        with open(self.test_db_path, "r") as f:
            header = f.readline().strip()
            self.assertEqual(header, "Doctor,Date,Time,Status,PatientName,PatientPhone,BookedAt")

    def test_add_and_get_slots(self):
        self.db.add_slot("Dr. Test", "2025-01-01", "10:00 AM")
        slots = self.db.get_available_slots()
        self.assertIn("Dr. Test", slots)
        self.assertIn("2025-01-01", slots["Dr. Test"])
        self.assertIn("10:00 AM", slots["Dr. Test"]["2025-01-01"])

    def test_book_slot(self):
        self.db.add_slot("Dr. Test", "2025-01-01", "10:00 AM")
        success = self.db.book_slot("Dr. Test", "2025-01-01", "10:00 AM", "John Doe", "1234567890")
        self.assertTrue(success)
        
        # Verify it's booked
        slots = self.db.get_available_slots()
        # Should be empty or not contain this slot
        if "Dr. Test" in slots and "2025-01-01" in slots["Dr. Test"]:
            self.assertNotIn("10:00 AM", slots["Dr. Test"]["2025-01-01"])

    def test_regex_parsing(self):
        text = "Sure, I'll book that. [BOOK_ACTION | Dr. Smith | 2025-10-10 | 10:00 AM | John | 555-1234]"
        pattern = r"\[BOOK_ACTION\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\]"
        match = re.search(pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "Dr. Smith")
        self.assertEqual(match.group(5).strip(), "555-1234")

    def test_regex_parsing_messy(self):
        text = "[BOOK_ACTION|Dr. Smith|2025-10-10|10:00 AM|John|555-1234]"
        pattern = r"\[BOOK_ACTION\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\]"
        match = re.search(pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "Dr. Smith")

if __name__ == "__main__":
    unittest.main()
