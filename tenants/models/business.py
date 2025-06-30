"""
Business profile models for BookingBot NG tenants
Handles detailed business information, settings, and operational configurations
"""

from datetime import datetime, time, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, DECIMAL, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import uuid

Base = declarative_base()


class BusinessType(str, Enum):
    """Types of businesses using BookingBot NG"""
    HEALTHCARE = "healthcare"
    AUTOMOTIVE = "automotive"
    BEAUTY = "beauty"
    FINANCIAL = "financial"
    EDUCATION = "education"
    RELIGIOUS = "religious"
    AGRICULTURE = "agriculture"
    CONSULTING = "consulting"
    LEGAL = "legal"
    TECHNOLOGY = "technology"
    HOSPITALITY = "hospitality"
    RETAIL = "retail"


class BusinessSize(str, Enum):
    """Business size categories"""
    SOLO = "solo"              # Single person business
    SMALL = "small"            # 2-10 employees
    MEDIUM = "medium"          # 11-50 employees
    LARGE = "large"            # 50+ employees


class VerificationStatus(str, Enum):
    """Business verification status"""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


# Pydantic Schemas

class BusinessAddressSchema(BaseModel):
    """Nigerian business address schema"""
    
    street_address: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    lga: Optional[str] = Field(None, max_length=100, description="Local Government Area")
    postal_code: Optional[str] = Field(None, max_length=10)
    country: str = Field("Nigeria", max_length=50)
    
    # Geographic coordinates for mapping
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    
    # Additional location info
    landmark: Optional[str] = Field(None, max_length=200)
    directions: Optional[str] = Field(None, max_length=500)
    
    @validator('state')
    def validate_nigerian_state(cls, v):
        nigerian_states = [
            "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
            "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
            "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna",
            "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
            "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers",
            "Sokoto", "Taraba", "Yobe", "Zamfara"
        ]
        if v not in nigerian_states:
            raise ValueError(f"Invalid Nigerian state: {v}")
        return v


class BusinessContactSchema(BaseModel):
    """Business contact information"""
    
    primary_phone: str = Field(..., description="Primary business phone number")
    secondary_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    
    primary_email: str = Field(..., description="Primary business email")
    support_email: Optional[str] = None
    
    website: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    @validator('primary_phone', 'secondary_phone', 'whatsapp_number')
    def validate_nigerian_phone(cls, v):
        if v is None:
            return v
        
        import re
        # Nigerian phone patterns
        patterns = [
            r'^\+234[789][01]\d{8}$',  # +234 format
            r'^0[789][01]\d{8}$',      # 0 prefix format
            r'^[789][01]\d{8}$'        # Direct format
        ]
        
        if not any(re.match(pattern, v) for pattern in patterns):
            raise ValueError("Invalid Nigerian phone number format")
        return v


class BusinessHoursSchema(BaseModel):
    """Business operating hours configuration"""
    
    monday: Optional[Dict[str, str]] = None      # {"open": "08:00", "close": "17:00"}
    tuesday: Optional[Dict[str, str]] = None
    wednesday: Optional[Dict[str, str]] = None
    thursday: Optional[Dict[str, str]] = None
    friday: Optional[Dict[str, str]] = None
    saturday: Optional[Dict[str, str]] = None
    sunday: Optional[Dict[str, str]] = None
    
    # Break times
    lunch_break_start: Optional[str] = Field(None, description="Lunch break start time (HH:MM)")
    lunch_break_end: Optional[str] = Field(None, description="Lunch break end time (HH:MM)")
    
    # Special hours
    ramadan_hours: Optional[Dict[str, Any]] = None
    holiday_hours: Optional[Dict[str, Any]] = None
    
    # Timezone
    timezone: str = Field("Africa/Lagos", description="Business timezone")
    
    # 24/7 operations
    is_24_7: bool = False
    
    @validator('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    def validate_hours(cls, v):
        if v is None:
            return v
        
        required_keys = ['open', 'close']
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required key: {key}")
        
        # Validate time format
        import re
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        
        for key, time_str in v.items():
            if key in required_keys and not re.match(time_pattern, time_str):
                raise ValueError(f"Invalid time format for {key}: {time_str}")
        
        return v


class PaymentSettingsSchema(BaseModel):
    """Payment configuration for the business"""
    
    # Accepted payment methods
    accepts_cash: bool = True
    accepts_card: bool = True
    accepts_bank_transfer: bool = True
    accepts_mobile_money: bool = False
    accepts_crypto: bool = False
    
    # Payment processor settings
    paystack_enabled: bool = True
    paystack_public_key: Optional[str] = None
    
    # Pricing settings
    currency: str = Field("NGN", description="Primary currency")
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="Tax rate percentage")
    service_charge: Optional[Decimal] = Field(None, ge=0, description="Fixed service charge")
    service_charge_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Payment policies
    payment_terms: Optional[str] = Field(None, max_length=500)
    refund_policy: Optional[str] = Field(None, max_length=1000)
    late_payment_fee: Optional[Decimal] = Field(None, ge=0)
    
    # Deposit requirements
    requires_deposit: bool = False
    default_deposit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Bank account details for direct transfers
    bank_accounts: Optional[List[Dict[str, str]]] = None


