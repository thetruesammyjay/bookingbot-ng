"""
BookingBot NG Public Booking Routes Module

This module contains all customer-facing API routes for booking services,
checking availability, and managing appointments through public booking links.
"""

from .public_booking_routes import router as public_booking_router

__all__ = [
    "public_booking_router"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Public booking routes for Nigerian customer-facing services"