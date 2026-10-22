import pytest
from app.models.user import User, OwnerProfile


def test_customer_registration(client, app):
    response = client.post('/auth/register', data={
        'name': 'Anita Roy',
        'email': 'anita.roy@example.com',
        'phone': '9876543219',
        'role': 'customer',
        'password': 'SecretPassword123',
        'confirm_password': 'SecretPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email='anita.roy@example.com').first()
        assert user is not None
        assert user.role == 'customer'
        assert user.check_password('SecretPassword123')


def test_owner_registration(client, app):
    response = client.post('/auth/register', data={
        'name': 'Gopal Rao',
        'email': 'gopal.rao@example.com',
        'phone': '9845011223',
        'role': 'owner',
        'business_name': 'Rao PG Accommodations',
        'password': 'OwnerPassword123',
        'confirm_password': 'OwnerPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email='gopal.rao@example.com').first()
        assert user is not None
        assert user.role == 'owner'
        assert user.owner_profile is not None
        assert user.owner_profile.business_name == 'Rao PG Accommodations'


def test_login_and_logout(client, test_users):
    # Valid login
    login_res = client.post('/auth/login', data={
        'email': 'customer@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Welcome back, Test Customer!" in login_res.data

    # Logout
    logout_res = client.get('/auth/logout', follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"logged out securely" in logout_res.data


def test_login_invalid_credentials(client, test_users):
    res = client.post('/auth/login', data={
        'email': 'customer@example.com',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert b"Invalid email address or password" in res.data
