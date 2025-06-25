# **BookingBot NG**
*Configurable Appointment System for Nigerian Businesses*


---

## **🚀 Key Features**
- **Admin-Configurable Services** - Tailor booking flows for any industry
- **Nigerian Payments** - Paystack + Bank Transfer with NIP verification
- **Branded Booking Links** - `yourbusiness.bookingbot.ng`
- **Multi-Calendar Sync** - Google, Outlook & Native Mobile Calendar
- **WhatsApp/SMS Reminders** - Localized notifications

---

## **🛠️ Setup for Local Development**

To get BookingBot NG running on your local machine, follow these steps:

1. **Clone with submodules**: Ensure you clone the repository including any potential submodules used for specific integrations or libraries.
   ```bash
   git clone --recurse-submodules https://github.com/thetruesammyjay/bookingbot-ng.git
   cd bookingbot-ng
   ```

2. **Start core services**: Use Docker Compose to bring up the essential backend services like PostgreSQL and Redis.
   ```bash
   docker-compose -f infrastructure/docker-compose.yml up -d postgres redis
   ```

3. **Install Python dependencies**: (Assuming a Python backend framework like FastAPI/Django)
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed test tenants**: Populate your local database with sample business data to get started quickly.
   ```bash
   python scripts/seed_tenants.py
   ```
   *(Follow any additional instructions from the `scripts/seed_tenants.py` output for accessing the admin portal and booking links for these sample tenants.)*

5. **Install Frontend Dependencies**:
   ```bash
   cd frontend/admin-portal
   npm install # or yarn install
   cd ../booking-page
   npm install # or yarn install
   ```

6. **Run Frontend Development Servers**:
   ```bash
   # In one terminal for the admin portal
   cd frontend/admin-portal
   npm start # or yarn start

   # In another terminal for the booking page
   cd frontend/booking-page
   npm start # or yarn start
   ```
   *(You may need to configure proxy settings in your frontend development servers to point to your backend API, depending on your chosen framework.)*

---

## **🔧 Configuration Highlights**

BookingBot NG is designed for extensive customizability through various configuration methods.

### **1. Tenant Service Setup (YAML Example)**
Business owners can configure their services, pricing, and custom fields via the admin portal, which then stores this data, often represented internally using a schema similar to this YAML example:

```yaml
# Example: Auto Workshop Configuration
services:
  - name: "Engine Diagnostics"
    duration: 45
    payment:
      required: true
      options:
        - type: paystack
          amount: 5000
        - type: bank_transfer
          account_name: "AutoFix NG"
          # NIP verification details would be linked here
    custom_fields:
      - name: "Vehicle Type"
        type: dropdown
        options: ["Car", "SUV", "Truck"]
  - name: "Tyre Rotation"
    duration: 30
    payment:
      required: false
      options: [] # Or just optional payment
```

### **2. Environment Variables**
Sensitive information and tenant-specific overrides are managed via environment variables.

```ini
# .env.tenant (Per-business overrides, often set at deployment or via admin UI)
BOOKING_PAGE_THEME=salon_red  # Predefined themes or custom CSS paths
TIMEZONE=Africa/Lagos         # Crucial for accurate scheduling
CURRENCY=NGN                  # Default currency for transactions
WHATSAPP_API_KEY=your_whatsapp_api_key
PAYSTACK_SECRET_KEY=your_paystack_secret_key
```

---

## **🌐 Supported Business Types**

BookingBot NG's configurable nature makes it suitable for a wide array of Nigerian businesses, each with potential special features:

| Industry          | Special Features                               |
|-------------------|------------------------------------------------|
| **Healthcare**    | Emergency slots, Patient record integration |
| **Automotive**    | Part availability check, VIN scanner, Mechanic assignment |
| **Beauty**        | Stylist portfolios, Deposit collections, Before/After galleries |
| **Religious**     | Group bookings for services/events, Recurring donations, Member management |
| **Agriculture**   | Farm location mapping, Weather alerts for optimal scheduling, Resource allocation |
| **Consulting**    | Consultant availability, Document sharing, Meeting room booking |
| **Education**     | Tutor scheduling, Class bookings, Course material access |

---

## **📈 Analytics Integration**

The platform provides robust analytics to give business owners insights into their bookings and performance.

```python
# Sample backend endpoint for business insights (e.g., FastAPI)
from fastapi import APIRouter, Request
from typing import Literal

router = APIRouter()

@router.get("/analytics/{tenant_id}")
async def get_bookings_analytics(
    request: Request,
    tenant_id: str,
    period: Literal["daily", "weekly", "monthly"] = "weekly"
):
    """
    Returns visualization-ready booking data for a given tenant and period.
    Authentication and authorization for the tenant_id are handled by middleware.
    """
    # Placeholder for actual data retrieval logic
    # tenant = verify_tenant_access(request, tenant_id) # Assumed to be handled by auth middleware
    # analytics_data = tenant.get_analytics(period)
    # return analytics_data
    return {
        "tenant_id": tenant_id,
        "period": period,
        "total_bookings": 150,
        "revenue_ngn": 750000,
        "bookings_by_service": {"Engine Diagnostics": 50, "Tyre Rotation": 100},
        "bookings_over_time": [{"date": "2025-06-01", "count": 10}, {"date": "2025-06-08", "count": 25}]
    }
```

---

## **📱 Mobile Optimization**

Designed with a mobile-first approach to ensure seamless experience even in low-bandwidth environments.

*USSD Shortcode Support Coming Soon (Example: `*347*5#` for quick bookings, enabling broader access)*


---

## **📜 License**

This project is licensed under the **AGPL-3.0**. This includes a specific requirement for Nigerian businesses to complete a verification process before deploying the system for production use, ensuring compliance and security.

---

## **📞 Contact**

For support, inquiries, or partnership opportunities, please reach out to our dedicated team:

**Nigerian Support Team (AGM TECHPLUSE)**:
- 📞 +234 800 BOOKBOT (Toll-free within Nigeria)
- 📧 support@agmtechpluse.net
- *Available 8am-6pm WAT, Monday - Friday*

---

This version emphasizes:

1. **Multi-tenancy** with clean separation of code and data paths.
2. **Nigerian-specific** payment and notification flows.
3. **Admin configurability** as the core feature, enabling diverse business types.
4. **Mobile-first** design optimized for the Nigerian digital landscape.