class NotificationSettingsSchema(BaseModel):
    """Notification preferences for the business"""
    
    # Email notifications
    email_notifications_enabled: bool = True
    booking_confirmation_email: bool = True
    booking_reminder_email: bool = True
    booking_cancellation_email: bool = True
    
    # SMS notifications
    sms_notifications_enabled: bool = True
    booking_confirmation_sms: bool = True
    booking_reminder_sms: bool = True
    booking_cancellation_sms: bool = True
    
    # WhatsApp notifications
    whatsapp_notifications_enabled: bool = False
    whatsapp_api_key: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    
    # Push notifications
    push_notifications_enabled: bool = True
    
    # Notification timing
    reminder_hours_before: List[int] = Field(default=[24, 2], description="Hours before appointment to send reminders")
    
    # Staff notifications
    notify_staff_new_booking: bool = True
    notify_staff_cancellation: bool = True
    notify_staff_no_show: bool = True
    
    # Admin notifications
    daily_summary_enabled: bool = True
    weekly_report_enabled: bool = True
    low_availability_alert: bool = True


class BrandingSchema(BaseModel):
    """Business branding and customization"""
    
    # Visual identity
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    
    # Color scheme
    primary_color: str = Field("#007bff", description="Primary brand color (hex)")
    secondary_color: str = Field("#6c757d", description="Secondary brand color (hex)")
    accent_color: str = Field("#28a745", description="Accent color (hex)")
    
    # Typography
    font_family: str = Field("Inter", description="Primary font family")
    
    # Custom CSS
    custom_css: Optional[str] = Field(None, max_length=5000)
    
    # Booking page customization
    booking_page_title: Optional[str] = None
    booking_page_subtitle: Optional[str] = None
    welcome_message: Optional[str] = Field(None, max_length=500)
    
    # Social proof
    testimonials_enabled: bool = True
    reviews_display_enabled: bool = True
    
    @validator('primary_color', 'secondary_color', 'accent_color')
    def validate_hex_color(cls, v):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError("Invalid hex color format")
        return v


# SQLAlchemy ORM Models

