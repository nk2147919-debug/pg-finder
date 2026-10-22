import uuid
import builtins
from datetime import datetime, date
from app import db


class ShortStayConfig(db.Model):
    __tablename__ = 'short_stay_configs'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # Rates
    daily_rate = db.Column(db.Float, nullable=False, default=1200.0)  # Rate per night for base_guests
    weekly_rate = db.Column(db.Float, nullable=True)  # Discounted flat rate for 7+ nights (optional)
    fortnightly_rate = db.Column(db.Float, nullable=True)  # Discounted flat rate for 14+ nights (optional)
    extra_guest_charge = db.Column(db.Float, default=350.0, nullable=False)  # Charge per extra guest per night

    # Occupancy limits
    base_guests = db.Column(db.Integer, default=1, nullable=False)  # Guests covered in daily_rate
    max_guests = db.Column(db.Integer, default=4, nullable=False)  # Permitted occupancy (for friends stay)

    # Duration limits
    min_nights = db.Column(db.Integer, default=1, nullable=False)  # Minimum stay (e.g. 1 night)
    max_nights = db.Column(db.Integer, default=30, nullable=False)  # Maximum stay (e.g. 30 days)

    # Fees & Deposits
    security_deposit = db.Column(db.Float, default=1000.0, nullable=False)  # Refundable deposit
    cleaning_fee = db.Column(db.Float, default=200.0, nullable=False)  # One-time cleaning fee
    tax_percentage = db.Column(db.Float, default=5.0, nullable=False)  # GST / Service tax %

    # House info
    check_in_time = db.Column(db.String(30), default='12:00 PM', nullable=False)
    check_out_time = db.Column(db.String(30), default='11:00 AM', nullable=False)
    short_stay_rules = db.Column(db.Text, nullable=True)
    cancellation_policy = db.Column(db.String(100), default='Free cancellation up to 24 hours before check-in', nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    property = db.relationship('Property', back_populates='short_stay_config')

    @builtins.property
    def max_guests_allowed(self):
        return self.max_guests

    @builtins.property
    def min_stay_days(self):
        return self.min_nights

    @builtins.property
    def max_stay_days(self):
        return self.max_nights

    @builtins.property
    def house_rules(self):
        return self.short_stay_rules

    @builtins.property
    def weekly_discount_percent(self):
        if self.weekly_rate and self.daily_rate > 0:
            full = self.daily_rate * 7.0
            return max(0.0, round(((full - self.weekly_rate) / full) * 100.0, 1))
        return 0.0

    @builtins.property
    def fortnightly_discount_percent(self):
        if self.fortnightly_rate and self.daily_rate > 0:
            full = self.daily_rate * 14.0
            return max(0.0, round(((full - self.fortnightly_rate) / full) * 100.0, 1))
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'is_enabled': self.is_enabled,
            'daily_rate': self.daily_rate,
            'weekly_rate': self.weekly_rate,
            'fortnightly_rate': self.fortnightly_rate,
            'extra_guest_charge': self.extra_guest_charge,
            'base_guests': self.base_guests,
            'max_guests': self.max_guests,
            'min_nights': self.min_nights,
            'max_nights': self.max_nights,
            'security_deposit': self.security_deposit,
            'cleaning_fee': self.cleaning_fee,
            'tax_percentage': self.tax_percentage,
            'check_in_time': self.check_in_time,
            'check_out_time': self.check_out_time,
            'cancellation_policy': self.cancellation_policy
        }


