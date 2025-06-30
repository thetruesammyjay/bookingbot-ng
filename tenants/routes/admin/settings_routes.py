"""
Admin settings management routes for BookingBot NG
Handles business hours, payment settings, notifications, and general tenant configuration
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from sqlalchemy.orm import Session
from loguru import logger
from pydantic import BaseModel, Field

# Core imports
from core.auth import (
    require_tenant_admin, get_current_tenant, get_current_user,
    TenantUser, Tenant, User
)
from core.database import get_db

# Tenant imports
from tenants.models import (
    BusinessProfile, BusinessDocument, NigerianBusinessCompliance,
    BusinessAddressSchema, BusinessContactSchema, BusinessHoursSchema,
    PaymentSettingsSchema, NotificationSettingsSchema, BrandingSchema,
    get_nigerian_business_requirements
)

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])


# Business Profile Management

@router.get("/profile", response_model=Dict[str, Any])
async def get_business_profile(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get complete business profile"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        # Create default business profile
        business_profile = BusinessProfile(
            tenant_id=tenant.id,
            business_type=tenant.business_type or "consulting",
            address={"street_address": "", "city": "", "state": "", "country": "Nigeria"},
            contact_info={"primary_phone": "", "primary_email": tenant.email},
            business_hours={},
            payment_settings={},
            notification_settings={},
            branding={}
        )
        db.add(business_profile)
        db.commit()
        db.refresh(business_profile)
    
    return {
        "id": str(business_profile.id),
        "business_type": business_profile.business_type,
        "business_size": business_profile.business_size,
        "industry_specialization": business_profile.industry_specialization,
        "years_in_operation": business_profile.years_in_operation,
        "cac_number": business_profile.cac_number,
        "tin": business_profile.tin,
        "business_registration_date": business_profile.business_registration_date.isoformat() if business_profile.business_registration_date else None,
        "verification_status": business_profile.verification_status,
        "verification_date": business_profile.verification_date.isoformat() if business_profile.verification_date else None,
        "tagline": business_profile.tagline,
        "description": business_profile.description,
        "specialties": business_profile.specialties,
        "certifications": business_profile.certifications,
        "address": business_profile.address,
        "contact_info": business_profile.contact_info,
        "business_hours": business_profile.business_hours,
        "payment_settings": business_profile.payment_settings,
        "notification_settings": business_profile.notification_settings,
        "branding": business_profile.branding,
        "max_staff": business_profile.max_staff,
        "max_daily_bookings": business_profile.max_daily_bookings,
        "max_services": business_profile.max_services,
        "total_bookings": business_profile.total_bookings,
        "total_revenue": float(business_profile.total_revenue),
        "customer_rating": float(business_profile.customer_rating) if business_profile.customer_rating else None,
        "review_count": business_profile.review_count,
        "meta_title": business_profile.meta_title,
        "meta_description": business_profile.meta_description,
        "keywords": business_profile.keywords,
        "features_enabled": business_profile.features_enabled,
        "created_at": business_profile.created_at.isoformat(),
        "updated_at": business_profile.updated_at.isoformat()
    }


@router.put("/profile", response_model=Dict[str, Any])
async def update_business_profile(
    profile_data: Dict[str, Any] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update business profile"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    # Update allowed fields
    updatable_fields = [
        'business_size', 'industry_specialization', 'years_in_operation',
        'cac_number', 'tin', 'business_registration_date', 'tagline',
        'description', 'specialties', 'certifications', 'meta_title',
        'meta_description', 'keywords'
    ]
    
    for field, value in profile_data.items():
        if field in updatable_fields and hasattr(business_profile, field):
            if field == 'business_registration_date' and value:
                # Parse date string
                from datetime import date
                if isinstance(value, str):
                    value = date.fromisoformat(value)
            setattr(business_profile, field, value)
    
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(business_profile)
    
    logger.info(f"Updated business profile for tenant {tenant.business_name}")
    
    return {
        "message": "Business profile updated successfully",
        "updated_at": business_profile.updated_at.isoformat()
    }


# Address Management

@router.get("/address", response_model=BusinessAddressSchema)
async def get_business_address(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get business address"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.address:
        return BusinessAddressSchema(
            street_address="",
            city="",
            state="",
            country="Nigeria"
        )
    
    return BusinessAddressSchema(**business_profile.address)


@router.put("/address", response_model=Dict[str, Any])
async def update_business_address(
    address: BusinessAddressSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update business address"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.address = address.dict()
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated business address for tenant {tenant.business_name}")
    
    return {"message": "Business address updated successfully"}


# Contact Information

@router.get("/contact", response_model=BusinessContactSchema)
async def get_business_contact(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get business contact information"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.contact_info:
        return BusinessContactSchema(
            primary_phone="",
            primary_email=tenant.email
        )
    
    return BusinessContactSchema(**business_profile.contact_info)


@router.put("/contact", response_model=Dict[str, Any])
async def update_business_contact(
    contact: BusinessContactSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update business contact information"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.contact_info = contact.dict()
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated business contact for tenant {tenant.business_name}")
    
    return {"message": "Business contact updated successfully"}


# Business Hours

@router.get("/hours", response_model=BusinessHoursSchema)
async def get_business_hours(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get business hours"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.business_hours:
        # Return default hours
        return BusinessHoursSchema(
            monday={"open": "08:00", "close": "17:00"},
            tuesday={"open": "08:00", "close": "17:00"},
            wednesday={"open": "08:00", "close": "17:00"},
            thursday={"open": "08:00", "close": "17:00"},
            friday={"open": "08:00", "close": "17:00"},
            saturday={"open": "09:00", "close": "15:00"},
            sunday=None,
            timezone="Africa/Lagos"
        )
    
    return BusinessHoursSchema(**business_profile.business_hours)


@router.put("/hours", response_model=Dict[str, Any])
async def update_business_hours(
    hours: BusinessHoursSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update business hours"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.business_hours = hours.dict()
    business_profile.updated_at = datetime.utcnow()
    
    # Update core business hours table
    from core.scheduling import BusinessHours as CoreBusinessHours
    
    # Delete existing core business hours
    db.query(CoreBusinessHours).filter(
        CoreBusinessHours.tenant_id == tenant.id
    ).delete()
    
    # Create new core business hours
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day_index, day_name in enumerate(days):
        day_hours = getattr(hours, day_name)
        if day_hours:
            core_hours = CoreBusinessHours(
                tenant_id=tenant.id,
                day_of_week=day_index,
                is_open=True,
                open_time=time.fromisoformat(day_hours["open"]),
                close_time=time.fromisoformat(day_hours["close"]),
                observes_public_holidays=hours.ramadan_hours is not None
            )
            db.add(core_hours)
        else:
            # Day is closed
            core_hours = CoreBusinessHours(
                tenant_id=tenant.id,
                day_of_week=day_index,
                is_open=False
            )
            db.add(core_hours)
    
    db.commit()
    
    logger.info(f"Updated business hours for tenant {tenant.business_name}")
    
    return {"message": "Business hours updated successfully"}


# Payment Settings

@router.get("/payment", response_model=PaymentSettingsSchema)
async def get_payment_settings(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get payment settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.payment_settings:
        return PaymentSettingsSchema(
            accepts_cash=True,
            accepts_card=True,
            accepts_bank_transfer=True,
            paystack_enabled=True,
            currency="NGN"
        )
    
    return PaymentSettingsSchema(**business_profile.payment_settings)


@router.put("/payment", response_model=Dict[str, Any])
async def update_payment_settings(
    payment_settings: PaymentSettingsSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update payment settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.payment_settings = payment_settings.dict()
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated payment settings for tenant {tenant.business_name}")
    
    return {"message": "Payment settings updated successfully"}


# Notification Settings

@router.get("/notifications", response_model=NotificationSettingsSchema)
async def get_notification_settings(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get notification settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.notification_settings:
        return NotificationSettingsSchema()
    
    return NotificationSettingsSchema(**business_profile.notification_settings)


@router.put("/notifications", response_model=Dict[str, Any])
async def update_notification_settings(
    notification_settings: NotificationSettingsSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update notification settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.notification_settings = notification_settings.dict()
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated notification settings for tenant {tenant.business_name}")
    
    return {"message": "Notification settings updated successfully"}


# Branding Settings

@router.get("/branding", response_model=BrandingSchema)
async def get_branding_settings(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get branding settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile or not business_profile.branding:
        return BrandingSchema()
    
    return BrandingSchema(**business_profile.branding)


@router.put("/branding", response_model=Dict[str, Any])
async def update_branding_settings(
    branding_settings: BrandingSchema,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update branding settings"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    business_profile.branding = branding_settings.dict()
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated branding settings for tenant {tenant.business_name}")
    
    return {"message": "Branding settings updated successfully"}


# Document Management

@router.get("/documents", response_model=List[Dict[str, Any]])
async def list_business_documents(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get list of business documents"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        return []
    
    documents = db.query(BusinessDocument).filter(
        BusinessDocument.business_profile_id == business_profile.id
    ).order_by(BusinessDocument.uploaded_at.desc()).all()
    
    return [
        {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "document_name": doc.document_name,
            "file_url": doc.file_url,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "is_verified": doc.is_verified,
            "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
            "verification_notes": doc.verification_notes,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
            "is_expired": doc.is_expired(),
            "days_until_expiry": doc.days_until_expiry(),
            "uploaded_at": doc.uploaded_at.isoformat()
        }
        for doc in documents
    ]


@router.post("/documents/upload", response_model=Dict[str, Any])
async def upload_business_document(
    document_type: str = Body(...),
    document_name: str = Body(...),
    file: UploadFile = File(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Upload a business document"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and image files are allowed."
        )
    
    # Validate file size (max 10MB)
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 10MB."
        )
    
    # TODO: Implement actual file upload to cloud storage
    # For now, we'll simulate the upload
    file_url = f"https://storage.bookingbot.ng/documents/{tenant.id}/{file.filename}"
    
    # Create document record
    document = BusinessDocument(
        business_profile_id=business_profile.id,
        tenant_id=tenant.id,
        document_type=document_type,
        document_name=document_name,
        file_url=file_url,
        file_size=file.size,
        file_type=file.content_type
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    logger.info(f"Uploaded document '{document_name}' for tenant {tenant.business_name}")
    
    return {
        "id": str(document.id),
        "document_type": document_type,
        "document_name": document_name,
        "file_url": file_url,
        "message": "Document uploaded successfully"
    }


@router.delete("/documents/{document_id}")
async def delete_business_document(
    document_id: UUID,
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Delete a business document"""
    
    document = db.query(BusinessDocument).filter(
        and_(
            BusinessDocument.id == document_id,
            BusinessDocument.tenant_id == tenant.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # TODO: Delete actual file from cloud storage
    
    db.delete(document)
    db.commit()
    
    logger.info(f"Deleted document '{document.document_name}' for tenant {tenant.business_name}")
    
    return {"message": "Document deleted successfully"}


# Nigerian Business Compliance

@router.get("/compliance", response_model=Dict[str, Any])
async def get_compliance_status(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get Nigerian business compliance status"""
    
    compliance = db.query(NigerianBusinessCompliance).filter(
        NigerianBusinessCompliance.tenant_id == tenant.id
    ).first()
    
    if not compliance:
        # Create default compliance record
        compliance = NigerianBusinessCompliance(
            tenant_id=tenant.id,
            business_profile_id=db.query(BusinessProfile).filter(
                BusinessProfile.tenant_id == tenant.id
            ).first().id
        )
        db.add(compliance)
        db.commit()
        db.refresh(compliance)
    
    # Get requirements for business type
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    requirements = get_nigerian_business_requirements(
        business_profile.business_type if business_profile else "consulting"
    )
    
    # Calculate compliance score
    compliance_score = compliance.calculate_compliance_score()
    
    return {
        "compliance_score": compliance_score,
        "cac_status": compliance.cac_status,
        "cac_verified_date": compliance.cac_verified_date.isoformat() if compliance.cac_verified_date else None,
        "tin_status": compliance.tin_status,
        "tax_clearance_expiry": compliance.tax_clearance_expiry.isoformat() if compliance.tax_clearance_expiry else None,
        "business_permit_status": compliance.business_permit_status,
        "business_permit_expiry": compliance.business_permit_expiry.isoformat() if compliance.business_permit_expiry else None,
        "industry_licenses": compliance.industry_licenses,
        "professional_memberships": compliance.professional_memberships,
        "last_compliance_check": compliance.last_compliance_check.isoformat() if compliance.last_compliance_check else None,
        "requirements": requirements,
        "created_at": compliance.created_at.isoformat(),
        "updated_at": compliance.updated_at.isoformat()
    }


# Feature Flags and Configuration

@router.get("/features", response_model=Dict[str, Any])
async def get_feature_flags(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get enabled features for the tenant"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    default_features = {
        "online_booking": True,
        "calendar_sync": True,
        "sms_notifications": True,
        "email_notifications": True,
        "whatsapp_notifications": False,
        "payment_processing": True,
        "customer_reviews": True,
        "staff_management": True,
        "analytics_dashboard": True,
        "custom_branding": False,
        "api_access": False,
        "priority_support": False
    }
    
    if not business_profile or not business_profile.features_enabled:
        return {"features": default_features}
    
    # Merge with saved features
    enabled_features = default_features.copy()
    enabled_features.update(business_profile.features_enabled)
    
    return {"features": enabled_features}


@router.put("/features", response_model=Dict[str, Any])
async def update_feature_flags(
    features: Dict[str, bool] = Body(...),
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update enabled features for the tenant"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    if not business_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found"
        )
    
    # Validate features based on subscription tier
    subscription_tier = tenant.subscription_tier or "basic"
    
    restricted_features = {
        "basic": ["custom_branding", "api_access", "priority_support"],
        "pro": ["api_access", "priority_support"],
        "enterprise": []
    }
    
    restricted = restricted_features.get(subscription_tier, [])
    
    for feature, enabled in features.items():
        if enabled and feature in restricted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' not available in {subscription_tier} tier"
            )
    
    business_profile.features_enabled = features
    business_profile.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Updated feature flags for tenant {tenant.business_name}")
    
    return {"message": "Feature flags updated successfully"}


# Analytics and Reports Settings

@router.get("/analytics-config", response_model=Dict[str, Any])
async def get_analytics_config(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get analytics and reporting configuration"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    default_config = {
        "enable_customer_analytics": True,
        "enable_revenue_tracking": True,
        "enable_staff_performance": True,
        "enable_service_analytics": True,
        "data_retention_months": 24,
        "export_formats": ["csv", "pdf"],
        "automated_reports": {
            "daily_summary": True,
            "weekly_report": True,
            "monthly_report": True
        },
        "dashboard_widgets": [
            "total_bookings",
            "revenue_chart",
            "customer_satisfaction",
            "staff_utilization"
        ]
    }
    
    return {"analytics_config": default_config}


@router.get("/subscription", response_model=Dict[str, Any])
async def get_subscription_info(
    tenant_user: TenantUser = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get current subscription information"""
    
    business_profile = db.query(BusinessProfile).filter(
        BusinessProfile.tenant_id == tenant.id
    ).first()
    
    return {
        "subscription_tier": tenant.subscription_tier,
        "max_staff": business_profile.max_staff if business_profile else 5,
        "max_daily_bookings": business_profile.max_daily_bookings if business_profile else 50,
        "max_services": business_profile.max_services if business_profile else 10,
        "current_usage": {
            "staff_count": db.query(TenantUser).filter(
                and_(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.is_active == True
                )
            ).count(),
            "service_count": db.query(TenantServiceConfig).filter(
                and_(
                    TenantServiceConfig.tenant_id == tenant.id,
                    TenantServiceConfig.is_active == True
                )
            ).count()
        }
    }