from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship

# ================================
# COMPREHENSIVE CLINIC MODELS
# ================================

class Clinic(SQLModel, table=True):
    """Enhanced clinic model with comprehensive information"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Basic Information
    name: str
    clinic_type: Optional[str] = None  # "General Practice", "Dentistry", "ENT", etc.
    specialties: Optional[str] = None  # JSON array of specialties
    
    # Contact Details
    phone_primary: str = Field(index=True, unique=True)  # Main phone number
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    
    # Address
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = Field(default="India")
    
    # Operational Info
    timezone: str = Field(default="Asia/Kolkata")
    languages_spoken: Optional[str] = None  # JSON array: ["Telugu", "English", "Hindi"]
    
    # Additional Info
    parking_info: Optional[str] = None
    wheelchair_accessible: bool = Field(default=False)
    accepts_walkins: bool = Field(default=True)
    
    # Integration Config
    twilio_phone: str = Field(index=True)
    whatsapp_enabled: bool = Field(default=False)
    whatsapp_api_key: Optional[str] = None
    
    # AI Configuration
    ai_config: Optional[str] = None  # JSON for voice settings
    
    # Rush/Queue Settings
    rush_low_threshold: int = Field(default=3)  # Patients waiting for "Low" rush
    rush_medium_threshold: int = Field(default=7)  # Patients waiting for "Medium" rush
    average_consultation_minutes: int = Field(default=10)  # Avg time per patient
    
    # Legacy fields
    cal_com_api_key: Optional[str] = None
    cal_com_event_type_id: Optional[int] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    providers: List["Provider"] = Relationship(back_populates="clinic")
    services: List["Service"] = Relationship(back_populates="clinic")
    faqs: List["FAQ"] = Relationship(back_populates="clinic")
    sessions: List["ClinicSession"] = Relationship(back_populates="clinic")
    holidays: List["Holiday"] = Relationship(back_populates="clinic")
    users: List["ClinicUser"] = Relationship(back_populates="clinic")


class ClinicUser(SQLModel, table=True):
    """Authentication user for clinic admins/staff"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    
    username: str = Field(index=True, unique=True)
    password_hash: str
    full_name: Optional[str] = None
    role: str = Field(default="admin") # admin, receptionist, doctor
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    clinic: Clinic = Relationship(back_populates="users")



class Provider(SQLModel, table=True):
    """Doctors and clinicians working at the clinic"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    
    # Personal Info
    name: str
    title: str  # "Dr.", "Prof.", etc.
    specialty: str  # "Cardiologist", "General Physician", etc.
    qualifications: Optional[str] = None  # "MBBS, MD", etc.
    
    # Professional Details
    years_of_experience: Optional[int] = None
    languages_spoken: Optional[str] = None  # JSON array
    bio: Optional[str] = None  # Short biography
    education: Optional[str] = None  # Educational background
    
    # Availability
    working_days: Optional[str] = None  # JSON array: ["monday", "tuesday"]
    working_hours: Optional[str] = None  # JSON: {"monday": {"start": "09:00", "end": "17:00"}}
    break_hours: Optional[str] = None  # JSON: lunch/break times
    
    # Booking Config
    default_appointment_duration: int = Field(default=15)  # minutes
    booking_buffer: int = Field(default=0)  # minutes between appointments
    
    # Status
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    clinic: Clinic = Relationship(back_populates="providers")
    visit_types: List["VisitType"] = Relationship(back_populates="provider")


class Service(SQLModel, table=True):
    """Clinic services catalog"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    
    # Service Details
    name: str  # "General Consultation", "Dental Cleaning", "Blood Test"
    description: Optional[str] = None
    category: Optional[str] = None  # "Consultation", "Diagnostic", "Procedure"
    
    # Pricing
    price: float  # in INR
    currency: str = Field(default="INR")
    
    # Timing
    duration_minutes: int  # Standard duration
    
    # Status
    is_active: bool = Field(default=True)
    display_order: Optional[int] = None  # For sorting in UI
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    clinic: Clinic = Relationship(back_populates="services")


class VisitType(SQLModel, table=True):
    """Provider-specific visit types with custom durations"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    provider_id: UUID = Field(foreign_key="provider.id")
    service_id: UUID = Field(foreign_key="service.id")
    
    # Custom configuration for this provider
    duration_minutes: Optional[int] = None  # Override service default
    price: Optional[float] = None  # Override service price
    
    is_active: bool = Field(default=True)
    
    # Relationships
    provider: Provider = Relationship(back_populates="visit_types")


class FAQ(SQLModel, table=True):
    """Frequently Asked Questions knowledge base"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    
    # Question & Answer
    category: str  # "General", "Billing", "Parking", "Services", etc.
    question: str
    answer_english: str
    answer_telugu: Optional[str] = None
    answer_hindi: Optional[str] = None
    
    # Keywords for matching
    keywords: Optional[str] = None  # JSON array for search
    
    # Status
    is_active: bool = Field(default=True)
    display_order: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    clinic: Clinic = Relationship(back_populates="faqs")


