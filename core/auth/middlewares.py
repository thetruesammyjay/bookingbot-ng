"""
Authentication and tenant middleware for BookingBot NG
Handles request processing, tenant resolution, and user authentication
"""

import re
import datetime
from typing import Optional, Callable, Dict, Any
from uuid import UUID

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .models import User, Tenant, TenantUser, UserRole
from .security import verify_token, SecurityHeaders, check_rate_limit
from .services import AuthService, TenantService, PermissionService
from .exceptions import AuthenticationError, AuthorizationError, TenantError


# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


class TenantMiddleware:
    """Middleware to resolve tenant from subdomain and inject into request"""
    
    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
    
    async def __call__(self, request: Request, call_next):
        """Process request and resolve tenant"""
        
        # Add security headers
        response = await call_next(request)
        for header, value in SecurityHeaders.get_security_headers().items():
            response.headers[header] = value
        
        return response
    
    def extract_tenant_from_host(self, host: str) -> Optional[str]:
        """Extract tenant subdomain from host header"""
        
        # Remove port if present
        host = host.split(':')[0]
        
        # Pattern for tenant subdomains: tenant.bookingbot.ng
        pattern = r'^([a-zA-Z0-9-]+)\.bookingbot\.ng$'
        match = re.match(pattern, host)
        
        if match:
            return match.group(1).lower()
        
        return None


def get_current_tenant(request: Request, db: Session = Depends()) -> Optional[Tenant]:
    """Dependency to get current tenant from request"""
    
    # Get host from request
    host = request.headers.get("host", "")
    
    # Extract tenant subdomain
    middleware = TenantMiddleware(lambda: db)
    tenant_subdomain = middleware.extract_tenant_from_host(host)
    
    if not tenant_subdomain:
        return None
    
    # Get tenant from database
    tenant_service = TenantService(db)
    tenant = db.query(Tenant).filter(
        Tenant.subdomain == tenant_subdomain,
        Tenant.status == "active"
    ).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_subdomain}' not found or inactive"
        )
    
    return tenant


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends()
) -> Optional[User]:
    """Dependency to get current authenticated user"""
    
    if not credentials:
        return None
    
    # Verify token
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user ID from token
    user_id_str = token_data.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    # Get user from database
    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


def require_authentication(
    user: User = Depends(get_current_user)
) -> User:
    """Dependency that requires user to be authenticated"""
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def require_tenant_member(
    user: User = Depends(require_authentication),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends()
) -> TenantUser:
    """Dependency that requires user to be a member of the current tenant"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context available"
        )
    
    # Check if user is member of tenant
    tenant_user = db.query(TenantUser).filter(
        TenantUser.user_id == user.id,
        TenantUser.tenant_id == tenant.id,
        TenantUser.is_active == True
    ).first()
    
    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Not a member of this tenant"
        )
    
    return tenant_user


def require_tenant_role(*required_roles: UserRole):
    """Dependency factory that requires specific tenant roles"""
    
    def role_checker(
        tenant_user: TenantUser = Depends(require_tenant_member)
    ) -> TenantUser:
        
        user_role = UserRole(tenant_user.role)
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {[role.value for role in required_roles]}"
            )
        
        return tenant_user
    
    return role_checker


def require_tenant_owner(
    tenant_user: TenantUser = Depends(require_tenant_role(UserRole.TENANT_OWNER))
) -> TenantUser:
    """Dependency that requires tenant owner role"""
    return tenant_user


def require_tenant_admin(
    tenant_user: TenantUser = Depends(require_tenant_role(UserRole.TENANT_OWNER, UserRole.TENANT_ADMIN))
) -> TenantUser:
    """Dependency that requires tenant admin or owner role"""
    return tenant_user


def require_staff_member(
    tenant_user: TenantUser = Depends(require_tenant_role(
        UserRole.TENANT_OWNER, 
        UserRole.TENANT_ADMIN, 
        UserRole.STAFF
    ))
) -> TenantUser:
    """Dependency that requires staff, admin, or owner role"""
    return tenant_user


class APIKeyMiddleware:
    """Middleware for API key authentication on webhook endpoints"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys  # Service name -> API key mapping
    
    def validate_api_key(self, request: Request, service: str) -> bool:
        """Validate API key for specific service"""
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        if not api_key:
            return False
        
        # Remove "Bearer " prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        expected_key = self.api_keys.get(service)
        if not expected_key:
            return False
        
        return api_key == expected_key


def rate_limit(max_attempts: int = 5):
    """Rate limiting decorator for endpoints"""
    
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            check_rate_limit(request, max_attempts)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


class TenantContextMiddleware:
    """Middleware to inject tenant context into request state"""
    
    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
    
    async def __call__(self, request: Request, call_next):
        """Inject tenant context into request"""
        
        # Initialize request state
        request.state.tenant = None
        request.state.user = None
        request.state.tenant_user = None
        
        # Extract tenant from host
        host = request.headers.get("host", "")
        tenant_middleware = TenantMiddleware(self.db_session_factory)
        tenant_subdomain = tenant_middleware.extract_tenant_from_host(host)
        
        if tenant_subdomain:
            # Get database session
            db = self.db_session_factory()
            try:
                # Get tenant
                tenant_service = TenantService(db)
                tenant = db.query(Tenant).filter(
                    Tenant.subdomain == tenant_subdomain,
                    Tenant.status == "active"
                ).first()
                
                if tenant:
                    request.state.tenant = tenant
                
            finally:
                db.close()
        
        response = await call_next(request)
        return response


def get_tenant_settings(
    tenant: Tenant = Depends(get_current_tenant)
) -> Dict[str, Any]:
    """Get tenant-specific settings and configuration"""
    
    if not tenant:
        return {}
    
    return {
        "tenant_id": str(tenant.id),
        "business_name": tenant.business_name,
        "business_type": tenant.business_type,
        "timezone": tenant.timezone,
        "currency": tenant.currency,
        "language": tenant.language,
        "brand_colors": tenant.brand_colors,
        "subscription_tier": tenant.subscription_tier,
        "max_staff": tenant.max_staff,
        "max_bookings_per_month": tenant.max_bookings_per_month
    }


def validate_tenant_limits(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends()
):
    """Middleware to validate tenant subscription limits"""
    
    def limiter(func):
        async def wrapper(*args, **kwargs):
            if not tenant:
                return await func(*args, **kwargs)
            
            # Example: Check staff limit
            current_staff_count = db.query(TenantUser).filter(
                TenantUser.tenant_id == tenant.id,
                TenantUser.role.in_([UserRole.STAFF, UserRole.TENANT_ADMIN]),
                TenantUser.is_active == True
            ).count()
            
            if current_staff_count >= tenant.max_staff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Staff limit reached ({tenant.max_staff}). Please upgrade your subscription."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return limiter


class AuditLogMiddleware:
    """Middleware for audit logging sensitive operations"""
    
    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
    
    async def log_action(
        self,
        user_id: Optional[UUID],
        tenant_id: Optional[UUID],
        action: str,
        resource: str,
        details: Dict[str, Any]
    ):
        """Log audit trail for sensitive actions"""
        
        # In production, you might want to log to a separate audit database
        # or use a dedicated logging service
        
        import json
        from loguru import logger
        
        log_entry = {
            "timestamp": str(datetime.utcnow()),
            "user_id": str(user_id) if user_id else None,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "action": action,
            "resource": resource,
            "details": details
        }
        
        logger.info(f"AUDIT: {json.dumps(log_entry)}")


def require_email_verification(
    user: User = Depends(require_authentication)
) -> User:
    """Dependency that requires user to have verified email"""
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return user