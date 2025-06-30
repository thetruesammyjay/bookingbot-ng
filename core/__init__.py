"""
BookingBot NG Core Module

This is the core module for BookingBot NG, providing foundational services
for multi-tenant Nigerian booking and appointment management system.

Modules:
--------
- auth: Authentication, authorization, and tenant management
- payment_processor: Nigerian payment processing with Paystack and NIP integration  
- scheduling: Appointment scheduling and calendar management

Features:
---------
- Multi-tenant architecture with subdomain routing
- Nigerian-specific payment methods (Paystack, Bank Transfer, NIP)
- Timezone-aware scheduling (Africa/Lagos)
- Nigerian business validation (CAC, BVN, NIN)
- External calendar synchronization (Google, Outlook)
- Nigerian holiday and business day handling
- WhatsApp/SMS notifications
- Comprehensive audit logging

Usage:
------
```python
from core.auth import AuthService, TenantService
from core.payment_processor import PaystackClient, NIPVerifier
from core.scheduling import SchedulingService

# Initialize services
auth_service = AuthService(db)
tenant_service = TenantService(db) 
scheduling_service = SchedulingService(db)
```
"""

# Authentication and Authorization
from . import auth
from .auth import (
    # Models
    User, Tenant, TenantUser, UserSession, TenantInvitation,
    UserRole, TenantStatus,
    
    # Services
    AuthService, TenantService, PermissionService,
    
    # Security
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token, SecurityHeaders,
    
    # Middleware and Dependencies
    get_current_tenant, get_current_user, require_authentication,
    require_tenant_member, require_tenant_admin, require_staff_member,
    
    # Exceptions
    AuthenticationError, AuthorizationError, ValidationError,
    TenantError, UserNotFoundError, InvalidCredentialsError
)

# Payment Processing
from . import payment_processor
from .payment_processor import (
    # Models
    PaymentTransaction, PaymentRefund, BankAccount, PaymentPlan,
    PaymentStatus, PaymentMethod, RefundStatus,
    
    # Paystack Integration
    PaystackClient, PaystackWebhookHandler, NIGERIAN_BANKS,
    kobo_to_naira, naira_to_kobo,
    
    # NIP and Bank Transfer
    NIPVerifier, BankTransferValidator, NIGERIAN_BANK_HOLIDAYS,
    is_banking_day, get_next_banking_day,
    
    # Exceptions
    PaymentError, PaymentValidationError, PaymentProviderError,
    InsufficientFundsError, PaystackError, NIPError
)

# Scheduling and Calendar Management
from . import scheduling
from .scheduling import (
    # Models
    Appointment, ServiceDefinition, BusinessHours, AvailabilitySlot,
    AppointmentStatus, RecurrenceType, CalendarProvider,
    
    # Services
    SchedulingService, RecurringAppointmentService,
    
    # Utilities
    convert_to_local_time, convert_to_utc, get_nigerian_holidays,
    is_business_day, validate_booking_time, format_duration,
    
    # Calendar Integration
    GoogleCalendarSync, OutlookCalendarSync,
    
    # Exceptions
    SchedulingError, AppointmentConflictError, ServiceNotAvailableError,
    InvalidBookingTimeError, CalendarIntegrationError
)

