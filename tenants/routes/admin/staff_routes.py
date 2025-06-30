"""
Admin staff management routes for BookingBot NG
Handles CRUD operations for tenant staff members, roles, and permissions
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from loguru import logger
from pydantic import BaseModel, Field

# Core imports
from core.auth import (
    require_tenant_admin, get_current_tenant, get_current_user,
    TenantUser, Tenant, User, UserRole, TenantService, TenantInvitation
)
from core.database import get_db

# Tenant imports
from tenants.models import BusinessProfile

router = APIRouter(prefix="/admin/staff", tags=["Admin Staff"])


# Pydantic Schemas for Staff Management

class StaffCreateSchema(BaseModel):
    """Schema for creating new staff member"""
    email: str = Field(..., description="Staff member's email")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, description="Nigerian phone number")
    role: UserRole = Field(..., description="Staff role")
    
    # Staff-specific information
    staff_title: Optional[str] = Field(None, max_length=100, description="Job title")
    specializations: Optional[List[str]] = Field(None, description="Areas of expertise")
    bio: Optional[str] = Field(None, max_length=1000, description="Staff biography")
    
    # Work settings
    hourly_rate: Optional[float] = Field(None, ge=0, description="Hourly rate in Naira")
    working_hours: Optional[Dict[str, Any]] = Field(None, description="Weekly schedule")
    is_accepting_bookings: bool = Field(True, description="Whether staff accepts new bookings")
    
    # Contact preferences
    notification_preferences: Optional[Dict[str, bool]] = Field(None)
    
    # Send invitation email
    send_invitation: bool = Field(True, description="Send invitation email to staff member")


class StaffUpdateSchema(BaseModel):
    """Schema for updating staff member"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, description="Nigerian phone number")
    role: Optional[UserRole] = Field(None, description="Staff role")
    
    # Staff-specific information
    staff_title: Optional[str] = Field(None, max_length=100)
    specializations: Optional[List[str]] = Field(None)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image_url: Optional[str] = Field(None)
    
    # Work settings
    hourly_rate: Optional[float] = Field(None, ge=0)
    working_hours: Optional[Dict[str, Any]] = Field(None)
    is_accepting_bookings: Optional[bool] = Field(None)
    
    # Status
    is_active: Optional[bool] = Field(None)


