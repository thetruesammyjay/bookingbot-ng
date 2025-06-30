"""
Service configuration models for BookingBot NG tenants
Handles dynamic service definitions and custom field configurations for different business types
"""

from datetime import datetime, time
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, DECIMAL, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import uuid

Base = declarative_base()


class ServiceCategory(str, Enum):
    """Service categories for Nigerian businesses"""
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


class CustomFieldType(str, Enum):
    """Types of custom fields for service booking forms"""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    TIME = "time"
    DROPDOWN = "dropdown"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE_UPLOAD = "file_upload"
    NIGERIAN_STATE = "nigerian_state"
    VEHICLE_TYPE = "vehicle_type"
    MEDICAL_CONDITION = "medical_condition"


class PricingType(str, Enum):
    """Pricing models for services"""
    FIXED = "fixed"
    HOURLY = "hourly"
    PACKAGE = "package"
    CONSULTATION = "consultation"
    FREE = "free"


# Pydantic Schemas for API validation

class CustomFieldSchema(BaseModel):
    """Schema for custom form fields"""
    
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=200)
    field_type: CustomFieldType
    description: Optional[str] = Field(None, max_length=500)
    required: bool = False
    placeholder: Optional[str] = Field(None, max_length=100)
    
    # Field-specific options
    options: Optional[List[str]] = None  # For dropdown, radio, checkbox
    min_value: Optional[Union[int, float]] = None  # For number fields
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None  # For text fields
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex validation
    
    # File upload options
    allowed_file_types: Optional[List[str]] = None
    max_file_size_mb: Optional[int] = None
    
    # Display options
    order: int = 0
    group: Optional[str] = None  # Group related fields
    conditional_on: Optional[str] = None  # Show based on other field value
    conditional_value: Optional[str] = None
    
    @validator('options')
    def validate_options(cls, v, values):
        field_type = values.get('field_type')
        if field_type in [CustomFieldType.DROPDOWN, CustomFieldType.RADIO, CustomFieldType.CHECKBOX]:
            if not v or len(v) == 0:
                raise ValueError(f"Options required for {field_type} field")
        return v
    
    @validator('allowed_file_types')
    def validate_file_types(cls, v, values):
        field_type = values.get('field_type')
        if field_type == CustomFieldType.FILE_UPLOAD and v:
            allowed_types = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif']
            for file_type in v:
                if file_type not in allowed_types:
                    raise ValueError(f"File type {file_type} not allowed")
        return v


class ServicePricingSchema(BaseModel):
    """Schema for service pricing configuration"""
    
    pricing_type: PricingType = PricingType.FIXED
    base_price: Decimal = Field(0, ge=0)
    currency: str = Field("NGN", regex=r"^[A-Z]{3}$")
    
    # Hourly pricing
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    minimum_hours: Optional[Decimal] = Field(None, ge=0)
    
    # Package pricing
    package_sessions: Optional[int] = Field(None, ge=1)
    package_price: Optional[Decimal] = Field(None, ge=0)
    package_validity_days: Optional[int] = Field(None, ge=1)
    
    # Dynamic pricing
    peak_hour_multiplier: Optional[Decimal] = Field(None, ge=1)
    weekend_multiplier: Optional[Decimal] = Field(None, ge=1)
    holiday_multiplier: Optional[Decimal] = Field(None, ge=1)
    
    # Discounts
    early_bird_discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    early_bird_hours: Optional[int] = Field(None, ge=1)
    bulk_discount_threshold: Optional[int] = Field(None, ge=2)
    bulk_discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Payment options
    payment_required: bool = True
    partial_payment_allowed: bool = False
    deposit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    
    @validator('deposit_percentage')
    def validate_deposit(cls, v, values):
        if values.get('partial_payment_allowed') and not v:
            raise ValueError("Deposit percentage required when partial payment is allowed")
        return v


