# 🏢 PG Finder Bengaluru — Modern Full-Stack PG Discovery & Management Platform

A modern, responsive, full-stack Paying Guest (PG) accommodation discovery and management platform tailored specifically for **Bengaluru, Karnataka, India**.

Built with **Python Flask**, **Flask-SQLAlchemy**, **Flask-Login**, **Flask-WTF**, **SQLite/PostgreSQL**, and a modern **Vanilla CSS & Bootstrap 5** frontend with **OpenStreetMap (Leaflet.js)**.

---

## 🌟 Key Product Features

### 1. Transparent PG Freshness System
Unlike static listing directories where rents and bed availabilities remain unverified for months, PG Finder Bengaluru introduces a transparent, database timestamp-derived freshness engine:
- **Availability Confirmed Today** (`< 24 hours`): Verified vacancies with zero surprises.
- **Confirmed Within Last 7 Days**: Active listings audited this week.
- **Not Recently Confirmed**: Transparent warning tag alerting searchers that owner re-confirmation is overdue.
- **Verified by Team**: Badges backed by physical field inspections or document audits.
- **1-Click Owner Re-confirmation**: Property managers can re-confirm their vacant beds and prices in one click to boost search ranking.

### 2. Multi-Role User Workflows
- **Customer**:
  - Browse and filter by locality, budget, room sharing, food type, and verified amenities.
  - Interactive Leaflet OpenStreetMap discovery with custom price pins.
  - Side-by-side PG comparison matrix (up to 4 properties).
  - Submit instant inquiries and book in-person visit slots (Morning, Afternoon, Evening).
  - Track enquiry and visit statuses on a customer dashboard.
  - Submit verified resident reviews and report inaccurate listings.
- **PG Owner / Property Manager**:
  - Portfolio dashboard tracking published listings, total vacancies, views, and enquiries.
  - Manage room types: Single, Double, Triple, 4+ sharing with live bed counts (Total, Occupied, Vacant).
  - Manage weekly food menus: breakfast, lunch, and dinner schedules for Monday through Sunday.
  - Inquiries pipeline: View customer move-in dates, contact details, and update statuses (`new`, `contacted`, `scheduled`, `closed`).
  - Visit requests: Accept, decline, reschedule, and record final move-in outcomes.
  - Listing views, conversion rates, and occupancy analytics.
- **Admin**:
  - Listing approvals queue: Review property details, photos, and approve or reject with reasons.
  - User directory: View registered customers/owners and activate or suspend accounts.
  - Review moderation: Audit resident reviews to eliminate spam and false feedback.
  - Complaints & Reports resolution: Investigate customer-reported issues.
  - Stale Availability Alerts: Identify listings needing re-confirmation.

### 3. Short-Stay & Friends Stay Feature
A flexible booking engine that lets customers discover and book paying guest accommodations for 1 night, 2–3 days, 1 week, 15 days, or custom durations:
- **Instant Quotes & Itemized Billing**: Real-time quote calculator breaking down base rent, duration discounts (weekly/fortnightly tiers), extra-guest charges, cleaning fee, 12% GST, and refundable security deposit.
- **Friends Stays (Group Bookings)**: Friends can book together (2, 3, 4+ guests) within the property's permitted occupancy limit.
- **Double-Booking & Blackout Protection**: Prevents overlapping reservations across all confirmed and pending requests and respects owner blackout dates.
- **Booking Status Lifecycle**: Full tracking with states: `Pending`, `Confirmed`, `Rejected`, `Cancelled`, and `Completed`.
- **Payment & Printable Receipts**: Advance token authorization, printable official tax receipt/invoice with receipt reference, transaction IDs, and cancellation management.
- **Owner Short-Stay Controls**: Toggle short-stay availability per property, set daily/weekly/fortnightly prices, extra-guest charges, check-in/out times, house rules, and block/unblock blackout dates on an interactive calendar.

