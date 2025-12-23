import requests
import random
from datetime import datetime, timedelta
import uuid

BASE_URL = "http://127.0.0.1:8000/dashboard"

def seed_data():
    # 1. Get Clinics
    try:
        resp = requests.get(f"{BASE_URL}/clinics")
        clinics = resp.json()
        if not clinics:
            print("No clinics found.")
            return
        clinic_id = clinics[0]['id']
        print(f"Using Clinic: {clinic_id}")
    except Exception as e:
        print(f"Error fetching clinics: {e}")
        return

    # 2. Get Doctors
    try:
        resp = requests.get(f"{BASE_URL}/doctors?clinic_id={clinic_id}")
        doctors = resp.json()
        if not doctors:
            print("No doctors found.")
            return
        print(f"Found {len(doctors)} doctors.")
    except Exception as e:
        print(f"Error fetching doctors: {e}")
        return

    # 3. Create Appointments
    start_date = datetime(2025, 12, 1)
    end_date = datetime(2025, 12, 31)
    
    current = start_date
    count = 0
    
    while current <= end_date:
        num_appts = random.randint(1, 8) # Ensure at least some data
        if current.weekday() >= 5: num_appts = random.randint(5, 12)
        
        for _ in range(num_appts):
            doc = random.choice(doctors)
            hour = random.randint(9, 17)
            minute = random.choice([0, 15, 30, 45])
            time_str = f"{hour:02d}:{minute:02d}"
            
            payload = {
                "clinic_id": clinic_id,
                "doctor_id": doc['id'],
                "patient_name": f"Patient {random.randint(100, 999)}",
                "patient_phone": f"+1555{random.randint(100000, 999999)}",
                "date": current.strftime("%Y-%m-%d"),
                "time": time_str,
                "duration": 15
            }
            
            try:
                # The create_appointment endpoint might have validation logic (e.g. past dates)
                # But for seeding, we hope it allows it or we might need to bypass validation.
                # Step 1120 showed: if appt_dt < now: raise HTTPException
                # So we can ONLY seed FUTURE appointments via API if that check is strict.
                # BUT the user wants to see "previous days".
                # I might need to temporarily disable that check in server.py or use a "force" flag.
                # OR, I just seed future dates (Dec 18-31) and maybe some today.
                # Wait, if I can't seed past dates via API, I'm stuck.
                # Let's try to seed anyway, maybe the check is only for "booking" logic and not "admin" logic?
                # The endpoint is generic.
                
                # Let's try to seed. If it fails for past dates, I'll know.
                resp = requests.post(f"{BASE_URL}/appointments", json=payload)
                if resp.status_code == 200:
                    count += 1
                    print(f"Created appt on {payload['date']}")
                else:
                    print(f"Failed {payload['date']}: {resp.text}")
            except Exception as e:
                print(f"Error creating appt: {e}")
                
        current += timedelta(days=1)
        
    print(f"Seeding complete. Created {count} appointments.")

if __name__ == "__main__":
    seed_data()
