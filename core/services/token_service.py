"""
Token Management Service
Handles token generation, assignment, and availability checks for appointments.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlmodel import Session, select, func
from uuid import UUID

from core.models_sql import Appointment, ClinicSession, Clinic, Doctor
from core.db_engine import engine

logger = logging.getLogger(__name__)


class TokenService:
    """Service for managing appointment tokens"""
    
    @staticmethod
    def get_session_for_time(requested_time: str, date: str, clinic_id: Optional[UUID] = None) -> Optional[ClinicSession]:
        """
        Determine which session a requested time belongs to based on actual session configuration.

        Args:
            requested_time: Time string like "10:00" or "19:30"
            date: Date string in YYYY-MM-DD format
            clinic_id: Optional clinic ID to filter sessions

        Returns:
            ClinicSession object or None
        """
        try:
            with Session(engine) as session:
                # Parse requested time to compare
                req_hour, req_min = map(int, requested_time.split(':'))
                req_minutes = req_hour * 60 + req_min  # Convert to minutes for easy comparison

                # Get all active sessions (optionally filtered by clinic)
                stmt = select(ClinicSession).where(ClinicSession.is_active == True)
                if clinic_id:
                    stmt = stmt.where(ClinicSession.clinic_id == clinic_id)

                sessions = session.exec(stmt).all()

                # Find the session that contains this time
                for clinic_session in sessions:
                    # Parse session times
                    start_hour, start_min = map(int, clinic_session.start_time.split(':'))
                    end_hour, end_min = map(int, clinic_session.end_time.split(':'))

                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    # Check if requested time falls within this session
                    if start_minutes <= req_minutes < end_minutes:
                        logger.info(f"Time {requested_time} matched session '{clinic_session.name}' ({clinic_session.start_time}-{clinic_session.end_time})")
                        return clinic_session

                # Fallback: if no exact match, return None to indicate closed/invalid time
                logger.warning(f"No session found for time {requested_time}")
                return None

        except Exception as e:
            logger.error(f"Error getting session for time {requested_time}: {e}")
            return None

    @staticmethod
    def is_session_active(clinic_id: UUID) -> Dict:
        """
        Check if any session is currently active for queue management.

        Args:
            clinic_id: UUID of the clinic

        Returns:
            Dict with:
                - is_active: bool
                - message: str (error message if not active)
                - active_session: Optional[dict] (session info if active)
        """
        try:
            with Session(engine) as session:
                now = datetime.now()
                current_time_str = now.strftime("%H:%M")
                current_minutes = now.hour * 60 + now.minute

                # Get all active sessions for this clinic
                stmt = select(ClinicSession).where(
                    ClinicSession.clinic_id == clinic_id,
                    ClinicSession.is_active == True
                )
                sessions = session.exec(stmt).all()

                if not sessions:
                    return {
                        "is_active": False,
                        "message": "No sessions configured for this clinic",
                        "active_session": None
                    }

                # Check if current time falls within any session
                for clinic_session in sessions:
                    start_hour, start_min = map(int, clinic_session.start_time.split(':'))
                    end_hour, end_min = map(int, clinic_session.end_time.split(':'))

                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    if start_minutes <= current_minutes < end_minutes:
                        logger.info(f"Session '{clinic_session.name}' is active ({clinic_session.start_time}-{clinic_session.end_time})")
                        return {
                            "is_active": True,
                            "message": f"Session '{clinic_session.name}' is active",
                            "active_session": {
                                "id": str(clinic_session.id),
                                "name": clinic_session.name,
                                "start_time": clinic_session.start_time,
                                "end_time": clinic_session.end_time
                            }
                        }

                # No active session found - find next session for helpful message
                next_session = None
                for clinic_session in sessions:
                    start_hour, start_min = map(int, clinic_session.start_time.split(':'))
                    start_minutes = start_hour * 60 + start_min
                    if start_minutes > current_minutes:
                        next_session = clinic_session
                        break

                if next_session:
                    return {
                        "is_active": False,
                        "message": f"Queue management available from {next_session.start_time} ({next_session.name} session)",
                        "active_session": None,
                        "next_session": {
                            "name": next_session.name,
                            "start_time": next_session.start_time
                        }
                    }
                else:
                    return {
                        "is_active": False,
                        "message": "No more sessions today. Queue management resumes tomorrow.",
                        "active_session": None
                    }

        except Exception as e:
            logger.error(f"Error checking session active status: {e}")
            return {
                "is_active": False,
                "message": f"Error checking session: {str(e)}",
                "active_session": None
            }
    
    @staticmethod
    def get_next_token_number(session_id: UUID, date: str) -> int:
        """
        Get the next available token number for a session on a specific date.
        
        Args:
            session_id: UUID of the clinic session
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Next available token number (starting from 1)
        """
        try:
            with Session(engine) as session:
                # Query max token for this session + date
                stmt = select(func.max(Appointment.token_number)).where(
                    Appointment.session_id == session_id,
                    Appointment.date == date,
                    Appointment.status != "CANCELLED"  # Don't count cancelled tokens
                )
                max_token = session.exec(stmt).one_or_none()
                
                next_token = (max_token or 0) + 1
                logger.info(f"Next token for session {session_id} on {date}: {next_token}")
                return next_token
                
        except Exception as e:
            logger.error(f"Error getting next token: {e}")
            return 1  # Default to token 1 on error
    
    @staticmethod
    def calculate_estimated_time(session: ClinicSession, token_number: int, date: str) -> datetime:
        """
        Calculate estimated appointment time based on token number and buffer.
        
        Formula: Session Start + (Token# - 1) × Buffer Minutes
        
        Args:
            session: ClinicSession object
            token_number: Token number (1, 2, 3, ...)
            date: Date string in YYYY-MM-DD format
            
        Returns:
            datetime object with estimated appointment time
        """
        try:
            # Parse session start time
            start_hour, start_min = map(int, session.start_time.split(':'))
            base_time = datetime.strptime(f"{date} {session.start_time}", "%Y-%m-%d %H:%M")
            
            # Add buffer time: (token_number - 1) * buffer_minutes
            buffer_offset = (token_number - 1) * session.buffer_minutes
            estimated_time = base_time + timedelta(minutes=buffer_offset)
            
            logger.info(f"Token {token_number} estimated time: {estimated_time.strftime('%I:%M %p')}")
            return estimated_time
            
        except Exception as e:
            logger.error(f"Error calculating estimated time: {e}")
            # Fallback to session start time
            return datetime.strptime(f"{date} {session.start_time}", "%Y-%m-%d %H:%M")
    
    @staticmethod
    def check_session_capacity(session: ClinicSession, date: str) -> Tuple[bool, int, int]:
        """
        Check if session has capacity for more tokens.
        
        Args:
            session: ClinicSession object
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Tuple of (has_capacity, current_count, max_tokens)
        """
        try:
            with Session(engine) as db_session:
                # Count active tokens for this session + date
                stmt = select(func.count(Appointment.id)).where(
                    Appointment.session_id == session.id,
                    Appointment.date == date,
                    Appointment.status != "CANCELLED"
                )
                current_count = db_session.exec(stmt).one()
                
                max_tokens = session.max_tokens or 999  # Default to unlimited if not set
                has_capacity = current_count < max_tokens
                
                logger.info(f"Session {session.name} on {date}: {current_count}/{max_tokens} tokens")
                return (has_capacity, current_count, max_tokens)
                
        except Exception as e:
            logger.error(f"Error checking session capacity: {e}")
            return (True, 0, 0)  # Default to available on error
    
    @staticmethod
    def generate_token(
        patient_name: str,
        patient_phone: str,
        date: str,
        requested_time: str,
        doctor_id: Optional[UUID] = None, # Added doctor_id
        source: str = "PHONE",
        created_by: str = "ai"
    ) -> Dict:
        """
        Generate and assign a token to a patient.
        """
        try:
            with Session(engine) as session:
                # 1. Determine session for the requested time
                clinic_session = TokenService.get_session_for_time(requested_time, date)
                if not clinic_session:
                    return {
                        "success": False,
                        "error": "No session found for requested time"
                    }
                
                # 2. Check capacity
                has_capacity, current, maximum = TokenService.check_session_capacity(clinic_session, date)
                if not has_capacity:
                    return {
                        "success": False,
                        "error": f"Session full ({current}/{maximum} tokens)"
                    }
                
                # 3. Get next token number
                token_number = TokenService.get_next_token_number(clinic_session.id, date)
                
                # 4. Determine Appointment Time (Strict Slot System)
                try:
                    target_time = None
                    if requested_time:
                         target_time = datetime.strptime(f"{date} {requested_time}", "%Y-%m-%d %H:%M")
                    else:
                         target_time = TokenService.calculate_estimated_time(clinic_session, token_number, date)

                    # Collision Check Loop
                    start_scan = target_time
                    found_slot = False
                    
                    # Parse session end time for boundary verify
                    sess_end = datetime.strptime(f"{date} {clinic_session.end_time}", "%Y-%m-%d %H:%M")

                    while start_scan < sess_end:
                         # Check if this exact time is booked
                         stmt = select(func.count(Appointment.id)).where(
                             Appointment.estimated_time == start_scan,
                             Appointment.status != "CANCELLED"
                         )
                         if session.exec(stmt).one() == 0:
                             estimated_time = start_scan
                             found_slot = True
                             if start_scan != target_time:
                                 logger.info(f"Requested {target_time} taken, bumped to {estimated_time}")
                             break
                         
                         # Increment by buffer (default 10 mins)
                         start_scan += timedelta(minutes=clinic_session.buffer_minutes or 10)
                    
                    if not found_slot:
                        return {"success": False, "error": "No slots available in this session (Time limit reached)"}

                except Exception as e:
                     logger.warning(f"Time calculation failed: {e}")
                     return {"success": False, "error": "Time calculation error"}
                
                # 5. Get Doctor
                doctor = None
                if doctor_id:
                    doctor = session.get(Doctor, doctor_id)
                
                if not doctor:
                    # Fallback to first available if not specified or not found
                    doctor = session.exec(select(Doctor)).first()
                
                if not doctor:
                    return {"success": False, "error": "No doctor available"}
                
                # 6. Create appointment
                appointment = Appointment(
                    clinic_id=doctor.clinic_id,
                    doctor_id=doctor.id,
                    session_id=clinic_session.id,
                    token_number=token_number,
                    booking_source=source,
                    patient_phone=patient_phone,
                    patient_name=patient_name,
                    date=date,
                    estimated_time=estimated_time,
                    status="BOOKED",
                    created_by=created_by
                )
                
                session.add(appointment)
                session.commit()
                session.refresh(appointment)
                
                logger.info(f"✓ Token #{token_number} generated for {patient_name} on {date} at {estimated_time.strftime('%I:%M %p')}")
                
                return {
                    "success": True,
                    "token_number": token_number,
                    "estimated_time": estimated_time.strftime("%I:%M %p"),
                    "estimated_time_24h": estimated_time.strftime("%H:%M"),
                    "session_name": clinic_session.name,
                    "patient_name": patient_name,
                    "date": date,
                    "appointment_id": str(appointment.id)
                }
                
        except Exception as e:
            logger.error(f"Error generating token: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @staticmethod
    def check_precise_availability(date: str, requested_time: str) -> Dict:
        """
        Check if a specific time is available, or suggest next slot.
        """
        try:
            with Session(engine) as session:
                clinic_session = TokenService.get_session_for_time(requested_time, date)
                if not clinic_session:
                    return {"available": False, "message": "Clinic is closed at this time."}

                # Check Session Capacity
                stmt_cap = select(func.count(Appointment.id)).where(
                    Appointment.session_id == clinic_session.id,
                    Appointment.date == date,
                    Appointment.status != "CANCELLED"
                )
                current_count = session.exec(stmt_cap).one()
                if current_count >= (clinic_session.max_tokens or 999):
                    return {"available": False, "message": "All slots for this session are fully booked."}

                # Check Specific Time Collision
                target_time = datetime.strptime(f"{date} {requested_time}", "%Y-%m-%d %H:%M")
                
                # Check collision at target
                stmt = select(func.count(Appointment.id)).where(
                     Appointment.estimated_time == target_time,
                     Appointment.status != "CANCELLED"
                )
                if session.exec(stmt).one() == 0:
                     return {"available": True, "message": f"{requested_time} is available."}
                
                # If taken, find next
                start_scan = target_time + timedelta(minutes=clinic_session.buffer_minutes or 10)
                sess_end = datetime.strptime(f"{date} {clinic_session.end_time}", "%Y-%m-%d %H:%M")
                
                while start_scan < sess_end:
                     stmt = select(func.count(Appointment.id)).where(
                         Appointment.estimated_time == start_scan,
                         Appointment.status != "CANCELLED"
                     )
                     if session.exec(stmt).one() == 0:
                         next_str = start_scan.strftime("%H:%M")
                         return {"available": False, "message": f"{requested_time} is booked. Next available slot is {next_str}.", "next_slot": next_str}
                     start_scan += timedelta(minutes=clinic_session.buffer_minutes or 10)
                
                return {"available": False, "message": "No more slots available in this session."}

        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return {"available": False, "message": "Could not verify availability."}

    @staticmethod
    def cancel_token(appointment_id: UUID, reason: str = "User requested") -> Dict:
        """
        Cancel an existing token/appointment.
        
        Args:
            appointment_id: UUID of the appointment
            reason: Cancellation reason
            
        Returns:
            Dict with success status
        """
        try:
            with Session(engine) as session:
                appointment = session.get(Appointment, appointment_id)
                if not appointment:
                    return {"success": False, "error": "Appointment not found"}
                
                if appointment.status == "CANCELLED":
                    return {"success": False, "error": "Already cancelled"}
                
                appointment.status = "CANCELLED"
                session.add(appointment)
                session.commit()
                
                logger.info(f"✓ Cancelled token #{appointment.token_number} for {appointment.patient_name}")
                
                return {
                    "success": True,
                    "token_number": appointment.token_number,
                    "patient_name": appointment.patient_name
                }
                
        except Exception as e:
            logger.error(f"Error cancelling token: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_tokens_for_session(session_id: UUID, date: str) -> List[Appointment]:
        """Get all tokens for a specific session and date."""
        try:
            with Session(engine) as session:
                stmt = select(Appointment).where(
                    Appointment.session_id == session_id,
                    Appointment.date == date
                ).order_by(Appointment.token_number)
                
                appointments = session.exec(stmt).all()
                return list(appointments)
                
        except Exception as e:
            logger.error(f"Error getting tokens: {e}")
            return []
    
    @staticmethod
    def get_queue_status(clinic_id: UUID, date: str, doctor_id: Optional[UUID] = None) -> Dict:
        """
        Get the current status of the queue for a clinic on a specific date.
        Returns current serving token, waiting list, and skipped list.

        Args:
            clinic_id: UUID of the clinic
            date: Date string in YYYY-MM-DD format
            doctor_id: Optional UUID to filter queue by specific doctor
        """
        try:
            with Session(engine) as session:
                # Get all appointments for the date, ordered by token number
                # Join with Doctor to get names
                stmt = select(Appointment, Doctor).join(Doctor, isouter=True).where(
                    Appointment.clinic_id == clinic_id,
                    Appointment.date == date,
                    Appointment.status != "CANCELLED"
                )

                # Filter by doctor if specified
                if doctor_id:
                    stmt = stmt.where(Appointment.doctor_id == doctor_id)

                stmt = stmt.order_by(Appointment.token_number)

                results = session.exec(stmt).all()

                # Categorize
                waiting = []
                skipped = []
                visited = []
                current_serving = None

                def serialize(appt, doc, position=None):
                    data = {
                        "id": str(appt.id),
                        "date": appt.date,
                        "time": appt.estimated_time.strftime("%H:%M") if appt.estimated_time else "00:00",
                        "duration": 15,
                        "patient_name": appt.patient_name or f"Patient {appt.patient_phone}",
                        "patient_phone": appt.patient_phone,
                        "doctor_name": doc.name if doc else "Unknown Doctor",
                        "doctor_id": str(doc.id) if doc else "",
                        "status": appt.status,
                        "type": "Walk-in" if appt.booking_source == "WALK_IN" else "Consultation",
                        "token_number": appt.token_number,
                        "is_checked_in": appt.status == "CHECKED_IN"
                    }
                    if position is not None:
                        data["queue_position"] = position
                    return data

                # First pass: count waiting to calculate positions
                for appt, doc in results:
                    if appt.status == "VISITED":
                        visited.append(serialize(appt, doc))
                    elif appt.status == "SKIPPED":
                        skipped.append(serialize(appt, doc))
                    elif appt.status == "SERVING":
                        current_serving = serialize(appt, doc, position=0)
                    elif appt.status == "BOOKED" or appt.status == "CHECKED_IN":
                        # Position calculated after loop
                        waiting.append((appt, doc))

                # Add positions to waiting list
                waiting_with_positions = []
                for idx, (appt, doc) in enumerate(waiting):
                    waiting_with_positions.append(serialize(appt, doc, position=idx + 1))

                return {
                    "current_token": current_serving,
                    "waiting": waiting_with_positions,
                    "skipped": skipped,
                    "total_visited": len(visited),
                    "total_waiting": len(waiting_with_positions)
                }

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"error": str(e)}

    @staticmethod
    def update_token_status(appointment_id: UUID, new_status: str) -> Dict:
        """
        Update the status of a specific token/appointment.
        Valid statuses: VISITED, SKIPPED, SERVING, NO_SHOW, BOOKED (re-queue)
        """
        try:
            with Session(engine) as session:
                appt = session.get(Appointment, appointment_id)
                if not appt:
                    return {"success": False, "error": "Appointment not found"}
                
                # Logic for status transitions
                if new_status == "SERVING":
                    # Ensure no other token is currently serving? 
                    # Ideally yes, but for simplicity we just mark this one.
                    # Maybe mark previous SERVING as VISITED automatically?
                    # Let's keep it manual for now or simple auto-close.
                    
                    # Auto-close previous serving
                    stmt = select(Appointment).where(
                        Appointment.clinic_id == appt.clinic_id,
                        Appointment.date == appt.date,
                        Appointment.status == "SERVING",
                        Appointment.id != appt.id
                    )
                    prev_serving = session.exec(stmt).first()
                    if prev_serving:
                        prev_serving.status = "VISITED"
                        session.add(prev_serving)
                
                appt.status = new_status
                session.add(appt)
                session.commit()
                
                return {"success": True, "status": new_status, "token": appt.token_number}
                
        except Exception as e:
            logger.error(f"Error updating token status: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def find_appointments_by_phone(phone: str, date: Optional[str] = None) -> List[Dict]:
        """
        Find appointments for a given phone number.
        """
        try:
            with Session(engine) as session:
                query = select(Appointment).where(Appointment.patient_phone == phone)
                
                if date:
                    query = query.where(Appointment.date == date)
                else:
                    # Default: Future or today's appointments only?
                    # Let's show all for now, or maybe just upcoming.
                    # For cancellation, we usually care about upcoming.
                    today = datetime.now().strftime("%Y-%m-%d")
                    query = query.where(Appointment.date >= today)
                
                query = query.where(Appointment.status != "CANCELLED")
                query = query.order_by(Appointment.date, Appointment.estimated_time)
                
                appointments = session.exec(query).all()
                
                results = []
                for appt in appointments:
                    results.append({
                        "id": str(appt.id),
                        "date": appt.date,
                        "time": appt.estimated_time.strftime("%H:%M") if appt.estimated_time else "N/A",
                        "patient_name": appt.patient_name,
                        "token": appt.token_number,
                        "status": appt.status
                    })
                return results
                
        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return []

    @staticmethod
    def get_clinic_rush_info(clinic_id: UUID) -> Dict:
        """
        Calculate rush level and estimated wait time for the voice agent.
        Uses clinic-specific thresholds from the database.
        """
        try:
            with Session(engine) as session:
                # Get clinic configuration
                clinic = session.get(Clinic, clinic_id)

                # Default thresholds if clinic not found
                low_threshold = 3
                medium_threshold = 7
                avg_minutes = 10

                if clinic:
                    low_threshold = clinic.rush_low_threshold or 3
                    medium_threshold = clinic.rush_medium_threshold or 7
                    avg_minutes = clinic.average_consultation_minutes or 10

                date_str = datetime.now().strftime("%Y-%m-%d")
                status = TokenService.get_queue_status(clinic_id, date_str)

                if "error" in status:
                    return {"rush_level": "Unknown", "estimated_wait": "Unknown"}

                waiting_count = status.get("total_waiting", len(status.get("waiting", [])))

                # Calculate rush level based on clinic-specific thresholds
                if waiting_count < low_threshold:
                    rush_level = "Low"
                elif waiting_count < medium_threshold:
                    rush_level = "Medium"
                else:
                    rush_level = "High"

                # Calculate dynamic wait time
                estimated_minutes = waiting_count * avg_minutes
                if estimated_minutes < 15:
                    wait_time = f"{max(5, estimated_minutes)}-15 minutes"
                elif estimated_minutes < 30:
                    wait_time = f"{estimated_minutes}-{estimated_minutes + 15} minutes"
                elif estimated_minutes < 60:
                    wait_time = f"{estimated_minutes // 10 * 10}-{(estimated_minutes // 10 * 10) + 15} minutes"
                else:
                    hours = estimated_minutes // 60
                    wait_time = f"about {hours} hour{'s' if hours > 1 else ''}"

                return {
                    "rush_level": rush_level,
                    "waiting_count": waiting_count,
                    "estimated_wait": wait_time,
                    "estimated_minutes": estimated_minutes,
                    "current_token": status.get("current_token"),
                    "thresholds": {
                        "low": low_threshold,
                        "medium": medium_threshold,
                        "avg_consultation_minutes": avg_minutes
                    }
                }

        except Exception as e:
            logger.error(f"Error calculating rush info: {e}")
            return {"rush_level": "Unknown", "estimated_wait": "Unknown"}
