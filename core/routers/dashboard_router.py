from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, desc, func
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from uuid import UUID
from core.db_engine import engine
from core.models_sql import Appointment, Clinic, Doctor, CallLog, ClinicUser, ClinicSession
from core.services.token_service import TokenService
from pydantic import BaseModel
from passlib.context import CryptContext

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    clinic_id: str
    clinic_name: str
    username: str
    full_name: str

@router.post("/login", response_model=LoginResponse)
async def login(creds: LoginRequest):
    with Session(engine) as session:
        # Normalize username
        username = creds.username.lower().strip()
        user = session.exec(select(ClinicUser).where(ClinicUser.username == username)).first()
        
        if not user or not pwd_context.verify(creds.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Determine clinic name
        clinic = session.get(Clinic, user.clinic_id)
        clinic_name = clinic.name if clinic else "Unknown Clinic"
        
        return {
            "success": True, 
            "clinic_id": str(user.clinic_id), 
            "clinic_name": clinic_name,
            "username": user.username,
            "full_name": user.full_name or user.username
        }

# --- Pydantic Models for Response ---

class StatCard(BaseModel):
    label: str
    value: str
    trend: Optional[str] = None
    icon: str
    color: str

class DashboardStats(BaseModel):
    cards: List[StatCard]
    
class ClinicResponse(BaseModel):
    id: str # UUID
    name: str

class DoctorResponse(BaseModel):
    id: str # UUID
    name: str
    specialization: Optional[str] = None

class AppointmentCreate(BaseModel):
    clinic_id: str # UUID
    doctor_id: str # UUID
    patient_name: str
    patient_phone: str
    date: str # ISO string "YYYY-MM-DD"
    time: str # "HH:MM"
    duration: int = 15
    notes: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    name: str # MORNING, EVENING
    start_time: str # "09:00"
    end_time: str # "13:00"

# --- Endpoints ---

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(clinic_id: Optional[str] = None):
    with Session(engine) as session:
        query = select(ClinicSession).where(ClinicSession.is_active == True)
        if clinic_id:
             query = query.where(ClinicSession.clinic_id == UUID(clinic_id))
        
        sessions = session.exec(query).all()
        return [
            SessionResponse(
                id=str(s.id),
                name=s.name,
                start_time=s.start_time,
                end_time=s.end_time
            ) for s in sessions
        ]

@router.get("/clinics", response_model=List[ClinicResponse])
async def get_clinics():
    with Session(engine) as session:
        clinics = session.exec(select(Clinic)).all()
        return [{"id": str(c.id), "name": c.name} for c in clinics]

@router.get("/doctors", response_model=List[DoctorResponse])
async def get_doctors(clinic_id: Optional[str] = None):
    with Session(engine) as session:
        query = select(Doctor)
        if clinic_id:
            query = query.where(Doctor.clinic_id == UUID(clinic_id))
        doctors = session.exec(query).all()
        return [{"id": str(d.id), "name": d.name, "specialization": d.specialization} for d in doctors]

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(clinic_id: Optional[str] = None):
    with Session(engine) as session:
        # Determine date range (today)
        today = date.today()
        
        # 1. Total Calls Today
        # SQLite doesn't have func.date easily compatible sometimes without cast, but try basic first
        # Python filtering is safer for small datasets if SQL fails
        call_query = select(CallLog)
        if clinic_id:
            call_query = call_query.where(CallLog.clinic_id == UUID(clinic_id))
        
        all_calls = session.exec(call_query).all()
        calls_today = sum(1 for c in all_calls if c.start_time.date() == today)
        
        # 2. Appointments Today
        appt_query = select(Appointment)
        if clinic_id:
            appt_query = appt_query.where(Appointment.clinic_id == UUID(clinic_id))
        
        all_appts = session.exec(appt_query).all()
        appts_today = sum(1 for a in all_appts if a.date == today.isoformat())
        
        # 3. Available Slots (Mock logic for now or calculate)
        total_capacity = 40 # Mock capacity
        available = max(0, total_capacity - appts_today)

        return DashboardStats(cards=[
            StatCard(label="Incoming Calls", value=str(calls_today), trend="Today", icon="phone_in_talk", color="blue"),
            StatCard(label="Appointments", value=str(appts_today), trend=f"{available} slots left", icon="calendar_today", color="teal"),
            StatCard(label="AI Success Rate", value="98%", trend="Last 24h", icon="smart_toy", color="orange"), # Mock for now
        ])

@router.get("/appointments")
async def get_appointments(
    date_str: Optional[str] = Query(None, alias="date"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    clinic_id: Optional[str] = None
):
    """
    Fetch appointments. Filter by specific date OR date range.
    """
    with Session(engine) as session:
        query = select(Appointment)
        
        if clinic_id:
            query = query.where(Appointment.clinic_id == UUID(clinic_id))
            
        if date_str:
             query = query.where(Appointment.date == date_str)
        elif start_date and end_date:
             query = query.where(Appointment.date >= start_date, Appointment.date <= end_date)
        
        appointments = session.exec(query).all()
        
        results = []
        for apt in appointments:
            # Fetch doctor name
            doc_name = "Unknown Doctor"
            if apt.doctor_id:
                doc = session.get(Doctor, apt.doctor_id)
                if doc:
                    doc_name = doc.name
            
            # Safe time extraction
            time_str = "00:00"
            if apt.estimated_time:
                time_str = apt.estimated_time.strftime("%H:%M")
            elif apt.time and isinstance(apt.time, str): # Fallback if model changed
                time_str = apt.time
            
            results.append({
                "id": str(apt.id),
                "date": apt.date, # Added date
                "time": time_str,
                "duration": 15, 
                "patient_name": apt.patient_name or f"Patient {apt.patient_phone}",
                "patient_phone": apt.patient_phone,
                "doctor_name": doc_name,
                "doctor_id": str(apt.doctor_id) if apt.doctor_id else None,
                "status": apt.status,
                "type": "Walk-in" if apt.booking_source == "DASHBOARD" else "Consultation",
                "token_number": apt.token_number
            })
        return results

@router.post("/appointments")
async def create_appointment(appt: AppointmentCreate):
    # Use TokenService for consistent booking logic
    result = TokenService.generate_token(
        patient_name=appt.patient_name,
        patient_phone=appt.patient_phone,
        date=appt.date,
        requested_time=appt.time,
        doctor_id=UUID(appt.doctor_id),
        source="DASHBOARD",
        created_by="admin"
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return {"success": True, "appointment_id": result.get("appointment_id")}

# --- Call Logs Endpoint ---

class CallLogResponse(BaseModel):
    id: str
    caller_phone: str
    start_time: str
    duration_seconds: Optional[int] = 0
    classification: Optional[str] = "General"
    transcript: Optional[str] = None
    was_successful: bool
    sentiment: Optional[str] = "Neutral" # Mock/Future

@router.get("/calls", response_model=List[CallLogResponse])
async def get_call_logs(clinic_id: Optional[str] = None, limit: int = 50):
    with Session(engine) as session:
        query = select(CallLog).order_by(desc(CallLog.start_time)).limit(limit)
        
        if clinic_id:
            query = query.where(CallLog.clinic_id == UUID(clinic_id))
            
        logs = session.exec(query).all()
        
        return [
            CallLogResponse(
                id=str(l.id),
                caller_phone=l.caller_phone,
                start_time=l.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                duration_seconds=l.duration_seconds,
                classification=l.classification or "General",
                transcript=l.transcript,
                was_successful=l.was_successful
            ) for l in logs
        ]

# --- Queue Management Endpoints ---

@router.get("/queue")
async def get_queue_status(clinic_id: str, date_str: Optional[str] = None):
    """Get current queue status for a clinic"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    status = TokenService.get_queue_status(UUID(clinic_id), date_str)
    return status

class TokenStatusUpdate(BaseModel):
    appointment_id: str
    status: str # VISITED, SKIPPED, SERVING, NO_SHOW, BOOKED

@router.post("/queue/status")
async def update_token_status(update: TokenStatusUpdate):
    """Update status of a specific token"""
    result = TokenService.update_token_status(UUID(update.appointment_id), update.status)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/queue/next")
async def call_next_token(clinic_id: str):
    """
    Call the next available token in the waiting list.
    Marks current serving as VISITED (if any) and sets next waiting as SERVING.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    status = TokenService.get_queue_status(UUID(clinic_id), date_str)
    
    if "error" in status:
        raise HTTPException(status_code=500, detail=status["error"])
        
    waiting_list = status.get("waiting", [])
    if not waiting_list:
        return {"success": False, "message": "No patients waiting"}
        
    # Get first person in line
    next_patient = waiting_list[0]
    
    # Update status to SERVING
    # Use 'id' from the serialized appointment object
    result = TokenService.update_token_status(UUID(next_patient["id"]), "SERVING")
    
    return {
        "success": True,
        "message": f"Now serving Token {next_patient['token_number']}",
        "token": next_patient['token_number'],
        "patient": next_patient['patient_name']
    }
