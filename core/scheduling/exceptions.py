"""
Scheduling-specific exceptions for BookingBot NG
Handles errors related to appointments, availability, and calendar management
"""

from datetime import datetime, date, time
from typing import Optional, Dict, Any, List


class SchedulingError(Exception):
    """Base exception for scheduling-related errors"""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None,
        appointment_id: Optional[str] = None,
        booking_reference: Optional[str] = None
    ):
        self.message = message
        self.code = code or "SCHEDULING_ERROR"
        self.details = details or {}
        self.appointment_id = appointment_id
        self.booking_reference = booking_reference
        super().__init__(self.message)


class AppointmentNotFoundError(SchedulingError):
    """Raised when appointment is not found"""
    
    def __init__(self, identifier: str, identifier_type: str = "id"):
        super().__init__(
            f"Appointment not found: {identifier}",
            code="APPOINTMENT_NOT_FOUND",
            details={identifier_type: identifier}
        )


class AppointmentConflictError(SchedulingError):
    """Raised when appointment time conflicts with existing bookings"""
    
    def __init__(
        self, 
        message: str = "Appointment time conflicts with existing booking",
        conflicting_appointments: Optional[List[str]] = None,
        requested_start_time: Optional[datetime] = None,
        requested_end_time: Optional[datetime] = None
    ):
        details = {}
        if conflicting_appointments:
            details["conflicting_appointments"] = conflicting_appointments
        if requested_start_time:
            details["requested_start_time"] = requested_start_time.isoformat()
        if requested_end_time:
            details["requested_end_time"] = requested_end_time.isoformat()
        
        super().__init__(
            message,
            code="APPOINTMENT_CONFLICT",
            details=details
        )


class ServiceNotAvailableError(SchedulingError):
    """Raised when service is not available for booking"""
    
    def __init__(
        self, 
        service_id: str, 
        reason: Optional[str] = None,
        available_from: Optional[datetime] = None
    ):
        message = f"Service {service_id} is not available"
        if reason:
            message += f": {reason}"
        
        details = {"service_id": service_id}
        if available_from:
            details["available_from"] = available_from.isoformat()
        if reason:
            details["reason"] = reason
        
        super().__init__(
            message,
            code="SERVICE_NOT_AVAILABLE",
            details=details
        )


class StaffNotAvailableError(SchedulingError):
    """Raised when requested staff member is not available"""
    
    def __init__(
        self, 
        staff_id: str, 
        requested_time: datetime,
        reason: Optional[str] = None,
        next_available: Optional[datetime] = None
    ):
        message = f"Staff member {staff_id} is not available at {requested_time}"
        if reason:
            message += f": {reason}"
        
        details = {
            "staff_id": staff_id,
            "requested_time": requested_time.isoformat()
        }
        if next_available:
            details["next_available"] = next_available.isoformat()
        if reason:
            details["reason"] = reason
        
        super().__init__(
            message,
            code="STAFF_NOT_AVAILABLE",
            details=details
        )


class InvalidBookingTimeError(SchedulingError):
    """Raised when booking time is invalid"""
    
    def __init__(
        self, 
        message: str = "Invalid booking time",
        requested_time: Optional[datetime] = None,
        valid_range_start: Optional[datetime] = None,
        valid_range_end: Optional[datetime] = None
    ):
        details = {}
        if requested_time:
            details["requested_time"] = requested_time.isoformat()
        if valid_range_start:
            details["valid_range_start"] = valid_range_start.isoformat()
        if valid_range_end:
            details["valid_range_end"] = valid_range_end.isoformat()
        
        super().__init__(
            message,
            code="INVALID_BOOKING_TIME",
            details=details
        )


class BookingLimitExceededError(SchedulingError):
    """Raised when booking limits are exceeded"""
    
    def __init__(
        self, 
        limit_type: str,
        current_count: int,
        maximum_allowed: int,
        period: Optional[str] = None
    ):
        message = f"{limit_type} limit exceeded: {current_count}/{maximum_allowed}"
        if period:
            message += f" for {period}"
        
        super().__init__(
            message,
            code="BOOKING_LIMIT_EXCEEDED",
            details={
                "limit_type": limit_type,
                "current_count": current_count,
                "maximum_allowed": maximum_allowed,
                "period": period
            }
        )


class InvalidAppointmentStatusError(SchedulingError):
    """Raised when appointment status transition is invalid"""
    
    def __init__(
        self, 
        current_status: str, 
        requested_status: str,
        appointment_id: Optional[str] = None
    ):
        super().__init__(
            f"Cannot change appointment status from '{current_status}' to '{requested_status}'",
            code="INVALID_STATUS_TRANSITION",
            details={
                "current_status": current_status,
                "requested_status": requested_status
            },
            appointment_id=appointment_id
        )


class AppointmentCancellationError(SchedulingError):
    """Raised when appointment cannot be cancelled"""
    
    def __init__(
        self, 
        reason: str,
        appointment_id: Optional[str] = None,
        cancellation_deadline: Optional[datetime] = None
    ):
        details = {"reason": reason}
        if cancellation_deadline:
            details["cancellation_deadline"] = cancellation_deadline.isoformat()
        
        super().__init__(
            f"Cannot cancel appointment: {reason}",
            code="CANCELLATION_NOT_ALLOWED",
            details=details,
            appointment_id=appointment_id
        )


