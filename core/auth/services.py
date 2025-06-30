"""
Authentication and authorization services for BookingBot NG
Handles user registration, login, tenant management, and Nigerian-specific validations
"""

import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from passlib.context import CryptContext
from jose import JWTError, jwt
from python_slugify import slugify

from .models import User, Tenant, TenantUser, UserSession, TenantInvitation, UserRole, TenantStatus
from .security import verify_password, get_password_hash, create_access_token, create_refresh_token
from .exceptions import AuthenticationError, AuthorizationError, TenantError, ValidationError


class AuthService:
    """Core authentication and user management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        nin: Optional[str] = None
    ) -> User:
        """Register a new user with Nigerian validation"""
        
        # Validate inputs
        self._validate_email(email)
        self._validate_password(password)
        if phone:
            self._validate_nigerian_phone(phone)
        if nin:
            self._validate_nin(nin)
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValidationError("User with this email already exists")
        
        # Create user
        user = User(
            email=email.lower().strip(),
            hashed_password=get_password_hash(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=self._normalize_nigerian_phone(phone) if phone else None,
            nin=nin
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        user = self.db.query(User).filter(
            User.email == email.lower().strip(),
            User.is_active == True
        ).first()
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    async def create_user_session(
        self,
        user: User,
        device_info: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a new user session with tokens"""
        
        # Create access and refresh tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            session_token=access_token,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(days=7)  # Refresh token expiry
        )
        
        self.db.add(session)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token"""
        
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise AuthenticationError("Invalid or expired refresh token")
        
        # Get user
        user = self.db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new access token
        new_access_token = create_access_token(data={"sub": str(user.id)})
        
        # Update session
        session.session_token = new_access_token
        session.last_activity = datetime.utcnow()
        self.db.commit()
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    async def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session"""
        
        session = self.db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if session:
            session.is_active = False
            session.logout_reason = "manual"
            self.db.commit()
            return True
        
        return False
    
    def _validate_email(self, email: str) -> None:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
    
    def _validate_password(self, password: str) -> None:
        """Validate password strength"""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number")
    
    def _validate_nigerian_phone(self, phone: str) -> None:
        """Validate Nigerian phone number format"""
        # Nigerian phone patterns: +234, 0, or direct network codes
        patterns = [
            r'^\+234[789][01]\d{8}$',  # +234 format
            r'^0[789][01]\d{8}$',      # 0 prefix format
            r'^[789][01]\d{8}$'        # Direct format
        ]
        
        if not any(re.match(pattern, phone) for pattern in patterns):
            raise ValidationError("Invalid Nigerian phone number format")
    
    def _normalize_nigerian_phone(self, phone: str) -> str:
        """Normalize Nigerian phone to +234 format"""
        # Remove spaces and hyphens
        phone = re.sub(r'[\s-]', '', phone)
        
        if phone.startswith('+234'):
            return phone
        elif phone.startswith('0'):
            return f'+234{phone[1:]}'
        elif phone.startswith(('7', '8', '9')):
            return f'+234{phone}'
        
        return phone
    
    def _validate_nin(self, nin: str) -> None:
        """Validate Nigerian National Identification Number"""
        if not re.match(r'^\d{11}$', nin):
            raise ValidationError("NIN must be 11 digits")