class ServiceAvailabilitySchema(BaseModel):
    """Schema for service availability settings"""
    
    # Booking windows
    min_advance_booking_hours: int = Field(1, ge=0)
    max_advance_booking_days: int = Field(30, ge=1)
    
    # Capacity limits
    max_daily_bookings: Optional[int] = Field(None, ge=1)
    max_concurrent_bookings: int = Field(1, ge=1)
    
    # Duration settings
    duration_minutes: int = Field(60, ge=15)
    buffer_before_minutes: int = Field(0, ge=0)
    buffer_after_minutes: int = Field(0, ge=0)
    
    # Staff requirements
    requires_specific_staff: bool = False
    allowed_staff_roles: Optional[List[str]] = None
    
    # Scheduling constraints
    available_days_of_week: List[int] = Field(default=[0, 1, 2, 3, 4], description="0=Monday, 6=Sunday")
    unavailable_dates: Optional[List[str]] = None  # ISO date strings
    
    # Nigerian business specific
    observes_public_holidays: bool = True
    observes_ramadan: bool = False
    ramadan_modified_hours: Optional[Dict[str, str]] = None
    
    @validator('available_days_of_week')
    def validate_days(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one day must be available")
        for day in v:
            if day < 0 or day > 6:
                raise ValueError("Days must be 0-6 (Monday-Sunday)")
        return sorted(list(set(v)))


class ServiceConfigurationSchema(BaseModel):
    """Complete service configuration schema"""
    
    # Basic information
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: ServiceCategory
    subcategory: Optional[str] = Field(None, max_length=100)
    
    # Visibility and status
    is_active: bool = True
    is_online_bookable: bool = True
    is_featured: bool = False
    display_order: int = 0
    
    # Pricing configuration
    pricing: ServicePricingSchema
    
    # Availability settings
    availability: ServiceAvailabilitySchema
    
    # Custom fields for booking form
    custom_fields: List[CustomFieldSchema] = []
    
    # Instructions and policies
    booking_instructions: Optional[str] = Field(None, max_length=1000)
    preparation_instructions: Optional[str] = Field(None, max_length=1000)
    cancellation_policy: Optional[str] = Field(None, max_length=1000)
    
    # Media
    image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    
    # SEO and marketing
    tags: Optional[List[str]] = None
    meta_description: Optional[str] = Field(None, max_length=160)
    
    # Industry-specific configurations
    industry_config: Optional[Dict[str, Any]] = None
    
    @validator('industry_config')
    def validate_industry_config(cls, v, values):
        category = values.get('category')
        if category and v:
            # Validate based on category
            if category == ServiceCategory.HEALTHCARE:
                required_fields = ['requires_medical_history', 'consultation_type']
            elif category == ServiceCategory.AUTOMOTIVE:
                required_fields = ['vehicle_inspection_required', 'parts_included']
            elif category == ServiceCategory.BEAUTY:
                required_fields = ['treatment_type', 'duration_category']
            else:
                required_fields = []
            
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Industry config missing required field: {field}")
        return v


# SQLAlchemy ORM Models

class TenantServiceConfig(Base):
    """Database model for tenant service configurations"""
    __tablename__ = "tenant_service_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Basic service information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=True)
    
    # Configuration as JSON
    configuration = Column(JSON, nullable=False)  # ServiceConfigurationSchema as dict
    
    # Status and visibility
    is_active = Column(Boolean, default=True)
    is_online_bookable = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    
    # Usage statistics
    total_bookings = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(12, 2), default=0)
    average_rating = Column(DECIMAL(3, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_schedules: Mapped[List["ServiceSchedule"]] = relationship("ServiceSchedule", back_populates="service_config")
    
    def __repr__(self):
        return f"<TenantServiceConfig(name='{self.name}', tenant='{self.tenant_id}')>"
    
    def to_schema(self) -> ServiceConfigurationSchema:
        """Convert ORM model to Pydantic schema"""
        return ServiceConfigurationSchema(**self.configuration)
    
    @classmethod
    def from_schema(cls, tenant_id: str, schema: ServiceConfigurationSchema) -> 'TenantServiceConfig':
        """Create ORM model from Pydantic schema"""
        return cls(
            tenant_id=tenant_id,
            name=schema.name,
            description=schema.description,
            category=schema.category.value,
            subcategory=schema.subcategory,
            configuration=schema.dict(),
            is_active=schema.is_active,
            is_online_bookable=schema.is_online_bookable,
            is_featured=schema.is_featured,
            display_order=schema.display_order
        )


class ServiceSchedule(Base):
    """Service-specific scheduling overrides"""
    __tablename__ = "service_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_config_id = Column(UUID(as_uuid=True), ForeignKey("tenant_service_configs.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Day-specific availability
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    is_available = Column(Boolean, default=True)
    
    # Time slots
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Capacity overrides
    max_bookings = Column(Integer, nullable=True)
    
    # Staff assignment
    assigned_staff_id = Column(UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=True)
    
    # Pricing overrides
    price_override = Column(DECIMAL(10, 2), nullable=True)
    
    # Special settings
    requires_approval = Column(Boolean, default=False)
    priority_booking = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_config: Mapped["TenantServiceConfig"] = relationship("TenantServiceConfig", back_populates="service_schedules")
    
    def __repr__(self):
        return f"<ServiceSchedule(service='{self.service_config_id}', day={self.day_of_week})>"


class ServiceCustomField(Base):
    """Custom fields for service booking forms"""
    __tablename__ = "service_custom_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_config_id = Column(UUID(as_uuid=True), ForeignKey("tenant_service_configs.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Field definition
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(200), nullable=False)
    field_type = Column(String(50), nullable=False)
    field_config = Column(JSON, nullable=False)  # CustomFieldSchema as dict
    
    # Display settings
    display_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    response_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ServiceCustomField(name='{self.field_name}', type='{self.field_type}')>"


# Industry-specific configuration schemas

class HealthcareServiceConfig(BaseModel):
    """Healthcare-specific service configuration"""
    
    consultation_type: str = Field(..., description="General, Specialist, Emergency, etc.")
    requires_medical_history: bool = True
    requires_insurance_info: bool = False
    accepts_nhis: bool = True
    
    # Medical requirements
    requires_referral: bool = False
    age_restrictions: Optional[Dict[str, int]] = None  # min_age, max_age
    gender_restrictions: Optional[str] = None  # male, female, none
    
    # Documentation
    required_documents: Optional[List[str]] = None
    medical_clearance_required: bool = False
    
    # Safety protocols
    covid_protocols: Optional[Dict[str, Any]] = None
    isolation_required: bool = False


class AutomotiveServiceConfig(BaseModel):
    """Automotive service configuration"""
    
    service_type: str = Field(..., description="Maintenance, Repair, Inspection, etc.")
    vehicle_inspection_required: bool = True
    parts_included: bool = False
    
    # Vehicle requirements
    supported_vehicle_types: List[str] = ["Car", "SUV", "Truck", "Motorcycle"]
    supported_makes: Optional[List[str]] = None
    year_restrictions: Optional[Dict[str, int]] = None
    
    # Service specifics
    requires_vehicle_history: bool = False
    warranty_provided: bool = False
    warranty_duration_days: Optional[int] = None
    
    # Documentation
    requires_registration_papers: bool = False
    requires_insurance_proof: bool = False


class BeautyServiceConfig(BaseModel):
    """Beauty and wellness service configuration"""
    
    treatment_type: str = Field(..., description="Hair, Skin, Nails, Massage, etc.")
    duration_category: str = Field(..., description="Express, Standard, Premium")
    
    # Treatment specifics
    gender_preference: Optional[str] = None  # male, female, unisex
    age_restrictions: Optional[Dict[str, int]] = None
    
    # Requirements
    skin_test_required: bool = False
    consultation_required: bool = False
    before_after_photos: bool = False
    
    # Products and equipment
    products_included: bool = True
    custom_products_allowed: bool = False
    equipment_required: Optional[List[str]] = None


# Predefined service templates for Nigerian businesses

def get_healthcare_templates() -> List[Dict[str, Any]]:
    """Get predefined healthcare service templates"""
    return [
        {
            "name": "General Consultation",
            "description": "Standard doctor consultation for general health issues",
            "category": ServiceCategory.HEALTHCARE,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 5000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 30,
                "min_advance_booking_hours": 2,
                "max_advance_booking_days": 14
            },
            "industry_config": HealthcareServiceConfig(
                consultation_type="General",
                requires_medical_history=True,
                accepts_nhis=True
            ).dict()
        },
        {
            "name": "Specialist Consultation",
            "description": "Consultation with medical specialist",
            "category": ServiceCategory.HEALTHCARE,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 15000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 45,
                "min_advance_booking_hours": 24,
                "max_advance_booking_days": 30
            },
            "industry_config": HealthcareServiceConfig(
                consultation_type="Specialist",
                requires_medical_history=True,
                requires_referral=True,
                accepts_nhis=True
            ).dict()
        }
    ]