### 4. REST API for Android Mobile Integration
Clean RESTful JSON endpoints (`/api/v1/...`) designed for native Android or hybrid apps:
- `GET /api/v1/properties`: Filtered PG search with pagination and freshness metadata.
- `GET /api/v1/properties/<id>`: Full details including rooms, weekly menu, and amenities.
- `GET /api/v1/localities`: Locality listings with count of active PGs.
- `POST /api/v1/enquiries`: Create enquiries directly from mobile.
- `GET /api/v1/short-stay/properties`: Filter short-stay properties by locality, dates, guests, and price.
- `GET /api/v1/short-stay/quote`: Calculate real-time price quotes for mobile checkout.
- `POST /api/v1/short-stay/book`: Submit short-stay bookings with multiple guest names.
- `GET /api/v1/short-stay/bookings/<booking_code>`: Query real-time booking status and receipt data.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.10+, Flask 3.1+, Flask-SQLAlchemy 3.1+, Flask-Login 0.6+, Flask-WTF 1.3+ |
| **Database** | SQLite (development) / PostgreSQL (production-compatible) |
| **Frontend** | HTML5, CSS3, JavaScript ES6+, Bootstrap 5.3, Bootstrap Icons |
| **Maps** | OpenStreetMap with Leaflet.js |
| **Testing** | pytest 8.0+ |
| **Security** | CSRF Protection, Password Hashing (`scrypt`), Role-Based Access Control (RBAC), Strict Property Ownership Validation |

---

## 📁 Project Structure

```text
pg/
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration
├── config.py                 # Application configuration & thresholds
├── pytest.ini                # Pytest configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application launch runner
├── seed_data.py              # Realistic Bengaluru demo seed script
├── app/
│   ├── __init__.py           # Flask app factory, extensions, and custom filters
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py           # User & OwnerProfile models
│   │   ├── property.py       # Property, Amenity, Media, VerificationRecord
│   │   ├── room.py           # RoomType model with bed counts & amenities
│   │   ├── food.py           # FoodMenu model with weekly Mon-Sun schedules
│   │   └── interaction.py    # Enquiry, VisitRequest, Favourite, Review, Complaint, Notification
│   ├── routes/               # Blueprint controllers
│   │   ├── auth.py           # Auth & RBAC security decorators
│   │   ├── customer.py       # Homepage, search, details, compare, map, dashboard
│   │   ├── owner.py          # Owner dashboard, room & food managers, enquiries
│   │   ├── admin.py          # Admin queue, users, moderation, stale alerts
│   │   └── api.py            # REST API endpoints for Android apps
│   ├── forms/                # Flask-WTF validated forms
│   │   ├── auth_forms.py
│   │   ├── property_forms.py
│   │   └── interaction_forms.py
│   ├── services/
│   │   ├── freshness.py      # Transparent freshness score calculation
│   │   └── search_service.py # Multi-criteria search, filtering & sorting
│   ├── static/
│   │   ├── css/style.css     # Bespoke modern startup UI design system
│   │   ├── js/main.js        # Dynamic AJAX favourites & comparison logic
│   │   ├── js/map.js         # Leaflet OpenStreetMap rendering
│   │   └── uploads/          # User-uploaded property photos
│   └── templates/            # Jinja2 responsive templates
│       ├── base.html
│       ├── index.html
│       ├── search.html
│       ├── property_detail.html
│       ├── compare.html
│       ├── map_view.html
│       ├── auth/             # Login & Registration
│       ├── customer/         # Customer Dashboard
│       ├── owner/            # PG Owner Dashboard & Managers
│       └── admin/            # Admin Panel & Moderation Queues
└── tests/                    # Automated pytest test suites
    ├── conftest.py           # Test fixtures & in-memory database
    ├── test_auth.py          # Authentication tests
    ├── test_authorization.py # RBAC & cross-owner security tests
    ├── test_search.py        # Search & filter tests
    ├── test_freshness.py     # Freshness timestamp tests
    ├── test_interactions.py  # Enquiry & review moderation tests
    └── test_api.py           # REST API tests
```

---

## 🚀 Quickstart & Local Installation

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Setup Virtual Environment
```bash
# Clone or navigate to the repository
cd pg

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

### 4. Seed Development Database
Populates 9 authentic Bengaluru PGs (Koramangala, HSR Layout, Indiranagar, Whitefield, Electronic City, BTM Layout, Bellandur, Marathahalli), demo users, room inventory, and food menus:
```bash
python seed_data.py
```

### 5. Launch the Application
```bash
python run.py
```
Open your browser at: **`http://127.0.0.1:5000`**

---

## 🔑 Demo Login Accounts

