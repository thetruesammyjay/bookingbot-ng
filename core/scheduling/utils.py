"""
Scheduling utilities for BookingBot NG
Timezone handling, Nigerian holidays, and date/time helpers
"""

import pytz
import holidays
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

# Nigerian timezone
NIGERIAN_TIMEZONE = pytz.timezone('Africa/Lagos')
UTC_TIMEZONE = pytz.UTC


def convert_to_local_time(utc_datetime: datetime, timezone_str: str = "Africa/Lagos") -> datetime:
    """Convert UTC datetime to local timezone"""
    
    if utc_datetime.tzinfo is None:
        utc_datetime = UTC_TIMEZONE.localize(utc_datetime)
    
    local_tz = pytz.timezone(timezone_str)
    return utc_datetime.astimezone(local_tz)


def convert_to_utc(local_datetime: datetime, timezone_str: str = "Africa/Lagos") -> datetime:
    """Convert local datetime to UTC"""
    
    if local_datetime.tzinfo is None:
        local_tz = pytz.timezone(timezone_str)
        local_datetime = local_tz.localize(local_datetime)
    
    return local_datetime.astimezone(UTC_TIMEZONE)


def get_nigerian_holidays(year: int) -> Dict[date, str]:
    """Get Nigerian public holidays for a given year"""
    
    # Base holidays
    ng_holidays = holidays.Nigeria(years=year)
    
    # Add additional Nigerian holidays that might not be in the library
    additional_holidays = {
        date(year, 1, 1): "New Year's Day",
        date(year, 10, 1): "Independence Day",
        date(year, 12, 25): "Christmas Day",
        date(year, 12, 26): "Boxing Day",
        date(year, 5, 1): "Workers' Day",
        date(year, 6, 12): "Democracy Day",
    }
    
    # Combine holidays
    all_holidays = dict(ng_holidays)
    all_holidays.update(additional_holidays)
    
    return all_holidays


def is_business_day(check_date: date, exclude_weekends: bool = True) -> bool:
    """Check if a date is a business day in Nigeria"""
    
    # Check weekends
    if exclude_weekends and check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check public holidays
    ng_holidays = get_nigerian_holidays(check_date.year)
    if check_date in ng_holidays:
        return False
    
    return True


def get_next_business_day(from_date: date, exclude_weekends: bool = True) -> date:
    """Get the next business day after the given date"""
    
    next_day = from_date + timedelta(days=1)
    
    while not is_business_day(next_day, exclude_weekends):
        next_day += timedelta(days=1)
    
    return next_day


def generate_time_slots(
    start_time: time,
    end_time: time,
    slot_duration_minutes: int,
    break_start: Optional[time] = None,
    break_end: Optional[time] = None
) -> List[time]:
    """Generate time slots for a given period"""
    
    slots = []
    current_time = datetime.combine(date.today(), start_time)
    end_datetime = datetime.combine(date.today(), end_time)
    
    while current_time + timedelta(minutes=slot_duration_minutes) <= end_datetime:
        # Check if slot overlaps with break time
        if break_start and break_end:
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            break_start_dt = datetime.combine(date.today(), break_start)
            break_end_dt = datetime.combine(date.today(), break_end)
            
            # Skip if slot overlaps with break
            if not (slot_end <= break_start_dt or current_time >= break_end_dt):
                current_time += timedelta(minutes=15)  # Skip to after break
                continue
        
        slots.append(current_time.time())
        current_time += timedelta(minutes=slot_duration_minutes)
    
    return slots


def validate_booking_time(
    booking_datetime: datetime,
    min_advance_hours: int = 1,
    max_advance_days: int = 30,
    business_hours: Optional[Tuple[time, time]] = None,
    timezone_str: str = "Africa/Lagos"
) -> Tuple[bool, str]:
    """Validate if a booking time is acceptable"""
    
    now = datetime.utcnow()
    local_tz = pytz.timezone(timezone_str)
    
    # Convert booking time to UTC if needed
    if booking_datetime.tzinfo is None:
        booking_datetime = local_tz.localize(booking_datetime).astimezone(UTC_TIMEZONE)
    
    # Check minimum advance booking
    min_advance = timedelta(hours=min_advance_hours)
    if booking_datetime < now + min_advance:
        return False, f"Booking must be at least {min_advance_hours} hours in advance"
    
    # Check maximum advance booking
    max_advance = timedelta(days=max_advance_days)
    if booking_datetime > now + max_advance:
        return False, f"Booking cannot be more than {max_advance_days} days in advance"
    
    # Check if it's a business day
    booking_date = booking_datetime.date()
    if not is_business_day(booking_date):
        return False, "Booking date is not a business day"
    
    # Check business hours if provided
    if business_hours:
        booking_time = convert_to_local_time(booking_datetime, timezone_str).time()
        start_time, end_time = business_hours
        
        if not (start_time <= booking_time <= end_time):
            return False, f"Booking time must be between {start_time} and {end_time}"
    
    return True, "Valid booking time"


