"""
Custom exceptions for authentication and authorization in BookingBot NG
"""

from typing import Optional, Dict, Any


class BookingBotException(Exception):
    """Base exception for BookingBot NG"""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(BookingBotException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class AuthorizationError(BookingBotException):
    """Raised when user lacks required permissions"""
    
    def __init__(self, message: str = "Insufficient permissions", code: str = "AUTH_INSUFFICIENT_PERMISSIONS", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class ValidationError(BookingBotException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class TenantError(BookingBotException):
    """Raised for tenant-related errors"""
    
    def __init__(self, message: str, code: str = "TENANT_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class UserNotFoundError(AuthenticationError):
    """Raised when user is not found"""
    
    def __init__(self, message: str = "User not found", user_id: Optional[str] = None):
        details = {"user_id": user_id} if user_id else {}
        super().__init__(message, "USER_NOT_FOUND", details)


class UserInactiveError(AuthenticationError):
    """Raised when user account is inactive"""
    
    def __init__(self, message: str = "User account is inactive", user_id: Optional[str] = None):
        details = {"user_id": user_id} if user_id else {}
        super().__init__(message, "USER_INACTIVE", details)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, "INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired"""
    
    def __init__(self, message: str = "Token has expired", token_type: str = "access"):
        super().__init__(message, "TOKEN_EXPIRED", {"token_type": token_type})


class TokenInvalidError(AuthenticationError):
    """Raised when token is invalid"""
    
    def __init__(self, message: str = "Invalid token", token_type: str = "access"):
        super().__init__(message, "TOKEN_INVALID", {"token_type": token_type})


class EmailAlreadyExistsError(ValidationError):
    """Raised when trying to register with existing email"""
    
    def __init__(self, email: str):
        super().__init__(f"Email '{email}' is already registered", "EMAIL_EXISTS", {"email": email})


class SubdomainNotAvailableError(TenantError):
    """Raised when subdomain is already taken"""
    
    def __init__(self, subdomain: str):
        super().__init__(f"Subdomain '{subdomain}' is not available", "SUBDOMAIN_TAKEN", {"subdomain": subdomain})


class TenantNotFoundError(TenantError):
    """Raised when tenant is not found"""
    
    def __init__(self, identifier: str, identifier_type: str = "subdomain"):
        super().__init__(
            f"Tenant not found: {identifier}",
            "TENANT_NOT_FOUND",
            {identifier_type: identifier}
        )


class TenantInactiveError(TenantError):
    """Raised when tenant is inactive or suspended"""
    
    def __init__(self, tenant_id: str, status: str):
        super().__init__(
            f"Tenant is {status}",
            "TENANT_INACTIVE",
            {"tenant_id": tenant_id, "status": status}
        )


class TenantMembershipError(AuthorizationError):
    """Raised when user is not a member of required tenant"""
    
    def __init__(self, user_id: str, tenant_id: str):
        super().__init__(
            "User is not a member of this tenant",
            "NOT_TENANT_MEMBER",
            {"user_id": user_id, "tenant_id": tenant_id}
        )


class InsufficientRoleError(AuthorizationError):
    """Raised when user doesn't have required role"""
    
    def __init__(self, current_role: str, required_roles: list):
        super().__init__(
            f"Role '{current_role}' insufficient. Required: {required_roles}",
            "INSUFFICIENT_ROLE",
            {"current_role": current_role, "required_roles": required_roles}
        )


class RateLimitExceededError(BookingBotException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: str, identifier: str):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}",
            "RATE_LIMIT_EXCEEDED",
            {"limit": limit, "window": window, "identifier": identifier}
        )


class VerificationRequiredError(AuthorizationError):
    """Raised when verification is required"""
    
    def __init__(self, verification_type: str = "email"):
        super().__init__(
            f"{verification_type.title()} verification required",
            "VERIFICATION_REQUIRED",
            {"verification_type": verification_type}
        )


class SubscriptionLimitError(TenantError):
    """Raised when tenant subscription limits are exceeded"""
    
    def __init__(self, limit_type: str, current: int, maximum: int):
        super().__init__(
            f"{limit_type.title()} limit exceeded: {current}/{maximum}",
            "SUBSCRIPTION_LIMIT_EXCEEDED",
            {"limit_type": limit_type, "current": current, "maximum": maximum}
        )


class InvalidNigerianIdError(ValidationError):
    """Raised when Nigerian ID validation fails"""
    
    def __init__(self, id_type: str, value: str):
        super().__init__(
            f"Invalid {id_type.upper()}: {value}",
            "INVALID_NIGERIAN_ID",
            {"id_type": id_type, "value": value}
        )


class BusinessVerificationError(TenantError):
    """Raised when business verification fails"""
    
    def __init__(self, message: str, verification_type: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            "BUSINESS_VERIFICATION_FAILED",
            {"verification_type": verification_type, "details": details or {}}
        )


class WebhookValidationError(BookingBotException):
    """Raised when webhook signature validation fails"""
    
    def __init__(self, provider: str, message: str = "Webhook signature validation failed"):
        super().__init__(
            message,
            "WEBHOOK_VALIDATION_FAILED",
            {"provider": provider}
        )


class SecurityViolationError(BookingBotException):
    """Raised when security policies are violated"""
    
    def __init__(self, violation_type: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            "SECURITY_VIOLATION",
            {"violation_type": violation_type, "details": details or {}}
        )


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAP = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    ValidationError: 400,
    TenantError: 400,
    UserNotFoundError: 401,
    UserInactiveError: 401,
    InvalidCredentialsError: 401,
    TokenExpiredError: 401,
    TokenInvalidError: 401,
    EmailAlreadyExistsError: 409,
    SubdomainNotAvailableError: 409,
    TenantNotFoundError: 404,
    TenantInactiveError: 403,
    TenantMembershipError: 403,
    InsufficientRoleError: 403,
    RateLimitExceededError: 429,
    VerificationRequiredError: 403,
    SubscriptionLimitError: 403,
    InvalidNigerianIdError: 400,
    BusinessVerificationError: 400,
    WebhookValidationError: 401,
    SecurityViolationError: 403
}


def get_exception_status_code(exception: BookingBotException) -> int:
    """Get HTTP status code for exception"""
    return EXCEPTION_STATUS_MAP.get(type(exception), 500)


def format_exception_response(exception: BookingBotException) -> Dict[str, Any]:
    """Format exception for API response"""
    return {
        "error": {
            "message": exception.message,
            "code": exception.code,
            "details": exception.details
        }
    }