def get_automotive_templates() -> List[Dict[str, Any]]:
    """Get predefined automotive service templates"""
    return [
        {
            "name": "Engine Diagnostics",
            "description": "Comprehensive engine diagnostic and fault finding",
            "category": ServiceCategory.AUTOMOTIVE,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 8000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 60,
                "min_advance_booking_hours": 4,
                "max_advance_booking_days": 7
            },
            "industry_config": AutomotiveServiceConfig(
                service_type="Diagnostics",
                vehicle_inspection_required=True,
                parts_included=False,
                supported_vehicle_types=["Car", "SUV", "Truck"]
            ).dict()
        },
        {
            "name": "Oil Change Service",
            "description": "Engine oil and filter replacement",
            "category": ServiceCategory.AUTOMOTIVE,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 12000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 30,
                "min_advance_booking_hours": 2,
                "max_advance_booking_days": 14
            },
            "industry_config": AutomotiveServiceConfig(
                service_type="Maintenance",
                vehicle_inspection_required=False,
                parts_included=True,
                warranty_provided=True,
                warranty_duration_days=90
            ).dict()
        }
    ]


def get_beauty_templates() -> List[Dict[str, Any]]:
    """Get predefined beauty service templates"""
    return [
        {
            "name": "Hair Cut & Styling",
            "description": "Professional haircut and styling service",
            "category": ServiceCategory.BEAUTY,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 5000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 60,
                "min_advance_booking_hours": 2,
                "max_advance_booking_days": 21
            },
            "industry_config": BeautyServiceConfig(
                treatment_type="Hair",
                duration_category="Standard",
                gender_preference="unisex",
                products_included=True
            ).dict()
        },
        {
            "name": "Facial Treatment",
            "description": "Deep cleansing and moisturizing facial treatment",
            "category": ServiceCategory.BEAUTY,
            "pricing": {
                "pricing_type": PricingType.FIXED,
                "base_price": 8000,
                "currency": "NGN"
            },
            "availability": {
                "duration_minutes": 90,
                "min_advance_booking_hours": 4,
                "max_advance_booking_days": 14
            },
            "industry_config": BeautyServiceConfig(
                treatment_type="Skin",
                duration_category="Premium",
                skin_test_required=True,
                consultation_required=True,
                products_included=True
            ).dict()
        }
    ]


