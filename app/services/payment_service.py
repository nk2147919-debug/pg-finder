import uuid
import hmac
import hashlib
from datetime import datetime
from flask import current_app
from app import db
from app.models.short_stay import ShortStayBooking, BookingPayment
from app.models.interaction import Notification


def get_razorpay_keys():
    """Returns active (key_id, key_secret, is_sandbox) tuple."""
    key_id = current_app.config.get('RAZORPAY_KEY_ID', 'rzp_test_pgfinder_sandbox')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', 'pgfinder_secret_sandbox_key_2026')
    is_sandbox = current_app.config.get('RAZORPAY_SANDBOX_MODE', True)
    return key_id, key_secret, is_sandbox


def create_payment_order(booking, amount_in_rupees=None, payment_type='full', notes=None):
    """
    Creates a Razorpay order for customer checkout.
    Uses real Razorpay client if keys are live, or deterministic sandbox order in test mode.
    """
    key_id, key_secret, is_sandbox = get_razorpay_keys()

    if amount_in_rupees is None:
        if payment_type == 'advance':
            amount_in_rupees = booking.advance_amount
        else:
            amount_in_rupees = booking.total_amount if booking.total_paid == 0 else booking.balance_due

    amount_in_rupees = float(amount_in_rupees)
    amount_in_paise = int(round(amount_in_rupees * 100))

    order_receipt = f"RCPT-{booking.booking_code}"
    order_id = None

    # Try live Razorpay SDK if not in explicit sandbox mode with placeholder keys
    if not is_sandbox and not key_id.startswith('rzp_test_mock'):
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            rzp_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': order_receipt,
                'payment_capture': 1,
                'notes': {
                    'booking_code': booking.booking_code,
                    'property_id': booking.property_id,
                    'customer_id': booking.customer_id,
                    'payment_type': payment_type
                }
            })
            order_id = rzp_order.get('id')
        except Exception as e:
            current_app.logger.warning(f"Razorpay live API order creation failed, falling back to sandbox: {e}")

    # Sandbox / Test fallback
    if not order_id:
        order_id = f"order_sbx_{uuid.uuid4().hex[:14]}"

    # Save order ID on booking
    booking.gateway_order_id = order_id
    db.session.commit()

    return {
        'order_id': order_id,
        'amount': amount_in_paise,
        'amount_in_rupees': amount_in_rupees,
        'currency': 'INR',
        'key_id': key_id,
        'booking_code': booking.booking_code,
        'payment_type': payment_type,
        'customer_name': booking.customer.name if booking.customer else '',
        'customer_email': booking.customer.email if booking.customer else '',
        'customer_phone': booking.customer.phone if booking.customer else '',
        'is_sandbox': is_sandbox
    }


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature, key_secret=None):
    """
    Cryptographically verifies the authenticity of a Razorpay payment signature
    using HMAC-SHA256 digest comparison.
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    if key_secret is None:
        _, key_secret, _ = get_razorpay_keys()

    msg = f"{razorpay_order_id}|{razorpay_payment_id}"
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated_signature, razorpay_signature)


def generate_sandbox_signature(order_id, payment_id, key_secret=None):
    """Utility helper to generate a valid test signature for sandbox/automated tests."""
    if key_secret is None:
        _, key_secret, _ = get_razorpay_keys()
    msg = f"{order_id}|{payment_id}"
    return hmac.new(key_secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()


def verify_webhook_signature(body_bytes, signature_header, webhook_secret=None):
    """Verifies Razorpay webhook header signature against raw request bytes."""
    if not body_bytes or not signature_header:
        return False
    if webhook_secret is None:
        webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET', 'pgfinder_webhook_secret_2026')

    generated = hmac.new(
        webhook_secret.encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated, signature_header)


def record_verified_payment(booking_id, gateway_order_id, gateway_payment_id, gateway_signature,
                            amount, payment_method='Razorpay/UPI', notes=None,
                            payment_type='full', verify_signature=True):
    """
    Records a verified transaction with strict idempotency / duplicate check.
    """
    booking = ShortStayBooking.query.get_or_404(booking_id)

    # 1. Idempotency Check: Prevent duplicate payment processing
    existing_payment = BookingPayment.query.filter(
        (BookingPayment.transaction_id == gateway_payment_id) |
        (BookingPayment.gateway_payment_id == gateway_payment_id)
    ).first()

    if existing_payment:
        return existing_payment

    # 2. Signature verification
    if verify_signature:
        is_valid = verify_payment_signature(gateway_order_id, gateway_payment_id, gateway_signature)
        if not is_valid:
            raise ValueError("Payment signature verification failed. The transaction may have been tampered with.")

    amount = float(amount)
    receipt_no = BookingPayment.generate_receipt_number()

    payment = BookingPayment(
        booking_id=booking.id,
        transaction_id=gateway_payment_id,
        receipt_number=receipt_no,
        gateway_order_id=gateway_order_id,
        gateway_payment_id=gateway_payment_id,
        gateway_signature=gateway_signature,
        amount=amount,
        payment_method=payment_method,
        payment_type=payment_type,
        status='successful',
        notes=notes or f"Online payment verified via {payment_method}"
    )
    db.session.add(payment)
    db.session.flush()

    # 3. Update booking financial and payment status
    current_total_paid = sum(p.amount for p in booking.payments if p.status == 'successful')
    if current_total_paid >= booking.total_amount:
        booking.payment_status = 'paid'
    else:
        booking.payment_status = 'advance_paid'
        booking.advance_paid_amount = current_total_paid

    booking.payment_method = payment_method
    booking.gateway_order_id = gateway_order_id

    # 4. Notify Owner
    if booking.property and booking.property.owner_id:
        notif = Notification(
            user_id=booking.property.owner_id,
            title=f"Payment Received: {booking.booking_code}",
            message=f"Received ₹{amount:,.0f} via {payment_method} (Receipt #{receipt_no}). Total paid: ₹{current_total_paid:,.0f}/{booking.total_amount:,.0f}.",
            link_url="/owner/short-stay/bookings"
        )
        db.session.add(notif)

    db.session.commit()
    return payment


def process_booking_refund(booking_id, reason="Customer cancellation"):
    """
    Marks payments as refunded according to cancellation policy.
    """
    booking = ShortStayBooking.query.get_or_404(booking_id)

    total_refund = 0.0
    for p in booking.payments:
        if p.status == 'successful':
            p.status = 'refunded'
            p.refund_amount = p.amount
            p.refund_notes = reason
            total_refund += p.amount

    booking.refund_amount = total_refund
    booking.payment_status = 'refunded'
    db.session.commit()
    return total_refund
