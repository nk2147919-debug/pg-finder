import pytest
from app import db
from app.models.property import Property
from app.models.gym import GymFacility, GymPhoto, GYM_EQUIPMENT_CHOICES
from app.services.search_service import search_properties


@pytest.fixture
def property_with_gym(app, test_property):
    gym = GymFacility(
        property_id=test_property.id,
        is_available=True,
        access_type='free',
        monthly_fee=0.0,
        capacity=10,
        opening_time='6:00 AM',
        closing_time='10:00 PM',
        description='State of the art in-house fitness studio.',
        usage_rules='Clean sports shoes required. Wipe equipment after use.'
    )
    gym.equipment = ['dumbbells', 'treadmill', 'yoga_mats']
    db.session.add(gym)
    db.session.commit()
    return test_property


def test_gym_model_properties(property_with_gym):
    gym = property_with_gym.gym_facility
    assert gym is not None
    assert gym.is_available is True
    assert gym.is_active is True
    assert gym.access_label == 'Included in Rent'
    assert 'Dumbbells' in gym.equipment_labels
    assert 'Treadmill' in gym.equipment_labels
    assert len(gym.equipment_with_icons) == 3
    assert property_with_gym.has_gym is True

    # Test paid access label
    gym.access_type = 'paid'
    gym.monthly_fee = 600.0
    assert '₹600/month extra' in gym.access_label

    # Test temporary unavailability
    gym.is_temporarily_unavailable = True
    assert gym.is_active is False

    # Test serialization
    data = gym.to_dict()
    assert data['is_available'] is True
    assert data['monthly_fee'] == 600.0
    assert 'dumbbells' in data['equipment']


def test_gym_search_filter(app, property_with_gym, test_users):
    # Create second property without gym
    prop_no_gym = Property(
        owner_id=test_users['owner1'].id,
        name="No Gym PG",
        slug="no-gym-pg-btm",
        locality="BTM Layout",
        address="456 7th Cross, BTM",
        pincode="560076",
        latitude=12.9165,
        longitude=77.6101,
        gender_policy="gents",
        property_type="standard",
        description="Simple PG without gym facility",
        status="approved"
    )
    db.session.add(prop_no_gym)
    db.session.commit()

    # Search without gym filter
    results_all = search_properties({})
    assert any(p.id == property_with_gym.id for p in results_all['items'])
    assert any(p.id == prop_no_gym.id for p in results_all['items'])

    # Search with has_gym=true
    results_gym = search_properties({'has_gym': 'true'})
    matching_ids = [p.id for p in results_gym['items']]
    assert property_with_gym.id in matching_ids
    assert prop_no_gym.id not in matching_ids


def test_owner_manage_gym_get(client, test_users, property_with_gym):
    # Login as owner1
    client.post('/auth/login', data={
        'email': 'owner1@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)

    res = client.get(f'/owner/property/{property_with_gym.id}/gym')
    assert res.status_code == 200
    assert b'In-House Gym Settings' in res.data
    assert b'Dumbbells' in res.data


def test_owner_manage_gym_post_update(client, test_users, property_with_gym):
    client.post('/auth/login', data={
        'email': 'owner1@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)

    form_data = {
        'is_available': 'y',
        'access_type': 'paid',
        'monthly_fee': '750',
        'opening_time': '5:30 AM',
        'closing_time': '10:30 PM',
        'capacity': '12',
        'maintenance_schedule': 'Sunday 12pm-2pm',
        'description': 'Updated modern fitness gym with new machines',
        'usage_rules': 'No outdoor footwear',
        'equipment': ['dumbbells', 'barbells', 'cable_machine']
    }

    res = client.post(f'/owner/property/{property_with_gym.id}/gym', data=form_data, follow_redirects=True)
    assert res.status_code == 200

    # Verify database update
    gym = GymFacility.query.filter_by(property_id=property_with_gym.id).first()
    assert gym.access_type == 'paid'
    assert gym.monthly_fee == 750.0
    assert gym.opening_time == '5:30 AM'
    assert gym.capacity == 12
    assert 'barbells' in gym.equipment


def test_owner_manage_gym_unauthorized(client, test_users, property_with_gym):
    # Login as owner2 (who doesn't own this property)
    client.post('/auth/login', data={
        'email': 'owner2@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)

    res = client.get(f'/owner/property/{property_with_gym.id}/gym')
    assert res.status_code == 403


def test_owner_delete_gym_photo(client, test_users, property_with_gym):
    client.post('/auth/login', data={
        'email': 'owner1@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)

    gym = property_with_gym.gym_facility
    photo = GymPhoto(
        gym_id=gym.id,
        file_path="/static/uploads/gym/test_gym.jpg",
        caption="Gym Treadmills",
        display_order=0
    )
    db.session.add(photo)
    db.session.commit()
    photo_id = photo.id

    res = client.post(f'/owner/property/{property_with_gym.id}/gym/photo/{photo_id}/delete', follow_redirects=True)
    assert res.status_code == 200

    deleted = GymPhoto.query.get(photo_id)
    assert deleted is None