def calculate_service_duration(
    base_duration_minutes: int,
    buffer_before_minutes: int = 0,
    buffer_after_minutes: int = 0
) -> Dict[str, int]:
    """Calculate total service duration including buffers"""
    
    total_duration = base_duration_minutes + buffer_before_minutes + buffer_after_minutes
    
    return {
        "base_duration": base_duration_minutes,
        "buffer_before": buffer_before_minutes,
        "buffer_after": buffer_after_minutes,
        "total_duration": total_duration
    }


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string"""
    
    if minutes < 60:
        return f"{minutes} minutes"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    
    return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minutes"


def get_time_slot_display(start_time: datetime, end_time: datetime, timezone_str: str = "Africa/Lagos") -> str:
    """Get formatted display string for a time slot"""
    
    local_start = convert_to_local_time(start_time, timezone_str)
    local_end = convert_to_local_time(end_time, timezone_str)
    
    # If same day, show date once
    if local_start.date() == local_end.date():
        return f"{local_start.strftime('%Y-%m-%d %I:%M %p')} - {local_end.strftime('%I:%M %p')}"
    else:
        return f"{local_start.strftime('%Y-%m-%d %I:%M %p')} - {local_end.strftime('%Y-%m-%d %I:%M %p')}"


def calculate_working_hours(
    business_hours: List[Tuple[time, time]],
    break_periods: Optional[List[Tuple[time, time]]] = None
) -> Decimal:
    """Calculate total working hours per day"""
    
    total_minutes = 0
    
    for start_time, end_time in business_hours:
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = datetime.combine(date.today(), end_time)
        
        period_minutes = (end_dt - start_dt).total_seconds() / 60
        total_minutes += period_minutes
    
    # Subtract break periods
    if break_periods:
        for break_start, break_end in break_periods:
            break_start_dt = datetime.combine(date.today(), break_start)
            break_end_dt = datetime.combine(date.today(), break_end)
            
            break_minutes = (break_end_dt - break_start_dt).total_seconds() / 60
            total_minutes -= break_minutes
    
    return Decimal(total_minutes) / 60  # Convert to hours


def get_optimal_slot_duration(service_duration: int, buffer_time: int = 0) -> int:
    """Get optimal slot duration for scheduling"""
    
    total_duration = service_duration + buffer_time
    
    # Round up to nearest 15 minutes for clean scheduling
    slot_duration = ((total_duration + 14) // 15) * 15
    
    return max(slot_duration, 15)  # Minimum 15 minutes


def is_weekend(check_date: date) -> bool:
    """Check if date is weekend (Saturday or Sunday)"""
    return check_date.weekday() >= 5


def get_week_range(from_date: date) -> Tuple[date, date]:
    """Get start and end of week for a given date (Monday to Sunday)"""
    
    # Monday is 0, Sunday is 6
    days_since_monday = from_date.weekday()
    week_start = from_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def get_month_range(from_date: date) -> Tuple[date, date]:
    """Get start and end of month for a given date"""
    
    month_start = from_date.replace(day=1)
    
    # Get last day of month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    
    month_end = next_month - timedelta(days=1)
    
    return month_start, month_end


def parse_nigerian_time_format(time_str: str) -> Optional[time]:
    """Parse Nigerian time format strings (12-hour with AM/PM)"""
    
    time_formats = [
        "%I:%M %p",      # 2:30 PM
        "%I:%M%p",       # 2:30PM
        "%I %p",         # 2 PM
        "%I%p",          # 2PM
        "%H:%M",         # 14:30
        "%H",            # 14
    ]
    
    time_str = time_str.strip().upper()
    
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt).time()
            return parsed_time
        except ValueError:
            continue
    
    return None


def format_nigerian_time(time_obj: time) -> str:
    """Format time in Nigerian 12-hour format"""
    return time_obj.strftime("%-I:%M %p")


def get_ramadan_dates(year: int) -> Tuple[Optional[date], Optional[date]]:
    """Get approximate Ramadan start and end dates for a given year"""
    
    # This is a simplified calculation - in practice you'd use a proper Islamic calendar library
    # Ramadan dates shift by about 11 days each year
    
    ramadan_2024_start = date(2024, 3, 11)
    ramadan_2024_end = date(2024, 4, 9)
    
    # Calculate approximate dates for other years
    years_diff = year - 2024
    days_shift = years_diff * -11  # Ramadan moves earlier each year
    
    try:
        start_date = ramadan_2024_start + timedelta(days=days_shift)
        end_date = ramadan_2024_end + timedelta(days=days_shift)
        
        return start_date, end_date
    except:
        return None, None


def is_ramadan_period(check_date: date) -> bool:
    """Check if date falls during Ramadan"""
    
    ramadan_start, ramadan_end = get_ramadan_dates(check_date.year)
    
    if ramadan_start and ramadan_end:
        return ramadan_start <= check_date <= ramadan_end
    
    return False


def adjust_for_ramadan_hours(
    regular_hours: Tuple[time, time],
    ramadan_hours: Optional[Tuple[time, time]] = None
) -> Tuple[time, time]:
    """Adjust business hours during Ramadan if configured"""
    
    if ramadan_hours:
        return ramadan_hours
    
    # Default adjustment: start later, end earlier
    start_time, end_time = regular_hours
    
    # Adjust by 1 hour later start, 1 hour earlier end
    adjusted_start = (datetime.combine(date.today(), start_time) + timedelta(hours=1)).time()
    adjusted_end = (datetime.combine(date.today(), end_time) - timedelta(hours=1)).time()
    
    return adjusted_start, adjusted_end


def calculate_appointment_utilization(
    appointments: List[Dict[str, Any]],
    available_hours: Decimal,
    period_days: int = 1
) -> Dict[str, Any]:
    """Calculate appointment utilization metrics"""
    
    total_appointment_hours = Decimal('0')
    total_revenue = Decimal('0')
    
    for appointment in appointments:
        duration_hours = Decimal(appointment.get('duration_minutes', 0)) / 60
        total_appointment_hours += duration_hours
        
        if appointment.get('revenue'):
            total_revenue += Decimal(appointment['revenue'])
    
    total_available_hours = available_hours * period_days
    utilization_rate = (total_appointment_hours / total_available_hours * 100) if total_available_hours > 0 else 0
    
    return {
        "total_appointments": len(appointments),
        "total_appointment_hours": float(total_appointment_hours),
        "total_available_hours": float(total_available_hours),
        "utilization_rate": float(utilization_rate),
        "total_revenue": float(total_revenue),
        "revenue_per_hour": float(total_revenue / total_appointment_hours) if total_appointment_hours > 0 else 0
    }


def get_nigerian_states() -> List[str]:
    """Get list of Nigerian states for location-based scheduling"""
    
    return [
        "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
        "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
        "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna",
        "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
        "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers",
        "Sokoto", "Taraba", "Yobe", "Zamfara"
    ]


def get_major_nigerian_cities() -> Dict[str, str]:
    """Get major Nigerian cities mapped to their states"""
    
    return {
        "Lagos": "Lagos",
        "Kano": "Kano",
        "Ibadan": "Oyo",
        "Kaduna": "Kaduna",
        "Port Harcourt": "Rivers",
        "Benin City": "Edo",
        "Maiduguri": "Borno",
        "Zaria": "Kaduna",
        "Aba": "Abia",
        "Jos": "Plateau",
        "Ilorin": "Kwara",
        "Oyo": "Oyo",
        "Enugu": "Enugu",
        "Abeokuta": "Ogun",
        "Abuja": "FCT",
        "Sokoto": "Sokoto",
        "Calabar": "Cross River",
        "Katsina": "Katsina",
        "Warri": "Delta",
        "Akure": "Ondo"
    }


def estimate_travel_time_between_cities(city1: str, city2: str) -> Optional[int]:
    """Estimate travel time between Nigerian cities in minutes"""
    
    # Simplified travel time matrix for major cities
    # In production, you'd use a proper mapping service
    
    travel_matrix = {
        ("Lagos", "Ibadan"): 120,
        ("Lagos", "Abeokuta"): 90,
        ("Lagos", "Benin City"): 300,
        ("Abuja", "Kaduna"): 120,
        ("Abuja", "Jos"): 180,
        ("Kano", "Kaduna"): 150,
        ("Port Harcourt", "Aba"): 60,
        ("Enugu", "Onitsha"): 60,
    }
    
    # Check both directions
    key1 = (city1, city2)
    key2 = (city2, city1)
    
    return travel_matrix.get(key1) or travel_matrix.get(key2)


def generate_booking_confirmation_details(
    appointment_data: Dict[str, Any],
    timezone_str: str = "Africa/Lagos"
) -> Dict[str, str]:
    """Generate formatted booking confirmation details"""
    
    start_time = appointment_data['start_time']
    end_time = appointment_data['end_time']
    
    local_start = convert_to_local_time(start_time, timezone_str)
    local_end = convert_to_local_time(end_time, timezone_str)
    
    return {
        "date": local_start.strftime("%A, %B %d, %Y"),
        "time": f"{local_start.strftime('%-I:%M %p')} - {local_end.strftime('%-I:%M %p')}",
        "duration": format_duration(appointment_data.get('duration_minutes', 0)),
        "timezone": timezone_str,
        "reference": appointment_data.get('booking_reference', ''),
        "service_name": appointment_data.get('service_name', ''),
        "staff_name": appointment_data.get('staff_name', ''),
        "location": appointment_data.get('location', ''),
        "notes": appointment_data.get('special_requests', '')
    }