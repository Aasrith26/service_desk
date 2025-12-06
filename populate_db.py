from core.database import ClinicDatabase
from datetime import datetime, timedelta

db = ClinicDatabase()

# Doctors from knowledge base
doctors = ["Dr. Kavya Sharma", "Dr. Rajesh Patel", "Dr. Priya Desai"]

# Add slots for today + 1 and today + 2
base_date = datetime.now().date()
dates = [base_date + timedelta(days=1), base_date + timedelta(days=2)]

times = ["10:00", "11:00", "16:00", "17:00"]

print("Populating DB with test slots...")
count = 0
for date in dates:
    date_str = date.strftime("%Y-%m-%d")
    for doc in doctors:
        for t in times:
            if db.add_slot(doc, date_str, t):
                print(f"Added: {doc} | {date_str} | {t}")
                count += 1

print(f"Done. Added {count} slots.")