class TenantService:
    """Tenant (business) management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_tenant(
        self,
        business_name: str,
        subdomain: str,
        business_type: str,
        owner_user_id: UUID,
        email: str,
        phone: str,
        cac_number: Optional[str] = None,
        address: Optional[Dict] = None
    ) -> Tenant:
        """Create a new business tenant"""
        
        # Validate subdomain
        subdomain = self._validate_and_normalize_subdomain(subdomain)
        
        # Check if subdomain is available
        existing_tenant = self.db.query(Tenant).filter(Tenant.subdomain == subdomain).first()
        if existing_tenant:
            raise TenantError(f"Subdomain '{subdomain}' is already taken")
        
        # Validate CAC number if provided
        if cac_number:
            self._validate_cac_number(cac_number)
        
        # Create tenant
        tenant = Tenant(
            business_name=business_name.strip(),
            subdomain=subdomain,
            business_type=business_type,
            email=email.lower().strip(),
            phone=phone,
            cac_number=cac_number,
            address=address,
            status=TenantStatus.PENDING
        )
        
        self.db.add(tenant)
        self.db.flush()  # Get the tenant ID
        
        # Create owner association
        tenant_user = TenantUser(
            user_id=owner_user_id,
            tenant_id=tenant.id,
            role=UserRole.TENANT_OWNER,
            is_active=True
        )
        
        self.db.add(tenant_user)
        self.db.commit()
        self.db.refresh(tenant)
        
        return tenant
    
    async def get_tenant_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """Get tenant by subdomain"""
        return self.db.query(Tenant).filter(
            Tenant.subdomain == subdomain.lower(),
            Tenant.status == TenantStatus.ACTIVE
        ).first()
    
    async def get_user_tenants(self, user_id: UUID) -> List[Tenant]:
        """Get all tenants associated with a user"""
        return self.db.query(Tenant).join(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.is_active == True,
            Tenant.status == TenantStatus.ACTIVE
        ).all()
    
    async def add_user_to_tenant(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role: UserRole,
        added_by_user_id: UUID,
        staff_title: Optional[str] = None,
        specializations: Optional[List[str]] = None
    ) -> TenantUser:
        """Add a user to a tenant with specific role"""
        
        # Verify the adding user has permission
        adding_user_tenant = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == added_by_user_id,
            TenantUser.role.in_([UserRole.TENANT_OWNER, UserRole.TENANT_ADMIN]),
            TenantUser.is_active == True
        ).first()
        
        if not adding_user_tenant:
            raise AuthorizationError("Insufficient permissions to add users")
        
        # Check if user is already in tenant
        existing_association = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id
        ).first()
        
        if existing_association:
            if existing_association.is_active:
                raise TenantError("User is already a member of this tenant")
            else:
                # Reactivate existing association
                existing_association.is_active = True
                existing_association.role = role
                self.db.commit()
                return existing_association
        
        # Create new association
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            staff_title=staff_title,
            specializations=specializations,
            is_active=True
        )
        
        self.db.add(tenant_user)
        self.db.commit()
        self.db.refresh(tenant_user)
        
        return tenant_user
    
    async def create_tenant_invitation(
        self,
        tenant_id: UUID,
        email: str,
        role: UserRole,
        invited_by_user_id: UUID,
        phone: Optional[str] = None,
        suggested_name: Optional[str] = None
    ) -> TenantInvitation:
        """Create an invitation for someone to join a tenant"""
        
        # Generate invitation token
        invitation_token = secrets.token_urlsafe(32)
        
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            invited_by_user_id=invited_by_user_id,
            email=email.lower().strip(),
            phone=phone,
            invited_role=role,
            invitation_token=invitation_token,
            suggested_name=suggested_name,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        
        return invitation
    
    def _validate_and_normalize_subdomain(self, subdomain: str) -> str:
        """Validate and normalize subdomain"""
        # Convert to lowercase and slug format
        normalized = slugify(subdomain, max_length=50)
        
        if not normalized:
            raise ValidationError("Invalid subdomain format")
        
        # Check against reserved words
        reserved_words = {
            'www', 'api', 'admin', 'app', 'mail', 'ftp', 'blog', 'shop',
            'support', 'help', 'docs', 'status', 'static', 'assets',
            'booking', 'bookingbot', 'nigeria', 'ng'
        }
        
        if normalized in reserved_words:
            raise ValidationError(f"Subdomain '{normalized}' is reserved")
        
        return normalized
    
    def _validate_cac_number(self, cac_number: str) -> None:
        """Validate Nigerian Corporate Affairs Commission number"""
        # CAC numbers are typically 6-7 digits, sometimes with prefixes
        if not re.match(r'^(RC|BN|IT)?\d{6,7}$', cac_number.upper()):
            raise ValidationError("Invalid CAC number format")


class PermissionService:
    """Role-based access control service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def check_tenant_permission(
        self,
        user_id: UUID,
        tenant_id: UUID,
        required_roles: List[UserRole]
    ) -> bool:
        """Check if user has required role in tenant"""
        
        tenant_user = self.db.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.is_active == True,
            TenantUser.role.in_(required_roles)
        ).first()
        
        return tenant_user is not None
    
    async def get_user_tenant_role(self, user_id: UUID, tenant_id: UUID) -> Optional[UserRole]:
        """Get user's role in a specific tenant"""
        
        tenant_user = self.db.query(TenantUser).filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.is_active == True
        ).first()
        
        return UserRole(tenant_user.role) if tenant_user else None
    
    async def get_tenant_staff(self, tenant_id: UUID) -> List[TenantUser]:
        """Get all active staff members for a tenant"""
        
        return self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role.in_([UserRole.STAFF, UserRole.TENANT_ADMIN, UserRole.TENANT_OWNER]),
            TenantUser.is_active == True
        ).all()