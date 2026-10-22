import json
import uuid
import pytest
from datetime import datetime, date, timedelta
from app import db
from app.models.property import Property
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment, BlockedDate
from app.services.short_stay_service import (
    calculate_quote, is_property_available, search_short_stay,
    create_booking, process_payment, calculate_property_occupancy
)
from app.services.receipt_service import generate_booking_receipt_pdf
from app.services.payment_service import (
    create_payment_order, verify_payment_signature, record_verified_payment,
    generate_sandbox_signature, verify_webhook_signature, process_booking_refund
)


@pytest.fixture
def short_stay_prop(app, test_property):
    """Configures test_property to accept short stays."""
    cfg = ShortStayConfig(
        property_id=test_property.id,
        is_enabled=True,
        daily_rate=1000.0,
        weekly_rate=6000.0,
        fortnightly_rate=11000.0,
        extra_guest_charge=300.0,
        base_guests=1,
        max_guests=4,
        min_nights=1,
        max_nights=30,
        check_in_time="12:00 PM",
        check_out_time="11:00 AM",
        security_deposit=1000.0,
        cleaning_fee=200.0,
        tax_percentage=10.0,
        cancellation_policy="Free cancellation up to 24 hours before check-in",
        short_stay_rules="Govt ID required. No loud music after 10 PM."
    )
    db.session.add(cfg)
    db.session.commit()
    return test_property


# ==============================================================================
# 1. Pricing Quote Calculation Tests
# ==============================================================================

def test_calculate_quote_single_night(short_stay_prop):
    cfg = short_stay_prop.short_stay_config
    today = date.today()
    tomorrow = today + timedelta(days=1)

    quote = calculate_quote(cfg, today, tomorrow, num_guests=1)
    assert quote['nights'] == 1
    assert quote['base_amount'] == 1000.0
    assert quote['extra_guests_amount'] == 0.0
    assert quote['cleaning_fee'] == 200.0
    assert quote['subtotal'] == 1200.0
    # 10% tax on 1200 = 120
    assert quote['tax_amount'] == 120.0
    assert quote['security_deposit'] == 1000.0
    # 1200 + 120 + 1000 = 2320
    assert quote['total_amount'] == 2320.0


def test_calculate_quote_extra_guests(short_stay_prop):
    cfg = short_stay_prop.short_stay_config
    today = date.today()
    checkout = today + timedelta(days=2)  # 2 nights

    # 3 guests: 1 base + 2 extra guests
    quote = calculate_quote(cfg, today, checkout, num_guests=3)
    assert quote['nights'] == 2
    assert quote['base_amount'] == 2000.0
    # Extra: 2 guests * 300 * 2 nights = 1200
    assert quote['extra_guests_amount'] == 1200.0
    assert quote['subtotal'] == 2000.0 + 1200.0 + 200.0  # 3400.0


def test_calculate_quote_weekly_discount(short_stay_prop):
    cfg = short_stay_prop.short_stay_config
    today = date.today()
    checkout = today + timedelta(days=7)  # 7 nights

    quote = calculate_quote(cfg, today, checkout, num_guests=1)
    assert quote['nights'] == 7
    # Weekly rate is 6000.0 instead of 7 * 1000 = 7000.0
    assert quote['base_amount'] == 6000.0
    assert "Weekly" in quote['pricing_tier']


def test_calculate_quote_validation_errors(short_stay_prop):
    cfg = short_stay_prop.short_stay_config
    today = date.today()

    # Invalid dates: checkout <= checkin
    with pytest.raises(ValueError, match="after check-in"):
        calculate_quote(cfg, today, today)

    # Exceeds max guests
    with pytest.raises(ValueError, match="Maximum permitted occupancy"):
        calculate_quote(cfg, today, today + timedelta(days=2), num_guests=10)


# ==============================================================================
# 2. Availability & Double-Booking Prevention Tests
# ==============================================================================

