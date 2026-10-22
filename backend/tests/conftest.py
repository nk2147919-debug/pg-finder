import sys
import os
import pytest
from datetime import datetime, date, timedelta

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app, db
from config import TestConfig
from app.models.user import User, OwnerProfile
from app.models.property import Property, Amenity, PropertyAmenity, PropertyMedia
from app.models.room import RoomType
from app.models.food import FoodMenu


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def test_users(app):
    # Customer
    customer = User(
        name="Test Customer",
        email="customer@example.com",
        phone="9876543210",
        role="customer"
    )
    customer.set_password("Password@123")

    # Owner 1
    owner1 = User(
        name="Test Owner One",
        email="owner1@example.com",
        phone="9876543211",
        role="owner"
    )
    owner1.set_password("Password@123")

    # Owner 2 (for cross-owner modification tests)
    owner2 = User(
        name="Test Owner Two",
        email="owner2@example.com",
        phone="9876543212",
        role="owner"
    )
    owner2.set_password("Password@123")

    # Admin
    admin = User(
        name="Test Admin",
        email="admin@example.com",
        phone="9876543213",
        role="admin"
    )
    admin.set_password("Password@123")

    db.session.add_all([customer, owner1, owner2, admin])
    db.session.commit()

    return {
        'customer': customer,
        'owner1': owner1,
        'owner2': owner2,
        'admin': admin
    }


@pytest.fixture
def test_property(app, test_users):
    owner = test_users['owner1']
    prop = Property(
        owner_id=owner.id,
        name="Sunrise Luxury Gents PG",
        slug="sunrise-luxury-gents-pg-koramangala",
        locality="Koramangala",
        sub_locality="5th Block",
        address="123 5th Cross, Koramangala, Bengaluru",
        pincode="560095",
        latitude=12.9352,
        longitude=77.6245,
        gender_policy="gents",
        property_type="premium",
        description="Comfortable PG near Sony World Signal with delicious 3 times food and high speed Wi-Fi.",
        status="approved",
        availability_last_confirmed_at=datetime.utcnow(),
        price_last_confirmed_at=datetime.utcnow(),
        menu_last_updated_at=datetime.utcnow(),
        photos_last_verified_at=datetime.utcnow()
    )
    db.session.add(prop)
    db.session.flush()

    # Room Type
    room = RoomType(
        property_id=prop.id,
        sharing_type="double",
        title="Double Sharing with AC",
        monthly_rent=12000.0,
        deposit_amount=12000.0,
        total_beds=6,
        occupied_beds=4,
        vacant_beds=2,
        has_ac=True,
        has_attached_bathroom=True,
        availability_date=date.today()
    )
    db.session.add(room)

    # Food Menu
    food = FoodMenu(
        property_id=prop.id,
        food_type="both",
        meals_provided="Breakfast, Dinner on weekdays, 3 meals on weekends",
        food_included_in_rent=True
    )
    food.set_menu_dict(FoodMenu.get_default_menu())
    db.session.add(food)

    db.session.commit()
    return prop