class ShortStayBooking(db.Model):
    __tablename__ = 'short_stay_bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id', ondelete='SET NULL'), nullable=True)

    # Dates & Stay details
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    nights = db.Column(db.Integer, nullable=False)
    num_guests = db.Column(db.Integer, default=1, nullable=False)

    # Financial breakdown
    daily_rate_applied = db.Column(db.Float, nullable=False)
    base_amount = db.Column(db.Float, nullable=False)
    extra_guests_amount = db.Column(db.Float, default=0.0, nullable=False)
    cleaning_fee = db.Column(db.Float, default=0.0, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0, nullable=False)
    security_deposit = db.Column(db.Float, default=0.0, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

    # Booking & Payment Statuses
    # Status: 'pending', 'confirmed', 'rejected', 'cancelled', 'completed'
    status = db.Column(db.String(30), default='pending', nullable=False, index=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Payment Status: 'pending', 'advance_paid', 'paid', 'refunded'
    payment_status = db.Column(db.String(30), default='pending', nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    gateway_order_id = db.Column(db.String(100), nullable=True, index=True)
    advance_paid_amount = db.Column(db.Float, default=0.0, nullable=False)
    refund_amount = db.Column(db.Float, default=0.0, nullable=False)

    special_requests = db.Column(db.Text, nullable=True)
    owner_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    property = db.relationship('Property', back_populates='short_stay_bookings')
    customer = db.relationship('User', back_populates='short_stay_bookings')
    room_type = db.relationship('RoomType')
    guests = db.relationship('ShortStayGuest', back_populates='booking', cascade='all, delete-orphan')
    payments = db.relationship('BookingPayment', back_populates='booking', cascade='all, delete-orphan')

    @builtins.property
    def total_nights(self):
        return self.nights

    @builtins.property
    def daily_rate(self):
        return self.daily_rate_applied

    @builtins.property
    def extra_guest_charges(self):
        return self.extra_guests_amount

    @builtins.property
    def taxes(self):
        return self.tax_amount

    @builtins.property
    def discount_amount(self):
        return 0.0

    @builtins.property
    def advance_amount(self):
        return round(self.total_amount * 0.5, 2)

    @builtins.property
    def total_paid(self):
        return round(sum(p.amount for p in self.payments if p.status == 'successful'), 2)

    @builtins.property
    def balance_due(self):
        return max(0.0, round(self.total_amount - self.total_paid, 2))

    @builtins.property
    def is_fully_paid(self):
        return self.payment_status == 'paid'

    @builtins.property
    def is_advance_paid(self):
        return self.payment_status == 'advance_paid'

    @staticmethod
    def generate_booking_code():
        return f"BK-BLR-{uuid.uuid4().hex[:6].upper()}"

    def to_dict(self):
        return {
            'id': self.id,
            'booking_code': self.booking_code,
            'property_id': self.property_id,
            'property_name': self.property.name if self.property else '',
            'locality': self.property.locality if self.property else '',
            'customer_name': self.customer.name if self.customer else '',
            'customer_phone': self.customer.phone if self.customer else '',
            'customer_email': self.customer.email if self.customer else '',
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'nights': self.nights,
            'num_guests': self.num_guests,
            'daily_rate_applied': self.daily_rate_applied,
            'base_amount': self.base_amount,
            'extra_guests_amount': self.extra_guests_amount,
            'cleaning_fee': self.cleaning_fee,
            'tax_amount': self.tax_amount,
            'security_deposit': self.security_deposit,
            'total_amount': self.total_amount,
            'total_paid': self.total_paid,
            'balance_due': self.balance_due,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'gateway_order_id': self.gateway_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ShortStayGuest(db.Model):
    __tablename__ = 'short_stay_guests'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('short_stay_bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    id_proof_type = db.Column(db.String(50), nullable=True)  # Aadhaar, Passport, Driving License, Student ID
    id_proof_number = db.Column(db.String(50), nullable=True)

    booking = db.relationship('ShortStayBooking', back_populates='guests')


class BookingPayment(db.Model):
    __tablename__ = 'booking_payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('short_stay_bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    transaction_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    receipt_number = db.Column(db.String(80), unique=True, nullable=False, index=True)
    gateway_order_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_payment_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_signature = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='UPI', nullable=False)
    payment_type = db.Column(db.String(30), default='full', nullable=False)  # 'advance', 'full', 'balance', 'security_deposit'
    status = db.Column(db.String(30), default='successful', nullable=False)  # successful, refunded, failed
    notes = db.Column(db.String(255), nullable=True)
    refund_amount = db.Column(db.Float, default=0.0, nullable=False)
    refund_notes = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    booking = db.relationship('ShortStayBooking', back_populates='payments')

    @builtins.property
    def created_at(self):
        return self.paid_at

    @builtins.property
    def is_successful(self):
        return self.status == 'successful'

    @builtins.property
    def is_refunded(self):
        return self.status == 'refunded'

    @staticmethod
    def generate_receipt_number():
        return f"REC-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"


class BlockedDate(db.Model):
    __tablename__ = 'blocked_dates'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    reason = db.Column(db.String(150), default='Owner Blocked', nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('property_id', 'date', name='uq_property_blocked_date'),
    )
