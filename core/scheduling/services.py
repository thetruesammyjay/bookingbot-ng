"""
Scheduling services for BookingBot NG
Core booking logic, conflict detection, and appointment management for Nigerian businesses
"""

import uuid
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_, func
from loguru import logger

from .models import (
    Appointment, ServiceDefinition, BusinessHours, AvailabilitySlot,
    StaffSchedule, AppointmentStatus, RecurrenceType
)
from .utils import (
    convert_to_local_time, convert_to_utc, get_nigerian_holidays,
    is_business_day, generate_time_slots, validate_booking_time
)
from .exceptions import (
    SchedulingError, AppointmentConflictError, ServiceNotAvailableError,
    StaffNotAvailableError, InvalidBookingTimeError, BookingLimitExceededError
)


class SchedulingService:
    """Core scheduling and appointment management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_available_slots(
        self,
        tenant_id: str,
        service_id: str,
        start_date: date,
        end_date: Optional[date] = None,
        staff_id: Optional[str] = None,
        preferred_times: Optional[List[time]] = None
    ) -> List[Dict[str, Any]]:
        """Find available booking slots for a service"""
        
        if not end_date:
            end_date = start_date + timedelta(days=30)  # Default 30-day window
        
        # Get service details
        service = self.db.query(ServiceDefinition).filter(
            ServiceDefinition.id == service_id,
            ServiceDefinition.tenant_id == tenant_id,
            ServiceDefinition.is_active == True
        ).first()
        
        if not service:
            raise ServiceNotAvailableError(f"Service {service_id} not found or inactive")
        
        # Get business hours
        business_hours = self.db.query(BusinessHours).filter(
            BusinessHours.tenant_id == tenant_id
        ).all()
        
        if not business_hours:
            raise SchedulingError("Business hours not configured")
        
        available_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            # Check if it's a valid booking day
            if not self._is_valid_booking_day(current_date, business_hours):
                current_date += timedelta(days=1)
                continue
            
            # Get day's business hours
            day_hours = self._get_business_hours_for_day(current_date, business_hours)
            if not day_hours or not day_hours.is_open:
                current_date += timedelta(days=1)
                continue
            
            # Generate time slots for the day
            day_slots = self._generate_day_slots(
                current_date, 
                day_hours, 
                service,
                staff_id
            )
            
            # Filter out conflicting slots
            available_day_slots = self._filter_available_slots(
                day_slots,
                tenant_id,
                service_id,
                staff_id
            )
            
            available_slots.extend(available_day_slots)
            current_date += timedelta(days=1)
        
        # Sort by datetime and apply preferences
        available_slots.sort(key=lambda x: x['start_time'])
        
        if preferred_times:
            available_slots = self._apply_time_preferences(available_slots, preferred_times)
        
        return available_slots
    
    def create_appointment(
        self,
        tenant_id: str,
        service_id: str,
        start_time: datetime,
        customer_data: Dict[str, Any],
        staff_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        payment_required: bool = False,
        payment_amount: Optional[Decimal] = None
    ) -> Appointment:
        """Create a new appointment"""
        
        # Validate the booking time
        if not self._validate_booking_time(tenant_id, service_id, start_time, staff_id):
            raise InvalidBookingTimeError("Selected time slot is not available")
        
        # Get service details
        service = self.db.query(ServiceDefinition).filter(
            ServiceDefinition.id == service_id,
            ServiceDefinition.tenant_id == tenant_id
        ).first()
        
        if not service:
            raise ServiceNotAvailableError(f"Service {service_id} not found")
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=service.duration_minutes)
        
        # Check for conflicts
        conflicts = self._check_appointment_conflicts(
            tenant_id, start_time, end_time, staff_id
        )
        
        if conflicts:
            raise AppointmentConflictError("Time slot conflicts with existing appointment")
        
        # Generate booking reference
        booking_reference = self._generate_booking_reference(tenant_id)
        
        # Create appointment
        appointment = Appointment(
            tenant_id=tenant_id,
            service_id=service_id,
            customer_name=customer_data.get('name'),
            customer_email=customer_data.get('email'),
            customer_phone=customer_data.get('phone'),
            customer_notes=customer_data.get('notes'),
            customer_nin=customer_data.get('nin'),
            customer_bvn=customer_data.get('bvn'),
            start_time=start_time,
            end_time=end_time,
            assigned_staff_id=staff_id,
            booking_reference=booking_reference,
            payment_required=payment_required,
            payment_amount=payment_amount,
            custom_field_values=custom_fields,
            special_requests=customer_data.get('special_requests')
        )
        
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        
        logger.info(f"Created appointment {booking_reference} for {customer_data.get('name')}")
        
        return appointment
    
    def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        reschedule_reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Reschedule an existing appointment"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise SchedulingError(f"Cannot reschedule {appointment.status} appointment")
        
        # Validate new time slot
        if not self._validate_booking_time(
            appointment.tenant_id,
            appointment.service_id,
            new_start_time,
            appointment.assigned_staff_id
        ):
            raise InvalidBookingTimeError("New time slot is not available")
        
        # Calculate new end time
        service = appointment.service
        new_end_time = new_start_time + timedelta(minutes=service.duration_minutes)
        
        # Check for conflicts (excluding current appointment)
        conflicts = self._check_appointment_conflicts(
            appointment.tenant_id,
            new_start_time,
            new_end_time,
            appointment.assigned_staff_id,
            exclude_appointment_id=appointment.id
        )
        
        if conflicts:
            raise AppointmentConflictError("New time slot conflicts with existing appointment")
        
        # Update appointment
        old_start_time = appointment.start_time
        appointment.start_time = new_start_time
        appointment.end_time = new_end_time
        appointment.status = AppointmentStatus.RESCHEDULED
        appointment.updated_at = datetime.utcnow()
        
        # Log the reschedule
        logger.info(
            f"Rescheduled appointment {appointment.booking_reference} "
            f"from {old_start_time} to {new_start_time}"
        )
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def cancel_appointment(
        self,
        appointment_id: str,
        cancellation_reason: Optional[str] = None,
        cancelled_by_user_id: Optional[str] = None
    ) -> Appointment:
        """Cancel an appointment"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        if appointment.status == AppointmentStatus.COMPLETED:
            raise SchedulingError("Cannot cancel completed appointment")
        
        if appointment.status == AppointmentStatus.CANCELLED:
            raise SchedulingError("Appointment is already cancelled")
        
        # Update appointment status
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = datetime.utcnow()
        appointment.cancellation_reason = cancellation_reason
        appointment.cancelled_by_user_id = cancelled_by_user_id
        appointment.updated_at = datetime.utcnow()
        
        logger.info(f"Cancelled appointment {appointment.booking_reference}")
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def check_in_appointment(self, appointment_id: str) -> Appointment:
        """Check in a customer for their appointment"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        if appointment.status != AppointmentStatus.CONFIRMED:
            raise SchedulingError(f"Cannot check in {appointment.status} appointment")
        
        appointment.status = AppointmentStatus.CHECKED_IN
        appointment.checked_in_at = datetime.utcnow()
        appointment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def start_service(self, appointment_id: str) -> Appointment:
        """Mark service as started"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        if appointment.status != AppointmentStatus.CHECKED_IN:
            raise SchedulingError("Customer must be checked in first")
        
        appointment.status = AppointmentStatus.IN_PROGRESS
        appointment.service_started_at = datetime.utcnow()
        appointment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def complete_appointment(
        self,
        appointment_id: str,
        internal_notes: Optional[str] = None
    ) -> Appointment:
        """Mark appointment as completed"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        if appointment.status != AppointmentStatus.IN_PROGRESS:
            raise SchedulingError("Service must be started first")
        
        appointment.status = AppointmentStatus.COMPLETED
        appointment.service_completed_at = datetime.utcnow()
        appointment.internal_notes = internal_notes
        appointment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def mark_no_show(self, appointment_id: str) -> Appointment:
        """Mark appointment as no-show"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            raise SchedulingError(f"Appointment {appointment_id} not found")
        
        appointment.status = AppointmentStatus.NO_SHOW
        appointment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def get_upcoming_appointments(
        self,
        tenant_id: str,
        staff_id: Optional[str] = None,
        days_ahead: int = 7
    ) -> List[Appointment]:
        """Get upcoming appointments for a tenant or staff member"""
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(days=days_ahead)
        
        query = self.db.query(Appointment).filter(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= start_time,
            Appointment.start_time <= end_time,
            Appointment.status.in_([
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN
            ])
        )
        
        if staff_id:
            query = query.filter(Appointment.assigned_staff_id == staff_id)
        
        return query.order_by(Appointment.start_time).all()
    
    def get_appointment_analytics(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get appointment analytics for a date range"""
        
        appointments = self.db.query(Appointment).filter(
            Appointment.tenant_id == tenant_id,
            func.date(Appointment.start_time) >= start_date,
            func.date(Appointment.start_time) <= end_date
        ).all()
        
        total_appointments = len(appointments)
        
        if total_appointments == 0:
            return {
                "total_appointments": 0,
                "confirmed_appointments": 0,
                "cancelled_appointments": 0,
                "no_show_appointments": 0,
                "completed_appointments": 0,
                "completion_rate": 0,
                "cancellation_rate": 0,
                "no_show_rate": 0,
                "total_revenue": 0,
                "average_booking_value": 0
            }
        
        # Count by status
        status_counts = {}
        total_revenue = Decimal('0')
        
        for appointment in appointments:
            status = appointment.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if appointment.payment_amount and appointment.status == AppointmentStatus.COMPLETED:
                total_revenue += appointment.payment_amount
        
        confirmed = status_counts.get(AppointmentStatus.CONFIRMED, 0)
        cancelled = status_counts.get(AppointmentStatus.CANCELLED, 0)
        no_show = status_counts.get(AppointmentStatus.NO_SHOW, 0)
        completed = status_counts.get(AppointmentStatus.COMPLETED, 0)
        
        return {
            "total_appointments": total_appointments,
            "confirmed_appointments": confirmed,
            "cancelled_appointments": cancelled,
            "no_show_appointments": no_show,
            "completed_appointments": completed,
            "completion_rate": (completed / total_appointments) * 100 if total_appointments > 0 else 0,
            "cancellation_rate": (cancelled / total_appointments) * 100 if total_appointments > 0 else 0,
            "no_show_rate": (no_show / total_appointments) * 100 if total_appointments > 0 else 0,
            "total_revenue": float(total_revenue),
            "average_booking_value": float(total_revenue / completed) if completed > 0 else 0
        }
    
    def _is_valid_booking_day(
        self,
        booking_date: date,
        business_hours: List[BusinessHours]
    ) -> bool:
        """Check if a date is valid for booking"""
        
        # Check Nigerian holidays
        nigerian_holidays = get_nigerian_holidays(booking_date.year)
        if booking_date in nigerian_holidays:
            return False
        
        # Check business hours for the day
        day_of_week = booking_date.weekday()  # 0=Monday, 6=Sunday
        day_hours = next((bh for bh in business_hours if bh.day_of_week == day_of_week), None)
        
        return day_hours and day_hours.is_open
    
    def _get_business_hours_for_day(
        self,
        date: date,
        business_hours: List[BusinessHours]
    ) -> Optional[BusinessHours]:
        """Get business hours for a specific day"""
        
        day_of_week = date.weekday()
        return next((bh for bh in business_hours if bh.day_of_week == day_of_week), None)
    
    def _generate_day_slots(
        self,
        date: date,
        business_hours: BusinessHours,
        service: ServiceDefinition,
        staff_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate available time slots for a day"""
        
        slots = []
        
        if not business_hours.open_time or not business_hours.close_time:
            return slots
        
        # Start from business opening
        current_time = datetime.combine(date, business_hours.open_time)
        end_time = datetime.combine(date, business_hours.close_time)
        
        # Generate slots
        while current_time + timedelta(minutes=service.duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=service.duration_minutes)
            
            # Skip break time if configured
            if (business_hours.break_start and business_hours.break_end and
                not (current_time.time() >= business_hours.break_end or 
                     slot_end.time() <= business_hours.break_start)):
                current_time += timedelta(minutes=15)  # Move past break
                continue
            
            slots.append({
                'start_time': current_time,
                'end_time': slot_end,
                'duration_minutes': service.duration_minutes,
                'service_id': service.id,
                'staff_id': staff_id
            })
            
            # Move to next slot (typically 15-30 minute intervals)
            current_time += timedelta(minutes=15)
        
        return slots
    
    def _filter_available_slots(
        self,
        slots: List[Dict[str, Any]],
        tenant_id: str,
        service_id: str,
        staff_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter out slots that conflict with existing appointments"""
        
        available_slots = []
        
        for slot in slots:
            # Check for existing appointments
            conflicts = self._check_appointment_conflicts(
                tenant_id,
                slot['start_time'],
                slot['end_time'],
                staff_id
            )
            
            if not conflicts:
                available_slots.append(slot)
        
        return available_slots
    
    def _check_appointment_conflicts(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        staff_id: Optional[str] = None,
        exclude_appointment_id: Optional[str] = None
    ) -> List[Appointment]:
        """Check for conflicting appointments"""
        
        query = self.db.query(Appointment).filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status.in_([
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]),
            or_(
                and_(
                    Appointment.start_time < end_time,
                    Appointment.end_time > start_time
                )
            )
        )
        
        if staff_id:
            query = query.filter(Appointment.assigned_staff_id == staff_id)
        
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
        
        return query.all()
    
    def _validate_booking_time(
        self,
        tenant_id: str,
        service_id: str,
        start_time: datetime,
        staff_id: Optional[str] = None
    ) -> bool:
        """Validate if a booking time is available"""
        
        # Get service
        service = self.db.query(ServiceDefinition).filter(
            ServiceDefinition.id == service_id
        ).first()
        
        if not service:
            return False
        
        # Check advance booking limits
        now = datetime.utcnow()
        min_advance = timedelta(hours=service.min_advance_booking_hours)
        max_advance = timedelta(days=service.max_advance_booking_days)
        
        if start_time < now + min_advance:
            return False
        
        if start_time > now + max_advance:
            return False
        
        # Check business hours
        business_hours = self.db.query(BusinessHours).filter(
            BusinessHours.tenant_id == tenant_id
        ).all()
        
        booking_date = start_time.date()
        if not self._is_valid_booking_day(booking_date, business_hours):
            return False
        
        return True
    
    def _generate_booking_reference(self, tenant_id: str) -> str:
        """Generate a unique booking reference"""
        
        # Use first 8 chars of tenant ID + timestamp + random
        tenant_prefix = str(tenant_id).replace('-', '')[:8].upper()
        timestamp = datetime.now().strftime("%m%d%H%M")
        random_suffix = str(uuid.uuid4())[:4].upper()
        
        return f"BK{tenant_prefix}{timestamp}{random_suffix}"
    
    def _apply_time_preferences(
        self,
        slots: List[Dict[str, Any]],
        preferred_times: List[time]
    ) -> List[Dict[str, Any]]:
        """Sort slots by time preferences"""
        
        def time_preference_score(slot):
            slot_time = slot['start_time'].time()
            
            # Find closest preferred time
            min_diff = float('inf')
            for pref_time in preferred_times:
                diff = abs((datetime.combine(date.today(), slot_time) - 
                           datetime.combine(date.today(), pref_time)).total_seconds())
                min_diff = min(min_diff, diff)
            
            return min_diff
        
        # Sort by preference score, then by time
        slots.sort(key=lambda x: (time_preference_score(x), x['start_time']))
        
        return slots


class RecurringAppointmentService:
    """Handle recurring appointment creation and management"""
    
    def __init__(self, db: Session, scheduling_service: SchedulingService):
        self.db = db
        self.scheduling_service = scheduling_service
    
    def create_recurring_appointments(
        self,
        parent_appointment: Appointment,
        recurrence_type: RecurrenceType,
        recurrence_interval: int,
        end_date: date,
        max_appointments: int = 52  # Safety limit
    ) -> List[Appointment]:
        """Create recurring appointments based on parent appointment"""
        
        if recurrence_type == RecurrenceType.NONE:
            return [parent_appointment]
        
        recurring_appointments = [parent_appointment]
        current_date = parent_appointment.start_time.date()
        appointment_count = 1
        
        while current_date < end_date and appointment_count < max_appointments:
            # Calculate next occurrence
            if recurrence_type == RecurrenceType.WEEKLY:
                current_date += timedelta(weeks=recurrence_interval)
            elif recurrence_type == RecurrenceType.MONTHLY:
                current_date += timedelta(days=30 * recurrence_interval)  # Simplified
            elif recurrence_type == RecurrenceType.YEARLY:
                current_date = current_date.replace(year=current_date.year + recurrence_interval)
            
            # Create next appointment
            next_start_time = datetime.combine(
                current_date,
                parent_appointment.start_time.time()
            )
            
            try:
                next_appointment = self.scheduling_service.create_appointment(
                    tenant_id=parent_appointment.tenant_id,
                    service_id=parent_appointment.service_id,
                    start_time=next_start_time,
                    customer_data={
                        'name': parent_appointment.customer_name,
                        'email': parent_appointment.customer_email,
                        'phone': parent_appointment.customer_phone,
                        'notes': parent_appointment.customer_notes
                    },
                    staff_id=parent_appointment.assigned_staff_id,
                    custom_fields=parent_appointment.custom_field_values,
                    payment_required=parent_appointment.payment_required,
                    payment_amount=parent_appointment.payment_amount
                )
                
                next_appointment.parent_appointment_id = parent_appointment.id
                next_appointment.recurrence_type = recurrence_type
                next_appointment.recurrence_interval = recurrence_interval
                
                recurring_appointments.append(next_appointment)
                appointment_count += 1
                
            except (AppointmentConflictError, InvalidBookingTimeError) as e:
                logger.warning(f"Skipping recurring appointment on {current_date}: {e}")
                continue
        
        self.db.commit()
        return recurring_appointments