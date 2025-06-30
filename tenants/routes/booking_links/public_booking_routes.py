"""
Public booking routes for BookingBot NG
Customer-facing API endpoints for service discovery and appointment booking
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from loguru import logger
from pydantic import BaseModel, Field

# Core imports
from core.auth import get_current_tenant, Tenant
from core.scheduling import (
    SchedulingService, find_available_slots, 
    convert_to_local_time, get_nigerian_holidays
)
from core.payment_processor import PaystackClient, NIPVerifier
from core.database import get_db

# Tenant imports
from tenants.models import (
    TenantServiceConfig, BusinessProfile, TenantCustomer, TenantBooking,
    CustomerProfileSchema, BookingFormDataSchema, BookingSource,
    generate_customer_reference
)

router = APIRouter(prefix="", tags=["Public Booking"])


# Pydantic Schemas for Public API

class ServiceDisplaySchema(BaseModel):
    """Schema for displaying services to customers"""
    id: str
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    duration_minutes: int
    base_price: float
    currency: str
    image_url: Optional[str]
    is_featured: bool
    booking_instructions: Optional[str]
    custom_fields: List[Dict[str, Any]] = []


class BusinessInfoSchema(BaseModel):
    """Schema for public business information"""
    business_name: str
    tagline: Optional[str]
    description: Optional[str]
    address: Dict[str, Any]
    contact_info: Dict[str, Any]
    business_hours: Dict[str, Any]
    specialties: Optional[List[str]]
    customer_rating: Optional[float]
    review_count: int
    branding: Dict[str, Any]


class AvailableSlotSchema(BaseModel):
    """Schema for available booking slots"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    staff_id: Optional[str]
    staff_name: Optional[str]
    price: float


class BookingRequestSchema(BaseModel):
    """Schema for booking requests"""
    service_id: str
    preferred_date: date
    preferred_time: Optional[time]
    staff_id: Optional[str]
    customer_profile: CustomerProfileSchema
    custom_field_responses: Dict[str, Any] = {}
    special_requests: Optional[str] = None
    payment_method: Optional[str] = None
    booking_source: BookingSource = BookingSource.ONLINE
    referral_source: Optional[str] = None


# Business Information Endpoints