| Role | Email | Password | Access Details |
|---|---|---|---|
| **Customer** | `rahul.tech@gmail.com` | `Customer@123` | Search, compare, enquiries, visit requests |
| **PG Owner 1** | `owner.suresh@gmail.com` | `Owner@123` | Sri Balaji PG Properties (Koramangala, HSR) |
| **PG Owner 2** | `owner.priya@gmail.com` | `Owner@123` | UrbanStay Coliving (Indiranagar, Whitefield) |
| **Admin** | `admin@pgfinder.in` | `Admin@123` | Listing approvals queue, user controls, reviews moderation |

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest -v
```

Tests cover:
1. **Authentication**: Registration, login, logout, password hashing, active status check.
2. **Authorization & RBAC**: Ensuring customers cannot access owner/admin portals, and owners cannot modify other owners' properties (403 Forbidden).
3. **Search & Filters**: Locality search, budget min/max, sharing type, food options, amenities, and available beds.
4. **PG Freshness System**: Timestamp audits, "Confirmed Today", "Confirmed within 7 days", "Stale alert", and reconfirmation action.
5. **Customer Interactions**: Enquiry delivery, owner status updates, visit scheduling, and review moderation.
6. **REST APIs**: JSON listing discovery, detail endpoints, and mobile enquiry submission.

---

## 📱 Android Integration Guide

### Architecture
The backend is structured as a dual-mode server:
1. **Responsive Web Views**: Completely optimized for Android Chrome and mobile browsers using responsive Bootstrap 5 and mobile touch targets.
2. **REST API**: JSON endpoints under `/api/v1/` for native Android (Kotlin / Jetpack Compose / Flutter) integration.

### Android WebView Wrapper Option
To package the web application as a lightweight Android app:
1. Create a new Android Studio project with an `Empty Activity`.
2. In `activity_main.xml`, add a `<WebView>` element filling the parent.
3. In `MainActivity.kt`:
   ```kotlin
   val webView = findViewById<WebView>(R.id.webView)
   webView.settings.javaScriptEnabled = true
   webView.settings.domStorageEnabled = true
   webView.webViewClient = WebViewClient()
   webView.loadUrl("https://your-domain.com")
   ```
4. In `AndroidManifest.xml`, request internet permission:
   ```xml
   <uses-permission android:name="android.permission.INTERNET" />
   ```

---

## 🌐 Production Deployment Guide

### Recommended Stack
- **OS**: Ubuntu 22.04 LTS
- **WSGI Server**: Gunicorn
- **Reverse Proxy**: Nginx with SSL (Let's Encrypt Certbot)
- **Database**: Managed PostgreSQL (AWS RDS, Supabase, or self-hosted)

### Deployment Steps
1. Set `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://pguser:securepassword@localhost:5432/pg_finder_db
   DEBUG=False
   SECRET_KEY=generate-a-strong-random-hex-key
   ```
2. Run with Gunicorn:
   ```bash
   gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app()"
   ```
3. Nginx configuration snippet:
   ```nginx
   server {
       server_name pgfinder.bengaluru.in;
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       location /static/ {
           alias /var/www/pg/app/static/;
           expires 30d;
       }
   }
   ```

---

## 📋 Feature Completeness Matrix

| Feature | Status | Details |
|---|---|---|
| User Authentication & Registration | ✅ Implemented | Customer & Owner registration with secure password hashing |
| Role-Based Authorization | ✅ Implemented | Server-side protection with `@role_required` and ownership checks |
| Search & Filtering | ✅ Implemented | Locality, budget, sharing, food, amenities, available beds, sorting |
| PG Freshness System | ✅ Implemented | Database timestamp-derived labels ("Today", "7 Days", "Overdue") |
| Property Details & Photos | ✅ Implemented | Photo gallery, bed availability, deposit breakdown, rules |
| Weekly Food Menu Schedule | ✅ Implemented | Mon–Sun breakfast, lunch, and dinner schedule with timings |
| Interactive Maps | ✅ Implemented | OpenStreetMap + Leaflet.js with custom pricing pins |
| Enquiries & Visit Requests | ✅ Implemented | Full workflow with move-in dates, time slots, and status updates |
| Side-by-Side PG Comparison | ✅ Implemented | Compare up to 4 shortlisted properties side-by-side |
| Customer Dashboard | ✅ Implemented | Enquiries, scheduled visits, favourites, and reviews management |
| Owner Dashboard | ✅ Implemented | Bed inventory, room manager, food menu editor, and 1-click reconfirm |
| Admin Panel | ✅ Implemented | Approvals queue, user directory, review moderation, and stale alerts |
| REST API Endpoints | ✅ Implemented | `/api/v1/properties`, `/api/v1/enquiries` for Android apps |
| Online Deposit Payments | ⏳ Prepared | Architectural separation kept free in initial MVP as specified |
