import pytest


def login_as(client, email, password='Password@123'):
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def test_unauthenticated_access_redirects(client):
    res = client.get('/owner/dashboard')
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']

    res = client.get('/admin/dashboard')
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']


def test_customer_cannot_access_owner_or_admin(client, test_users):
    login_as(client, 'customer@example.com')

    # Try accessing owner dashboard
    res = client.get('/owner/dashboard', follow_redirects=True)
    assert b"Access denied" in res.data

    # Try accessing admin dashboard
    res = client.get('/admin/dashboard', follow_redirects=True)
    assert b"Access denied" in res.data


def test_cross_owner_modification_forbidden(client, test_users, test_property):
    # Log in as Owner 2, who does NOT own test_property (which belongs to Owner 1)
    login_as(client, 'owner2@example.com')

    # Try to edit Owner 1's property
    res = client.get(f'/owner/property/{test_property.id}/edit')
    assert res.status_code == 403

    # Try to manage rooms of Owner 1's property
    res = client.get(f'/owner/property/{test_property.id}/rooms')
    assert res.status_code == 403

    # Try to delete room belonging to Owner 1
    room = test_property.room_types[0]
    res = client.post(f'/owner/property/{test_property.id}/room/{room.id}/delete')
    assert res.status_code == 403