@router.get("/info", response_model=BusinessInfoSchema)
async def get_business_info(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get public business information"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get business profile
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        # Return basic tenant information
        return BusinessInfoSchema(
            business_name=tenant.business_name,
            tagline=None,
            description=tenant.description,
            address={"city": "", "state": "", "country": "Nigeria"},
            contact_info={"primary_email": tenant.email, "primary_phone": tenant.phone},
            business_hours={},
            specialties=None,
            customer_rating=None,
            review_count=0,
            branding={}
        )
    
    return BusinessInfoSchema(
        business_name=tenant.business_name,
        tagline=business_profile.tagline,
        description=business_profile.description,
        address=business_profile.address,
        contact_info=business_profile.contact_info,
        business_hours=business_profile.business_hours,
        specialties=business_profile.specialties,
        customer_rating=float(business_profile.customer_rating) if business_profile.customer_rating else None,
        review_count=business_profile.review_count,
        branding=business_profile.branding
    )


@router.get("/status")
async def get_business_status(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Check if business is currently open and accepting bookings"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    is_open = business_profile.is_open_now() if business_profile else False
    
    # Check if business is accepting online bookings
    active_services = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    ).count()
    
    return {
        "is_open": is_open,
        "accepts_online_bookings": active_services > 0,
        "business_status": tenant.status,
        "timezone": business_profile.get_business_hours().timezone if business_profile else "Africa/Lagos",
        "current_time": datetime.now().isoformat()
    }


# Service Discovery

@router.get("/services", response_model=List[ServiceDisplaySchema])
async def list_public_services(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    featured_only: bool = Query(False, description="Show only featured services"),
    search: Optional[str] = Query(None, description="Search services")
):
    """Get list of bookable services"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    query = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    )
    
    # Apply filters
    if category:
        query = query.filter(TenantServiceConfig.category == category)
    
    if featured_only:
        query = query.filter(TenantServiceConfig.is_featured == True)
    
    if search:
        query = query.filter(
            or_(
                TenantServiceConfig.name.ilike(f"%{search}%"),
                TenantServiceConfig.description.ilike(f"%{search}%")
            )
        )
    
    # Order by featured first, then display order
    services = query.order_by(
        desc(TenantServiceConfig.is_featured),
        asc(TenantServiceConfig.display_order),
        asc(TenantServiceConfig.name)
    ).all()
    
    # Format for public display
    service_list = []
    for service in services:
        config = service.to_schema()
        
        service_display = ServiceDisplaySchema(
            id=str(service.id),
            name=service.name,
            description=service.description,
            category=service.category,
            subcategory=service.subcategory,
            duration_minutes=config.availability.duration_minutes,
            base_price=float(config.pricing.base_price),
            currency=config.pricing.currency,
            image_url=config.image_url,
            is_featured=service.is_featured,
            booking_instructions=config.booking_instructions,
            custom_fields=[field.dict() for field in config.custom_fields]
        )
        service_list.append(service_display)
    
    return service_list


@router.get("/services/{service_id}", response_model=ServiceDisplaySchema)
async def get_service_details(
    service_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific service"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or not available for booking"
        )
    
    config = service.to_schema()
    
    return ServiceDisplaySchema(
        id=str(service.id),
        name=service.name,
        description=service.description,
        category=service.category,
        subcategory=service.subcategory,
        duration_minutes=config.availability.duration_minutes,
        base_price=float(config.pricing.base_price),
        currency=config.pricing.currency,
        image_url=config.image_url,
        is_featured=service.is_featured,
        booking_instructions=config.booking_instructions,
        custom_fields=[field.dict() for field in config.custom_fields]
    )


# Availability and Slot Management

@router.get("/services/{service_id}/availability", response_model=List[AvailableSlotSchema])
async def get_service_availability(
    service_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    date_from: date = Query(..., description="Start date for availability check"),
    date_to: Optional[date] = Query(None, description="End date (defaults to 7 days from start)"),
    staff_id: Optional[UUID] = Query(None, description="Specific staff member")
):
    """Get available booking slots for a service"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Default to 7 days if end date not provided
    if not date_to:
        date_to = date_from + timedelta(days=7)
    
    # Limit to maximum 30 days
    if (date_to - date_from).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 30 days range allowed"
        )
    
    # Get available slots using core scheduling service
    scheduling_service = SchedulingService(db)
    
    try:
        available_slots = scheduling_service.find_available_slots(
            tenant_id=str(tenant.id),
            service_id=str(service_id),
            start_date=date_from,
            end_date=date_to,
            staff_id=str(staff_id) if staff_id else None
        )
        
        # Format slots for response
        formatted_slots = []
        for slot in available_slots:
            # Get staff information if available
            staff_name = None
            if slot.get('staff_id'):
                from core.auth import TenantUser, User
                staff_user = db.query(TenantUser).join(User).filter(
                    TenantUser.id == slot['staff_id']
                ).first()
                if staff_user:
                    staff_name = staff_user.user.full_name
            
            formatted_slot = AvailableSlotSchema(
                start_time=slot['start_time'],
                end_time=slot['end_time'],
                duration_minutes=slot['duration_minutes'],
                staff_id=slot.get('staff_id'),
                staff_name=staff_name,
                price=float(service.to_schema().pricing.base_price)
            )
            formatted_slots.append(formatted_slot)
        
        return formatted_slots
        
    except Exception as e:
        logger.error(f"Error getting availability for service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving availability"
        )


# Booking Creation

