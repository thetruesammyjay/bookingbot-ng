"""
Calendar synchronization module for BookingBot NG
Handles integration with external calendar providers (Google, Outlook, Apple)
"""

from .google_calendar import GoogleCalendarSync
from .outlook_calendar import OutlookCalendarSync

__all__ = [
    "GoogleCalendarSync",
    "OutlookCalendarSync"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "External calendar integration and synchronization"