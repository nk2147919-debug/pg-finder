# PG Finder Bengaluru — Frontend

This directory contains the user interface components, Jinja2 semantic templates, styles, and interactive JavaScript for the PG Finder Bengaluru web platform.

## Architecture & Layout

```
frontend/
├── static/
│   ├── css/
│   │   └── style.css            # Custom CSS styles, design tokens, cards, and animations
│   ├── js/
│   │   ├── main.js              # Interactive client scripts, comparisons, filters, alerts
│   │   └── map.js               # Leaflet / interactive map rendering for Bengaluru localities
│   └── images/
│       └── pg-default.svg       # Vector fallback and placeholder imagery
├── templates/
│   ├── base.html                # Main master template with responsive navbar & footer
│   ├── index.html               # Homepage with featured PGs, locality counters, search
│   ├── search.html              # Filterable PG listings search
│   ├── map_view.html            # Bengaluru interactive map view
│   ├── compare.html             # Side-by-side PG comparison tool
│   ├── property_detail.html     # Comprehensive property view (rooms, gym, amenities, reviews)
│   ├── short_stay_search.html   # Short-stay / 1-30 days flexible bookings
│   ├── short_stay_receipt.html  # Official booking receipt with printable PDF download
│   ├── customer/
│   │   ├── dashboard.html       # Customer portal with enquiry tracking and Roommates tab
│   │   └── roommates.html       # Smart Roommate Matching Hub (Recommendations, Mutual Matches, Requests)
│   ├── community/
│   │   └── pg_board.html        # Gated private PG resident discussion & announcements board
│   ├── owner/
│   │   ├── base_owner.html      # Owner portal navigation and layout
│   │   ├── dashboard.html       # Overview of enquiries, visits, occupancy, views
│   │   ├── manage_shared_rooms.html # Shared room applications & resident broadcasts
│   │   ├── manage_rooms.html    # Bed inventory & sharing types
│   │   ├── manage_short_stay.html # Short-stay pricing, calendar blocking, rules
│   │   ├── manage_food.html     # Weekly food menus & meal options
│   │   └── manage_gym.html      # On-site gym facilities & photos
│   ├── admin/                   # Platform administration & verification
│   └── auth/                    # Registration & Login templates
└── package.json
```

## Key Frontend Features

1. **Smart Roommate Matching Hub** (`templates/customer/roommates.html`):
   - **Recommended Candidates**: Profile cards featuring compatibility percentage badges.
   - **Interactive Factor Accordion**: Shows points awarded for Budget Alignment, Locality, Cleanliness, Food Habits, Sleep Routine, and Smoking Preference.
   - **Mutual Match Privacy Shield**: Clearly indicates when contact information is unlocked versus protected.
   - **Action Controls**: Like, Skip, Send Shared-Room Request, Block, and Report modals.

2. **Private PG Community Board** (`templates/community/pg_board.html`):
   - **Gated Access**: Accessible only to verified residents and the respective property owner.
   - **Category Filters**: Announcements, Maintenance Alerts, Questions, Discussions, and Events.
   - **Threaded Comments & Moderation**: Direct replies and report options for inappropriate content.

3. **Owner Shared Occupancy Portal** (`templates/owner/manage_shared_rooms.html`):
   - Real-time room occupancy and vacant bed monitoring per property.
   - Review and approve/reject shared-room roommate applications.
   - Owner broadcast tool for official resident announcements.
