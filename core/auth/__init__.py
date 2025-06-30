"""
BookingBot NG Authentication and Authorization Module

This module provides comprehensive authentication and authorization services
for the multi-tenant booking system with Nigerian business requirements.
"""

from .models import (
    User,
    Tenant,
    TenantUser,
    UserSession,
    TenantInvitation,
    UserRole,
    TenantStatus
)

from .services import (
    AuthService,
    TenantService,
    PermissionService
)

from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_password_reset_token,
    verify_password_reset_token,
    create_email_verification_token,
    verify_email_verification_token,
    SecurityHeaders,
    RateLimiter,
    APIKeyValidator,
    TenantSecurityConfig,
    validate_nigerian_business_id
)

from .middlewares import (
    TenantMiddleware,
    get_current_tenant,
    get_current_user,
    require_authentication,
    require_tenant_member,
    require_tenant_role,
    require_tenant_owner,
    require_tenant_admin,
    require_staff_member,
    require_email_verification,
    APIKeyMiddleware,
    TenantContextMiddleware,
    AuditLogMiddleware,
    get_tenant_settings,
    validate_tenant_limits
)

from .exceptions import (
    BookingBotException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    TenantError,
    UserNotFoundError,
    UserInactiveError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    EmailAlreadyExistsError,
    SubdomainNotAvailableError,
    TenantNotFoundError,
    TenantInactiveError,
    TenantMembershipError,
    InsufficientRoleError,
    RateLimitExceededError,
    VerificationRequiredError,
    SubscriptionLimitError,
    InvalidNigerianIdError,
    BusinessVerificationError,
    WebhookValidationError,
    SecurityViolationError,
    get_exception_status_code,
    format_exception_response
)

__all__ = [
    # Models
    "User",
    "Tenant", 
    "TenantUser",
    "UserSession",
    "TenantInvitation",
    "UserRole",
    "TenantStatus",
    
    # Services
    "AuthService",
    "TenantService", 
    "PermissionService",
    
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "create_password_reset_token",
    "verify_password_reset_token", 
    "create_email_verification_token",
    "verify_email_verification_token",
    "SecurityHeaders",
    "RateLimiter",
    "APIKeyValidator",
    "TenantSecurityConfig",
    "validate_nigerian_business_id",
    
    # Middlewares and Dependencies
    "TenantMiddleware",
    "get_current_tenant",
    "get_current_user",
    "require_authentication", 
    "require_tenant_member",
    "require_tenant_role",
    "require_tenant_owner",
    "require_tenant_admin",
    "require_staff_member",
    "require_email_verification",
    "APIKeyMiddleware",
    "TenantContextMiddleware",
    "AuditLogMiddleware",
    "get_tenant_settings",
    "validate_tenant_limits",
    
    # Exceptions
    "BookingBotException",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "TenantError",
    "UserNotFoundError",
    "UserInactiveError", 
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "EmailAlreadyExistsError",
    "SubdomainNotAvailableError",
    "TenantNotFoundError",
    "TenantInactiveError",
    "TenantMembershipError",
    "InsufficientRoleError",
    "RateLimitExceededError",
    "VerificationRequiredError",
    "SubscriptionLimitError",
    "InvalidNigerianIdError",
    "BusinessVerificationError",
    "WebhookValidationError",
    "SecurityViolationError",
    "get_exception_status_code",
    "format_exception_response"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Authentication and authorization module for Nigerian multi-tenant booking system"