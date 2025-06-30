"""
Scheduling models for BookingBot NG
Handles appointments, calendars, time slots, and Nigerian timezone-aware scheduling
"""

from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, DECIMAL, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class AppointmentStatus(str, Enum):
    """Appointment status options"""
    PENDING = "pending"              # Awaiting confirmation
    CONFIRMED = "confirmed"          # Confirmed by business
    CHECKED_IN = "checked_in"        # Customer has arrived
    IN_PROGRESS = "in_progress"      # Service is being provided
    COMPLETED = "completed"          # Service completed successfully
    CANCELLED = "cancelled"          # Cancelled by customer or business
    NO_SHOW = "no_show"             # Customer didn't show up
    RESCHEDULED = "rescheduled"     # Appointment was rescheduled


class RecurrenceType(str, Enum):
    """Recurrence patterns for appointments"""
    NONE = "none"                    # One-time appointment
    DAILY = "daily"                  # Daily recurrence
    WEEKLY = "weekly"                # Weekly recurrence
    MONTHLY = "monthly"              # Monthly recurrence
    YEARLY = "yearly"                # Yearly recurrence


class CalendarProvider(str, Enum):
    """External calendar providers"""
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"
    INTERNAL = "internal"            # BookingBot's internal calendar


class BusinessHours(Base):
    """Business operating hours for tenants"""
    __tablename__ = "business_hours"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = Column(Integer, nullable=False)  
    
    # Operating hours
    is_open = Column(Boolean, default=True)
    open_time = Column(Time, nullable=True)    # Opening time
    close_time = Column(Time, nullable=True)   # Closing time
    
    # Break times (optional)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    
    # Special settings
    max_bookings_per_day = Column(Integer, nullable=True)
    advance_booking_days = Column(Integer, default=30)  # How far ahead to allow bookings
    
    # Nigerian holidays consideration
    observes_public_holidays = Column(Boolean, default=True)
    observes_religious_holidays = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BusinessHours(tenant='{self.tenant_id}', day={self.day_of_week}, open={self.is_open})>"


class ServiceDefinition(Base):
    """Service definitions with scheduling parameters"""
    __tablename__ = "service_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Service details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # Medical, Beauty, Automotive, etc.
    
    # Scheduling parameters
    duration_minutes = Column(Integer, nullable=False)  # Service duration
    buffer_before_minutes = Column(Integer, default=0)  # Prep time before service
    buffer_after_minutes = Column(Integer, default=0)   # Cleanup time after service
    
    # Booking constraints
    max_advance_booking_days = Column(Integer, default=30)
    min_advance_booking_hours = Column(Integer, default=1)
    max_bookings_per_day = Column(Integer, nullable=True)
    max_concurrent_bookings = Column(Integer, default=1)
    
    # Pricing
    base_price = Column(DECIMAL(10, 2), default=0)
    currency = Column(String(3), default="NGN")
    
    # Staff requirements
    requires_specific_staff = Column(Boolean, default=False)
    staff_count_required = Column(Integer, default=1)
    
    # Nigerian market specifics
    requires_nin_verification = Column(Boolean, default=False)
    requires_bvn_verification = Column(Boolean, default=False)
    age_restriction_minimum = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online_bookable = Column(Boolean, default=True)
    
    # Configuration
    custom_fields = Column(JSON, nullable=True)  # Additional form fields
    booking_instructions = Column(Text, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="service")
    
    def __repr__(self):
        return f"<ServiceDefinition(name='{self.name}', duration={self.duration_minutes}min)>"


class Appointment(Base):
    """Core appointment/booking model"""
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("service_definitions.id"), nullable=False)
    
    # Customer information
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=False)  # Nigerian phone format
    customer_notes = Column(Text, nullable=True)
    
    # Nigerian customer details
    customer_nin = Column(String(11), nullable=True)
    customer_bvn = Column(String(11), nullable=True)
    
    # Appointment timing
    start_time = Column(DateTime, nullable=False)  # Start time (UTC)
    end_time = Column(DateTime, nullable=False)    # End time (UTC)
    timezone = Column(String(50), default="Africa/Lagos")
    
    # Staff assignment
    assigned_staff_id = Column(UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=True)
    
    # Status and tracking
    status = Column(String(20), default=AppointmentStatus.PENDING)
    booking_reference = Column(String(50), unique=True, index=True, nullable=False)
    
    # Payment information
    payment_required = Column(Boolean, default=False)
    payment_amount = Column(DECIMAL(10, 2), nullable=True)
    payment_status = Column(String(20), default="pending")
    payment_transaction_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Booking details
    custom_field_values = Column(JSON, nullable=True)  # Responses to custom fields
    special_requests = Column(Text, nullable=True)
    booking_source = Column(String(50), default="online")  # online, phone, walk-in
    
    # Recurrence
    recurrence_type = Column(String(20), default=RecurrenceType.NONE)
    recurrence_interval = Column(Integer, default=1)
    recurrence_end_date = Column(Date, nullable=True)
    parent_appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    
    # Cancellation and rescheduling
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Attendance tracking
    checked_in_at = Column(DateTime, nullable=True)
    service_started_at = Column(DateTime, nullable=True)
    service_completed_at = Column(DateTime, nullable=True)
    
    # Notifications
    confirmation_sent_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    # Quality and feedback
    customer_rating = Column(Integer, nullable=True)  # 1-5 stars
    customer_feedback = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service: Mapped["ServiceDefinition"] = relationship("ServiceDefinition", back_populates="appointments")
    assigned_staff: Mapped[Optional["TenantUser"]] = relationship("TenantUser")
    child_appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment", 
        backref="parent_appointment",
        remote_side=[id]
    )
    
    def __repr__(self):
        return f"<Appointment(reference='{self.booking_reference}', status='{self.status}')>"


