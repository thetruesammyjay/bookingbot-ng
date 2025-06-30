"""
Authentication and authorization models for BookingBot NG
Supports multi-tenant architecture with Nigerian business context
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class UserRole(str, Enum):
    """User roles within the system"""
    SUPER_ADMIN = "super_admin"      # Platform administrators
    TENANT_OWNER = "tenant_owner"    # Business owners
    TENANT_ADMIN = "tenant_admin"    # Business managers
    STAFF = "staff"                  # Service providers (doctors, stylists, etc.)
    CUSTOMER = "customer"            # End users booking services


class TenantStatus(str, Enum):
    """Tenant business status"""
    PENDING = "pending"              # Awaiting verification
    ACTIVE = "active"                # Fully operational
    SUSPENDED = "suspended"          # Temporarily disabled
    CANCELLED = "cancelled"          # Permanently closed


class User(Base):
    """Core user model - platform-wide users"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), index=True, nullable=True)  # Nigerian phone format (+234...)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Nigerian-specific fields
    nin = Column(String(11), nullable=True, index=True)  # National Identification Number
    bvn = Column(String(11), nullable=True)              # Bank Verification Number
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    tenant_associations: Mapped[List["TenantUser"]] = relationship(
        "TenantUser", back_populates="user"
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession", back_populates="user"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User(email='{self.email}', active={self.is_active})>"


class Tenant(Base):
    """Business tenant model - each business using BookingBot NG"""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Business identification
    business_name = Column(String(200), nullable=False)
    subdomain = Column(String(50), unique=True, index=True, nullable=False)  # e.g., 'clinic' in clinic.bookingbot.ng
    domain = Column(String(100), nullable=True)  # Custom domain if provided
    
    # Registration details
    cac_number = Column(String(20), nullable=True, index=True)  # Corporate Affairs Commission number
    tin = Column(String(20), nullable=True)                     # Tax Identification Number
    
    # Business information
    business_type = Column(String(50), nullable=False)  # healthcare, automotive, beauty, etc.
    description = Column(Text, nullable=True)
    
    # Contact information
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(JSON, nullable=True)  # Nigerian address structure
    
    # Operational settings
    timezone = Column(String(50), default="Africa/Lagos")
    currency = Column(String(3), default="NGN")
    language = Column(String(5), default="en-NG")
    
    # Status and compliance
    status = Column(String(20), default=TenantStatus.PENDING)
    is_verified = Column(Boolean, default=False)
    verification_documents = Column(JSON, nullable=True)
    
    # Subscription and limits
    subscription_tier = Column(String(20), default="basic")  # basic, pro, enterprise
    max_staff = Column(Integer, default=5)
    max_bookings_per_month = Column(Integer, default=100)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    brand_colors = Column(JSON, nullable=True)  # Theme colors
    custom_css = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant_users: Mapped[List["TenantUser"]] = relationship(
        "TenantUser", back_populates="tenant"
    )
    
    def __repr__(self):
        return f"<Tenant(business_name='{self.business_name}', subdomain='{self.subdomain}')>"


class TenantUser(Base):
    """Association between users and tenants with roles"""
    __tablename__ = "tenant_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Role and permissions
    role = Column(String(20), nullable=False)  # UserRole enum values
    permissions = Column(JSON, nullable=True)  # Granular permissions
    
    # Staff-specific information (for STAFF role)
    staff_title = Column(String(100), nullable=True)  # Doctor, Stylist, Mechanic, etc.
    specializations = Column(JSON, nullable=True)     # Areas of expertise
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    
    # Availability and settings
    working_hours = Column(JSON, nullable=True)       # Weekly schedule
    is_accepting_bookings = Column(Boolean, default=True)
    notification_preferences = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tenant_associations")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tenant_users")
    
    def __repr__(self):
        return f"<TenantUser(user_id='{self.user_id}', tenant_id='{self.tenant_id}', role='{self.role}')>"


class UserSession(Base):
    """User session management for security tracking"""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session information
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=True)
    
    # Device and location info
    device_info = Column(JSON, nullable=True)  # Browser, OS, device type
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    location = Column(JSON, nullable=True)  # Country, state, city
    
    # Session lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Security flags
    is_suspicious = Column(Boolean, default=False)
    logout_reason = Column(String(50), nullable=True)  # manual, expired, security
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(user_id='{self.user_id}', active={self.is_active})>"


class TenantInvitation(Base):
    """Invitations to join a tenant as staff or admin"""
    __tablename__ = "tenant_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Invitation details
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    invited_role = Column(String(20), nullable=False)
    
    # Invitation token and status
    invitation_token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending, accepted, expired, cancelled
    
    # Optional pre-filled information
    suggested_name = Column(String(200), nullable=True)
    welcome_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<TenantInvitation(email='{self.email}', tenant_id='{self.tenant_id}', status='{self.status}')>"