def test_availability_and_double_booking(short_stay_prop, test_users):
    cust = test_users['customer']
    prop_id = short_stay_prop.id
    d1 = date.today() + timedelta(days=10)
    d2 = date.today() + timedelta(days=15)

    # Initially available
    avail, reason = is_property_available(prop_id, d1, d2)
    assert avail is True

    # Block a date inside the range
    blocked = BlockedDate(property_id=prop_id, date=d1 + timedelta(days=2), reason="Renovation")
    db.session.add(blocked)
    db.session.commit()

    avail, reason = is_property_available(prop_id, d1, d2)
    assert avail is False
    assert "blocked by owner" in reason.lower()

    # Unblock and check
    db.session.delete(blocked)
    db.session.commit()

    # Create a confirmed booking in that range
    b = create_booking(
        customer_id=cust.id,
        property_id=prop_id,
        check_in_date=d1,
        check_out_date=d2,
        num_guests=2
    )
    b.status = 'confirmed'
    db.session.commit()

    # Overlapping attempt: d1+1 to d2-1
    avail, reason = is_property_available(prop_id, d1 + timedelta(days=1), d2 - timedelta(days=1))
    assert avail is False
    assert "overlap" in reason.lower() or "confirmed" in reason.lower()

    # Non-overlapping range: d2 to d2+3 should be available
    avail, reason = is_property_available(prop_id, d2, d2 + timedelta(days=3))
    assert avail is True


# ==============================================================================
# 3. Customer Web Journey Tests
# ==============================================================================

def test_short_stay_search_page(client, short_stay_prop):
    res = client.get('/short-stay')
    assert res.status_code == 200
    assert b"Short Stay" in res.data
    assert short_stay_prop.name.encode() in res.data


def test_short_stay_quote_api(client, short_stay_prop):
    today = date.today().strftime('%Y-%m-%d')
    checkout = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')

    res = client.get(f'/short-stay/quote?property_id={short_stay_prop.id}&check_in={today}&check_out={checkout}&num_guests=2')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert data['available'] is True
    assert data['quote']['nights'] == 3