class StaffScheduleSchema(BaseModel):
    """Schema for staff schedule"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_working: bool = Field(True)
    start_time: Optional[str] = Field(None, description="Start time (HH:MM)")
    end_time: Optional[str] = Field(None, description="End time (HH:MM)")
    break_start: Optional[str] = Field(None, description="Break start time (HH:MM)")
    break_end: Optional[str] = Field(None, description="Break end time (HH:MM)")
    max_appointments: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)


# Staff CRUD Operations

@router.get("/", response_model=Dict[str, Any])
async def list_staff(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_accepting_bookings: Optional[bool] = Query(None, description="Filter by booking acceptance"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get list of staff members for the tenant"""
    
    query = db.query(TenantUser).join(User).filter(
        TenantUser.tenant_id == tenant.id,
        TenantUser.role.in_([UserRole.STAFF, UserRole.TENANT_ADMIN, UserRole.TENANT_OWNER])
    )
    
    # Apply filters
    if role:
        query = query.filter(TenantUser.role == role)
    
    if is_active is not None:
        query = query.filter(TenantUser.is_active == is_active)
    
    if is_accepting_bookings is not None:
        query = query.filter(TenantUser.is_accepting_bookings == is_accepting_bookings)
    
    if search:
        query = query.filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                TenantUser.staff_title.ilike(f"%{search}%")
            )
        )
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    staff_members = query.order_by(
        desc(TenantUser.role == UserRole.TENANT_OWNER),
        desc(TenantUser.role == UserRole.TENANT_ADMIN),
        asc(User.first_name),
        asc(User.last_name)
    ).offset(offset).limit(limit).all()
    
    # Format response
    staff_list = []
    for staff in staff_members:
        user = staff.user
        staff_data = {
            "id": str(staff.id),
            "user_id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": staff.role,
            "staff_title": staff.staff_title,
            "specializations": staff.specializations,
            "bio": staff.bio,
            "profile_image_url": staff.profile_image_url,
            "working_hours": staff.working_hours,
            "is_accepting_bookings": staff.is_accepting_bookings,
            "is_active": staff.is_active,
            "joined_at": staff.joined_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        staff_list.append(staff_data)
    
    return {
        "staff": staff_list,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{staff_id}", response_model=Dict[str, Any])
async def get_staff_member(
    staff_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get a specific staff member by ID"""
    
    staff = db.query(TenantUser).join(User).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    user = staff.user
    
    # Get staff performance metrics
    from core.scheduling import Appointment, AppointmentStatus
    from datetime import timedelta
    
    # Last 30 days performance
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_appointments = db.query(Appointment).filter(
        and_(
            Appointment.assigned_staff_id == staff.id,
            Appointment.start_time >= thirty_days_ago
        )
    ).all()
    
    completed_appointments = [a for a in recent_appointments if a.status == AppointmentStatus.COMPLETED]
    total_revenue = sum([float(a.payment_amount or 0) for a in completed_appointments])
    average_rating = sum([a.customer_rating for a in completed_appointments if a.customer_rating]) / len(completed_appointments) if completed_appointments else None
    
    return {
        "id": str(staff.id),
        "user_id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": staff.role,
        "staff_title": staff.staff_title,
        "specializations": staff.specializations,
        "bio": staff.bio,
        "profile_image_url": staff.profile_image_url,
        "working_hours": staff.working_hours,
        "is_accepting_bookings": staff.is_accepting_bookings,
        "is_active": staff.is_active,
        "notification_preferences": staff.notification_preferences,
        "joined_at": staff.joined_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "performance_metrics": {
            "total_appointments_30_days": len(recent_appointments),
            "completed_appointments_30_days": len(completed_appointments),
            "total_revenue_30_days": total_revenue,
            "average_rating": float(average_rating) if average_rating else None,
            "completion_rate": (len(completed_appointments) / len(recent_appointments) * 100) if recent_appointments else 0
        }
    }


@router.post("/", response_model=Dict[str, Any])
async def create_staff_member(
    staff_data: StaffCreateSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create a new staff member (send invitation)"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == staff_data.email).first()
    
    if existing_user:
        # Check if already part of this tenant
        existing_tenant_user = db.query(TenantUser).filter(
            and_(
                TenantUser.user_id == existing_user.id,
                TenantUser.tenant_id == tenant.id
            )
        ).first()
        
        if existing_tenant_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this tenant"
            )
    
    # Check tenant staff limits
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    current_staff_count = db.query(TenantUser).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.role.in_([UserRole.STAFF, UserRole.TENANT_ADMIN]),
            TenantUser.is_active == True
        )
    ).count()
    
    max_staff = business_profile.max_staff if business_profile else 5
    
    if current_staff_count >= max_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Staff limit reached ({max_staff}). Please upgrade your subscription."
        )
    
    # Create invitation
    tenant_service = TenantService(db)
    
    invitation = await tenant_service.create_tenant_invitation(
        tenant_id=tenant.id,
        email=staff_data.email,
        role=staff_data.role,
        invited_by_user_id=tenant_user.user_id,
        phone=staff_data.phone,
        suggested_name=f"{staff_data.first_name} {staff_data.last_name}"
    )
    
    # If user exists, add them directly to tenant
    if existing_user:
        tenant_user_new = await tenant_service.add_user_to_tenant(
            tenant_id=tenant.id,
            user_id=existing_user.id,
            role=staff_data.role,
            added_by_user_id=tenant_user.user_id,
            staff_title=staff_data.staff_title,
            specializations=staff_data.specializations
        )
        
        # Update additional staff information
        tenant_user_new.bio = staff_data.bio
        tenant_user_new.working_hours = staff_data.working_hours
        tenant_user_new.is_accepting_bookings = staff_data.is_accepting_bookings
        tenant_user_new.notification_preferences = staff_data.notification_preferences
        
        db.commit()
        
        logger.info(f"Added existing user {staff_data.email} as staff to tenant {tenant.business_name}")
        
        return {
            "id": str(tenant_user_new.id),
            "email": staff_data.email,
            "message": "Staff member added successfully",
            "invitation_required": False
        }
    
    # Send invitation email if requested
    if staff_data.send_invitation:
        # TODO: Implement email sending service
        logger.info(f"Invitation email should be sent to {staff_data.email}")
    
    logger.info(f"Created invitation for {staff_data.email} to join tenant {tenant.business_name}")
    
    return {
        "invitation_id": str(invitation.id),
        "email": staff_data.email,
        "message": "Staff invitation created successfully",
        "invitation_required": True,
        "invitation_token": invitation.invitation_token
    }


@router.put("/{staff_id}", response_model=Dict[str, Any])
async def update_staff_member(
    staff_id: UUID,
    staff_data: StaffUpdateSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update a staff member's information"""
    
    staff = db.query(TenantUser).join(User).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Check permissions - only owners can modify admins
    if staff.role == UserRole.TENANT_OWNER and tenant_user.role != UserRole.TENANT_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify tenant owner"
        )
    
    if staff.role == UserRole.TENANT_ADMIN and tenant_user.role not in [UserRole.TENANT_OWNER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify admin"
        )
    
    user = staff.user
    
    # Update user information
    if staff_data.first_name is not None:
        user.first_name = staff_data.first_name
    if staff_data.last_name is not None:
        user.last_name = staff_data.last_name
    if staff_data.phone is not None:
        user.phone = staff_data.phone
    
    # Update tenant user information
    if staff_data.role is not None:
        staff.role = staff_data.role
    if staff_data.staff_title is not None:
        staff.staff_title = staff_data.staff_title
    if staff_data.specializations is not None:
        staff.specializations = staff_data.specializations
    if staff_data.bio is not None:
        staff.bio = staff_data.bio
    if staff_data.profile_image_url is not None:
        staff.profile_image_url = staff_data.profile_image_url
    if staff_data.working_hours is not None:
        staff.working_hours = staff_data.working_hours
    if staff_data.is_accepting_bookings is not None:
        staff.is_accepting_bookings = staff_data.is_accepting_bookings
    if staff_data.is_active is not None:
        staff.is_active = staff_data.is_active
    
    db.commit()
    db.refresh(staff)
    
    logger.info(f"Updated staff member {user.email} for tenant {tenant.business_name}")
    
    return {
        "id": str(staff.id),
        "email": user.email,
        "message": "Staff member updated successfully"
    }


@router.delete("/{staff_id}")
async def remove_staff_member(
    staff_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Remove a staff member from the tenant"""
    
    staff = db.query(TenantUser).join(User).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Check permissions
    if staff.role == UserRole.TENANT_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove tenant owner"
        )
    
    if staff.role == UserRole.TENANT_ADMIN and tenant_user.role != UserRole.TENANT_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant owner can remove admins"
        )
    
    # Check for active bookings
    from core.scheduling import Appointment, AppointmentStatus
    active_bookings = db.query(Appointment).filter(
        and_(
            Appointment.assigned_staff_id == staff.id,
            Appointment.status.in_([
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN
            ])
        )
    ).count()
    
    if active_bookings > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot remove staff member with {active_bookings} active bookings. Please reassign or complete them first."
        )
    
    # Soft delete by deactivating
    staff.is_active = False
    staff.is_accepting_bookings = False
    
    db.commit()
    
    logger.info(f"Removed staff member {staff.user.email} from tenant {tenant.business_name}")
    
    return {"message": "Staff member removed successfully"}


# Staff Scheduling

@router.get("/{staff_id}/schedule", response_model=Dict[str, Any])
async def get_staff_schedule(
    staff_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Start date for schedule"),
    date_to: Optional[date] = Query(None, description="End date for schedule")
):
    """Get staff member's schedule"""
    
    staff = db.query(TenantUser).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Get staff schedules
    from core.scheduling import StaffSchedule
    
    query = db.query(StaffSchedule).filter(
        and_(
            StaffSchedule.staff_id == staff.id,
            StaffSchedule.tenant_id == tenant.id
        )
    )
    
    if date_from:
        query = query.filter(StaffSchedule.date >= date_from)
    if date_to:
        query = query.filter(StaffSchedule.date <= date_to)
    
    schedules = query.order_by(StaffSchedule.date).all()
    
    return {
        "staff_id": str(staff_id),
        "staff_name": staff.user.full_name,
        "working_hours": staff.working_hours,
        "schedules": [
            {
                "id": str(schedule.id),
                "date": schedule.date.isoformat(),
                "is_working": schedule.is_working,
                "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
                "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
                "break_start": schedule.break_start.isoformat() if schedule.break_start else None,
                "break_end": schedule.break_end.isoformat() if schedule.break_end else None,
                "max_appointments": schedule.max_appointments,
                "schedule_type": schedule.schedule_type,
                "notes": schedule.notes
            }
            for schedule in schedules
        ]
    }


@router.put("/{staff_id}/schedule", response_model=Dict[str, Any])
async def update_staff_schedule(
    staff_id: UUID,
    schedules: List[StaffScheduleSchema] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update staff member's schedule"""
    
    staff = db.query(TenantUser).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Update working hours in TenantUser
    working_hours = {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    for schedule in schedules:
        day_name = days[schedule.day_of_week]
        if schedule.is_working and schedule.start_time and schedule.end_time:
            working_hours[day_name] = {
                "start": schedule.start_time,
                "end": schedule.end_time,
                "break_start": schedule.break_start,
                "break_end": schedule.break_end
            }
    
    staff.working_hours = working_hours
    
    db.commit()
    
    logger.info(f"Updated schedule for staff member {staff.user.email}")
    
    return {
        "staff_id": str(staff_id),
        "message": "Staff schedule updated successfully"
    }


# Staff Performance and Analytics

@router.get("/{staff_id}/performance", response_model=Dict[str, Any])
async def get_staff_performance(
    staff_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """Get staff member's performance metrics"""
    
    staff = db.query(TenantUser).filter(
        and_(
            TenantUser.id == staff_id,
            TenantUser.tenant_id == tenant.id
        )
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Get appointments for analysis
    from core.scheduling import Appointment, AppointmentStatus
    from datetime import timedelta
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    appointments = db.query(Appointment).filter(
        and_(
            Appointment.assigned_staff_id == staff.id,
            Appointment.start_time >= start_date,
            Appointment.start_time <= end_date
        )
    ).all()
    
    # Calculate metrics
    total_appointments = len(appointments)
    completed_appointments = [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
    cancelled_appointments = [a for a in appointments if a.status == AppointmentStatus.CANCELLED]
    no_show_appointments = [a for a in appointments if a.status == AppointmentStatus.NO_SHOW]
    
    total_revenue = sum([float(a.payment_amount or 0) for a in completed_appointments])
    ratings = [a.customer_rating for a in completed_appointments if a.customer_rating]
    average_rating = sum(ratings) / len(ratings) if ratings else None
    
    # Calculate utilization (appointments vs available time)
    # This is a simplified calculation
    total_hours_worked = len(completed_appointments) * 1  # Assume 1 hour per appointment
    
    return {
        "staff_id": str(staff_id),
        "staff_name": staff.user.full_name,
        "period": f"{start_date.date()} to {end_date.date()}",
        "metrics": {
            "total_appointments": total_appointments,
            "completed_appointments": len(completed_appointments),
            "cancelled_appointments": len(cancelled_appointments),
            "no_show_appointments": len(no_show_appointments),
            "completion_rate": (len(completed_appointments) / total_appointments * 100) if total_appointments > 0 else 0,
            "cancellation_rate": (len(cancelled_appointments) / total_appointments * 100) if total_appointments > 0 else 0,
            "no_show_rate": (len(no_show_appointments) / total_appointments * 100) if total_appointments > 0 else 0,
            "total_revenue": total_revenue,
            "average_booking_value": total_revenue / len(completed_appointments) if completed_appointments else 0,
            "average_rating": float(average_rating) if average_rating else None,
            "total_ratings": len(ratings),
            "estimated_hours_worked": total_hours_worked
        }
    }


# Staff Invitations

@router.get("/invitations", response_model=List[Dict[str, Any]])
async def list_staff_invitations(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by invitation status")
):
    """Get list of pending staff invitations"""
    
    query = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant.id
    )
    
    if status_filter:
        query = query.filter(TenantInvitation.status == status_filter)
    
    invitations = query.order_by(desc(TenantInvitation.created_at)).all()
    
    return [
        {
            "id": str(invitation.id),
            "email": invitation.email,
            "phone": invitation.phone,
            "invited_role": invitation.invited_role,
            "status": invitation.status,
            "suggested_name": invitation.suggested_name,
            "created_at": invitation.created_at.isoformat(),
            "expires_at": invitation.expires_at.isoformat(),
            "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None
        }
        for invitation in invitations
    ]


@router.delete("/invitations/{invitation_id}")
async def cancel_staff_invitation(
    invitation_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Cancel a pending staff invitation"""
    
    invitation = db.query(TenantInvitation).filter(
        and_(
            TenantInvitation.id == invitation_id,
            TenantInvitation.tenant_id == tenant.id
        )
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel non-pending invitation"
        )
    
    invitation.status = "cancelled"
    db.commit()
    
    logger.info(f"Cancelled staff invitation for {invitation.email}")
    
    return {"message": "Invitation cancelled successfully"}


# Bulk Staff Operations

@router.post("/bulk-update", response_model=Dict[str, Any])
async def bulk_update_staff(
    staff_ids: List[UUID] = Body(...),
    updates: Dict[str, Any] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Bulk update multiple staff members"""
    
    # Validate staff IDs belong to tenant
    staff_members = db.query(TenantUser).filter(
        and_(
            TenantUser.id.in_(staff_ids),
            TenantUser.tenant_id == tenant.id
        )
    ).all()
    
    if len(staff_members) != len(staff_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more staff members not found"
        )
    
    # Apply updates
    allowed_fields = ['is_active', 'is_accepting_bookings', 'notification_preferences']
    
    for staff in staff_members:
        # Check permissions for each staff member
        if staff.role == UserRole.TENANT_OWNER:
            continue  # Skip owner
        
        if staff.role == UserRole.TENANT_ADMIN and tenant_user.role != UserRole.TENANT_OWNER:
            continue  # Skip admin if not owner
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(staff, field, value)
    
    db.commit()
    
    logger.info(f"Bulk updated {len(staff_members)} staff members for tenant {tenant.business_name}")
    
    return {
        "updated_staff": len(staff_members),
        "message": f"Successfully updated {len(staff_members)} staff members"
    }