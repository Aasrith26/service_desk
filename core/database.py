import csv
import os
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ClinicDatabase:
    def __init__(self, db_path="data/appointments.csv"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Creates the CSV file with headers if it doesn't exist."""
        path = Path(self.db_path)
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Doctor", "Date", "Time", "Status", "PatientName", "PatientPhone", "BookedAt"])
                logger.info(f"Initialized new database at {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")

    def get_available_slots(self):
        """Reads the CSV and returns a dictionary of available slots."""
        slots = {}
        if not os.path.exists(self.db_path):
            return slots

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Status"] == "available":
                        doctor = row["Doctor"]
                        date = row["Date"]
                        time = row["Time"]
                        
                        if doctor not in slots:
                            slots[doctor] = {}
                        if date not in slots[doctor]:
                            slots[doctor][date] = []
                        
                        slots[doctor][date].append(time)
            return slots
        except Exception as e:
            logger.error(f"Error reading database: {e}")
            return {}


    def is_slot_available(self, doctor, date, time):
        """Check if a specific slot is available for booking."""
        try:
            if not os.path.exists(self.db_path):
                return False
                
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row["Doctor"] == doctor and 
                        row["Date"] == date and 
                        row["Time"] == time):
                        return row["Status"] == "available"
            return False
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False

    def book_slot(self, doctor, date, time, patient_name, patient_phone):
        """Updates a slot status to 'booked' and adds patient details."""
        if not os.path.exists(self.db_path):
            return False

        rows = []
        updated = False
        
        try:
            # Read all rows
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    # Check if this is the slot we want to book
                    if (row["Doctor"] == doctor and 
                        row["Date"] == date and 
                        row["Time"] == time and 
                        row["Status"] == "available"):
                        
                        row["Status"] = "booked"
                        row["PatientName"] = patient_name
                        row["PatientPhone"] = patient_phone
                        row["BookedAt"] = datetime.now().isoformat()
                        updated = True
                    rows.append(row)

            # Write back if updated
            if updated:
                with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                logger.info(f"Successfully booked slot for {doctor} on {date} at {time}")
                return True
            else:
                logger.warning(f"Slot not found or already booked: {doctor} {date} {time}")
                return False

        except Exception as e:
            logger.error(f"Error updating database: {e}")
            return False

    def add_slot(self, doctor, date, time):
        """Helper to add a new available slot (for testing/setup)."""
        if not os.path.exists(self.db_path):
            self._initialize_db()
            
        try:
            with open(self.db_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([doctor, date, time, "available", "", "", ""])
            return True
        except Exception as e:
            logger.error(f"Error adding slot: {e}")
            return False