class SchedulingRule(SQLModel, table=True):
    """Clinic-wide scheduling policies"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id", unique=True)
    
    # Booking Window
    advance_booking_days: int = Field(default=30)  # How far ahead
    same_day_cutoff_hour: Optional[int] = None  # e.g., 12 for noon
    
    # Approval & Confirmation
    requires_manual_approval: bool = Field(default=False)
    send_confirmation: bool = Field(default=True)
    confirmation_methods: Optional[str] = None  # JSON: ["sms", "whatsapp", "email"]
    
    # Cancellation Policy
    cancellation_hours: int = Field(default=24)  # Notice required
    cancellation_fee_percent: float = Field(default=0.0)  # % of appointment fee
    no_show_fee: Optional[float] = None
    
    # Age Restrictions
    min_patient_age: Optional[int] = None
    max_patient_age: Optional[int] = None
    
    # Other Policies
    allow_reschedule: bool = Field(default=True)
    reschedule_hours: int = Field(default=24)
    max_appointments_per_day: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Holiday(SQLModel, table=True):
    """Clinic holidays and closures"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    
    date: date
    name: str  # "Diwali", "Christmas", "Clinic Annual Maintenance"
    is_recurring: bool = Field(default=False)  # Annual holiday
    affects_all_providers: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    clinic: Clinic = Relationship(back_populates="holidays")


# ================================
# EXISTING APPOINTMENT MODELS
# ================================

class ClinicSession(SQLModel, table=True):
    """Morning/Evening session configuration"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    name: str  # "MORNING", "EVENING"
    start_time: str  # "09:00"
    end_time: str  # "13:00"
    max_tokens: Optional[int] = None
    buffer_minutes: int = Field(default=10)  # Default buffer per patient
    days_of_week: Optional[str] = None  # JSON array: ["monday", "tuesday", ...]
    is_active: bool = Field(default=True)  # Enable/disable sessions
    
    clinic: Clinic = Relationship(back_populates="sessions")


class Doctor(SQLModel, table=True):
    """Legacy doctor model - use Provider for new implementations"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    name: str
    specialization: Optional[str] = None
    cal_com_user_id: Optional[int] = None
    is_active: bool = True


class Appointment(SQLModel, table=True):
    """Patient appointments with token-based system"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    doctor_id: Optional[UUID] = Field(foreign_key="doctor.id", nullable=True)
    session_id: Optional[UUID] = Field(foreign_key="clinicsession.id", nullable=True)
    
    # Token Logic
    token_number: int  # sequential daily ID (1, 2, 3...)
    booking_source: str = Field(default="PHONE")  # PHONE, WALK_IN
    
    # Patient Info
    patient_phone: str
    patient_name: Optional[str] = None
    
    # Timing
    date: str  # YYYY-MM-DD
    estimated_time: Optional[datetime] = None  # For delay management
    
    # State
    status: str = Field(default="BOOKED")  # BOOKED, CANCELLED, COMPLETED, CHECKED_IN
    cal_booking_id: Optional[int] = None  # External Cal.com ID
    whatsapp_confirmation_sent: bool = Field(default=False)
    created_by: str = Field(default="ai")  # "ai" or receptionist username for walk-ins
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallLog(SQLModel, table=True):
    """Call logs with transcripts and classification"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: Optional[UUID] = Field(foreign_key="clinic.id", nullable=True)
    
    caller_phone: str
    twilio_call_sid: str
    direction: str = "INBOUND"
    
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    classification: Optional[str] = None  # enquiry, appointment_booking, scheduling, cancelled, wait_time, revisit, other
    transcript: Optional[str] = None  # Full text
    was_successful: bool = Field(default=False)  # Did call achieve patient's goal?
    termination_reason: Optional[str] = None  # "completed", "timeout", "guard_rail", "user_hangup"
    appointment_id: Optional[UUID] = Field(foreign_key="appointment.id", nullable=True)  # Link to booked appointment


class KnowledgeBase(SQLModel, table=True):
    """Legacy knowledge base - use FAQ for new implementations"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clinic_id: UUID = Field(foreign_key="clinic.id")
    category: str  # e.g. "hours", "services", "location", "pricing"
    question_pattern: str  # Regex or keywords to match user query
    response_telugu: Optional[str] = None
    response_english: Optional[str] = None
    is_active: bool = Field(default=True)