@router.post("/book", response_model=Dict[str, Any])
async def create_booking(
    booking_request: BookingRequestSchema,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create a new booking"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Validate service exists and is bookable
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == booking_request.service_id,
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or not available for booking"
        )
    
    # Create or get customer
    customer = db.query(TenantCustomer).filter(
        and_(
            TenantCustomer.tenant_id == tenant.id,
            TenantCustomer.profile_data['email'].astext == booking_request.customer_profile.email
        )
    ).first()
    
    if not customer:
        # Create new customer
        customer_reference = generate_customer_reference(
            str(tenant.id),
            db.query(TenantCustomer).filter(TenantCustomer.tenant_id == tenant.id).count() + 1
        )
        
        customer = TenantCustomer(
            tenant_id=tenant.id,
            customer_reference=customer_reference,
            profile_data=booking_request.customer_profile.dict(),
            acquisition_source=booking_request.booking_source.value
        )
        db.add(customer)
        db.flush()  # Get customer ID
    else:
        # Update existing customer profile
        customer.profile_data = booking_request.customer_profile.dict()
        customer.last_visit_date = datetime.utcnow()
    
    # Create booking using core scheduling service
    scheduling_service = SchedulingService(db)
    
    try:
        # Determine booking time
        if booking_request.preferred_time:
            start_time = datetime.combine(booking_request.preferred_date, booking_request.preferred_time)
        else:
            # Find the earliest available slot for the date
            available_slots = scheduling_service.find_available_slots(
                tenant_id=str(tenant.id),
                service_id=booking_request.service_id,
                start_date=booking_request.preferred_date,
                end_date=booking_request.preferred_date,
                staff_id=booking_request.staff_id
            )
            
            if not available_slots:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No available slots for the selected date"
                )
            
            start_time = available_slots[0]['start_time']
        
        # Convert to UTC for storage
        from core.scheduling import convert_to_utc
        start_time_utc = convert_to_utc(start_time, "Africa/Lagos")
        
        # Create appointment
        service_config = service.to_schema()
        payment_required = service_config.pricing.payment_required
        payment_amount = service_config.pricing.base_price if payment_required else None
        
        appointment = scheduling_service.create_appointment(
            tenant_id=str(tenant.id),
            service_id=booking_request.service_id,
            start_time=start_time_utc,
            customer_data={
                'name': f"{booking_request.customer_profile.first_name} {booking_request.customer_profile.last_name}",
                'email': booking_request.customer_profile.email,
                'phone': booking_request.customer_profile.phone,
                'notes': booking_request.customer_profile.notes if hasattr(booking_request.customer_profile, 'notes') else None,
                'special_requests': booking_request.special_requests
            },
            staff_id=booking_request.staff_id,
            custom_fields=booking_request.custom_field_responses,
            payment_required=payment_required,
            payment_amount=payment_amount
        )
        
        # Create tenant booking record
        booking_form_data = BookingFormDataSchema(
            service_id=booking_request.service_id,
            preferred_date=booking_request.preferred_date,
            preferred_time=booking_request.preferred_time,
            staff_id=booking_request.staff_id,
            customer_profile=booking_request.customer_profile,
            custom_field_responses=booking_request.custom_field_responses,
            special_requests=booking_request.special_requests,
            booking_source=booking_request.booking_source,
            referral_source=booking_request.referral_source,
            payment_method=booking_request.payment_method
        )
        
        tenant_booking = TenantBooking(
            tenant_id=tenant.id,
            customer_id=customer.id,
            appointment_id=appointment.id,
            booking_form_data=booking_form_data.dict(),
            custom_field_responses=booking_request.custom_field_responses,
            booking_source=booking_request.booking_source.value,
            referral_source=booking_request.referral_source
        )
        
        db.add(tenant_booking)
        
        # Update customer stats
        customer.total_bookings += 1
        if customer.total_bookings == 1:
            customer.customer_type = "new"
            customer.first_visit_date = datetime.utcnow()
        else:
            customer.customer_type = "returning"
        
        customer.last_booking_date = datetime.utcnow()
        
        db.commit()
        
        # Get local time for response
        local_start_time = convert_to_local_time(appointment.start_time, "Africa/Lagos")
        local_end_time = convert_to_local_time(appointment.end_time, "Africa/Lagos")
        
        logger.info(f"Created booking {appointment.booking_reference} for customer {customer.customer_reference}")
        
        response_data = {
            "booking_reference": appointment.booking_reference,
            "appointment_id": str(appointment.id),
            "customer_reference": customer.customer_reference,
            "service_name": service.name,
            "start_time": local_start_time.isoformat(),
            "end_time": local_end_time.isoformat(),
            "timezone": "Africa/Lagos",
            "status": appointment.status,
            "payment_required": payment_required,
            "payment_amount": float(payment_amount) if payment_amount else None,
            "created_at": appointment.created_at.isoformat()
        }
        
        # Add payment information if required
        if payment_required and payment_amount:
            response_data["payment_info"] = {
                "amount": float(payment_amount),
                "currency": service_config.pricing.currency,
                "methods_accepted": ["paystack", "bank_transfer", "cash"]
            }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        db.rollback()
        
        if "conflict" in str(e).lower() or "not available" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating booking. Please try again."
            )


# Booking Management

