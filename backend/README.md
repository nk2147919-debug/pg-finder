# PG Finder Bengaluru — Backend

This directory houses the Python Flask application server, database models, business logic services, forms, API routes, and automated testing suite.

## Architecture

```
backend/
├── app/
│   ├── forms/
│   │   ├── auth_forms.py            # User registration & login WTForms
│   │   ├── property_forms.py        # Property listing & room configuration
│   │   ├── interaction_forms.py     # Enquiries, visits, reviews, complaints
│   │   ├── short_stay_forms.py      # Short-stay quotes, bookings, blocking
│   │   └── roommate_forms.py        # Roommate profiles, requests, posts, comments
│   ├── models/
│   │   ├── user.py                  # User authentication & owner profiles
│   │   ├── property.py              # Property listings, amenities, media
│   │   ├── room.py                  # Room types, sharing options, bed vacancy
│   │   ├── food.py                  # Food menus & meal options
│   │   ├── gym.py                   # On-site gym facilities & photos
│   │   ├── interaction.py           # Enquiries, visits, reviews, notifications
│   │   ├── short_stay.py            # Short-stay configs, bookings, payments
│   │   ├── roommate.py              # RoommateProfile, Interest, Request, Block, Report
│   │   └── community.py             # PGResident, PGCommunityPost, Comment, Report
│   ├── routes/
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── customer.py              # Customer portal & Roommate/Community views
│   │   ├── owner.py                 # Owner dashboard & shared-occupancy management
│   │   ├── admin.py                 # Administrative verification & moderation
│   │   └── api.py                   # Android REST API endpoints (/api/v1/...)
│   └── services/
│       ├── roommate_service.py      # Compatibility engine, recommendations, matching
│       ├── community_service.py     # Residency authorization & moderation
│       ├── short_stay_service.py    # Availability checking & quotes
│       ├── payment_service.py       # Payment verification & Razorpay webhooks
│       ├── receipt_service.py       # Automated PDF receipt generation
│       ├── freshness.py             # Freshness score & availability timestamps
│       └── search_service.py        # Search & filtering query builder
├── tests/                           # Complete automated pytest test suite
├── config.py                        # Configuration settings
├── run.py                           # Application entry point
├── seed_data.py                     # Demo data population script
└── requirements.txt                 # Python dependencies
```

## Running the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Running Tests

```bash
pytest -v
```
All 59 automated test cases verify matching, privacy rules, duplicate prevention, occupancy limits, gated communities, and API endpoints.