class AppointmentRescheduleError(SchedulingError):
    """Raised when appointment cannot be rescheduled"""
    
    def __init__(
        self, 
        reason: str,
        appointment_id: Optional[str] = None,
        reschedule_deadline: Optional[datetime] = None
    ):
        details = {"reason": reason}
        if reschedule_deadline:
            details["reschedule_deadline"] = reschedule_deadline.isoformat()
        
        super().__init__(
            f"Cannot reschedule appointment: {reason}",
            code="RESCHEDULE_NOT_ALLOWED",
            details=details,
            appointment_id=appointment_id
        )


class BusinessHoursError(SchedulingError):
    """Raised for business hours configuration errors"""
    
    def __init__(
        self, 
        message: str,
        tenant_id: Optional[str] = None,
        day_of_week: Optional[int] = None
    ):
        details = {}
        if tenant_id:
            details["tenant_id"] = tenant_id
        if day_of_week is not None:
            details["day_of_week"] = day_of_week
        
        super().__init__(
            message,
            code="BUSINESS_HOURS_ERROR",
            details=details
        )


class RecurringAppointmentError(SchedulingError):
    """Raised for recurring appointment errors"""
    
    def __init__(
        self, 
        message: str,
        recurrence_type: Optional[str] = None,
        parent_appointment_id: Optional[str] = None
    ):
        details = {}
        if recurrence_type:
            details["recurrence_type"] = recurrence_type
        if parent_appointment_id:
            details["parent_appointment_id"] = parent_appointment_id
        
        super().__init__(
            message,
            code="RECURRING_APPOINTMENT_ERROR",
            details=details
        )


# Calendar Integration Exceptions

