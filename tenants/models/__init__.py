"""
BookingBot NG Tenant Models Module

This module contains all tenant-specific models including service configurations,
business profiles, and booking management for Nigerian businesses.
"""

# Service Configuration Models
from .service_config import (
    # Enums
    ServiceCategory,
    CustomFieldType,
    PricingType,
    
    # Pydantic Schemas
    CustomFieldSchema,
    ServicePricingSchema,
    ServiceAvailabilitySchema,
    ServiceConfigurationSchema,
    HealthcareServiceConfig,
    AutomotiveServiceConfig,
    BeautyServiceConfig,
    
    # SQLAlchemy Models
    TenantServiceConfig,
    ServiceSchedule,
    ServiceCustomField,
    
    # Utility Functions
    get_healthcare_templates,
    get_automotive_templates,
    get_beauty_templates,
    get_service_templates_by_category,
    get_nigerian_custom_field_templates
)

# Business Profile Models
from .business import (
    # Enums
    BusinessType,
    BusinessSize,
    VerificationStatus,
    
    # Pydantic Schemas
    BusinessAddressSchema,
    BusinessContactSchema,
    BusinessHoursSchema,
    PaymentSettingsSchema,
    NotificationSettingsSchema,
    BrandingSchema,
    
    # SQLAlchemy Models
    BusinessProfile,
    BusinessDocument,
    BusinessReview,
    BusinessAnalytics,
    NigerianBusinessCompliance,
    
    # Utility Functions
    get_nigerian_business_requirements
)

# Booking and Customer Models
from .booking import (
    # Enums
    CustomerType,
    CustomerStatus,
    BookingSource,
    PreferenceType,
    
    # Pydantic Schemas
    CustomerProfileSchema,
    BookingFormDataSchema,
    
    # SQLAlchemy Models
    TenantCustomer,
    TenantBooking,
    CustomerNote,
    BookingNote,
    CustomerPreference,
    CustomerSegment,
    CustomerSegmentMembership,
    BookingTemplate,
    NigerianCustomerProfile,
    
    # Utility Functions
    generate_customer_reference,
    generate_booking_templates_for_industry,
    get_nigerian_customer_segments
)

__all__ = [
    # Service Configuration
    "ServiceCategory",
    "CustomFieldType",
    "PricingType",
    "CustomFieldSchema",
    "ServicePricingSchema",
    "ServiceAvailabilitySchema",
    "ServiceConfigurationSchema",
    "HealthcareServiceConfig",
    "AutomotiveServiceConfig",
    "BeautyServiceConfig",
    "TenantServiceConfig",
    "ServiceSchedule",
    "ServiceCustomField",
    "get_healthcare_templates",
    "get_automotive_templates",
    "get_beauty_templates",
    "get_service_templates_by_category",
    "get_nigerian_custom_field_templates",
    
    # Business Profile
    "BusinessType",
    "BusinessSize",
    "VerificationStatus",
    "BusinessAddressSchema",
    "BusinessContactSchema",
    "BusinessHoursSchema",
    "PaymentSettingsSchema",
    "NotificationSettingsSchema",
    "BrandingSchema",
    "BusinessProfile",
    "BusinessDocument",
    "BusinessReview",
    "BusinessAnalytics",
    "NigerianBusinessCompliance",
    "get_nigerian_business_requirements",
    
    # Booking and Customer Management
    "CustomerType",
    "CustomerStatus",
    "BookingSource",
    "PreferenceType",
    "CustomerProfileSchema",
    "BookingFormDataSchema",
    "TenantCustomer",
    "TenantBooking",
    "CustomerNote",
    "BookingNote",
    "CustomerPreference",
    "CustomerSegment",
    "CustomerSegmentMembership",
    "BookingTemplate",
    "NigerianCustomerProfile",
    "generate_customer_reference",
    "generate_booking_templates_for_industry",
    "get_nigerian_customer_segments"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Tenant-specific models for Nigerian multi-tenant booking system"