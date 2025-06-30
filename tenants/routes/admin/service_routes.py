"""
Admin service management routes for BookingBot NG
Handles CRUD operations for tenant services, pricing, and availability settings
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from loguru import logger

# Core imports
from core.auth import (
    require_tenant_admin, get_current_tenant, get_current_user,
    TenantUser, Tenant, User
)
from core.scheduling import SchedulingService
from core.database import get_db

# Tenant imports
from tenants.models import (
    TenantServiceConfig, ServiceSchedule, ServiceCustomField,
    ServiceConfigurationSchema, ServiceCategory,
    get_service_templates_by_category, get_nigerian_custom_field_templates
)

router = APIRouter(prefix="/admin/services", tags=["Admin Services"])


# Service CRUD Operations

@router.get("/", response_model=List[Dict[str, Any]])
async def list_services(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    category: Optional[ServiceCategory] = Query(None, description="Filter by service category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by service name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get list of services for the tenant"""
    
    query = db.query(TenantServiceConfig).filter(
        TenantServiceConfig.tenant_id == tenant.id
    )
    
    # Apply filters
    if category:
        query = query.filter(TenantServiceConfig.category == category.value)
    
    if is_active is not None:
        query = query.filter(TenantServiceConfig.is_active == is_active)
    
    if search:
        query = query.filter(
            or_(
                TenantServiceConfig.name.ilike(f"%{search}%"),
                TenantServiceConfig.description.ilike(f"%{search}%")
            )
        )
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    services = query.order_by(
        desc(TenantServiceConfig.is_featured),
        asc(TenantServiceConfig.display_order),
        asc(TenantServiceConfig.name)
    ).offset(offset).limit(limit).all()
    
    # Format response
    service_list = []
    for service in services:
        service_data = {
            "id": str(service.id),
            "name": service.name,
            "description": service.description,
            "category": service.category,
            "subcategory": service.subcategory,
            "configuration": service.configuration,
            "is_active": service.is_active,
            "is_online_bookable": service.is_online_bookable,
            "is_featured": service.is_featured,
            "display_order": service.display_order,
            "total_bookings": service.total_bookings,
            "total_revenue": float(service.total_revenue),
            "average_rating": float(service.average_rating) if service.average_rating else None,
            "created_at": service.created_at.isoformat(),
            "updated_at": service.updated_at.isoformat()
        }
        service_list.append(service_data)
    
    return {
        "services": service_list,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{service_id}", response_model=Dict[str, Any])
async def get_service(
    service_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get a specific service by ID"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Get service schedules
    schedules = db.query(ServiceSchedule).filter(
        ServiceSchedule.service_config_id == service.id
    ).all()
    
    # Get custom fields
    custom_fields = db.query(ServiceCustomField).filter(
        ServiceCustomField.service_config_id == service.id
    ).order_by(ServiceCustomField.display_order).all()
    
    return {
        "id": str(service.id),
        "name": service.name,
        "description": service.description,
        "category": service.category,
        "subcategory": service.subcategory,
        "configuration": service.configuration,
        "is_active": service.is_active,
        "is_online_bookable": service.is_online_bookable,
        "is_featured": service.is_featured,
        "display_order": service.display_order,
        "total_bookings": service.total_bookings,
        "total_revenue": float(service.total_revenue),
        "average_rating": float(service.average_rating) if service.average_rating else None,
        "schedules": [
            {
                "id": str(schedule.id),
                "day_of_week": schedule.day_of_week,
                "is_available": schedule.is_available,
                "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
                "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
                "max_bookings": schedule.max_bookings,
                "assigned_staff_id": str(schedule.assigned_staff_id) if schedule.assigned_staff_id else None,
                "price_override": float(schedule.price_override) if schedule.price_override else None
            }
            for schedule in schedules
        ],
        "custom_fields": [
            {
                "id": str(field.id),
                "field_name": field.field_name,
                "field_label": field.field_label,
                "field_type": field.field_type,
                "field_config": field.field_config,
                "display_order": field.display_order,
                "is_required": field.is_required,
                "is_active": field.is_active
            }
            for field in custom_fields
        ],
        "created_at": service.created_at.isoformat(),
        "updated_at": service.updated_at.isoformat()
    }


@router.post("/", response_model=Dict[str, Any])
async def create_service(
    service_config: ServiceConfigurationSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create a new service"""
    
    # Check if service name already exists for this tenant
    existing_service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.tenant_id == tenant.id,
            TenantServiceConfig.name == service_config.name
        )
    ).first()
    
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service with this name already exists"
        )
    
    # Create service from schema
    service = TenantServiceConfig.from_schema(str(tenant.id), service_config)
    
    db.add(service)
    db.flush()  # Get the service ID
    
    # Create custom fields if provided
    for field_schema in service_config.custom_fields:
        custom_field = ServiceCustomField(
            service_config_id=service.id,
            tenant_id=tenant.id,
            field_name=field_schema.name,
            field_label=field_schema.label,
            field_type=field_schema.field_type.value,
            field_config=field_schema.dict(),
            display_order=field_schema.order,
            is_required=field_schema.required
        )
        db.add(custom_field)
    
    # Create default schedules based on availability settings
    for day in service_config.availability.available_days_of_week:
        schedule = ServiceSchedule(
            service_config_id=service.id,
            tenant_id=tenant.id,
            day_of_week=day,
            is_available=True
        )
        db.add(schedule)
    
    db.commit()
    db.refresh(service)
    
    logger.info(f"Created service '{service.name}' for tenant {tenant.business_name}")
    
    return {
        "id": str(service.id),
        "name": service.name,
        "message": "Service created successfully"
    }


@router.put("/{service_id}", response_model=Dict[str, Any])
async def update_service(
    service_id: UUID,
    service_config: ServiceConfigurationSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update an existing service"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Check if new name conflicts with existing services
    if service_config.name != service.name:
        existing_service = db.query(TenantServiceConfig).filter(
            and_(
                TenantServiceConfig.tenant_id == tenant.id,
                TenantServiceConfig.name == service_config.name,
                TenantServiceConfig.id != service_id
            )
        ).first()
        
        if existing_service:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Service with this name already exists"
            )
    
    # Update service
    service.name = service_config.name
    service.description = service_config.description
    service.category = service_config.category.value
    service.subcategory = service_config.subcategory
    service.configuration = service_config.dict()
    service.is_active = service_config.is_active
    service.is_online_bookable = service_config.is_online_bookable
    service.is_featured = service_config.is_featured
    service.display_order = service_config.display_order
    service.updated_at = datetime.utcnow()
    
    # Update custom fields (delete and recreate for simplicity)
    db.query(ServiceCustomField).filter(
        ServiceCustomField.service_config_id == service.id
    ).delete()
    
    for field_schema in service_config.custom_fields:
        custom_field = ServiceCustomField(
            service_config_id=service.id,
            tenant_id=tenant.id,
            field_name=field_schema.name,
            field_label=field_schema.label,
            field_type=field_schema.field_type.value,
            field_config=field_schema.dict(),
            display_order=field_schema.order,
            is_required=field_schema.required
        )
        db.add(custom_field)
    
    db.commit()
    db.refresh(service)
    
    logger.info(f"Updated service '{service.name}' for tenant {tenant.business_name}")
    
    return {
        "id": str(service.id),
        "name": service.name,
        "message": "Service updated successfully"
    }


@router.delete("/{service_id}")
async def delete_service(
    service_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Delete a service (soft delete by deactivating)"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Check if service has active bookings
    from core.scheduling import Appointment, AppointmentStatus
    active_bookings = db.query(Appointment).filter(
        and_(
            Appointment.service_id == service_id,
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
            detail=f"Cannot delete service with {active_bookings} active bookings. Please complete or cancel them first."
        )
    
    # Soft delete by deactivating
    service.is_active = False
    service.is_online_bookable = False
    service.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Deactivated service '{service.name}' for tenant {tenant.business_name}")
    
    return {"message": "Service deactivated successfully"}


# Service Templates and Wizards

@router.get("/templates/{category}", response_model=List[Dict[str, Any]])
async def get_service_templates(
    category: ServiceCategory,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get service templates for a specific category"""
    
    templates = get_service_templates_by_category(category)
    
    return {
        "category": category.value,
        "templates": templates
    }


@router.post("/from-template", response_model=Dict[str, Any])
async def create_service_from_template(
    template_data: Dict[str, Any] = Body(...),
    customizations: Optional[Dict[str, Any]] = Body(None),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create a service from a template with customizations"""
    
    # Merge template data with customizations
    service_data = template_data.copy()
    if customizations:
        service_data.update(customizations)
    
    # Validate and create service
    try:
        service_config = ServiceConfigurationSchema(**service_data)
        
        # Create service
        service = TenantServiceConfig.from_schema(str(tenant.id), service_config)
        
        db.add(service)
        db.flush()
        
        # Create custom fields from template
        if service_config.custom_fields:
            for field_schema in service_config.custom_fields:
                custom_field = ServiceCustomField(
                    service_config_id=service.id,
                    tenant_id=tenant.id,
                    field_name=field_schema.name,
                    field_label=field_schema.label,
                    field_type=field_schema.field_type.value,
                    field_config=field_schema.dict(),
                    display_order=field_schema.order,
                    is_required=field_schema.required
                )
                db.add(custom_field)
        
        db.commit()
        db.refresh(service)
        
        logger.info(f"Created service '{service.name}' from template for tenant {tenant.business_name}")
        
        return {
            "id": str(service.id),
            "name": service.name,
            "message": "Service created from template successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template data: {str(e)}"
        )


# Service Analytics

@router.get("/{service_id}/analytics", response_model=Dict[str, Any])
async def get_service_analytics(
    service_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """Get analytics for a specific service"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Get booking analytics from core scheduling service
    scheduling_service = SchedulingService(db)
    
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Get appointments for this service
    from core.scheduling import Appointment
    appointments = db.query(Appointment).filter(
        and_(
            Appointment.service_id == service_id,
            Appointment.start_time >= start_date,
            Appointment.start_time <= end_date
        )
    ).all()
    
    # Calculate metrics
    total_bookings = len(appointments)
    completed_bookings = len([a for a in appointments if a.status == "completed"])
    cancelled_bookings = len([a for a in appointments if a.status == "cancelled"])
    no_show_bookings = len([a for a in appointments if a.status == "no_show"])
    
    total_revenue = sum([float(a.payment_amount or 0) for a in appointments if a.status == "completed"])
    average_booking_value = total_revenue / completed_bookings if completed_bookings > 0 else 0
    
    return {
        "service_id": str(service_id),
        "service_name": service.name,
        "period": f"{start_date} to {end_date}",
        "metrics": {
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "no_show_bookings": no_show_bookings,
            "completion_rate": (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0,
            "cancellation_rate": (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0,
            "no_show_rate": (no_show_bookings / total_bookings * 100) if total_bookings > 0 else 0,
            "total_revenue": total_revenue,
            "average_booking_value": average_booking_value
        },
        "lifetime_stats": {
            "total_bookings": service.total_bookings,
            "total_revenue": float(service.total_revenue),
            "average_rating": float(service.average_rating) if service.average_rating else None
        }
    }


# Bulk Operations

@router.post("/bulk-update", response_model=Dict[str, Any])
async def bulk_update_services(
    service_ids: List[UUID] = Body(...),
    updates: Dict[str, Any] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Bulk update multiple services"""
    
    # Validate service IDs belong to tenant
    services = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id.in_(service_ids),
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).all()
    
    if len(services) != len(service_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more services not found"
        )
    
    # Apply updates
    updated_count = 0
    allowed_fields = ['is_active', 'is_online_bookable', 'is_featured', 'display_order']
    
    for service in services:
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(service, field, value)
                updated_count += 1
        
        service.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Bulk updated {len(services)} services for tenant {tenant.business_name}")
    
    return {
        "updated_services": len(services),
        "message": f"Successfully updated {len(services)} services"
    }


# Service Availability Management

@router.get("/{service_id}/availability", response_model=Dict[str, Any])
async def get_service_availability(
    service_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get availability settings for a service"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Get service schedules
    schedules = db.query(ServiceSchedule).filter(
        ServiceSchedule.service_config_id == service.id
    ).order_by(ServiceSchedule.day_of_week).all()
    
    return {
        "service_id": str(service_id),
        "service_name": service.name,
        "availability_config": service.configuration.get("availability", {}),
        "schedules": [
            {
                "id": str(schedule.id),
                "day_of_week": schedule.day_of_week,
                "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][schedule.day_of_week],
                "is_available": schedule.is_available,
                "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
                "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
                "max_bookings": schedule.max_bookings,
                "assigned_staff_id": str(schedule.assigned_staff_id) if schedule.assigned_staff_id else None,
                "price_override": float(schedule.price_override) if schedule.price_override else None
            }
            for schedule in schedules
        ]
    }


@router.put("/{service_id}/availability", response_model=Dict[str, Any])
async def update_service_availability(
    service_id: UUID,
    schedules: List[Dict[str, Any]] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update availability schedules for a service"""
    
    service = db.query(TenantServiceConfig).filter(
        and_(
            TenantServiceConfig.id == service_id,
            TenantServiceConfig.tenant_id == tenant.id
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Delete existing schedules
    db.query(ServiceSchedule).filter(
        ServiceSchedule.service_config_id == service.id
    ).delete()
    
    # Create new schedules
    for schedule_data in schedules:
        schedule = ServiceSchedule(
            service_config_id=service.id,
            tenant_id=tenant.id,
            day_of_week=schedule_data["day_of_week"],
            is_available=schedule_data.get("is_available", True),
            start_time=schedule_data.get("start_time"),
            end_time=schedule_data.get("end_time"),
            max_bookings=schedule_data.get("max_bookings"),
            assigned_staff_id=schedule_data.get("assigned_staff_id"),
            price_override=schedule_data.get("price_override")
        )
        db.add(schedule)
    
    service.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated availability for service '{service.name}' for tenant {tenant.business_name}")
    
    return {
        "service_id": str(service_id),
        "message": "Service availability updated successfully"
    }