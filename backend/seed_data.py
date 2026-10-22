import sys
import os
import json
from datetime import datetime, timedelta, date

curr_dir = os.path.abspath(os.path.dirname(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)

from app import create_app, db
from app.models.user import User, OwnerProfile
from app.models.property import Property, Amenity, PropertyAmenity, PropertyMedia, VerificationRecord
from app.models.room import RoomType
from app.models.food import FoodMenu
from app.models.interaction import Enquiry, VisitRequest, Favourite, Review, Notification
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment, BlockedDate
from app.models.gym import GymFacility, GymPhoto

app = create_app()


def seed_database():
    with app.app_context():
        print("🌱 Dropping existing tables and creating fresh schema...")
        db.drop_all()
        db.create_all()

        print("✨ Seeding amenities...")
        amenities_data = [
            ('High-Speed Wi-Fi (300 Mbps)', 'wifi', 'bi-wifi', 'connectivity'),
            ('3 Times Nutritious Food', 'food-3-times', 'bi-cup-hot', 'food'),
            ('Power Backup (24/7 Inverter/DG)', 'power-backup', 'bi-lightning-charge', 'utility'),
            ('Daily Room & Bath Cleaning', 'housekeeping', 'bi-stars', 'comfort'),
            ('Fully Automatic Washing Machine', 'laundry', 'bi-droplet', 'utility'),
            ('RO Mineral Water Purifier', 'ro-water', 'bi-moisture', 'food'),
            ('CCTV 24/7 Security & Guard', 'cctv-security', 'bi-shield-check', 'security'),
            ('Air Conditioner (AC)', 'ac', 'bi-snow', 'comfort'),
            ('Attached Western Bathroom', 'attached-bath', 'bi-door-closed', 'comfort'),
            ('Geyser / 24h Hot Water', 'geyser', 'bi-thermometer-half', 'utility'),
            ('Refrigerator / Fridge', 'fridge', 'bi-inbox', 'utility'),
            ('Microwave Oven & Induction', 'microwave', 'bi-oven', 'food'),
            ('Elevator / Lift', 'lift', 'bi-arrow-up-circle', 'comfort'),
            ('Two-Wheeler Covered Parking', 'bike-parking', 'bi-bicycle', 'utility'),
            ('Four-Wheeler Car Parking', 'car-parking', 'bi-car-front', 'utility'),
            ('Biometric Fingerprint Entry', 'biometric', 'bi-fingerprint', 'security'),
            ('TV with OTT (Netflix/Prime)', 'tv-ott', 'bi-tv', 'connectivity'),
            ('Individual Cupboards & Lockers', 'wardrobe', 'bi-lock', 'comfort')
        ]

        amenity_objs = {}
        for name, slug, icon, cat in amenities_data:
            am = Amenity(name=name, slug=slug, icon=icon, category=cat)
            db.session.add(am)
            amenity_objs[slug] = am

        db.session.flush()

        print("👤 Seeding demo users...")
        # Admin
        admin = User(
            name="Antigravity Admin",
            email="admin@pgfinder.in",
            phone="9880011223",
            role="admin"
        )
        admin.set_password("Admin@123")
        db.session.add(admin)

        # Owners
        owner1 = User(
            name="Suresh Kumar",
            email="owner.suresh@gmail.com",
            phone="9845012345",
            role="owner"
        )
        owner1.set_password("Owner@123")
        db.session.add(owner1)
        db.session.flush()

        owner1_profile = OwnerProfile(
            user_id=owner1.id,
            business_name="Sri Balaji & Venkateshwara PG Network",
            pan_or_gst="AAAPK1234Q",
            id_proof_type="Aadhaar",
            id_proof_number="XXXX-XXXX-4589",
            is_verified=True,
            verification_status="verified"
        )
        db.session.add(owner1_profile)

        owner2 = User(
            name="Priya Reddy",
            email="owner.priya@gmail.com",
            phone="9742098765",
            role="owner"
        )
        owner2.set_password("Owner@123")
        db.session.add(owner2)
        db.session.flush()

        owner2_profile = OwnerProfile(
            user_id=owner2.id,
            business_name="UrbanStay Coliving Ventures",
            pan_or_gst="BLRPR9988Z",
            id_proof_type="PAN",
            id_proof_number="ABCDE1234F",
            is_verified=True,
            verification_status="verified"
        )
        db.session.add(owner2_profile)

        # Customers
        cust1 = User(
            name="Rahul Sharma",
            email="rahul.tech@gmail.com",
            phone="9123456780",
            role="customer"
        )
        cust1.set_password("Customer@123")
        db.session.add(cust1)

        cust2 = User(
            name="Ananya Deshmukh",
            email="ananya.deshmukh@gmail.com",
            phone="9876543210",
            role="customer"
        )
        cust2.set_password("Customer@123")
        db.session.add(cust2)

        db.session.commit()

        print("🏢 Seeding Bengaluru PG Properties with real locations & coordinates...")
        now = datetime.utcnow()

        properties_seed = [
            {
                'owner': owner1,
                'name': 'Sri Balaji Luxury Gents PG',
                'slug': 'sri-balaji-luxury-gents-pg-koramangala',
                'locality': 'Koramangala',
                'sub_locality': '5th Block, near Jyoti Nivas College Road',
                'address': '#142, 5th Main, 5th Block, Koramangala, Bengaluru',
                'pincode': '560095',
                'lat': 12.9352,
                'lng': 77.6245,
                'landmark': 'Behind Sony World Signal / Near Forum Mall',
                'metro_dist': 2.4,
                'bus_dist': 0.2,
                'gender': 'gents',
                'prop_type': 'premium',
                'description': 'Premium, well-ventilated PG for male working professionals and students in the heart of Koramangala 5th Block. Walkable distance to top tech offices, cafes, and restaurants. Features North & South Indian 3 times fresh homestyle food, super-fast 300 Mbps Wi-Fi, lift, daily housekeeping, and 24/7 power backup.',
                'house_rules': 'Entry allowed till 11:30 PM. No loud music post 10 PM. Non-smoking property inside rooms. Guests allowed in lounge area.',
                'closing_time': '11:30 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': True,
                'views': 412,
                'avail_conf': now - timedelta(hours=3),  # Confirmed today
                'price_conf': now - timedelta(hours=3),
                'menu_conf': now - timedelta(days=2),
                'photo_conf': now - timedelta(days=10),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'attached-bath', 'geyser', 'lift', 'bike-parking'],
                'rooms': [
                    ('single', 'Executive Single Room (Private with Attached Bath & Balcony)', 18500.0, 18500.0, 6, 4, 2, True, True, True),
                    ('double', 'Spacious 2 Sharing Room with Attached Bath', 10500.0, 10500.0, 12, 10, 2, False, True, False),
                    ('triple', 'Economy 3 Sharing Room', 8000.0, 8000.0, 9, 6, 3, False, True, False)
                ]
            },
            {
                'owner': owner2,
                'name': 'UrbanStay Premium Coliving & PG',
                'slug': 'urbanstay-premium-coliving-pg-hsr-layout',
                'locality': 'HSR Layout',
                'sub_locality': 'Sector 3, 27th Main Commercial Street',
                'address': '#488, 14th Cross, 27th Main, Sector 3, HSR Layout, Bengaluru',
                'pincode': '560102',
                'lat': 12.9116,
                'lng': 77.6389,
                'landmark': 'Near BDA Complex & Sector 2 Park',
                'metro_dist': 3.1,
                'bus_dist': 0.1,
                'gender': 'unisex',
                'prop_type': 'luxury',
                'description': 'Vibrant coliving destination in HSR Layout Sector 3 designed for startup engineers and creatives. Work-from-home dedicated workstations, ergonomic chairs, high-speed fiber broadband, gaming lounge, and open terrace garden. Healthy gourmet breakfast and dinner prepared by experienced chefs.',
                'house_rules': '24/7 keyless digital door lock. Visitors permitted until 9 PM. Pets allowed on terrace. Quiet hours after 11 PM.',
                'closing_time': 'No Curfew (Digital Biometric)',
                'notice_days': 30,
                'min_months': 3,
                'deposit_months': 1.5,
                'maint': 500.0,
                'elec': 'per_unit',
                'featured': True,
                'views': 560,
                'avail_conf': now - timedelta(hours=6),  # Confirmed today
                'price_conf': now - timedelta(hours=6),
                'menu_conf': now - timedelta(days=1),
                'photo_conf': now - timedelta(days=5),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'ac', 'attached-bath', 'geyser', 'fridge', 'microwave', 'tv-ott', 'biometric', 'car-parking'],
                'rooms': [
                    ('single', 'Luxury Studio Single with AC & Smart TV', 23000.0, 30000.0, 4, 3, 1, True, True, True),
                    ('double', 'Modern Double Sharing with AC & Work Desks', 13500.0, 20000.0, 10, 8, 2, True, True, False),
                    ('triple', 'Premium Triple Sharing Suite', 9500.0, 14000.0, 6, 5, 1, False, True, False)
                ]
            },
            {
                'owner': owner1,
                'name': 'Venkateshwara Executive Ladies PG',
                'slug': 'venkateshwara-executive-ladies-pg-indiranagar',
                'locality': 'Indiranagar',
                'sub_locality': '100ft Road, Defence Colony',
                'address': '#21, 6th Cross, 100ft Road, Indiranagar, Bengaluru',
                'pincode': '560038',
                'lat': 12.9784,
                'lng': 77.6408,
                'landmark': '500m from Indiranagar Metro Station',
                'metro_dist': 0.5,
                'bus_dist': 0.3,
                'gender': 'ladies',
                'prop_type': 'premium',
                'description': 'Safe, secure, and modern PG exclusively for women working or studying in Indiranagar and Central Bengaluru. CCTV monitored with 24/7 lady warden, biometric gate access, hot water, washing machines, and tasty homely South & North Indian meals.',
                'house_rules': 'Curfew at 10:30 PM for safety. Male guests restricted to lobby. Late entry permitted with prior intimation to warden.',
                'closing_time': '10:30 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': True,
                'views': 380,
                'avail_conf': now - timedelta(days=2),  # Confirmed within 7 days
                'price_conf': now - timedelta(days=2),
                'menu_conf': now - timedelta(days=3),
                'photo_conf': now - timedelta(days=20),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'attached-bath', 'geyser', 'fridge', 'lift', 'biometric', 'wardrobe'],
                'rooms': [
                    ('single', 'Solo Room with Attached Bath & Wardrobe', 17000.0, 17000.0, 4, 3, 1, False, True, False),
                    ('double', 'Cozy 2 Sharing with Attached Bathroom', 10000.0, 10000.0, 8, 6, 2, False, True, False),
                    ('triple', 'Budget 3 Sharing with Study Table', 7500.0, 7500.0, 6, 4, 2, False, True, False)
                ]
            },
            {
                'owner': owner2,
                'name': 'Silicon Valley Tech PG for Men & Women',
                'slug': 'silicon-valley-tech-pg-whitefield',
                'locality': 'Whitefield',
                'sub_locality': 'Near ITPL Gate 3, Pattandur Agrahara',
                'address': '#78, Pattandur Agrahara Main Road, Whitefield, Bengaluru',
                'pincode': '560066',
                'lat': 12.9863,
                'lng': 77.7376,
                'landmark': 'Opposite ITPL Back Gate / Pattandur Metro',
                'metro_dist': 0.4,
                'bus_dist': 0.1,
                'gender': 'unisex',
                'prop_type': 'standard',
                'description': 'Ideal accommodation for tech employees working at ITPL, SAP, TCS, and Whitefield tech parks. Just 400 meters from metro station. Offers high-speed dual-line internet, healthy vegetarian & non-vegetarian food, spacious rooms, and round-the-clock power backup.',
                'house_rules': 'Quiet hours 11 PM to 6 AM. No smoking in common corridors. Biometric attendance.',
                'closing_time': '11:00 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': False,
                'views': 295,
                'avail_conf': now - timedelta(days=4),  # Confirmed within 7 days
                'price_conf': now - timedelta(days=4),
                'menu_conf': now - timedelta(days=5),
                'photo_conf': now - timedelta(days=25),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1540518614846-7ede433c4b12?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'attached-bath', 'geyser', 'lift', 'bike-parking'],
                'rooms': [
                    ('single', 'Single Private Room with Balcony', 15000.0, 15000.0, 5, 4, 1, False, True, True),
                    ('double', 'Double Sharing Room with AC', 9000.0, 9000.0, 14, 12, 2, True, True, False),
                    ('triple', 'Economy 3 Sharing', 6800.0, 6800.0, 9, 8, 1, False, True, False),
                    ('four_plus', 'Budget 4 Sharing Room', 5500.0, 5500.0, 8, 6, 2, False, True, False)
                ]
            },
            {
                'owner': owner1,
                'name': 'TechPark Coliving Suites',
                'slug': 'techpark-coliving-suites-electronic-city',
                'locality': 'Electronic City',
                'sub_locality': 'Phase 1, Near Infosys Campus Gate 1',
                'address': '#32, Neeladri Road, Electronic City Phase 1, Bengaluru',
                'pincode': '560100',
                'lat': 12.8399,
                'lng': 77.6770,
                'landmark': '5 mins from Infosys, Wipro & HP',
                'metro_dist': 1.2,
                'bus_dist': 0.2,
                'gender': 'unisex',
                'prop_type': 'premium',
                'description': 'Designed for Electronic City IT professionals. Modern furnishings, high speed Wi-Fi with backup, 3 nutritious meals daily, gym room, table tennis, and dedicated parking. Easy commute to all Phase 1 campuses.',
                'house_rules': 'No alcohol in shared areas. Friendly community atmosphere. Night shift transport drop allowed.',
                'closing_time': 'No Curfew',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 300.0,
                'elec': 'included',
                'featured': False,
                'views': 230,
                'avail_conf': now - timedelta(days=1),  # Confirmed within 7 days
                'price_conf': now - timedelta(days=1),
                'menu_conf': now - timedelta(days=2),
                'photo_conf': now - timedelta(days=12),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'ac', 'attached-bath', 'geyser', 'fridge', 'lift', 'bike-parking', 'car-parking'],
                'rooms': [
                    ('single', 'Executive AC Single Room', 16000.0, 16000.0, 4, 3, 1, True, True, False),
                    ('double', 'Spacious Double Sharing with AC', 9500.0, 9500.0, 10, 8, 2, True, True, False),
                    ('triple', '3 Sharing Room', 7000.0, 7000.0, 6, 5, 1, False, True, False)
                ]
            },
            {
                'owner': owner2,
                'name': 'Greenview Comfort PG for Gents',
                'slug': 'greenview-comfort-pg-for-gents-btm-layout',
                'locality': 'BTM Layout',
                'sub_locality': '2nd Stage, near Udupi Garden',
                'address': '#91, 16th Main, 2nd Stage, BTM Layout, Bengaluru',
                'pincode': '560076',
                'lat': 12.9166,
                'lng': 77.6101,
                'landmark': 'Walking distance to Udupi Garden Signal & Silk Board',
                'metro_dist': 1.8,
                'bus_dist': 0.1,
                'gender': 'gents',
                'prop_type': 'standard',
                'description': 'Pocket-friendly and clean PG accommodation in BTM Layout 2nd Stage. Central location with instant connectivity to Silk Board, Bannerghatta Road, and Koramangala. Tasty homestyle South Indian food, Wi-Fi, washing machine, and hot water.',
                'house_rules': 'Curfew at 11 PM. Cleanliness in rooms required.',
                'closing_time': '11:00 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': False,
                'views': 185,
                'avail_conf': now - timedelta(days=12),  # Stale (> 7 days)
                'price_conf': now - timedelta(days=12),
                'menu_conf': now - timedelta(days=15),
                'photo_conf': now - timedelta(days=40),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'attached-bath', 'geyser', 'bike-parking'],
                'rooms': [
                    ('single', 'Standard Single Room', 12000.0, 12000.0, 3, 3, 0, False, True, False),  # 0 vacant beds!
                    ('double', 'Double Sharing with Attached Bathroom', 7500.0, 7500.0, 8, 7, 1, False, True, False),
                    ('triple', '3 Sharing Economy Room', 6000.0, 6000.0, 6, 4, 2, False, True, False)
                ]
            },
            {
                'owner': owner1,
                'name': 'EcoSpace Hive Coliving for Techies',
                'slug': 'ecospace-hive-coliving-bellandur',
                'locality': 'Bellandur',
                'sub_locality': 'Outer Ring Road, near EcoSpace Tech Park',
                'address': '#63, Green Glen Layout, Bellandur, Bengaluru',
                'pincode': '560103',
                'lat': 12.9304,
                'lng': 77.6784,
                'landmark': '500m to RMZ EcoSpace & EcoWorld',
                'metro_dist': 2.0,
                'bus_dist': 0.2,
                'gender': 'unisex',
                'prop_type': 'luxury',
                'description': 'Zero commute living for EcoSpace and Outer Ring Road techies! Ultra-modern coliving suites with community lounge, rooftop cafeteria, gym, 500 Mbps fiber internet, and biometric security. High hygiene standards with daily professional housekeeping.',
                'house_rules': 'Community respect policy. Visitors allowed in lounge. Smoking strictly on terrace only.',
                'closing_time': 'No Curfew',
                'notice_days': 30,
                'min_months': 2,
                'deposit_months': 1.5,
                'maint': 500.0,
                'elec': 'per_unit',
                'featured': True,
                'views': 475,
                'avail_conf': now - timedelta(hours=8),  # Confirmed today
                'price_conf': now - timedelta(hours=8),
                'menu_conf': now - timedelta(days=2),
                'photo_conf': now - timedelta(days=14),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'ac', 'attached-bath', 'geyser', 'fridge', 'microwave', 'lift', 'tv-ott', 'biometric', 'bike-parking', 'car-parking'],
                'rooms': [
                    ('single', 'Luxury Single Studio with AC & Smart TV', 22000.0, 25000.0, 5, 3, 2, True, True, True),
                    ('double', 'Double Sharing Suite with Work Desk', 13000.0, 18000.0, 10, 8, 2, True, True, False),
                    ('triple', 'Triple Sharing Deluxe', 9000.0, 12000.0, 6, 5, 1, False, True, False)
                ]
            },
            {
                'owner': owner2,
                'name': 'Sai Krupa Girls Executive PG',
                'slug': 'sai-krupa-girls-executive-pg-marathahalli',
                'locality': 'Marathahalli',
                'sub_locality': 'Near Kalamandir & Multiplex',
                'address': '#19, Sanjay Nagar, Marathahalli, Bengaluru',
                'pincode': '560037',
                'lat': 12.9591,
                'lng': 77.6974,
                'landmark': 'Behind Kalamandir, 2 mins from Marathahalli Bridge',
                'metro_dist': 2.8,
                'bus_dist': 0.1,
                'gender': 'ladies',
                'prop_type': 'standard',
                'description': 'Convenient and safe PG for working ladies and students near Marathahalli Bridge. Quick bus connectivity to Prestige Tech Park, Embassy TechVillage, and Whitefield. Quality home-cooked food, North & South Indian varieties, lift, and Wi-Fi.',
                'house_rules': 'Curfew 10:30 PM. Safe biometric entry. No male visitors allowed on residential floors.',
                'closing_time': '10:30 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': False,
                'views': 190,
                'avail_conf': now - timedelta(days=1),  # Confirmed yesterday (< 7 days)
                'price_conf': now - timedelta(days=1),
                'menu_conf': now - timedelta(days=4),
                'photo_conf': now - timedelta(days=22),
                'status': 'approved',
                'image': 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'food-3-times', 'power-backup', 'housekeeping', 'laundry', 'ro-water', 'cctv-security', 'attached-bath', 'geyser', 'lift', 'biometric', 'wardrobe'],
                'rooms': [
                    ('single', 'Solo Room with Attached Bath', 13500.0, 13500.0, 3, 2, 1, False, True, False),
                    ('double', 'Double Sharing with Storage', 8500.0, 8500.0, 8, 6, 2, False, True, False),
                    ('triple', 'Economy 3 Sharing', 6500.0, 6500.0, 6, 5, 1, False, True, False)
                ]
            },
            {
                'owner': owner1,
                'name': 'New Bangalore Coliving Concept (Pending Approval)',
                'slug': 'new-bangalore-coliving-jp-nagar',
                'locality': 'JP Nagar',
                'sub_locality': 'Phase 4, near Central Mall',
                'address': '#88, 24th Main, JP Nagar 4th Phase, Bengaluru',
                'pincode': '560078',
                'lat': 12.9063,
                'lng': 77.5857,
                'landmark': 'Near JP Nagar Central Mall & Metro',
                'metro_dist': 1.1,
                'bus_dist': 0.2,
                'gender': 'unisex',
                'prop_type': 'premium',
                'description': 'Brand new coliving property submitted by owner awaiting verification team review. Features furnished rooms and shared dining.',
                'house_rules': 'Curfew 11 PM.',
                'closing_time': '11:00 PM',
                'notice_days': 30,
                'min_months': 1,
                'deposit_months': 1.0,
                'maint': 0.0,
                'elec': 'included',
                'featured': False,
                'views': 12,
                'avail_conf': now,
                'price_conf': now,
                'menu_conf': now,
                'photo_conf': now,
                'status': 'pending_approval',  # For testing admin approval queue!
                'image': 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80',
                'amenities': ['wifi', 'power-backup', 'laundry', 'attached-bath'],
                'rooms': [
                    ('double', '2 Sharing Double Room', 9500.0, 9500.0, 6, 0, 6, False, True, False)
                ]
            }
        ]

        created_props = []
        for pdata in properties_seed:
            prop = Property(
                owner_id=pdata['owner'].id,
                name=pdata['name'],
                slug=pdata['slug'],
                locality=pdata['locality'],
                sub_locality=pdata['sub_locality'],
                address=pdata['address'],
                city='Bengaluru',
                pincode=pdata['pincode'],
                latitude=pdata['lat'],
                longitude=pdata['lng'],
                nearest_landmark=pdata['landmark'],
                metro_distance_km=pdata['metro_dist'],
                bus_distance_km=pdata['bus_dist'],
                gender_policy=pdata['gender'],
                property_type=pdata['prop_type'],
                description=pdata['description'],
                house_rules=pdata['house_rules'],
                gate_closing_time=pdata['closing_time'],
                notice_period_days=pdata['notice_days'],
                minimum_stay_months=pdata['min_months'],
                deposit_months=pdata['deposit_months'],
                maintenance_charges=pdata['maint'],
                electricity_charges_type=pdata['elec'],
                status=pdata['status'],
                is_featured=pdata['featured'],
                views_count=pdata['views'],
                availability_last_confirmed_at=pdata['avail_conf'],
                price_last_confirmed_at=pdata['price_conf'],
                menu_last_updated_at=pdata['menu_conf'],
                photos_last_verified_at=pdata['photo_conf']
            )
            db.session.add(prop)
            db.session.flush()
            created_props.append(prop)

            # Add Cover Media
            media = PropertyMedia(
                property_id=prop.id,
                file_path=pdata['image'],
                caption=f"{prop.name} - Front View",
                is_cover=True
            )
            db.session.add(media)

            # Add Amenities
            for amen_slug in pdata['amenities']:
                if amen_slug in amenity_objs:
                    pa = PropertyAmenity(property_id=prop.id, amenity_id=amenity_objs[amen_slug].id)
                    db.session.add(pa)

            # Add Room Types
            for sh_type, title, rent, dep, tot, occ, vac, ac, bath, balc in pdata['rooms']:
                rt = RoomType(
                    property_id=prop.id,
                    sharing_type=sh_type,
                    title=title,
                    monthly_rent=rent,
                    deposit_amount=dep,
                    total_beds=tot,
                    occupied_beds=occ,
                    vacant_beds=vac,
                    has_ac=ac,
                    has_attached_bathroom=bath,
                    has_balcony=balc,
                    availability_date=date.today()
                )
                db.session.add(rt)

            # Add Food Menu
            food = FoodMenu(
                property_id=prop.id,
                food_type='both',
                meals_provided='Breakfast, Dinner on weekdays & 3 meals on weekends',
                food_included_in_rent=True,
                breakfast_timings='7:30 AM - 9:30 AM',
                lunch_timings='1:00 PM - 2:30 PM',
                dinner_timings='8:00 PM - 10:00 PM',
                special_sunday_menu='Special Chicken Biryani / Hyderabadi Veg Biryani with Gulab Jamun',
                last_updated_at=pdata['menu_conf']
            )
            food.set_menu_dict(FoodMenu.get_default_menu())
            db.session.add(food)

            # Add Verification Record for approved ones
            if prop.status == 'approved':
                v_rec = VerificationRecord(
                    property_id=prop.id,
                    verified_by_user_id=admin.id,
                    document_type='physical_inspection',
                    status='verified',
                    notes='Property premises, bed count, and hygiene verified during physical field audit.',
                    verified_at=pdata['photo_conf']
                )
                db.session.add(v_rec)

        db.session.commit()

        print("💬 Seeding reviews, enquiries, and visit requests...")
        # Add Reviews
        rev1 = Review(
            user_id=cust1.id,
            property_id=created_props[0].id,
            rating=5,
            cleanliness_rating=5,
            food_rating=4,
            amenities_rating=5,
            stay_duration="6 - 12 months",
            review_text="Been staying at Sri Balaji for 8 months. Very clean property in Koramangala. The Wi-Fi never disconnects even during remote work hours, and power backup is instant. Food is homely and consistent.",
            status="approved",
            created_at=now - timedelta(days=15)
        )
        db.session.add(rev1)

        rev2 = Review(
            user_id=cust2.id,
            property_id=created_props[1].id,
            rating=5,
            cleanliness_rating=5,
            food_rating=5,
            amenities_rating=5,
            stay_duration="3 - 6 months",
            review_text="Best coliving in HSR Layout! The crowd is awesome, mostly tech startup folks. The rooms are spacious, terrace garden is great for evening calls, and biometrics mean you don't worry about keys.",
            status="approved",
            created_at=now - timedelta(days=8)
        )
        db.session.add(rev2)

        rev3 = Review(
            user_id=cust2.id,
            property_id=created_props[2].id,
            rating=4,
            cleanliness_rating=4,
            food_rating=4,
            amenities_rating=4,
            stay_duration="1 - 3 months",
            review_text="Very safe PG for girls in Indiranagar. Indiranagar metro is literally 5 mins walk away. Warden is helpful and food is good South Indian style.",
            status="approved",
            created_at=now - timedelta(days=20)
        )
        db.session.add(rev3)

        # Pending review for moderation test
        rev4 = Review(
            user_id=cust1.id,
            property_id=created_props[3].id,
            rating=4,
            cleanliness_rating=4,
            food_rating=3,
            amenities_rating=4,
            stay_duration="Currently Staying",
            review_text="Good budget stay near ITPL Whitefield. Metro access is super convenient. Food could use a bit more North Indian variety on weekdays.",
            status="pending",
            created_at=now - timedelta(days=1)
        )
        db.session.add(rev4)

        # Customer Favourites
        fav1 = Favourite(user_id=cust1.id, property_id=created_props[0].id)
        fav2 = Favourite(user_id=cust1.id, property_id=created_props[1].id)
        fav3 = Favourite(user_id=cust2.id, property_id=created_props[2].id)
        db.session.add_all([fav1, fav2, fav3])

        # Enquiries
        enq1 = Enquiry(
            customer_id=cust1.id,
            property_id=created_props[0].id,
            room_type_id=created_props[0].room_types[0].id,
            move_in_date=date.today() + timedelta(days=5),
            budget_max=20000.0,
            message="Hi Suresh ji, I am starting work at Koramangala 5th block next week. Is the Single room on 2nd floor available for immediate possession?",
            status="contacted",
            owner_notes="Called Rahul on phone. Promised to show room on Saturday morning."
        )
        db.session.add(enq1)

        enq2 = Enquiry(
            customer_id=cust2.id,
            property_id=created_props[1].id,
            room_type_id=created_props[1].room_types[1].id,
            move_in_date=date.today() + timedelta(days=10),
            budget_max=15000.0,
            message="Hello, looking for a double sharing room in HSR. Does the rent include electricity and food?",
            status="new"
        )
        db.session.add(enq2)

        # Visit Requests
        vis1 = VisitRequest(
            customer_id=cust1.id,
            property_id=created_props[0].id,
            preferred_date=date.today() + timedelta(days=2),
            preferred_time_slot="Morning (9:00 AM - 12:00 PM)",
            status="accepted",
            owner_message="Welcome Rahul! Please call me at 9845012345 when you reach Sony World signal."
        )
        db.session.add(vis1)

        vis2 = VisitRequest(
            customer_id=cust2.id,
            property_id=created_props[2].id,
            preferred_date=date.today() + timedelta(days=3),
            preferred_time_slot="Evening (4:00 PM - 8:00 PM)",
            status="requested"
        )
        db.session.add(vis2)

        # Notifications
        notif1 = Notification(
            user_id=owner1.id,
            title="New Enquiry Received",
            message="Rahul Sharma enquired about Single Room at Sri Balaji Luxury Gents PG.",
            link_url="/owner/enquiries"
        )
        db.session.add(notif1)

        # ======================================================================
        # Short-Stay Configurations & Demo Reservations
        # ======================================================================
        print("⚡ Seeding Short-Stay configurations & bookings...")
        
        # Property 1: Koramangala
        ss_cfg1 = ShortStayConfig(
            property_id=created_props[0].id,
            is_enabled=True,
            daily_rate=799.0,
            weekly_rate=4999.0,
            fortnightly_rate=9499.0,
            extra_guest_charge=299.0,
            base_guests=1,
            max_guests=4,
            min_nights=1,
            max_nights=30,
            check_in_time="12:00 PM",
            check_out_time="11:00 AM",
            security_deposit=1000.0,
            cleaning_fee=150.0,
            tax_percentage=5.0,
            short_stay_rules="Gates close at 11:00 PM. No loud noise after 10 PM. Non-smoking property. Govt ID mandatory."
        )
        db.session.add(ss_cfg1)

        # Property 3: Manyata Tech Park / Nagawara
        ss_cfg2 = ShortStayConfig(
            property_id=created_props[2].id,
            is_enabled=True,
            daily_rate=649.0,
            weekly_rate=3999.0,
            fortnightly_rate=7499.0,
            extra_guest_charge=249.0,
            base_guests=1,
            max_guests=4,
            min_nights=1,
            max_nights=30,
            check_in_time="1:00 PM",
            check_out_time="11:00 AM",
            security_deposit=800.0,
            cleaning_fee=150.0,
            tax_percentage=5.0,
            short_stay_rules="Direct gate entry to Manyata Tech park backgate. High speed Wi-Fi included. Visitors allowed till 8 PM."
        )
        db.session.add(ss_cfg2)

        # Property 4: Whitefield ITPL
        ss_cfg3 = ShortStayConfig(
            property_id=created_props[3].id,
            is_enabled=True,
            daily_rate=699.0,
            weekly_rate=4399.0,
            fortnightly_rate=8199.0,
            extra_guest_charge=250.0,
            base_guests=1,
            max_guests=3,
            min_nights=1,
            max_nights=25,
            check_in_time="12:00 PM",
            check_out_time="11:00 AM",
            security_deposit=1000.0,
            cleaning_fee=200.0,
            tax_percentage=5.0,
            short_stay_rules="Quiet work hours 9 PM to 7 AM. 24/7 security. Keycard entry."
        )
        db.session.add(ss_cfg3)

        # Property 5: Electronic City Phase 1
        ss_cfg4 = ShortStayConfig(
            property_id=created_props[4].id,
            is_enabled=True,
            daily_rate=549.0,
            weekly_rate=3299.0,
            fortnightly_rate=6199.0,
            extra_guest_charge=199.0,
            base_guests=1,
            max_guests=4,
            min_nights=1,
            max_nights=30,
            check_in_time="12:00 PM",
            check_out_time="11:00 AM",
            security_deposit=500.0,
            cleaning_fee=150.0,
            tax_percentage=5.0,
            short_stay_rules="Near Infosys Gate 1. Breakfast and dinner provided. No smoking indoors."
        )
        db.session.add(ss_cfg4)

        db.session.flush()

        # Seed Sample Bookings
        # Booking 1: Rahul Sharma at Manyata Tech Park for 2 nights with a friend (2 guests)
        b1_checkin = date.today() + timedelta(days=2)
        b1_checkout = date.today() + timedelta(days=4)
        b1 = ShortStayBooking(
            booking_code="SSB-20261017-001",
            customer_id=cust1.id,
            property_id=created_props[2].id,
            check_in_date=b1_checkin,
            check_out_date=b1_checkout,
            nights=2,
            num_guests=2,
            daily_rate_applied=649.0,
            base_amount=1298.0,
            extra_guests_amount=498.0,
            cleaning_fee=150.0,
            tax_amount=97.3,
            security_deposit=800.0,
            total_amount=2843.3,
            status="confirmed",
            payment_status="advance_paid",
            special_requests="Arriving around 2 PM by cab from Kempegowda Airport.",
            owner_notes="Room prepared on 2nd floor with high-speed desk setup."
        )
        db.session.add(b1)
        db.session.flush()

        # Add guest details
        g1 = ShortStayGuest(booking_id=b1.id, full_name="Rahul Sharma", id_proof_number="XXXX-XXXX-8912")
        g2 = ShortStayGuest(booking_id=b1.id, full_name="Rohan Verma", id_proof_number="XXXX-XXXX-3341")
        db.session.add_all([g1, g2])

        # Add payment record
        pay1 = BookingPayment(
            booking_id=b1.id,
            transaction_id="TXN-UPI-98234123",
            receipt_number="RCP-20261017-001",
            amount=1421.65,
            payment_method="UPI",
            status="successful",
            notes="Advance token paid via Google Pay"
        )
        db.session.add(pay1)

        # Booking 2: Sneha Patel at Koramangala for 7 nights (1 week friends stay)
        b2_checkin = date.today() + timedelta(days=5)
        b2_checkout = date.today() + timedelta(days=12)
        b2 = ShortStayBooking(
            booking_code="SSB-20261017-002",
            customer_id=cust2.id,
            property_id=created_props[0].id,
            check_in_date=b2_checkin,
            check_out_date=b2_checkout,
            nights=7,
            num_guests=3,
            daily_rate_applied=714.14,
            base_amount=4999.0,
            extra_guests_amount=4186.0,
            cleaning_fee=150.0,
            tax_amount=466.75,
            security_deposit=1000.0,
            total_amount=10801.75,
            status="pending",
            payment_status="pending",
            special_requests="Friends trip from Pune for tech interview rounds at Sony World."
        )
        db.session.add(b2)
        db.session.flush()

        g3 = ShortStayGuest(booking_id=b2.id, full_name="Sneha Patel", id_proof_number="XXXX-XXXX-9921")
        g4 = ShortStayGuest(booking_id=b2.id, full_name="Ananya Roy", id_proof_number="XXXX-XXXX-7712")
        g5 = ShortStayGuest(booking_id=b2.id, full_name="Kavya Nair", id_proof_number="XXXX-XXXX-4411")
        db.session.add_all([g3, g4, g5])

        # Blocked Date for maintenance
        blk1 = BlockedDate(
            property_id=created_props[2].id,
            date=date.today() + timedelta(days=20),
            reason="Air Conditioner Annual Deep Servicing"
        )
        db.session.add(blk1)

        db.session.commit()

        print("\U0001f3cb Seeding gym facilities for select properties...")
        # Gym 1 — Free, fully equipped (Property 0: Koramangala)
        gym1 = GymFacility(
            property_id=created_props[0].id,
            is_available=True,
            access_type='free',
            monthly_fee=0.0,
            opening_time='5:30 AM',
            closing_time='11:00 PM',
            capacity=10,
            maintenance_schedule='Every Sunday 10:00 AM – 12:00 PM',
            description='A fully equipped in-house gym on the ground floor. Free for all residents, open 365 days. Yoga space available on the terrace every morning.',
            usage_rules='Gym shoes are mandatory. Wipe equipment after use. No loud music after 9 PM. Maintain hygiene at all times. Govt-issued gym slots may be introduced during peak hours.',
            is_temporarily_unavailable=False,
        )
        gym1.equipment = ['dumbbells', 'barbells', 'weight_benches', 'treadmill', 'exercise_bike', 'yoga_mats', 'pull_up_bar']
        db.session.add(gym1)
        db.session.flush()

        # Gym 2 — Paid, premium setup (Property 1: HSR Layout)
        gym2 = GymFacility(
            property_id=created_props[1].id,
            is_available=True,
            access_type='paid',
            monthly_fee=800.0,
            opening_time='6:00 AM',
            closing_time='10:00 PM',
            capacity=8,
            maintenance_schedule='Last Saturday of every month',
            description='Premium fitness studio on the first floor with modern cable machines, treadmills, and a dedicated stretching zone.',
            usage_rules='Access card required. No food or beverages inside. Return all weights to racks after use.',
            is_temporarily_unavailable=False,
        )
        gym2.equipment = ['cable_machine', 'treadmill', 'elliptical', 'dumbbells', 'multi_gym_station', 'yoga_mats']
        db.session.add(gym2)
        db.session.flush()

        # Gym 3 — Temporarily unavailable (Property 3: Whitefield)
        gym3 = GymFacility(
            property_id=created_props[3].id,
            is_available=True,
            access_type='free',
            monthly_fee=0.0,
            opening_time='6:00 AM',
            closing_time='9:00 PM',
            capacity=6,
            description='In-house gym with basic free weights and a treadmill. Currently undergoing renovation to add new equipment.',
            usage_rules='Residents only. Show your resident ID at the gym entrance.',
            is_temporarily_unavailable=True,
            unavailability_reason='Gym expansion in progress — new treadmills and cable machines being installed. Expected to reopen by Nov 15.',
        )
        gym3.equipment = ['dumbbells', 'kettlebells', 'yoga_mats', 'rowing_machine']
        db.session.add(gym3)
        db.session.flush()

        db.session.commit()
        print("\u2705 Gym facilities seeded for 3 properties (free, paid, temporarily unavailable).")
        print("\u2705 Database successfully seeded with 9 authentic Bengaluru properties, short stays, users, gym data, and interaction data!")


if __name__ == '__main__':
    seed_database()
