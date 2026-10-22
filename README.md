# PG Finder Bengaluru — Smart Roommate Matching, Short-Stay & PG Community Platform

A modern, full-stack accommodation discovery platform for Bengaluru, India. It includes long-term PG rentals, verified amenities, freshness score tracking, 1–30 day flexible short-stay bookings, and **Smart Roommate Matching with Private PG Communities**.

---

## 🗂️ Project Organization

The repository is organized into distinct **Frontend** and **Backend** directories:

```
pg-finder/
├── backend/                         # Backend Flask application, models, services & API
│   ├── app/                         # Core application package
│   │   ├── forms/                   # WTForms validation classes
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── routes/                  # Modular Blueprints (auth, customer, owner, admin, api)
│   │   └── services/                # Business logic, matching algorithms & payments
│   ├── tests/                       # 59 automated test cases (pytest)
│   ├── config.py                    # App configuration
│   ├── pytest.ini                   # Pytest configuration
│   ├── requirements.txt             # Dependency specification
│   ├── run.py                       # Server runner
│   ├── seed_data.py                 # Initial data populator
│   ├── .env.example                 # Environment variable templates
│   └── README.md                    # Backend documentation
├── frontend/                        # UI templates, styles, and client scripts
│   ├── static/                      # Static assets
│   │   ├── css/style.css            # Custom responsive styles & design tokens
│   │   ├── js/main.js               # Client interactive scripts
│   │   ├── js/map.js                # Bengaluru locality maps
│   │   └── images/                  # Media assets & fallback graphics
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── admin/                   # Admin portal views
│   │   ├── auth/                    # Login & registration views
│   │   ├── community/pg_board.html  # Gated private PG community board
│   │   ├── customer/dashboard.html  # Customer dashboard with Find Roommates tab
│   │   ├── customer/roommates.html  # Smart Roommate Matching Hub
│   │   ├── owner/manage_shared_rooms.html # Owner shared occupancy & announcements
│   │   ├── base.html                # Responsive master layout
│   │   └── ...                      # Listings, search, receipts, details
│   ├── package.json                 # Frontend manifest & scripts
│   └── README.md                    # Frontend documentation
├── run.py                           # Root runner to start the server from root directory
├── pytest.ini                       # Root pytest configuration
├── .gitignore                       # Clean Git ignore rules (ignoring venv, caches, DBs)
└── README.md                        # Master project documentation
```

---

## 🌟 Key Features

### 1. Smart Roommate Matching
- **Lifestyle Profiles**: Set preferred locality in Bengaluru, budget limits, room sharing style (`single`, `double`, `triple`, `any`), occupation, cleanliness (`very_clean`, `moderate`, `relaxed`), food preference (`veg`, `eggetarian`, `non_veg`, `any`), sleep routine (`early_bird`, `night_owl`, `flexible`), and smoking policy.
- **Compatibility Scoring Engine**: Calculates an instant $0-100\%$ score across 6 weighted categories:
  - Budget Alignment (25 pts)
  - Location Preference (20 pts)
  - Cleanliness Standard (15 pts)
  - Dietary Compatibility (15 pts)
  - Sleep Routine & Quiet Hours (15 pts)
  - Smoking Preference (10 pts)
- **Itemized Explanations**: Expandable breakdown cards showing exact points awarded and reasons for each factor.
- **Privacy & Mutual Consent Shield**: Mobile numbers and emails remain securely masked during browsing. Direct contact is unlocked **only** when both candidates mutually like each other.
- **Profile Controls**: Users can activate, pause, edit, or delete their roommate profiles at any time.

### 2. Shared Rooms & Request Workflow
- **Roommate Requests**: Users can send shared room requests specifying an existing PG, room type, proposed split rent, and personal intro.
- **Lifecycle Tracking**: Requests follow clear stages: `pending` ➔ `accepted` ➔ `owner_approved` (or `rejected`/`cancelled`).
- **Owner Occupancy Verification**: When users agree to share a room in an existing PG, the request transitions to the property owner. The owner verifies maximum occupancy limits and vacant bed counts before granting final approval.
- **Automatic Occupancy Updates**: Approving an arrangement automatically decrements vacant beds in that room and enrolls both roommates as verified residents.
- **Safety**: Users can block unwanted profiles and submit safety moderation reports.