def test_customer_booking_flow(client, short_stay_prop, test_users):
    # Login as customer
    client.post('/auth/login', data={'email': 'customer@example.com', 'password': 'Password@123'}, follow_redirects=True)

    c_in = (date.today() + timedelta(days=5)).strftime('%Y-%m-%d')
    c_out = (date.today() + timedelta(days=8)).strftime('%Y-%m-%d')

    res = client.post(f'/short-stay/book/{short_stay_prop.id}', data={
        'check_in_date': c_in,
        'check_out_date': c_out,
        'num_guests': 2,
        'primary_guest_name': 'Test Traveler',
        'primary_guest_phone': '9876543210',
        'primary_guest_id_proof': 'Aadhaar-1234',
        'special_requests': 'Late check-in requested'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Booking Receipt" in res.data
    assert b"Test Traveler" in res.data

    # Check booking created in DB
    booking = ShortStayBooking.query.filter_by(property_id=short_stay_prop.id).first()
    assert booking is not None
    assert booking.status == 'pending'
    assert booking.nights == 3

    # Test payment simulation
    pay_res = client.post(f'/short-stay/booking/{booking.booking_code}/pay', data={
        'amount': booking.total_amount,
        'payment_method': 'UPI',
        'notes': 'Paid via UPI ref 123456'
    }, follow_redirects=True)

    assert pay_res.status_code == 200
    assert booking.payment_status == 'paid'

    # Check customer dashboard shows the booking
    dash_res = client.get('/dashboard')
    assert dash_res.status_code == 200
    assert booking.booking_code.encode() in dash_res.data


# ==============================================================================
# 4. Owner Management Journey Tests
# ==============================================================================

def test_owner_manage_short_stay(client, short_stay_prop, test_users):
    # Logout customer and login as owner1
    client.get('/auth/logout')
    client.post('/auth/login', data={'email': 'owner1@example.com', 'password': 'Password@123'}, follow_redirects=True)

    # View short stay config
    res = client.get(f'/owner/property/{short_stay_prop.id}/short-stay')
    assert res.status_code == 200
    assert b"Short-Stay Settings" in res.data

    # Update rates
    post_res = client.post(f'/owner/property/{short_stay_prop.id}/short-stay', data={
        'is_enabled': 'y',
        'daily_rate': 1250.0,
        'weekly_rate': 7500.0,
        'fortnightly_rate': 13500.0,
        'base_guests': 1,
        'max_guests': 5,
        'extra_guest_charge': 400.0,
        'min_nights': 1,
        'max_nights': 20,
        'security_deposit': 1500.0,
        'cleaning_fee': 250.0,
        'tax_percentage': 5.0,
        'check_in_time': '1:00 PM',
        'check_out_time': '10:00 AM',
        'cancellation_policy': 'Flexible',
        'short_stay_rules': 'No smoking indoors'
    }, follow_redirects=True)

    assert post_res.status_code == 200
    assert short_stay_prop.short_stay_config.daily_rate == 1250.0
    assert short_stay_prop.short_stay_config.max_guests == 5


def test_owner_booking_acceptance_and_calendar(client, short_stay_prop, test_users):
    # Create booking request
    cust = test_users['customer']
    b = create_booking(
        customer_id=cust.id,
        property_id=short_stay_prop.id,
        check_in_date=date.today() + timedelta(days=3),
        check_out_date=date.today() + timedelta(days=5),
        num_guests=2
    )

    client.get('/auth/logout')
    client.post('/auth/login', data={'email': 'owner1@example.com', 'password': 'Password@123'}, follow_redirects=True)

    # View bookings pipeline
    b_res = client.get('/owner/short-stay/bookings')
    assert b_res.status_code == 200
    assert b.booking_code.encode() in b_res.data

    # Accept booking
    act_res = client.post(f'/owner/short-stay/booking/{b.id}/action', data={
        'action': 'confirm',
        'owner_notes': 'Booking confirmed by owner!'
    }, follow_redirects=True)

    assert act_res.status_code == 200
    assert b.status == 'confirmed'

    # Test calendar blocking
    block_date_str = (date.today() + timedelta(days=25)).strftime('%Y-%m-%d')
    cal_res = client.post(f'/owner/property/{short_stay_prop.id}/short-stay/calendar', data={
        'date': block_date_str,
        'reason': 'Scheduled Pest Control'
    }, follow_redirects=True)

    assert cal_res.status_code == 200
    assert b"Scheduled Pest Control" in cal_res.data


# ==============================================================================
# 5. Android REST API Tests
# ==============================================================================

def test_short_stay_rest_api(client, short_stay_prop, test_users):
    # 1. Properties endpoint
    res = client.get('/api/v1/short-stay/properties?locality=Koramangala')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['status'] == 'success'
    assert len(data['data']) >= 1

    # 2. Quote endpoint
    c_in = (date.today() + timedelta(days=4)).strftime('%Y-%m-%d')
    c_out = (date.today() + timedelta(days=6)).strftime('%Y-%m-%d')
    quote_res = client.get(f'/api/v1/short-stay/quote?property_id={short_stay_prop.id}&check_in={c_in}&check_out={c_out}&num_guests=2')
    assert quote_res.status_code == 200
    q_data = json.loads(quote_res.data)
    assert q_data['status'] == 'success'
    assert q_data['data']['nights'] == 2

    # 3. Booking endpoint
    cust = test_users['customer']
    book_res = client.post('/api/v1/short-stay/book', json={
        'property_id': short_stay_prop.id,
        'customer_id': cust.id,
        'check_in': c_in,
        'check_out': c_out,
        'num_guests': 2,
        'special_requests': 'Android App Booking',
        'guests_data': [
            {'full_name': 'Mobile User 1'},
            {'full_name': 'Mobile User 2'}
        ]
    })
    assert book_res.status_code == 201
    b_data = json.loads(book_res.data)
    assert b_data['status'] == 'success'
    code = b_data['data']['booking_code']

    # 4. Booking status query
    status_res = client.get(f'/api/v1/short-stay/bookings/{code}')
    assert status_res.status_code == 200
    s_data = json.loads(status_res.data)
    assert s_data['status'] == 'success'
    assert s_data['data']['status'] == 'pending'


# ==============================================================================
# 6. Advanced Edge Cases, Concurrency, PDF & Payment Gateway Tests
# ==============================================================================

def test_calculate_quote_fortnightly_discount(short_stay_prop):
    """Verifies that 14-night stays apply the fortnightly discounted rate."""
    cfg = short_stay_prop.short_stay_config
    today = date.today()
    checkout = today + timedelta(days=14)

    quote = calculate_quote(cfg, today, checkout, num_guests=1)
    assert quote['nights'] == 14
    assert quote['base_amount'] == 11000.0
    assert "Fortnightly" in quote['pricing_tier']


def test_calculate_quote_partial_extended_stay(short_stay_prop):
    """Verifies partial stays (e.g. 8 nights) apply tiered rates properly."""
    cfg = short_stay_prop.short_stay_config
    today = date.today()
    checkout = today + timedelta(days=8)

    quote = calculate_quote(cfg, today, checkout, num_guests=1)
    assert quote['nights'] == 8
    # 8 nights at effective weekly daily rate (6000 / 7 = 857.14 * 8 = 6857.12)
    assert quote['base_amount'] < 8000.0  # cheaper than standard daily rate 8 * 1000
    assert quote['base_amount'] > 6000.0  # more than 7 nights


def test_exclusive_checkout_boundary(short_stay_prop, test_users):
    """Tests that one booking can check out on the exact date another checks in."""
    cust = test_users['customer']
    prop_id = short_stay_prop.id
    d_start = date.today() + timedelta(days=30)
    d_mid = d_start + timedelta(days=3)
    d_end = d_mid + timedelta(days=3)

    # Booking 1: d_start to d_mid
    b1 = create_booking(cust.id, prop_id, d_start, d_mid, num_guests=1)
    b1.status = 'confirmed'
    db.session.commit()

    # Booking 2: d_mid to d_end (starts on the same day Booking 1 ends)
    avail, reason = is_property_available(prop_id, d_mid, d_end)
    assert avail is True
    b2 = create_booking(cust.id, prop_id, d_mid, d_end, num_guests=1)
    assert b2 is not None


def test_owner_confirmation_recheck_availability(short_stay_prop, test_users):
    """
    Prevents race condition: If two bookings are requested for overlapping dates,
    confirming the first one must prevent confirming the second one.
    """
    cust = test_users['customer']
    prop_id = short_stay_prop.id
    d1 = date.today() + timedelta(days=40)
    d2 = d1 + timedelta(days=4)

    # Booking A
    b_a = create_booking(cust.id, prop_id, d1, d2, num_guests=1)

    # Simulate overlapping pending booking B created concurrently
    b_b = ShortStayBooking(
        booking_code=ShortStayBooking.generate_booking_code(),
        property_id=prop_id,
        customer_id=cust.id,
        check_in_date=d1 + timedelta(days=1),
        check_out_date=d2,
        nights=3,
        num_guests=1,
        daily_rate_applied=1000.0,
        base_amount=3000.0,
        total_amount=3000.0,
        status='pending',
        payment_status='pending'
    )
    db.session.add(b_b)
    db.session.commit()

    # Confirm booking A
    b_a.status = 'confirmed'
    db.session.commit()

    # Now attempt to confirm booking B via is_property_available with only_confirmed=True
    avail, reason = is_property_available(prop_id, b_b.check_in_date, b_b.check_out_date, exclude_booking_id=b_b.id, only_confirmed=True)
    assert avail is False
    assert "overlap" in reason.lower() or "confirmed" in reason.lower()


def test_pdf_receipt_generation(short_stay_prop, test_users):
    """Tests the PDF invoice generation service using ReportLab."""
    cust = test_users['customer']
    d1 = date.today() + timedelta(days=12)
    d2 = d1 + timedelta(days=3)

    booking = create_booking(
        customer_id=cust.id,
        property_id=short_stay_prop.id,
        check_in_date=d1,
        check_out_date=d2,
        num_guests=2,
        guests_data=[{'full_name': 'Traveler One'}, {'full_name': 'Traveler Two'}]
    )

    pdf_buffer = generate_booking_receipt_pdf(booking)
    pdf_bytes = pdf_buffer.getvalue()

    # ReportLab output starts with %PDF magic header
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_pdf_receipt_download_route(client, short_stay_prop, test_users):
    """Tests the GET /short-stay/booking/<booking_code>/receipt/pdf route."""
    cust = test_users['customer']
    booking = create_booking(
        customer_id=cust.id,
        property_id=short_stay_prop.id,
        check_in_date=date.today() + timedelta(days=18),
        check_out_date=date.today() + timedelta(days=20),
        num_guests=1
    )

    # Login as booking customer
    client.post('/auth/login', data={'email': 'customer@example.com', 'password': 'Password@123'}, follow_redirects=True)

    res = client.get(f'/short-stay/booking/{booking.booking_code}/receipt/pdf')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/pdf'
    assert f"PG_Receipt_{booking.booking_code}.pdf" in res.headers['Content-Disposition']
    assert res.data.startswith(b"%PDF")


def test_razorpay_order_and_signature_verification(app, short_stay_prop, test_users):
    """Tests payment order creation and cryptographic HMAC signature validation."""
    with app.app_context():
        cust = test_users['customer']
        booking = create_booking(
            customer_id=cust.id,
            property_id=short_stay_prop.id,
            check_in_date=date.today() + timedelta(days=22),
            check_out_date=date.today() + timedelta(days=24),
            num_guests=1
        )

        # 1. Create order
        order_info = create_payment_order(booking, amount_in_rupees=booking.total_amount)
        assert 'order_id' in order_info
        assert order_info['amount_in_rupees'] == booking.total_amount
        order_id = order_info['order_id']

        # 2. Valid signature test
        test_payment_id = "pay_test_987654321"
        valid_sig = generate_sandbox_signature(order_id, test_payment_id)
        assert verify_payment_signature(order_id, test_payment_id, valid_sig) is True

        # 3. Tampered signature test
        assert verify_payment_signature(order_id, test_payment_id, "invalid_tampered_signature") is False


def test_duplicate_payment_prevention(app, short_stay_prop, test_users):
    """Tests that duplicate payment callbacks/submissions with the same gateway ID are idempotent."""
    with app.app_context():
        cust = test_users['customer']
        booking = create_booking(
            customer_id=cust.id,
            property_id=short_stay_prop.id,
            check_in_date=date.today() + timedelta(days=26),
            check_out_date=date.today() + timedelta(days=28),
            num_guests=1
        )

        order_id = f"order_test_{uuid.uuid4().hex[:8]}"
        pay_id = f"pay_test_{uuid.uuid4().hex[:8]}"
        sig = generate_sandbox_signature(order_id, pay_id)

        # First recording
        p1 = record_verified_payment(
            booking_id=booking.id,
            gateway_order_id=order_id,
            gateway_payment_id=pay_id,
            gateway_signature=sig,
            amount=booking.total_amount,
            payment_method='UPI'
        )
        assert p1 is not None
        assert booking.payment_status == 'paid'

        # Duplicate recording attempt
        p2 = record_verified_payment(
            booking_id=booking.id,
            gateway_order_id=order_id,
            gateway_payment_id=pay_id,
            gateway_signature=sig,
            amount=booking.total_amount,
            payment_method='UPI'
        )
        # Should return existing payment without creating a second record
        assert p1.id == p2.id
        payments_count = BookingPayment.query.filter_by(booking_id=booking.id).count()
        assert payments_count == 1


def test_booking_cancellation_and_refund(client, short_stay_prop, test_users):
    """Tests cancelling a paid booking and refunding deposited funds."""
    client.post('/auth/login', data={'email': 'customer@example.com', 'password': 'Password@123'}, follow_redirects=True)

    cust = test_users['customer']
    booking = create_booking(
        customer_id=cust.id,
        property_id=short_stay_prop.id,
        check_in_date=date.today() + timedelta(days=35),
        check_out_date=date.today() + timedelta(days=37),
        num_guests=1
    )

    # Process advance payment
    process_payment(booking.id, amount=booking.advance_amount, payment_method='UPI')
    assert booking.payment_status == 'advance_paid'

    # Cancel booking
    res = client.post(f'/short-stay/booking/{booking.booking_code}/cancel', follow_redirects=True)
    assert res.status_code == 200
    assert booking.status == 'cancelled'
    assert booking.payment_status == 'refunded'
    assert booking.refund_amount == booking.advance_amount


def test_owner_unauthorized_property_access(client, short_stay_prop, test_users):
    """Verifies that Owner 2 cannot edit or access Owner 1's short stay config or calendar."""
    client.post('/auth/login', data={'email': 'owner2@example.com', 'password': 'Password@123'}, follow_redirects=True)

    # Owner 2 attempts to edit Owner 1's property settings
    res = client.get(f'/owner/property/{short_stay_prop.id}/short-stay')
    assert res.status_code == 403

    # Owner 2 attempts to view Owner 1's calendar
    cal_res = client.get(f'/owner/property/{short_stay_prop.id}/short-stay/calendar')
    assert cal_res.status_code == 403


def test_android_api_data_masking_and_payment(client, short_stay_prop, test_users):
    """Tests data masking for unauthenticated requests and the REST API payment endpoint."""
    cust = test_users['customer']
    c_in = (date.today() + timedelta(days=45)).strftime('%Y-%m-%d')
    c_out = (date.today() + timedelta(days=47)).strftime('%Y-%m-%d')

    booking = create_booking(
        customer_id=cust.id,
        property_id=short_stay_prop.id,
        check_in_date=c_in,
        check_out_date=c_out,
        num_guests=2,
        guests_data=[{'full_name': 'Private Traveler', 'id_proof_number': 'AADHAAR-9999'}]
    )

    # 1. Unauthenticated query: phone and email should be masked
    res = client.get(f'/api/v1/short-stay/bookings/{booking.booking_code}')
    assert res.status_code == 200
    data = json.loads(res.data)['data']
    assert '******' in data['customer_phone']
    assert '***@' in data['customer_email']
    # ID proof number should not be exposed
    assert 'id_proof_number' not in data['guests'][0]

    # 2. Authenticated query as the customer: full details visible
    auth_res = client.get(f'/api/v1/short-stay/bookings/{booking.booking_code}?user_id={cust.id}')
    assert auth_res.status_code == 200
    auth_data = json.loads(auth_res.data)['data']
    assert auth_data['customer_phone'] == cust.phone
    assert auth_data['guests'][0]['id_proof_number'] == 'AADHAAR-9999'

    # 3. Payment via REST API
    pay_res = client.post(f'/api/v1/short-stay/bookings/{booking.booking_code}/pay', json={
        'amount': booking.total_amount,
        'payment_method': 'GooglePay'
    })
    assert pay_res.status_code == 200
    p_json = json.loads(pay_res.data)
    assert p_json['status'] == 'success'
    assert booking.payment_status == 'paid'

