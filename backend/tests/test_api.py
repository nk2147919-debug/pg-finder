from datetime import date, timedelta


def test_api_get_properties(client, test_property):
    res = client.get('/api/v1/properties')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert len(data['data']) >= 1
    assert data['data'][0]['name'] == test_property.name
    assert 'freshness' in data['data'][0]


def test_api_get_property_detail(client, test_property):
    res = client.get(f'/api/v1/properties/{test_property.id}')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['data']['id'] == test_property.id
    assert len(data['data']['rooms']) >= 1
    assert data['data']['food_menu'] is not None


def test_api_create_enquiry(client, test_users, test_property):
    payload = {
        'customer_id': test_users['customer'].id,
        'property_id': test_property.id,
        'move_in_date': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'message': 'API test enquiry from mobile application'
    }
    res = client.post('/api/v1/enquiries', json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['data']['customer_name'] == test_users['customer'].name


def test_api_get_property_gym_endpoint(client, test_property):
    from app import db
    from app.models.gym import GymFacility

    # When property has no gym
    res = client.get(f'/api/v1/properties/{test_property.id}/gym')
    assert res.status_code == 200
    assert res.get_json()['has_gym'] is False

    # Add gym
    gym = GymFacility(
        property_id=test_property.id,
        is_available=True,
        access_type='free',
        opening_time='6:00 AM',
        closing_time='10:00 PM'
    )
    gym.equipment = ['dumbbells', 'treadmill']
    db.session.add(gym)
    db.session.commit()

    # Query gym endpoint
    res = client.get(f'/api/v1/properties/{test_property.id}/gym')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['has_gym'] is True
    assert data['data']['opening_time'] == '6:00 AM'
    assert 'dumbbells' in data['data']['equipment']

    # Query property detail endpoint and verify gym payload is included
    detail_res = client.get(f'/api/v1/properties/{test_property.id}')
    assert detail_res.status_code == 200
    detail_data = detail_res.get_json()
    assert detail_data['data']['has_gym'] is True
    assert detail_data['data']['gym']['opening_time'] == '6:00 AM'