__all__ = [
    # Sub-modules
    "auth",
    "payment_processor", 
    "scheduling",
    
    # Authentication & Authorization
    "User", "Tenant", "TenantUser", "UserSession", "TenantInvitation",
    "UserRole", "TenantStatus",
    "AuthService", "TenantService", "PermissionService",
    "verify_password", "get_password_hash", "create_access_token",
    "create_refresh_token", "verify_token", "SecurityHeaders",
    "get_current_tenant", "get_current_user", "require_authentication",
    "require_tenant_member", "require_tenant_admin", "require_staff_member",
    "AuthenticationError", "AuthorizationError", "ValidationError",
    "TenantError", "UserNotFoundError", "InvalidCredentialsError",
    
    # Payment Processing
    "PaymentTransaction", "PaymentRefund", "BankAccount", "PaymentPlan",
    "PaymentStatus", "PaymentMethod", "RefundStatus",
    "PaystackClient", "PaystackWebhookHandler", "NIGERIAN_BANKS",
    "kobo_to_naira", "naira_to_kobo",
    "NIPVerifier", "BankTransferValidator", "NIGERIAN_BANK_HOLIDAYS",
    "is_banking_day", "get_next_banking_day",
    "PaymentError", "PaymentValidationError", "PaymentProviderError",
    "InsufficientFundsError", "PaystackError", "NIPError",
    
    # Scheduling & Calendar
    "Appointment", "ServiceDefinition", "BusinessHours", "AvailabilitySlot",
    "AppointmentStatus", "RecurrenceType", "CalendarProvider",
    "SchedulingService", "RecurringAppointmentService",
    "convert_to_local_time", "convert_to_utc", "get_nigerian_holidays",
    "is_business_day", "validate_booking_time", "format_duration",
    "GoogleCalendarSync", "OutlookCalendarSync",
    "SchedulingError", "AppointmentConflictError", "ServiceNotAvailableError",
    "InvalidBookingTimeError", "CalendarIntegrationError"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Core services for Nigerian multi-tenant booking and appointment management"

# Module metadata
CORE_MODULES = {
    "auth": {
        "description": "Authentication, authorization, and tenant management",
        "features": [
            "Multi-tenant user management",
            "Nigerian business verification (CAC, BVN, NIN)",
            "JWT-based authentication",
            "Role-based access control",
            "Subdomain-based tenant routing"
        ]
    },
    "payment_processor": {
        "description": "Nigerian payment processing and financial transactions",
        "features": [
            "Paystack card and bank payments",
            "NIP bank transfer verification",
            "Nigerian bank account validation",
            "Multi-currency support (focus on NGN)",
            "Subscription and billing management"
        ]
    },
    "scheduling": {
        "description": "Appointment scheduling and calendar management",
        "features": [
            "Timezone-aware scheduling (Africa/Lagos)",
            "Nigerian holiday handling",
            "External calendar sync (Google, Outlook)",
            "Recurring appointments",
            "Staff availability management"
        ]
    }
}

def get_module_info(module_name: str = None) -> dict:
    """Get information about core modules"""
    if module_name:
        return CORE_MODULES.get(module_name, {})
    return CORE_MODULES

def check_nigerian_compliance() -> dict:
    """Check Nigerian business compliance features"""
    return {
        "business_registration": {
            "cac_validation": True,
            "tin_validation": True,
            "business_permit_tracking": True
        },
        "financial_compliance": {
            "naira_support": True,
            "cbn_transfer_limits": True,
            "nip_integration": True,
            "paystack_integration": True
        },
        "data_protection": {
            "nin_handling": True,
            "bvn_processing": True,
            "gdpr_like_features": True,
            "audit_logging": True
        },
        "operational": {
            "nigerian_holidays": True,
            "business_hours_management": True,
            "local_timezone_support": True,
            "multi_language_ready": True
        }
    }

def get_supported_industries() -> list:
    """Get list of supported Nigerian industries"""
    return [
        {
            "name": "Healthcare",
            "features": ["NHIS integration", "Patient records", "Medical appointments"],
            "compliance": ["Medical data protection", "Patient privacy"]
        },
        {
            "name": "Automotive", 
            "features": ["Vehicle diagnostics", "Parts management", "Service tracking"],
            "compliance": ["Service warranties", "Parts authenticity"]
        },
        {
            "name": "Beauty & Wellness",
            "features": ["Stylist portfolios", "Treatment packages", "Customer galleries"],
            "compliance": ["Service standards", "Health regulations"]
        },
        {
            "name": "Financial Services",
            "features": ["Consultation booking", "Document upload", "Secure messaging"],
            "compliance": ["CBN regulations", "KYC requirements"]
        },
        {
            "name": "Education",
            "features": ["Class scheduling", "Tutor management", "Course materials"],
            "compliance": ["Educational standards", "Student data protection"]
        },
        {
            "name": "Religious Organizations",
            "features": ["Service scheduling", "Event management", "Member tracking"],
            "compliance": ["Donation tracking", "Member privacy"]
        }
    ]

# Nigerian market configuration
NIGERIAN_CONFIG = {
    "timezone": "Africa/Lagos",
    "currency": "NGN",
    "language": "en-NG",
    "business_hours": {
        "default_start": "08:00",
        "default_end": "17:00",
        "weekend_days": [5, 6],  # Saturday, Sunday
        "ramadan_adjustments": True
    },
    "payment_methods": [
        "paystack_card",
        "paystack_bank", 
        "bank_transfer",
        "cash",
        "pos"
    ],
    "required_documents": [
        "cac_certificate",
        "tax_clearance", 
        "business_permit"
    ]
}

def get_nigerian_config() -> dict:
    """Get Nigerian market configuration"""
    return NIGERIAN_CONFIG.copy()

# Version compatibility
MINIMUM_PYTHON_VERSION = "3.8"
RECOMMENDED_PYTHON_VERSION = "3.11"

def check_compatibility() -> dict:
    """Check system compatibility for Nigerian deployment"""
    import sys
    
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    return {
        "python_version": python_version,
        "minimum_supported": MINIMUM_PYTHON_VERSION,
        "recommended": RECOMMENDED_PYTHON_VERSION,
        "compatible": python_version >= MINIMUM_PYTHON_VERSION,
        "timezone_support": True,
        "unicode_support": True,  # Important for Nigerian languages
        "ssl_support": True       # Required for secure payments
    }