class BusinessProfile(Base):
    """Extended business profile for tenants"""
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    
    # Business details
    business_type = Column(String(50), nullable=False)
    business_size = Column(String(20), default=BusinessSize.SMALL)
    industry_specialization = Column(String(100), nullable=True)
    years_in_operation = Column(Integer, nullable=True)
    
    # Registration and legal
    cac_number = Column(String(20), nullable=True, index=True)
    tin = Column(String(20), nullable=True)
    business_registration_date = Column(Date, nullable=True)
    business_license_url = Column(String(500), nullable=True)
    
    # Verification
    verification_status = Column(String(20), default=VerificationStatus.UNVERIFIED)
    verification_date = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verification_documents = Column(JSON, nullable=True)
    
    # Business information
    tagline = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    specialties = Column(JSON, nullable=True)  # List of specialties
    certifications = Column(JSON, nullable=True)  # Professional certifications
    
    # Contact and location
    address = Column(JSON, nullable=False)  # BusinessAddressSchema
    contact_info = Column(JSON, nullable=False)  # BusinessContactSchema
    
    # Operational settings
    business_hours = Column(JSON, nullable=False)  # BusinessHoursSchema
    payment_settings = Column(JSON, nullable=False)  # PaymentSettingsSchema
    notification_settings = Column(JSON, nullable=False)  # NotificationSettingsSchema
    branding = Column(JSON, nullable=False)  # BrandingSchema
    
    # Capacity and limits
    max_staff = Column(Integer, default=5)
    max_daily_bookings = Column(Integer, default=50)
    max_services = Column(Integer, default=10)
    
    # Performance metrics
    total_bookings = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(15, 2), default=0)
    customer_rating = Column(DECIMAL(3, 2), nullable=True)
    review_count = Column(Integer, default=0)
    
    # Compliance and safety
    covid_protocols = Column(JSON, nullable=True)
    safety_measures = Column(JSON, nullable=True)
    insurance_info = Column(JSON, nullable=True)
    
    # SEO and marketing
    meta_title = Column(String(60), nullable=True)
    meta_description = Column(String(160), nullable=True)
    keywords = Column(JSON, nullable=True)  # SEO keywords
    
    # Feature flags
    features_enabled = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_documents: Mapped[List["BusinessDocument"]] = relationship("BusinessDocument", back_populates="business_profile")
    business_reviews: Mapped[List["BusinessReview"]] = relationship("BusinessReview", back_populates="business_profile")
    
    def __repr__(self):
        return f"<BusinessProfile(tenant='{self.tenant_id}', type='{self.business_type}')>"
    
    def get_address(self) -> BusinessAddressSchema:
        """Get business address as Pydantic model"""
        return BusinessAddressSchema(**self.address)
    
    def get_contact_info(self) -> BusinessContactSchema:
        """Get contact information as Pydantic model"""
        return BusinessContactSchema(**self.contact_info)
    
    def get_business_hours(self) -> BusinessHoursSchema:
        """Get business hours as Pydantic model"""
        return BusinessHoursSchema(**self.business_hours)
    
    def get_payment_settings(self) -> PaymentSettingsSchema:
        """Get payment settings as Pydantic model"""
        return PaymentSettingsSchema(**self.payment_settings)
    
    def get_notification_settings(self) -> NotificationSettingsSchema:
        """Get notification settings as Pydantic model"""
        return NotificationSettingsSchema(**self.notification_settings)
    
    def get_branding(self) -> BrandingSchema:
        """Get branding settings as Pydantic model"""
        return BrandingSchema(**self.branding)
    
    def is_open_now(self) -> bool:
        """Check if business is currently open"""
        from datetime import datetime
        import pytz
        
        # Get current time in business timezone
        tz = pytz.timezone(self.get_business_hours().timezone)
        now = datetime.now(tz)
        current_day = now.strftime('%A').lower()
        current_time = now.time()
        
        # Get business hours for current day
        business_hours = self.get_business_hours()
        day_hours = getattr(business_hours, current_day, None)
        
        if not day_hours:
            return False
        
        # Check if within business hours
        from datetime import time as dt_time
        open_time = dt_time.fromisoformat(day_hours['open'])
        close_time = dt_time.fromisoformat(day_hours['close'])
        
        return open_time <= current_time <= close_time


