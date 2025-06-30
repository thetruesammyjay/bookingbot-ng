"""
Google Calendar integration for BookingBot NG
Handles OAuth2 authentication and bidirectional calendar synchronization
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import requests
from loguru import logger

from ..exceptions import CalendarIntegrationError, CalendarAuthenticationError, CalendarSyncError, CalendarEventError
from ..utils import convert_to_utc, convert_to_local_time


class GoogleCalendarSync:
    """Google Calendar API integration"""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI")
        
        # Google Calendar API endpoints
        self.base_url = "https://www.googleapis.com/calendar/v3"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        
        # Required scopes for calendar access
        self.scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events"
        ]
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.warning("Google Calendar credentials not fully configured")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate OAuth2 authorization URL"""
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate token expiry
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": expires_at,
                "scope": token_data.get("scope", " ".join(self.scopes))
            }
            
        except requests.exceptions.RequestException as e:
            raise CalendarAuthenticationError(
                "google",
                provider_response={"error": str(e)}
            )
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                "access_token": token_data["access_token"],
                "expires_at": expires_at
            }
            
        except requests.exceptions.RequestException as e:
            raise CalendarAuthenticationError(
                "google",
                token_expired=True,
                provider_response={"error": str(e)}
            )
    
    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Google Calendar API"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise CalendarIntegrationError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty responses (e.g., from DELETE)
            if response.status_code == 204 or not response.content:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            if response.status_code == 401:
                raise CalendarAuthenticationError(
                    "google",
                    token_expired=True,
                    provider_response=error_data
                )
            else:
                raise CalendarIntegrationError(
                    f"Google Calendar API error: {e}",
                    provider="google",
                    provider_response=error_data
                )
        
        except requests.exceptions.RequestException as e:
            raise CalendarIntegrationError(
                f"Failed to connect to Google Calendar: {e}",
                provider="google"
            )
    
    def get_calendar_list(self, access_token: str) -> List[Dict[str, Any]]:
        """Get list of user's calendars"""
        
        response = self._make_api_request("GET", "/users/me/calendarList", access_token)
        return response.get("items", [])
    
    def get_primary_calendar(self, access_token: str) -> Dict[str, Any]:
        """Get user's primary calendar"""
        
        return self._make_api_request("GET", "/calendars/primary", access_token)
    
    def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new calendar event"""
        
        # Convert BookingBot appointment to Google Calendar event format
        google_event = self._convert_to_google_event(event_data)
        
        logger.info(f"Creating Google Calendar event: {event_data.get('summary', 'Untitled')}")
        
        response = self._make_api_request(
            "POST",
            f"/calendars/{calendar_id}/events",
            access_token,
            data=google_event
        )
        
        return response
    
    def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing calendar event"""
        
        google_event = self._convert_to_google_event(event_data)
        
        logger.info(f"Updating Google Calendar event: {event_id}")
        
        response = self._make_api_request(
            "PUT",
            f"/calendars/{calendar_id}/events/{event_id}",
            access_token,
            data=google_event
        )
        
        return response
    
    def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """Delete a calendar event"""
        
        logger.info(f"Deleting Google Calendar event: {event_id}")
        
        try:
            self._make_api_request(
                "DELETE",
                f"/calendars/{calendar_id}/events/{event_id}",
                access_token
            )
            return True
        except CalendarIntegrationError:
            return False
    
    def get_events(
        self,
        access_token: str,
        calendar_id: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 250
    ) -> List[Dict[str, Any]]:
        """Get events from calendar within time range"""
        
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        
        if time_max:
            params["timeMax"] = time_max.isoformat() + "Z"
        
        response = self._make_api_request(
            "GET",
            f"/calendars/{calendar_id}/events",
            access_token,
            params=params
        )
        
        return response.get("items", [])
    
    def check_availability(
        self,
        access_token: str,
        calendar_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if time slot is available (no conflicting events)"""
        
        events = self.get_events(
            access_token,
            calendar_id,
            time_min=start_time,
            time_max=end_time
        )
        
        # Check for conflicts
        for event in events:
            event_start = self._parse_google_datetime(event.get("start", {}))
            event_end = self._parse_google_datetime(event.get("end", {}))
            
            if event_start and event_end:
                # Check for overlap
                if not (end_time <= event_start or start_time >= event_end):
                    return False  # Conflict found
        
        return True  # No conflicts
    
    def sync_appointment_to_calendar(
        self,
        access_token: str,
        calendar_id: str,
        appointment_data: Dict[str, Any],
        external_event_id: Optional[str] = None
    ) -> str:
        """Sync BookingBot appointment to Google Calendar"""
        
        try:
            if external_event_id:
                # Update existing event
                response = self.update_event(
                    access_token,
                    calendar_id,
                    external_event_id,
                    appointment_data
                )
            else:
                # Create new event
                response = self.create_event(
                    access_token,
                    calendar_id,
                    appointment_data
                )
            
            return response.get("id", "")
            
        except CalendarIntegrationError as e:
            logger.error(f"Failed to sync appointment to Google Calendar: {e}")
            raise CalendarSyncError(
                "Failed to sync appointment to Google Calendar",
                provider="google",
                sync_direction="to_external"
            )
    
    def _convert_to_google_event(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BookingBot appointment data to Google Calendar event format"""
        
        start_time = appointment_data["start_time"]
        end_time = appointment_data["end_time"]
        timezone = appointment_data.get("timezone", "Africa/Lagos")
        
        # Convert to ISO format with timezone
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        
        google_event = {
            "summary": appointment_data.get("summary", "BookingBot Appointment"),
            "description": self._format_event_description(appointment_data),
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": timezone
            },
            "location": appointment_data.get("location", ""),
            "attendees": []
        }
        
        # Add customer as attendee
        customer_email = appointment_data.get("customer_email")
        if customer_email:
            google_event["attendees"].append({
                "email": customer_email,
                "displayName": appointment_data.get("customer_name", ""),
                "responseStatus": "needsAction"
            })
        
        # Add staff as attendee
        staff_email = appointment_data.get("staff_email")
        if staff_email:
            google_event["attendees"].append({
                "email": staff_email,
                "displayName": appointment_data.get("staff_name", ""),
                "responseStatus": "accepted"
            })
        
        # Add reminders
        google_event["reminders"] = {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},    # 1 hour before
                {"method": "popup", "minutes": 15}     # 15 minutes before
            ]
        }
        
        # Add custom properties for BookingBot integration
        google_event["extendedProperties"] = {
            "private": {
                "bookingbot_appointment_id": appointment_data.get("appointment_id", ""),
                "bookingbot_booking_reference": appointment_data.get("booking_reference", ""),
                "bookingbot_service_id": appointment_data.get("service_id", ""),
                "bookingbot_tenant_id": appointment_data.get("tenant_id", "")
            }
        }
        
        return google_event
    
    def _format_event_description(self, appointment_data: Dict[str, Any]) -> str:
        """Format appointment data into event description"""
        
        description_lines = [
            f"Service: {appointment_data.get('service_name', 'N/A')}",
            f"Customer: {appointment_data.get('customer_name', 'N/A')}",
            f"Phone: {appointment_data.get('customer_phone', 'N/A')}",
            f"Booking Reference: {appointment_data.get('booking_reference', 'N/A')}"
        ]
        
        if appointment_data.get("customer_notes"):
            description_lines.append(f"Notes: {appointment_data['customer_notes']}")
        
        if appointment_data.get("special_requests"):
            description_lines.append(f"Special Requests: {appointment_data['special_requests']}")
        
        description_lines.append("\n--- Powered by BookingBot NG ---")
        
        return "\n".join(description_lines)
    
    def _parse_google_datetime(self, datetime_obj: Dict[str, Any]) -> Optional[datetime]:
        """Parse Google Calendar datetime object"""
        
        if "dateTime" in datetime_obj:
            # Event with specific time
            dt_str = datetime_obj["dateTime"]
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                return None
        elif "date" in datetime_obj:
            # All-day event
            date_str = datetime_obj["date"]
            try:
                return datetime.fromisoformat(date_str + "T00:00:00+00:00")
            except ValueError:
                return None
        
        return None
    
    def create_meeting_link(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> Optional[str]:
        """Add Google Meet link to calendar event"""
        
        event_data = {
            "conferenceData": {
                "createRequest": {
                    "requestId": f"bookingbot-{event_id}",
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }
        
        try:
            response = self._make_api_request(
                "PATCH",
                f"/calendars/{calendar_id}/events/{event_id}?conferenceDataVersion=1",
                access_token,
                data=event_data
            )
            
            conference_data = response.get("conferenceData", {})
            entry_points = conference_data.get("entryPoints", [])
            
            for entry_point in entry_points:
                if entry_point.get("entryPointType") == "video":
                    return entry_point.get("uri")
            
            return None
            
        except CalendarIntegrationError as e:
            logger.warning(f"Failed to create Google Meet link: {e}")
            return None
    
    def webhook_verification(self, headers: Dict[str, str]) -> bool:
        """Verify Google Calendar webhook notification"""
        
        # Google Calendar push notifications use channel ID and resource ID
        channel_id = headers.get("X-Goog-Channel-ID")
        resource_id = headers.get("X-Goog-Resource-ID")
        
        return bool(channel_id and resource_id)