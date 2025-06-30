"""
BookingBot NG Scheduling Module

This module provides comprehensive appointment scheduling and calendar management
for Nigerian businesses with timezone-aware booking and external calendar integration.
"""

from .models import (
    Appointment,
    ServiceDefinition,
    BusinessHours,
    AvailabilitySlot,
    CalendarIntegration,
    AppointmentReminder,
    BookingAnalytics,
    StaffSchedule,
    AppointmentStatus,
    RecurrenceType,
    CalendarProvider
)

from .services import (
    SchedulingService,
    RecurringAppointmentService
)

from .utils import (
    convert_to_local_time,
    convert_to_utc,
    get_nigerian_holidays,
    is_business_day,
    get_next_business_day,
    generate_time_slots,
    validate_booking_time,
    calculate_service_duration,
    format_duration,
    get_time_slot_display,
    calculate_working_hours,
    get_optimal_slot_duration,
    is_weekend,
    get_week_range,
    get_month_range,
    parse_nigerian_time_format,
    format_nigerian_time,
    get_ramadan_dates,
    is_ramadan_period,
    adjust_for_ramadan_hours,
    calculate_appointment_utilization,
    get_nigerian_states,
    get_major_nigerian_cities,
    estimate_travel_time_between_cities,
    generate_booking_confirmation_details
)

from .calendar_sync import (
    GoogleCalendarSync,
    OutlookCalendarSync
)

from .exceptions import (
    SchedulingError,
    AppointmentNotFoundError,
    AppointmentConflictError,
    ServiceNotAvailableError,
    StaffNotAvailableError,
    InvalidBookingTimeError,
    BookingLimitExceededError,
    InvalidAppointmentStatusError,
    AppointmentCancellationError,
    AppointmentRescheduleError,
    BusinessHoursError,
    RecurringAppointmentError,
    CalendarIntegrationError,
    CalendarSyncError,
    CalendarAuthenticationError,
    CalendarEventError,
    AvailabilityError,
    SlotNotAvailableError,
    OverBookingError,
    NigerianHolidayError,
    RamadanSchedulingError,
    StateRegulationError,
    ReminderError,
    NotificationDeliveryError,
    get_scheduling_exception_status_code,
    format_scheduling_exception_response,
    is_retryable_scheduling_error
)

__all__ = [
    # Models
    "Appointment",
    "ServiceDefinition",
    "BusinessHours",
    "AvailabilitySlot",
    "CalendarIntegration",
    "AppointmentReminder",
    "BookingAnalytics",
    "StaffSchedule",
    "AppointmentStatus",
    "RecurrenceType",
    "CalendarProvider",
    
    # Services
    "SchedulingService",
    "RecurringAppointmentService",
    
    # Utilities
    "convert_to_local_time",
    "convert_to_utc",
    "get_nigerian_holidays",
    "is_business_day",
    "get_next_business_day",
    "generate_time_slots",
    "validate_booking_time",
    "calculate_service_duration",
    "format_duration",
    "get_time_slot_display",
    "calculate_working_hours",
    "get_optimal_slot_duration",
    "is_weekend",
    "get_week_range",
    "get_month_range",
    "parse_nigerian_time_format",
    "format_nigerian_time",
    "get_ramadan_dates",
    "is_ramadan_period",
    "adjust_for_ramadan_hours",
    "calculate_appointment_utilization",
    "get_nigerian_states",
    "get_major_nigerian_cities",
    "estimate_travel_time_between_cities",
    "generate_booking_confirmation_details",
    
    # Calendar Integration
    "GoogleCalendarSync",
    "OutlookCalendarSync",
    
    # Exceptions
    "SchedulingError",
    "AppointmentNotFoundError",
    "AppointmentConflictError",
    "ServiceNotAvailableError",
    "StaffNotAvailableError",
    "InvalidBookingTimeError",
    "BookingLimitExceededError",
    "InvalidAppointmentStatusError",
    "AppointmentCancellationError",
    "AppointmentRescheduleError",
    "BusinessHoursError",
    "RecurringAppointmentError",
    "CalendarIntegrationError",
    "CalendarSyncError",
    "CalendarAuthenticationError",
    "CalendarEventError",
    "AvailabilityError",
    "SlotNotAvailableError",
    "OverBookingError",
    "NigerianHolidayError",
    "RamadanSchedulingError",
    "StateRegulationError",
    "ReminderError",
    "NotificationDeliveryError",
    "get_scheduling_exception_status_code",
    "format_scheduling_exception_response",
    "is_retryable_scheduling_error"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Nigerian timezone-aware scheduling and calendar management system"