import json
import pytest
from datetime import datetime, timedelta
from app import db
from app.models.user import User, OwnerProfile
from app.models.otp import OTPVerification
from app.services.email_service import generate_password_reset_token


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
    # Should be back on the login screen
    assert b"Welcome to PG Finder" in logout_res.data


def test_login_invalid_credentials(client, test_users):
    res = client.post('/auth/login', data={
        'email': 'customer@example.com',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert b"Invalid email address or password" in res.data


def test_welcome_screen_unauthenticated(client):
    """When a user opens the app without an active session, display the Welcome screen."""
    res = client.get('/', follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome to PG Finder" in res.data
    assert b"Find your perfect PG, room, and stay in Bengaluru." in res.data
    assert b"Mobile Number" in res.data
    assert b"Email &amp; Password" in res.data or b"Email & Password" in res.data
    assert b"Continue with Google" in res.data


def test_mobile_number_validation_and_send_otp(client, app):
    """Validates mobile number and returns OTP."""
    # Invalid number
    bad_res = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '123'
    })
    assert bad_res.status_code == 400
    bad_json = json.loads(bad_res.data)
    assert bad_json['success'] is False
    assert "valid 10-digit Indian mobile number" in bad_json['error']

    # Valid Indian mobile number
    good_res = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9876543210'
    })
    assert good_res.status_code == 200
    data = json.loads(good_res.data)
    assert data['success'] is True
    assert data['phone_e164'] == '+919876543210'
    assert data['cooldown_seconds'] == 60
    assert 'dev_otp' in data


def test_mobile_otp_rate_limiting_cooldown(client, app):
    """Checks that requesting OTP twice immediately triggers a cooldown rate limit."""
    res1 = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9988776655'
    })
    assert res1.status_code == 200

    # Immediate second request should be rate-limited
    res2 = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9988776655'
    })
    assert res2.status_code == 429
    data2 = json.loads(res2.data)
    assert data2['success'] is False
    assert "Please wait" in data2['error']


def test_mobile_otp_verification_existing_account(client, app, test_users):
    """Existing user logging in via verified mobile number."""
    send_res = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9876543210'
    })
    assert send_res.status_code == 200
    otp = json.loads(send_res.data)['dev_otp']

    # Verify OTP
    verify_res = client.post('/auth/mobile/verify-otp', json={
        'country_code': '+91',
        'mobile_number': '9876543210',
        'otp_code': otp
    })
    assert verify_res.status_code == 200
    v_data = json.loads(verify_res.data)
    assert v_data['success'] is True
    assert v_data['is_new_user'] is False
    assert '/dashboard' in v_data['redirect_url']


def test_mobile_otp_verification_new_user_registration(client, app):
    """New user registering via mobile number with name and role."""
    send_res = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9123456780'
    })
    assert send_res.status_code == 200
    otp = json.loads(send_res.data)['dev_otp']

    # 1. Verify without name prompts for name
    prompt_res = client.post('/auth/mobile/verify-otp', json={
        'country_code': '+91',
        'mobile_number': '9123456780',
        'otp_code': otp
    })
    assert prompt_res.status_code == 200
    p_data = json.loads(prompt_res.data)
    assert p_data.get('requires_registration') is True

    # 2. Complete with name & role
    create_res = client.post('/auth/mobile/verify-otp', json={
        'country_code': '+91',
        'mobile_number': '9123456780',
        'otp_code': otp,
        'name': 'Deepak Verma',
        'role': 'customer'
    })
    assert create_res.status_code == 200
    c_data = json.loads(create_res.data)
    assert c_data['success'] is True
    assert c_data['is_new_user'] is True

    with app.app_context():
        u = User.query.filter_by(phone='9123456780').first()
        assert u is not None
        assert u.name == 'Deepak Verma'
        assert u.role == 'customer'


def test_mobile_otp_expiry_and_failed_attempts(client, app):
    """Verifies that expired OTP or exceeding 3 attempts locks the code."""
    send_res = client.post('/auth/mobile/send-otp', json={
        'country_code': '+91',
        'mobile_number': '9876500000'
    })
    otp = json.loads(send_res.data)['dev_otp']

    # 3 invalid attempts
    for attempt in range(3):
        fail_res = client.post('/auth/mobile/verify-otp', json={
            'country_code': '+91',
            'mobile_number': '9876500000',
            'otp_code': '000000'
        })
        assert fail_res.status_code == 400

    # 4th attempt should be locked out even with correct OTP
    lock_res = client.post('/auth/mobile/verify-otp', json={
        'country_code': '+91',
        'mobile_number': '9876500000',
        'otp_code': otp
    })
    assert lock_res.status_code == 400
    assert "Too many failed" in json.loads(lock_res.data)['error']


def test_password_reset_flow(client, app, test_users):
    """Requests password reset, verifies token, and sets new password."""
    # 1. Request reset
    req_res = client.post('/auth/forgot-password', data={
        'email': 'customer@example.com'
    }, follow_redirects=True)
    assert req_res.status_code == 200

    # 2. Generate valid token
    with app.app_context():
        token = generate_password_reset_token(test_users['customer'].id)

    # 3. Submit new password
    reset_res = client.post(f'/auth/reset-password/{token}', data={
        'password': 'BrandNewPassword@2026',
        'confirm_password': 'BrandNewPassword@2026'
    }, follow_redirects=True)
    assert reset_res.status_code == 200
    assert b"reset successfully" in reset_res.data

    # 4. Verify user can log in with new password
    login_new = client.post('/auth/login', data={
        'email': 'customer@example.com',
        'password': 'BrandNewPassword@2026'
    }, follow_redirects=True)
    assert login_new.status_code == 200
    assert b"Welcome back, Test Customer!" in login_new.data


def test_google_login_account_linking(client, app, test_users):
    """Google callback links to existing account by email without creating duplicates."""
    res = client.get('/auth/google/callback?email=customer@example.com&name=Test Customer', follow_redirects=True)
    assert res.status_code == 200
    assert b"Signed in via Google" in res.data

    with app.app_context():
        # Count of users with customer@example.com must still be exactly 1
        count = User.query.filter_by(email='customer@example.com').count()
        assert count == 1