class CalendarIntegrationError(SchedulingError):
    """Base exception for calendar integration errors"""
    
    def __init__(
        self, 
        message: str,
        provider: Optional[str] = None,
        provider_response: Optional[Dict] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if provider:
            details["provider"] = provider
        if provider_response:
            details["provider_response"] = provider_response
        
        super().__init__(
            message,
            code="CALENDAR_INTEGRATION_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class CalendarSyncError(CalendarIntegrationError):
    """Raised when calendar synchronization fails"""
    
    def __init__(
        self, 
        message: str,
        sync_direction: Optional[str] = None,
        last_successful_sync: Optional[datetime] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if sync_direction:
            details["sync_direction"] = sync_direction
        if last_successful_sync:
            details["last_successful_sync"] = last_successful_sync.isoformat()
        
        super().__init__(
            message,
            code="CALENDAR_SYNC_ERROR",
            details=details,
            **kwargs
        )


class CalendarAuthenticationError(CalendarIntegrationError):
    """Raised when calendar authentication fails"""
    
    def __init__(
        self, 
        provider: str,
        token_expired: bool = False,
        **kwargs
    ):
        message = f"Calendar authentication failed for {provider}"
        if token_expired:
            message += " (token expired)"
        
        details = kwargs.get("details", {})
        details["token_expired"] = token_expired
        
        super().__init__(
            message,
            provider=provider,
            code="CALENDAR_AUTH_ERROR",
            details=details,
            **kwargs
        )


class CalendarEventError(CalendarIntegrationError):
    """Raised for calendar event operations"""
    
    def __init__(
        self, 
        message: str,
        event_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if event_id:
            details["event_id"] = event_id
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message,
            code="CALENDAR_EVENT_ERROR",
            details=details,
            **kwargs
        )


# Availability and Slot Exceptions

class AvailabilityError(SchedulingError):
    """Raised for availability-related errors"""
    
    def __init__(
        self, 
        message: str,
        date: Optional[date] = None,
        time_range: Optional[tuple] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if date:
            details["date"] = date.isoformat()
        if time_range:
            details["time_range"] = [t.isoformat() for t in time_range]
        
        super().__init__(
            message,
            code="AVAILABILITY_ERROR",
            details=details,
            **kwargs
        )


class SlotNotAvailableError(AvailabilityError):
    """Raised when time slot is not available"""
    
    def __init__(
        self, 
        slot_time: datetime,
        reason: Optional[str] = None,
        alternative_slots: Optional[List[datetime]] = None
    ):
        message = f"Time slot {slot_time} is not available"
        if reason:
            message += f": {reason}"
        
        details = {"slot_time": slot_time.isoformat()}
        if alternative_slots:
            details["alternative_slots"] = [s.isoformat() for s in alternative_slots]
        if reason:
            details["reason"] = reason
        
        super().__init__(
            message,
            code="SLOT_NOT_AVAILABLE",
            details=details
        )


class OverBookingError(SchedulingError):
    """Raised when attempting to overbook a time slot"""
    
    def __init__(
        self, 
        time_slot: datetime,
        current_bookings: int,
        maximum_capacity: int
    ):
        super().__init__(
            f"Time slot {time_slot} is overbooked: {current_bookings}/{maximum_capacity}",
            code="OVERBOOKING_ERROR",
            details={
                "time_slot": time_slot.isoformat(),
                "current_bookings": current_bookings,
                "maximum_capacity": maximum_capacity
            }
        )


# Nigerian Business Specific Exceptions

class NigerianHolidayError(SchedulingError):
    """Raised when trying to book on Nigerian public holidays"""
    
    def __init__(
        self, 
        holiday_date: date,
        holiday_name: str
    ):
        super().__init__(
            f"Cannot book appointment on {holiday_name} ({holiday_date})",
            code="NIGERIAN_HOLIDAY_ERROR",
            details={
                "holiday_date": holiday_date.isoformat(),
                "holiday_name": holiday_name
            }
        )


class RamadanSchedulingError(SchedulingError):
    """Raised for Ramadan-specific scheduling constraints"""
    
    def __init__(
        self, 
        message: str,
        ramadan_period: Optional[tuple] = None,
        suggested_hours: Optional[tuple] = None
    ):
        details = {}
        if ramadan_period:
            details["ramadan_period"] = [d.isoformat() for d in ramadan_period]
        if suggested_hours:
            details["suggested_hours"] = [t.isoformat() for t in suggested_hours]
        
        super().__init__(
            message,
            code="RAMADAN_SCHEDULING_ERROR",
            details=details
        )


class StateRegulationError(SchedulingError):
    """Raised when appointment violates state-specific regulations"""
    
    def __init__(
        self, 
        message: str,
        state: str,
        regulation_type: str,
        regulation_details: Optional[Dict] = None
    ):
        details = {
            "state": state,
            "regulation_type": regulation_type
        }
        if regulation_details:
            details.update(regulation_details)
        
        super().__init__(
            message,
            code="STATE_REGULATION_ERROR",
            details=details
        )


# Notification and Reminder Exceptions

class ReminderError(SchedulingError):
    """Raised for appointment reminder errors"""
    
    def __init__(
        self, 
        message: str,
        reminder_type: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if reminder_type:
            details["reminder_type"] = reminder_type
        if delivery_method:
            details["delivery_method"] = delivery_method
        
        super().__init__(
            message,
            code="REMINDER_ERROR",
            details=details,
            **kwargs
        )


class NotificationDeliveryError(ReminderError):
    """Raised when notification delivery fails"""
    
    def __init__(
        self, 
        delivery_method: str,
        recipient: str,
        error_details: Optional[Dict] = None
    ):
        details = {
            "delivery_method": delivery_method,
            "recipient": recipient
        }
        if error_details:
            details.update(error_details)
        
        super().__init__(
            f"Failed to deliver {delivery_method} notification to {recipient}",
            code="NOTIFICATION_DELIVERY_FAILED",
            details=details
        )


# Exception mapping for HTTP status codes
SCHEDULING_EXCEPTION_STATUS_MAP = {
    SchedulingError: 400,
    AppointmentNotFoundError: 404,
    AppointmentConflictError: 409,
    ServiceNotAvailableError: 404,
    StaffNotAvailableError: 409,
    InvalidBookingTimeError: 400,
    BookingLimitExceededError: 403,
    InvalidAppointmentStatusError: 400,
    AppointmentCancellationError: 403,
    AppointmentRescheduleError: 403,
    BusinessHoursError: 400,
    RecurringAppointmentError: 400,
    CalendarIntegrationError: 502,
    CalendarSyncError: 502,
    CalendarAuthenticationError: 401,
    CalendarEventError: 502,
    AvailabilityError: 400,
    SlotNotAvailableError: 409,
    OverBookingError: 409,
    NigerianHolidayError: 400,
    RamadanSchedulingError: 400,
    StateRegulationError: 403,
    ReminderError: 500,
    NotificationDeliveryError: 502
}


def get_scheduling_exception_status_code(exception: SchedulingError) -> int:
    """Get HTTP status code for scheduling exception"""
    return SCHEDULING_EXCEPTION_STATUS_MAP.get(type(exception), 500)


def format_scheduling_exception_response(exception: SchedulingError) -> Dict[str, Any]:
    """Format scheduling exception for API response"""
    return {
        "error": {
            "message": exception.message,
            "code": exception.code,
            "details": exception.details,
            "appointment_id": exception.appointment_id,
            "booking_reference": exception.booking_reference
        }
    }


def is_retryable_scheduling_error(exception: SchedulingError) -> bool:
    """Check if a scheduling error is retryable"""
    
    retryable_types = [
        CalendarIntegrationError,
        CalendarSyncError,
        NotificationDeliveryError
    ]
    
    non_retryable_codes = [
        "APPOINTMENT_NOT_FOUND",
        "SERVICE_NOT_AVAILABLE",
        "INVALID_BOOKING_TIME",
        "BOOKING_LIMIT_EXCEEDED",
        "NIGERIAN_HOLIDAY_ERROR",
        "STATE_REGULATION_ERROR"
    ]
    
    return (
        type(exception) in retryable_types and 
        exception.code not in non_retryable_codes
    )