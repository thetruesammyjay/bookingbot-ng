"""
Microsoft Outlook Calendar integration for BookingBot NG
Handles OAuth2 authentication and calendar synchronization via Microsoft Graph API
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


class OutlookCalendarSync:
    """Microsoft Outlook Calendar integration via Microsoft Graph API"""
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.getenv("MICROSOFT_TENANT_ID", "common")
        self.redirect_uri = redirect_uri or os.getenv("MICROSOFT_REDIRECT_URI")
        
        # Microsoft Graph API endpoints
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Required scopes for calendar access
        self.scopes = [
            "https://graph.microsoft.com/Calendars.ReadWrite",
            "https://graph.microsoft.com/User.Read"
        ]
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.warning("Microsoft Outlook credentials not fully configured")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate OAuth2 authorization URL"""
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "response_mode": "query",
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
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes)
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
                "outlook",
                provider_response={"error": str(e)}
            )
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.scopes)
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
                "outlook",
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
        """Make authenticated request to Microsoft Graph API"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
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
                    "outlook",
                    token_expired=True,
                    provider_response=error_data
                )
            else:
                raise CalendarIntegrationError(
                    f"Microsoft Graph API error: {e}",
                    provider="outlook",
                    provider_response=error_data
                )
        
        except requests.exceptions.RequestException as e:
            raise CalendarIntegrationError(
                f"Failed to connect to Microsoft Graph: {e}",
                provider="outlook"
            )
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated user information"""
        
        return self._make_api_request("GET", "/me", access_token)
    
    def get_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        """Get list of user's calendars"""
        
        response = self._make_api_request("GET", "/me/calendars", access_token)
        return response.get("value", [])
    
    def get_default_calendar(self, access_token: str) -> Dict[str, Any]:
        """Get user's default calendar"""
        
        return self._make_api_request("GET", "/me/calendar", access_token)
    
    def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new calendar event"""
        
        # Convert BookingBot appointment to Outlook event format
        outlook_event = self._convert_to_outlook_event(event_data)
        
        logger.info(f"Creating Outlook Calendar event: {event_data.get('subject', 'Untitled')}")
        
        endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id != "default" else "/me/events"
        
        response = self._make_api_request(
            "POST",
            endpoint,
            access_token,
            data=outlook_event
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
        
        outlook_event = self._convert_to_outlook_event(event_data)
        
        logger.info(f"Updating Outlook Calendar event: {event_id}")
        
        endpoint = f"/me/calendars/{calendar_id}/events/{event_id}" if calendar_id != "default" else f"/me/events/{event_id}"
        
        response = self._make_api_request(
            "PATCH",
            endpoint,
            access_token,
            data=outlook_event
        )
        
        return response
    
    def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """Delete a calendar event"""
        
        logger.info(f"Deleting Outlook Calendar event: {event_id}")
        
        try:
            endpoint = f"/me/calendars/{calendar_id}/events/{event_id}" if calendar_id != "default" else f"/me/events/{event_id}"
            
            self._make_api_request(
                "DELETE",
                endpoint,
                access_token
            )
            return True
        except CalendarIntegrationError:
            return False
    
    def get_events(
        self,
        access_token: str,
        calendar_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top: int = 250
    ) -> List[Dict[str, Any]]:
        """Get events from calendar within time range"""
        
        params = {
            "$top": top,
            "$orderby": "start/dateTime"
        }
        
        # Build filter for time range
        filters = []
        if start_time:
            filters.append(f"start/dateTime ge '{start_time.isoformat()}'")
        if end_time:
            filters.append(f"end/dateTime le '{end_time.isoformat()}'")
        
        if filters:
            params["$filter"] = " and ".join(filters)
        
        endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id != "default" else "/me/events"
        
        response = self._make_api_request(
            "GET",
            endpoint,
            access_token,
            params=params
        )
        
        return response.get("value", [])
    
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
            start_time=start_time,
            end_time=end_time
        )
        
        # Check for conflicts
        for event in events:
            event_start = self._parse_outlook_datetime(event.get("start", {}))
            event_end = self._parse_outlook_datetime(event.get("end", {}))
            
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
        """Sync BookingBot appointment to Outlook Calendar"""
        
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
            logger.error(f"Failed to sync appointment to Outlook Calendar: {e}")
            raise CalendarSyncError(
                "Failed to sync appointment to Outlook Calendar",
                provider="outlook",
                sync_direction="to_external"
            )
    
    def create_teams_meeting(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> Optional[str]:
        """Add Microsoft Teams meeting to calendar event"""
        
        event_data = {
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness"
        }
        
        try:
            endpoint = f"/me/calendars/{calendar_id}/events/{event_id}" if calendar_id != "default" else f"/me/events/{event_id}"
            
            response = self._make_api_request(
                "PATCH",
                endpoint,
                access_token,
                data=event_data
            )
            
            online_meeting = response.get("onlineMeeting", {})
            return online_meeting.get("joinUrl")
            
        except CalendarIntegrationError as e:
            logger.warning(f"Failed to create Teams meeting: {e}")
            return None
    
    def _convert_to_outlook_event(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BookingBot appointment data to Outlook event format"""
        
        start_time = appointment_data["start_time"]
        end_time = appointment_data["end_time"]
        timezone = appointment_data.get("timezone", "Africa/Lagos")
        
        # Convert to ISO format
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        
        outlook_event = {
            "subject": appointment_data.get("subject", "BookingBot Appointment"),
            "body": {
                "contentType": "HTML",
                "content": self._format_event_body(appointment_data)
            },
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": timezone
            },
            "location": {
                "displayName": appointment_data.get("location", "")
            },
            "attendees": [],
            "importance": "normal",
            "sensitivity": "normal",
            "showAs": "busy"
        }
        
        # Add customer as attendee
        customer_email = appointment_data.get("customer_email")
        if customer_email:
            outlook_event["attendees"].append({
                "emailAddress": {
                    "address": customer_email,
                    "name": appointment_data.get("customer_name", "")
                },
                "type": "required"
            })
        
        # Add staff as attendee
        staff_email = appointment_data.get("staff_email")
        if staff_email:
            outlook_event["attendees"].append({
                "emailAddress": {
                    "address": staff_email,
                    "name": appointment_data.get("staff_name", "")
                },
                "type": "required"
            })
        
        # Add reminders
        outlook_event["reminderMinutesBeforeStart"] = 60  # 1 hour before
        
        # Add custom properties for BookingBot integration
        outlook_event["singleValueExtendedProperties"] = [
            {
                "id": "String {00020329-0000-0000-C000-000000000046} Name bookingbot_appointment_id",
                "value": appointment_data.get("appointment_id", "")
            },
            {
                "id": "String {00020329-0000-0000-C000-000000000046} Name bookingbot_booking_reference",
                "value": appointment_data.get("booking_reference", "")
            },
            {
                "id": "String {00020329-0000-0000-C000-000000000046} Name bookingbot_service_id",
                "value": appointment_data.get("service_id", "")
            },
            {
                "id": "String {00020329-0000-0000-C000-000000000046} Name bookingbot_tenant_id",
                "value": appointment_data.get("tenant_id", "")
            }
        ]
        
        return outlook_event
    
    def _format_event_body(self, appointment_data: Dict[str, Any]) -> str:
        """Format appointment data into HTML event body"""
        
        body_content = f"""
        <html>
        <body>
        <h3>Appointment Details</h3>
        <p><strong>Service:</strong> {appointment_data.get('service_name', 'N/A')}</p>
        <p><strong>Customer:</strong> {appointment_data.get('customer_name', 'N/A')}</p>
        <p><strong>Phone:</strong> {appointment_data.get('customer_phone', 'N/A')}</p>
        <p><strong>Booking Reference:</strong> {appointment_data.get('booking_reference', 'N/A')}</p>
        """
        
        if appointment_data.get("customer_notes"):
            body_content += f"<p><strong>Notes:</strong> {appointment_data['customer_notes']}</p>"
        
        if appointment_data.get("special_requests"):
            body_content += f"<p><strong>Special Requests:</strong> {appointment_data['special_requests']}</p>"
        
        body_content += """
        <hr>
        <p><em>Powered by BookingBot NG</em></p>
        </body>
        </html>
        """
        
        return body_content
    
    def _parse_outlook_datetime(self, datetime_obj: Dict[str, Any]) -> Optional[datetime]:
        """Parse Outlook datetime object"""
        
        if "dateTime" in datetime_obj and "timeZone" in datetime_obj:
            dt_str = datetime_obj["dateTime"]
            try:
                # Parse ISO format datetime
                if dt_str.endswith("Z"):
                    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                else:
                    return datetime.fromisoformat(dt_str)
            except ValueError:
                return None
        
        return None
    
    def get_free_busy_info(
        self,
        access_token: str,
        email_addresses: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get free/busy information for multiple users"""
        
        data = {
            "schedules": email_addresses,
            "startTime": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC"
            },
            "endTime": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC"
            },
            "availabilityViewInterval": 60  # 60-minute intervals
        }
        
        response = self._make_api_request(
            "POST",
            "/me/calendar/getSchedule",
            access_token,
            data=data
        )
        
        return response
    
    def webhook_validation(self, validation_token: str) -> str:
        """Validate Outlook webhook subscription"""
        
        # Microsoft Graph webhooks require returning the validation token
        return validation_token
    
    def webhook_verification(self, headers: Dict[str, str], body: str) -> bool:
        """Verify Outlook webhook notification"""
        
        # Microsoft Graph uses client state for verification
        client_state = headers.get("X-ClientState", "")
        expected_state = os.getenv("MICROSOFT_WEBHOOK_CLIENT_STATE", "")
        
        return client_state == expected_state if expected_state else True