def get_service_templates_by_category(category: ServiceCategory) -> List[Dict[str, Any]]:
    """Get service templates for a specific category"""
    templates = {
        ServiceCategory.HEALTHCARE: get_healthcare_templates(),
        ServiceCategory.AUTOMOTIVE: get_automotive_templates(),
        ServiceCategory.BEAUTY: get_beauty_templates()
    }
    
    return templates.get(category, [])


def get_nigerian_custom_field_templates() -> List[CustomFieldSchema]:
    """Get common custom field templates for Nigerian businesses"""
    return [
        CustomFieldSchema(
            name="nigerian_state",
            label="State of Residence",
            field_type=CustomFieldType.NIGERIAN_STATE,
            description="Select your state of residence",
            required=True,
            options=[
                "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
                "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
                "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna",
                "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
                "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers",
                "Sokoto", "Taraba", "Yobe", "Zamfara"
            ],
            order=1
        ),
        CustomFieldSchema(
            name="emergency_contact",
            label="Emergency Contact",
            field_type=CustomFieldType.PHONE,
            description="Emergency contact phone number",
            required=True,
            pattern=r"^\+?234[789][01]\d{8}$",
            order=2
        ),
        CustomFieldSchema(
            name="vehicle_type",
            label="Vehicle Type",
            field_type=CustomFieldType.VEHICLE_TYPE,
            description="Type of vehicle for service",
            required=True,
            options=["Car", "SUV", "Truck", "Motorcycle", "Bus"],
            order=3
        ),
        CustomFieldSchema(
            name="preferred_language",
            label="Preferred Language",
            field_type=CustomFieldType.DROPDOWN,
            description="Preferred language for service",
            required=False,
            options=["English", "Yoruba", "Igbo", "Hausa", "Pidgin"],
            order=4
        )
    ]