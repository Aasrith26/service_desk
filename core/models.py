from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, JSON

class Clinic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone_number: str = Field(index=True) # Twilio number
    timezone: str = "UTC"
    config: dict = Field(default={}, sa_type=JSON) 

class Doctor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinic.id")
    name: str
    specialization: str
    cal_com_user_id: Optional[str] = None
    is_active: bool = True
    
    clinic: Clinic = Relationship()

class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: Optional[str] = None # Cal.com booking ID
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_phone: str
    patient_name: Optional[str] = None
    
    start_time: datetime
    end_time: datetime
    
    # Token System
    token_number: int 
    estimated_start_time: datetime
    status: str = "BOOKED" # BOOKED, CANCELLED, COMPLETED, DELAYED
    
    doctor: Doctor = Relationship()