@router.get("/bookings/{booking_reference}", response_model=Dict[str, Any])
async def get_booking_details(
    booking_reference: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get booking details by reference"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get appointment by booking reference
    from core.scheduling import Appointment
    appointment = db.query(Appointment).filter(
        and_(
            Appointment.booking_reference == booking_reference,
            Appointment.tenant_id == tenant.id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Get service information
    service = db.query(TenantServiceConfig).filter(
        TenantServiceConfig.id == appointment.service_id
    ).first()
    
    # Get tenant booking for additional information
    tenant_booking = db.query(TenantBooking).filter(
        TenantBooking.appointment_id == appointment.id
    ).first()
    
    # Get customer information
    customer = db.query(TenantCustomer).filter(
        TenantCustomer.id == tenant_booking.customer_id
    ).first() if tenant_booking else None
    
    # Convert times to local timezone
    local_start_time = convert_to_local_time(appointment.start_time, "Africa/Lagos")
    local_end_time = convert_to_local_time(appointment.end_time, "Africa/Lagos")
    
    return {
        "booking_reference": appointment.booking_reference,
        "status": appointment.status,
        "service": {
            "name": service.name,
            "description": service.description,
            "category": service.category
        } if service else None,
        "customer": {
            "name": appointment.customer_name,
            "email": appointment.customer_email,
            "phone": appointment.customer_phone,
            "reference": customer.customer_reference if customer else None
        },
        "appointment_time": {
            "start": local_start_time.isoformat(),
            "end": local_end_time.isoformat(),
            "timezone": "Africa/Lagos",
            "date": local_start_time.date().isoformat(),
            "time": local_start_time.time().isoformat()
        },
        "payment": {
            "required": appointment.payment_required,
            "amount": float(appointment.payment_amount) if appointment.payment_amount else None,
            "status": appointment.payment_status,
            "currency": "NGN"
        },
        "special_requests": appointment.special_requests,
        "custom_field_responses": tenant_booking.custom_field_responses if tenant_booking else {},
        "created_at": appointment.created_at.isoformat(),
        "can_cancel": appointment.status in ["pending", "confirmed"],
        "can_reschedule": appointment.status in ["pending", "confirmed"]
    }


@router.post("/bookings/{booking_reference}/cancel", response_model=Dict[str, Any])
async def cancel_booking(
    booking_reference: str,
    cancellation_reason: Optional[str] = Body(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get appointment
    from core.scheduling import Appointment, AppointmentStatus
    appointment = db.query(Appointment).filter(
        and_(
            Appointment.booking_reference == booking_reference,
            Appointment.tenant_id == tenant.id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel booking with status: {appointment.status}"
        )
    
    # Check cancellation policy (e.g., minimum hours before appointment)
    hours_until_appointment = (appointment.start_time - datetime.utcnow()).total_seconds() / 3600
    
    if hours_until_appointment < 2:  # Less than 2 hours notice
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancellations must be made at least 2 hours before the appointment"
        )
    
    # Cancel using scheduling service
    scheduling_service = SchedulingService(db)
    
    try:
        cancelled_appointment = scheduling_service.cancel_appointment(
            appointment_id=str(appointment.id),
            cancellation_reason=cancellation_reason
        )
        
        logger.info(f"Cancelled booking {booking_reference}")
        
        return {
            "booking_reference": booking_reference,
            "status": cancelled_appointment.status,
            "cancelled_at": cancelled_appointment.cancelled_at.isoformat(),
            "message": "Booking cancelled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_reference}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelling booking. Please contact the business directly."
        )


# Utility Endpoints

@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_service_categories(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get available service categories for this business"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get categories that have active services
    from sqlalchemy import func
    categories = db.query(
        TenantServiceConfig.category,
        func.count(TenantServiceConfig.id).label('service_count')
    ).filter(
        and_(
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.is_active == True,
            TenantServiceConfig.is_online_bookable == True
        )
    ).group_by(TenantServiceConfig.category).all()
    
    return [
        {
            "category": category,
            "service_count": service_count
        }
        for category, service_count in categories
    ]


@router.get("/holidays", response_model=List[Dict[str, str]])
async def get_business_holidays(
    year: int = Query(datetime.now().year, description="Year to get holidays for"),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get Nigerian holidays and business closure dates"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get Nigerian holidays
    holidays = get_nigerian_holidays(year)
    
    return [
        {
            "date": holiday_date.isoformat(),
            "name": holiday_name
        }
        for holiday_date, holiday_name in holidays.items()
    ]


@router.get("/staff", response_model=List[Dict[str, Any]])
async def get_public_staff_list(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    service_id: Optional[UUID] = Query(None, description="Filter staff by service")
):
    """Get list of staff available for booking"""
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    from core.auth import TenantUser, User, UserRole
    
    query = db.query(TenantUser).join(User).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.role.in_([UserRole.STAFF, UserRole.TENANT_ADMIN, UserRole.TENANT_OWNER]),
            TenantUser.is_active == True,
            TenantUser.is_accepting_bookings == True
        )
    )
    
    staff_members = query.all()
    
    return [
        {
            "id": str(staff.id),
            "name": staff.user.full_name,
            "title": staff.staff_title,
            "bio": staff.bio,
            "specializations": staff.specializations,
            "profile_image_url": staff.profile_image_url
        }
        for staff in staff_members
    ]