class BusinessDocument(Base):
    """Business verification and legal documents"""
    __tablename__ = "business_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_profile_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Document information
    document_type = Column(String(50), nullable=False)  # cac_certificate, tax_clearance, etc.
    document_name = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(20), nullable=True)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Expiry tracking
    expiry_date = Column(Date, nullable=True)
    expiry_reminder_sent = Column(Boolean, default=False)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_profile: Mapped["BusinessProfile"] = relationship("BusinessProfile", back_populates="business_documents")
    
    def __repr__(self):
        return f"<BusinessDocument(type='{self.document_type}', verified={self.is_verified})>"
    
    def is_expired(self) -> bool:
        """Check if document has expired"""
        if not self.expiry_date:
            return False
        return date.today() > self.expiry_date
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until document expiry"""
        if not self.expiry_date:
            return None
        
        delta = self.expiry_date - date.today()
        return delta.days


class BusinessReview(Base):
    """Customer reviews for businesses"""
    __tablename__ = "business_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_profile_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Review details
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text, nullable=True)
    
    # Service-specific
    service_name = Column(String(200), nullable=True)
    booking_reference = Column(String(50), nullable=True)
    
    # Review metadata
    is_verified_customer = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Response from business
    business_response = Column(Text, nullable=True)
    response_date = Column(DateTime, nullable=True)
    
    # Moderation
    is_approved = Column(Boolean, default=True)
    moderation_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_profile: Mapped["BusinessProfile"] = relationship("BusinessProfile", back_populates="business_reviews")
    
    def __repr__(self):
        return f"<BusinessReview(rating={self.rating}, customer='{self.customer_name}')>"


class BusinessAnalytics(Base):
    """Business performance analytics"""
    __tablename__ = "business_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    business_profile_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id"), nullable=False)
    
    # Analytics period
    date = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Booking metrics
    total_bookings = Column(Integer, default=0)
    confirmed_bookings = Column(Integer, default=0)
    cancelled_bookings = Column(Integer, default=0)
    no_show_bookings = Column(Integer, default=0)
    
    # Revenue metrics
    total_revenue = Column(DECIMAL(12, 2), default=0)
    average_booking_value = Column(DECIMAL(10, 2), default=0)
    
    # Customer metrics
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    customer_satisfaction = Column(DECIMAL(3, 2), nullable=True)
    
    # Operational metrics
    staff_utilization = Column(DECIMAL(5, 2), default=0)  # Percentage
    capacity_utilization = Column(DECIMAL(5, 2), default=0)
    
    # Marketing metrics
    website_visits = Column(Integer, default=0)
    conversion_rate = Column(DECIMAL(5, 2), default=0)
    booking_source_breakdown = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BusinessAnalytics(date='{self.date}', bookings={self.total_bookings})>"


# Nigerian Business Specific Models

class NigerianBusinessCompliance(Base):
    """Nigerian business compliance tracking"""
    __tablename__ = "nigerian_business_compliance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    business_profile_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id"), nullable=False)
    
    # CAC Compliance
    cac_status = Column(String(20), default="pending")
    cac_certificate_url = Column(String(500), nullable=True)
    cac_verified_date = Column(DateTime, nullable=True)
    
    # Tax Compliance
    tin_status = Column(String(20), default="pending")
    tax_clearance_url = Column(String(500), nullable=True)
    tax_clearance_expiry = Column(Date, nullable=True)
    
    # Local Government Compliance
    business_permit_status = Column(String(20), default="pending")
    business_permit_url = Column(String(500), nullable=True)
    business_permit_expiry = Column(Date, nullable=True)
    
    # Industry-specific compliance
    industry_licenses = Column(JSON, nullable=True)
    professional_memberships = Column(JSON, nullable=True)
    
    # Compliance score
    compliance_score = Column(Integer, default=0)  # 0-100
    last_compliance_check = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<NigerianBusinessCompliance(tenant='{self.tenant_id}', score={self.compliance_score})>"
    
    def calculate_compliance_score(self) -> int:
        """Calculate compliance score based on completed requirements"""
        score = 0
        
        # CAC compliance (40 points)
        if self.cac_status == "verified":
            score += 40
        
        # Tax compliance (30 points)
        if self.tin_status == "verified":
            score += 30
        
        # Business permit (20 points)
        if self.business_permit_status == "verified":
            score += 20
        
        # Industry licenses (10 points)
        if self.industry_licenses:
            score += 10
        
        self.compliance_score = score
        return score


def get_nigerian_business_requirements(business_type: str) -> Dict[str, Any]:
    """Get compliance requirements for Nigerian business types"""
    
    base_requirements = {
        "cac_certificate": {"required": True, "description": "Certificate of Incorporation"},
        "tax_clearance": {"required": True, "description": "Tax Clearance Certificate"},
        "business_permit": {"required": True, "description": "Local Government Business Permit"}
    }
    
    industry_requirements = {
        "healthcare": {
            "medical_license": {"required": True, "description": "Medical Practice License"},
            "pharmacy_license": {"required": False, "description": "Pharmacy License (if applicable)"},
            "health_facility_license": {"required": True, "description": "Health Facility License"}
        },
        "financial": {
            "cbn_license": {"required": True, "description": "Central Bank License"},
            "fccpc_registration": {"required": True, "description": "FCCPC Registration"},
            "sec_registration": {"required": False, "description": "SEC Registration (if applicable)"}
        },
        "education": {
            "ministry_approval": {"required": True, "description": "Ministry of Education Approval"},
            "teacher_registration": {"required": True, "description": "Teachers Registration Council"}
        },
        "automotive": {
            "workshop_license": {"required": True, "description": "Automotive Workshop License"},
            "environmental_permit": {"required": True, "description": "Environmental Impact Permit"}
        }
    }
    
    requirements = base_requirements.copy()
    if business_type in industry_requirements:
        requirements.update(industry_requirements[business_type])
    
    return requirements