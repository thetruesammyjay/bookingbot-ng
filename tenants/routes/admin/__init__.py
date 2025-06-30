"""
BookingBot NG Admin Routes Module

This module contains all admin-facing API routes for tenant management,
including service configuration, staff management, and business settings.
"""

from .service_routes import router as service_router
from .staff_routes import router as staff_router
from .settings_routes import router as settings_router

__all__ = [
    "service_router",
    "staff_router", 
    "settings_router"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Admin routes for Nigerian business management"