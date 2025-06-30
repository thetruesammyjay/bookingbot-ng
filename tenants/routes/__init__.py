"""
BookingBot NG Tenant Routes Module

This module contains all tenant-specific API routes including both admin-facing
management routes and customer-facing public booking routes.
"""

from fastapi import APIRouter

# Import admin routes
from .admin import (
    service_router,
    staff_router,
    settings_router
)

# Import public booking routes
from .booking_links import public_booking_router

# Create main tenant router
tenant_router = APIRouter()

# Include admin routes with authentication
tenant_router.include_router(service_router)
tenant_router.include_router(staff_router)
tenant_router.include_router(settings_router)

# Include public booking routes (no authentication required)
tenant_router.include_router(public_booking_router)

__all__ = [
    "tenant_router",
    "service_router",
    "staff_router", 
    "settings_router",
    "public_booking_router"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Complete tenant route collection for Nigerian businesses"

# Route summary for documentation
ROUTE_SUMMARY = {
    "admin_routes": {
        "services": {
            "prefix": "/admin/services",
            "description": "Service configuration and management",
            "endpoints": [
                "GET / - List services",
                "POST / - Create service",
                "GET /{service_id} - Get service details", 
                "PUT /{service_id} - Update service",
                "DELETE /{service_id} - Delete service",
                "GET /templates/{category} - Get service templates",
                "POST /from-template - Create from template",
                "GET /{service_id}/analytics - Service analytics",
                "POST /bulk-update - Bulk update services",
                "GET /{service_id}/availability - Get availability",
                "PUT /{service_id}/availability - Update availability"
            ]
        },
        "staff": {
            "prefix": "/admin/staff",
            "description": "Staff management and scheduling",
            "endpoints": [
                "GET / - List staff members",
                "POST / - Create staff member (invitation)",
                "GET /{staff_id} - Get staff details",
                "PUT /{staff_id} - Update staff member", 
                "DELETE /{staff_id} - Remove staff member",
                "GET /{staff_id}/schedule - Get staff schedule",
                "PUT /{staff_id}/schedule - Update staff schedule",
                "GET /{staff_id}/performance - Staff performance metrics",
                "GET /invitations - List pending invitations",
                "DELETE /invitations/{invitation_id} - Cancel invitation",
                "POST /bulk-update - Bulk update staff"
            ]
        },
        "settings": {
            "prefix": "/admin/settings",
            "description": "Business configuration and settings",
            "endpoints": [
                "GET /profile - Get business profile",
                "PUT /profile - Update business profile",
                "GET /address - Get business address",
                "PUT /address - Update business address",
                "GET /contact - Get contact information",
                "PUT /contact - Update contact information",
                "GET /hours - Get business hours",
                "PUT /hours - Update business hours",
                "GET /payment - Get payment settings",
                "PUT /payment - Update payment settings",
                "GET /notifications - Get notification settings",
                "PUT /notifications - Update notification settings",
                "GET /branding - Get branding settings",
                "PUT /branding - Update branding settings",
                "GET /documents - List business documents",
                "POST /documents/upload - Upload document",
                "DELETE /documents/{document_id} - Delete document",
                "GET /compliance - Get compliance status",
                "GET /features - Get feature flags",
                "PUT /features - Update feature flags",
                "GET /analytics-config - Get analytics configuration",
                "GET /subscription - Get subscription information"
            ]
        }
    },
    "public_routes": {
        "booking": {
            "prefix": "",
            "description": "Customer-facing booking and information",
            "endpoints": [
                "GET /info - Get business information",
                "GET /status - Check business status",
                "GET /services - List bookable services",
                "GET /services/{service_id} - Get service details",
                "GET /services/{service_id}/availability - Get availability",
                "POST /book - Create booking",
                "GET /bookings/{booking_reference} - Get booking details",
                "POST /bookings/{booking_reference}/cancel - Cancel booking",
                "GET /categories - Get service categories",
                "GET /holidays - Get business holidays",
                "GET /staff - Get public staff list"
            ]
        }
    }
}

def get_route_summary() -> dict:
    """Get summary of all available routes"""
    return ROUTE_SUMMARY

def get_admin_routes() -> list:
    """Get list of admin route prefixes"""
    return [
        "/admin/services",
        "/admin/staff", 
        "/admin/settings"
    ]

def get_public_routes() -> list:
    """Get list of public route prefixes"""
    return [
        "/info",
        "/status",
        "/services", 
        "/book",
        "/bookings",
        "/categories",
        "/holidays",
        "/staff"
    ]