class CalendarIntegration(Base):
    """External calendar integration settings"""
    __tablename__ = "calendar_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Integration details
    provider = Column(String(20), nullable=False)  # CalendarProvider enum
    provider_user_id = Column(String(200), nullable=True)  # User ID in external system
    calendar_id = Column(String(200), nullable=True)       # Calendar ID in external system
    
    # Authentication
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Sync settings
    is_two_way_sync = Column(Boolean, default=False)  # Sync both ways
    sync_all_events = Column(Boolean, default=False)  # Sync non-BookingBot events
    auto_create_meetings = Column(Boolean, default=False)  # Auto-create video meetings
    
    # Sync status
    last_sync_at = Column(DateTime, nullable=True)
    sync_errors = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CalendarIntegration(provider='{self.provider}', tenant='{self.tenant_id}')>"


class AvailabilitySlot(Base):
    """Available time slots for booking"""
    __tablename__ = "availability_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=True)
    
    # Slot timing
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Slot configuration
    slot_duration_minutes = Column(Integer, default=30)
    max_bookings = Column(Integer, default=1)
    current_bookings = Column(Integer, default=0)
    
    # Availability status
    is_available = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(200), nullable=True)
    
    # Pricing overrides
    price_override = Column(DECIMAL(10, 2), nullable=True)
    
    # Special settings
    requires_approval = Column(Boolean, default=False)
    is_emergency_slot = Column(Boolean, default=False)
    priority_level = Column(Integer, default=1)  # 1=normal, 2=priority, 3=emergency
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AvailabilitySlot(date='{self.date}', time='{self.start_time}-{self.end_time}')>"


class AppointmentReminder(Base):
    """Scheduled reminders for appointments"""
    __tablename__ = "appointment_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Reminder details
    reminder_type = Column(String(20), nullable=False)  # email, sms, whatsapp, push
    send_at = Column(DateTime, nullable=False)
    
    # Content
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    message_template = Column(String(100), nullable=True)
    
    # Status
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    delivery_status = Column(String(50), nullable=True)
    provider_response = Column(JSON, nullable=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AppointmentReminder(type='{self.reminder_type}', sent={self.is_sent})>"


class BookingAnalytics(Base):
    """Analytics data for booking patterns and business insights"""
    __tablename__ = "booking_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Time period
    date = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Booking metrics
    total_bookings = Column(Integer, default=0)
    confirmed_bookings = Column(Integer, default=0)
    cancelled_bookings = Column(Integer, default=0)
    no_show_bookings = Column(Integer, default=0)
    completed_bookings = Column(Integer, default=0)
    
    # Revenue metrics
    total_revenue = Column(DECIMAL(12, 2), default=0)
    average_booking_value = Column(DECIMAL(10, 2), default=0)
    
    # Time utilization
    total_available_hours = Column(DECIMAL(8, 2), default=0)
    total_booked_hours = Column(DECIMAL(8, 2), default=0)
    utilization_rate = Column(DECIMAL(5, 2), default=0)  # Percentage
    
    # Popular times
    peak_hour_start = Column(Time, nullable=True)
    peak_hour_end = Column(Time, nullable=True)
    busiest_day_of_week = Column(Integer, nullable=True)
    
    # Service breakdown
    service_breakdown = Column(JSON, nullable=True)  # Service ID -> booking count
    staff_breakdown = Column(JSON, nullable=True)    # Staff ID -> booking count
    
    # Customer insights
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    average_customer_rating = Column(DECIMAL(3, 2), nullable=True)
    
    # Nigerian market insights
    payment_method_breakdown = Column(JSON, nullable=True)
    location_breakdown = Column(JSON, nullable=True)  # State/city breakdown
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BookingAnalytics(tenant='{self.tenant_id}', date='{self.date}', bookings={self.total_bookings})>"


class StaffSchedule(Base):
    """Staff working schedules and availability"""
    __tablename__ = "staff_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Schedule details
    date = Column(Date, nullable=False)
    is_working = Column(Boolean, default=True)
    
    # Working hours
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Break times
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    
    # Schedule type
    schedule_type = Column(String(20), default="regular")  # regular, overtime, on_call
    
    # Special settings
    max_appointments = Column(Integer, nullable=True)
    hourly_rate = Column(DECIMAL(8, 2), nullable=True)
    overtime_rate = Column(DECIMAL(8, 2), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StaffSchedule(staff='{self.staff_id}', date='{self.date}', working={self.is_working})>"