### 3. Private PG Community Boards
- **Private Gated Access**: Restricted to active residents, checked-in short-stay guests, and the PG property owner (`403 Forbidden` / redirect for unauthorized users).
- **Resident Discussion Board**: Post questions, coordinate activities (e.g. weekend sports, shared rides), and share local tips.
- **Owner Broadcasts**: Owners can broadcast maintenance notices (power backup alerts, water tank cleaning, curfew rules) pinned to the top of the board.
- **Moderation**: Community members can report inappropriate content, while owners and admins can remove policy-violating posts.

### 4. Short-Stay Booking System (1–30 Days)
- **Flexible Stays**: Book 1 day, 2 days, 1 week, or longer.
- **Dynamic Quotes**: Computes base charges, extra guests, weekly/fortnightly discounts, cleaning fees, security deposit, and GST.
- **Instant Availability & Double-Booking Protection**: Validates dates against confirmed bookings and owner blocked dates.
- **Payment Processing**: Integrated Razorpay checkout, sandbox simulation, signature verification, and duplicate payment protection.
- **Official Receipts**: Instant automated PDF booking receipt generation with unique alphanumeric confirmation codes.

### 5. Android Mobile REST API
All features are exposed under `/api/v1/`:
- `GET /api/v1/roommates/recommended`: Authenticated recommendations with privacy masking.
- `GET/POST /api/v1/roommates/profile`: Roommate profile CRUD.
- `POST /api/v1/roommates/interest`: Like/skip action with mutual match return payload.
- `POST /api/v1/roommates/request`: Send roommate pairing requests.
- `GET/POST /api/v1/roommates/requests`: List and respond to requests (`accept`, `reject`, `cancel`).
- `GET/POST /api/v1/community/<property_id>/posts`: Gated PG community feed and post creation.
- `POST /api/v1/community/posts/<post_id>/comments`: Comment on community posts.
- `POST /api/v1/safety/block` & `/api/v1/safety/report`: Safety blocking and reporting.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (macOS / Linux / Windows)
- Git

### 2. Installation & Setup
```bash
# Clone the repository
git clone https://github.com/nk2147919-debug/pg-finder.git
cd pg-finder

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Seed demo data (optional)
python backend/seed_data.py
```

### 3. Run the Server
You can run the application directly from the root directory:
```bash
python run.py
```
Or from the `backend/` directory:
```bash
cd backend
python run.py
```
Open your browser at **`http://127.0.0.1:5001`**.

---

## 👥 Demo Accounts

| Role | Email | Password | Features Accessible |
|---|---|---|---|
| **Customer** | `rahul.tech@gmail.com` | `Customer@123` | Find Roommates, Bookings, PG Community Board |
| **Customer** | `ananya.deshmukh@gmail.com` | `Customer@123` | Roommate Matching, Candidate Profiles |
| **Owner** | `owner.suresh@gmail.com` | `Owner@123` | Shared Room Approvals, Bed Inventory, Announcements |
| **Admin** | `admin@pgfinder.in` | `Admin@123` | Platform Moderation, Verification, Queue |

---

## 🧪 Testing & Verification

Run the full automated test suite containing **59 tests**:

```bash
# From root directory
./venv/bin/pytest -v
```

### Test Coverage Highlights:
- `tests/test_roommates_community.py` (9 tests):
  - Roommate profile creation, updating, pausing, and deletion
  - 6-factor compatibility calculation & breakdown accuracy
  - Candidate recommendation filtering (excluding self, blocked, and skipped users)
  - Mutual match privacy shield (masking phone/email until mutual interest exists)
  - Roommate request flow, status transitions, and duplicate request prevention
  - Owner shared room occupancy verification, bed decrement, and max limit rejection
  - Gated PG community access authorization (403 for unauthorized users)
  - Community post creation, comments, owner announcements, and moderation deletion
  - Android REST API endpoints with authentication and privacy enforcement
- `tests/test_short_stay.py` (22 tests): Quotes, availability, payments, refunds, and receipts.
- `tests/test_search.py`, `tests/test_property.py`, `tests/test_interactions.py`, `tests/test_gym.py`, `tests/test_freshness.py`, `tests/test_api.py` (28 tests): Core regression coverage.
