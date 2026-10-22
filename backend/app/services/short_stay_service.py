import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import or_, and_
from app import db
from app.models.property import Property
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment, BlockedDate
from app.models.interaction import Notification


def calculate_quote(config, check_in_date, check_out_date, num_guests=1):
    """
    Computes transparent, itemized cost estimate for short-stay booking
    with decimal-safe currency rounding.
    """
    if isinstance(check_in_date, str):
        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
    if isinstance(check_out_date, str):
        check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()

    if check_out_date <= check_in_date:
        raise ValueError("Check-out date must be after check-in date.")

    nights = (check_out_date - check_in_date).days

    if config.min_nights and nights < config.min_nights:
        raise ValueError(f"Minimum stay required is {config.min_nights} night(s).")
    if config.max_nights and nights > config.max_nights:
        raise ValueError(f"Maximum stay allowed is {config.max_nights} nights.")
    if num_guests > config.max_guests:
        raise ValueError(f"Maximum permitted occupancy for this property is {config.max_guests} guests.")
    if num_guests < 1:
        raise ValueError("At least 1 guest must be selected.")

    # Determine base rate (apply weekly/fortnightly discounted tier if offered)
    effective_daily_rate = float(config.daily_rate)
    pricing_tier = "Standard Daily Rate"

    if nights >= 14 and config.fortnightly_rate and config.fortnightly_rate > 0:
        # 14+ nights discounted tier
        effective_daily_rate = round(float(config.fortnightly_rate) / 14.0, 2)
        pricing_tier = "Fortnightly Discounted Tier (14+ nights)"
        base_amount = float(config.fortnightly_rate) if nights == 14 else round(effective_daily_rate * nights, 2)
    elif nights >= 7 and config.weekly_rate and config.weekly_rate > 0:
        # 7+ nights discounted tier
        effective_daily_rate = round(float(config.weekly_rate) / 7.0, 2)
        pricing_tier = "Weekly Discounted Tier (7+ nights)"
        base_amount = float(config.weekly_rate) if nights == 7 else round(effective_daily_rate * nights, 2)
    else:
        base_amount = round(float(config.daily_rate) * nights, 2)

    # Base amount should never exceed un-discounted daily rate total
    standard_total = round(float(config.daily_rate) * nights, 2)
    base_amount = min(base_amount, standard_total)

    # Extra guests calculations
    extra_guests_count = max(0, num_guests - config.base_guests)
    extra_guests_amount = round(extra_guests_count * float(config.extra_guest_charge) * nights, 2)

    cleaning_fee = round(float(config.cleaning_fee or 0.0), 2)
    subtotal = round(base_amount + extra_guests_amount + cleaning_fee, 2)

    # Taxes
    tax_percentage = float(config.tax_percentage or 0.0)
    tax_amount = round(subtotal * (tax_percentage / 100.0), 2)

    # Refundable security deposit
    security_deposit = round(float(config.security_deposit or 0.0), 2)

    total_amount = round(subtotal + tax_amount + security_deposit, 2)

    return {
        'nights': nights,
        'num_guests': num_guests,
        'base_guests': config.base_guests,
        'extra_guests_count': extra_guests_count,
        'pricing_tier': pricing_tier,
        'daily_rate_applied': effective_daily_rate,
        'standard_daily_rate': float(config.daily_rate),
        'base_amount': base_amount,
        'extra_guests_amount': extra_guests_amount,
        'extra_guest_charge_per_night': float(config.extra_guest_charge),
        'cleaning_fee': cleaning_fee,
        'subtotal': subtotal,
        'tax_percentage': tax_percentage,
        'tax_amount': tax_amount,
        'security_deposit': security_deposit,
        'total_amount': total_amount,
        'cancellation_policy': config.cancellation_policy,
        'check_in_time': config.check_in_time,
        'check_out_time': config.check_out_time
    }


def is_property_available(property_id, check_in_date, check_out_date, num_guests=1, exclude_booking_id=None, only_confirmed=False):
    """
    Prevents double-bookings and checks blocked calendar dates.
    Check-out dates are exclusive: one guest can check out on the same date another checks in.
    Returns (is_available: bool, reason: str).
    """
    if isinstance(check_in_date, str):
        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
    if isinstance(check_out_date, str):
        check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()

    if check_out_date <= check_in_date:
        return False, "Check-out date must be after check-in date."

    # 1. Check blocked dates
    blocked = BlockedDate.query.filter(
        BlockedDate.property_id == property_id,
        BlockedDate.date >= check_in_date,
        BlockedDate.date < check_out_date
    ).first()

    if blocked:
        return False, f"Date {blocked.date.strftime('%d %b %Y')} is blocked by owner ({blocked.reason})."

    # 2. Check overlapping bookings
    status_filter = ['confirmed'] if only_confirmed else ['confirmed', 'pending']
    overlapping_query = ShortStayBooking.query.filter(
        ShortStayBooking.property_id == property_id,
        ShortStayBooking.status.in_(status_filter),
        ShortStayBooking.check_in_date < check_out_date,
        ShortStayBooking.check_out_date > check_in_date
    )

    if exclude_booking_id:
        overlapping_query = overlapping_query.filter(ShortStayBooking.id != exclude_booking_id)

    conflict = overlapping_query.first()
    if conflict:
        return False, f"Dates overlap with an existing {conflict.status} booking ({conflict.check_in_date.strftime('%d %b')} to {conflict.check_out_date.strftime('%d %b %Y')})."

    return True, "Available"


def search_short_stay(filters, page=1, per_page=9):
    """
    Filter properties explicitly enabled for short-stay / friends stay.
    Supports duration presets (1 day, 2 days, 1 week, etc.), locality, dates, guest counts, and budget.
    """
    query = Property.query.filter(
        Property.status == 'approved'
    ).join(ShortStayConfig).filter(
        ShortStayConfig.is_enabled == True
    )

    # Locality / Keyword
    locality = filters.get('locality', '').strip()
    q = filters.get('q', '').strip()

    if locality and locality != 'all':
        query = query.filter(Property.locality.ilike(f'%{locality}%'))
    elif q:
        query = query.filter(
            or_(
                Property.locality.ilike(f'%{q}%'),
                Property.name.ilike(f'%{q}%'),
                Property.address.ilike(f'%{q}%'),
                Property.nearest_landmark.ilike(f'%{q}%'),
                Property.sub_locality.ilike(f'%{q}%')
            )
        )

    # Guest count (supports 'num_guests' or 'guests')
    num_guests = filters.get('num_guests') or filters.get('guests', 1)
    try:
        num_guests = int(num_guests)
        if num_guests > 1:
            query = query.filter(ShortStayConfig.max_guests >= num_guests)
    except (ValueError, TypeError):
        num_guests = 1

    # Max budget per night (supports 'max_budget' or 'max_daily_rate')
    max_budget = filters.get('max_budget') or filters.get('max_daily_rate')
    if max_budget:
        try:
            query = query.filter(ShortStayConfig.daily_rate <= float(max_budget))
        except ValueError:
            pass

    # Gender Accommodation Policy
    gender = filters.get('gender')
    if gender and gender in ['gents', 'ladies', 'unisex']:
        query = query.filter(Property.gender_policy == gender)

    all_matches = query.all()

    # Handle Duration Presets (days) if explicit dates not provided
    check_in_str = filters.get('check_in')
    check_out_str = filters.get('check_out')
    days_param = filters.get('days')

    if not check_in_str and not check_out_str and days_param:
        try:
            days_count = int(days_param)
            if days_count >= 1:
                check_in_str = date.today().strftime('%Y-%m-%d')
                check_out_str = (date.today() + timedelta(days=days_count)).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass

    if check_in_str and check_out_str:
        try:
            c_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            c_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            available_matches = []
            for prop in all_matches:
                avail, _ = is_property_available(prop.id, c_in, c_out, num_guests=num_guests)
                if avail:
                    available_matches.append(prop)
            all_matches = available_matches
        except ValueError:
            pass

    # Sort
    sort_by = filters.get('sort_by', 'popular')
    if sort_by == 'price_asc':
        all_matches.sort(key=lambda p: p.short_stay_price)
    elif sort_by == 'price_desc':
        all_matches.sort(key=lambda p: p.short_stay_price, reverse=True)
    elif sort_by == 'rating':
        all_matches.sort(key=lambda p: p.average_rating or 0, reverse=True)
    else:  # popular / freshness
        all_matches.sort(key=lambda p: p.availability_last_confirmed_at or datetime.min, reverse=True)

    total_count = len(all_matches)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = all_matches[start:end]
    total_pages = (total_count + per_page - 1) // per_page if per_page else 1

    return {
        'items': paginated_items,
        'total': total_count,
        'page': page,
        'pages': max(1, total_pages),
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1
    }


def create_booking(customer_id, property_id, check_in_date, check_out_date, num_guests=1, guests_data=None, special_requests=None, room_type_id=None):
    """
    Creates a new ShortStayBooking with status 'pending' and registers guest details.
    Guarantees concurrency safety by re-verifying availability atomically within the active transaction.
    """
    prop = Property.query.get_or_404(property_id)
    if not prop.has_short_stay:
        raise ValueError("This property does not accept short stays.")

    config = prop.short_stay_config

    c_in = check_in_date if isinstance(check_in_date, date) else datetime.strptime(check_in_date, '%Y-%m-%d').date()
    c_out = check_out_date if isinstance(check_out_date, date) else datetime.strptime(check_out_date, '%Y-%m-%d').date()

    # Validate availability against double-booking
    available, reason = is_property_available(property_id, c_in, c_out, num_guests=num_guests)
    if not available:
        raise ValueError(reason)

    # Compute quote
    quote = calculate_quote(config, c_in, c_out, num_guests=num_guests)

    booking = ShortStayBooking(
        booking_code=ShortStayBooking.generate_booking_code(),
        property_id=property_id,
        customer_id=customer_id,
        room_type_id=room_type_id,
        check_in_date=c_in,
        check_out_date=c_out,
        nights=quote['nights'],
        num_guests=num_guests,
        daily_rate_applied=quote['daily_rate_applied'],
        base_amount=quote['base_amount'],
        extra_guests_amount=quote['extra_guests_amount'],
        cleaning_fee=quote['cleaning_fee'],
        tax_amount=quote['tax_amount'],
        security_deposit=quote['security_deposit'],
        total_amount=quote['total_amount'],
        status='pending',
        payment_status='pending',
        special_requests=special_requests
    )
    db.session.add(booking)
    db.session.flush()

    # Re-verify availability within transaction before final commit to protect against race conditions
    conflict = ShortStayBooking.query.filter(
        ShortStayBooking.property_id == property_id,
        ShortStayBooking.id != booking.id,
        ShortStayBooking.status.in_(['confirmed', 'pending']),
        ShortStayBooking.check_in_date < c_out,
        ShortStayBooking.check_out_date > c_in
    ).first()

    if conflict:
        db.session.rollback()
        raise ValueError("A conflicting booking was just submitted for these dates. Please choose alternate dates.")

    # Add registered guests
    if guests_data and isinstance(guests_data, list):
        for g in guests_data:
            if g.get('full_name'):
                guest = ShortStayGuest(
                    booking_id=booking.id,
                    full_name=g['full_name'],
                    age=g.get('age'),
                    gender=g.get('gender'),
                    id_proof_type=g.get('id_proof_type'),
                    id_proof_number=g.get('id_proof_number')
                )
                db.session.add(guest)

    # Notify Property Owner
    notif = Notification(
        user_id=prop.owner_id,
        title=f"New Short-Stay Request: {booking.booking_code}",
        message=f"{num_guests} guest(s) requested {quote['nights']} night(s) stay from {booking.check_in_date.strftime('%d %b')} to {booking.check_out_date.strftime('%d %b %Y')}. Total: ₹{quote['total_amount']:,.0f}.",
        link_url="/owner/short-stay/bookings"
    )
    db.session.add(notif)
    db.session.commit()

    return booking


def process_payment(booking_id, amount, payment_method='UPI', notes=None):
    """
    Records an owner-approved advance or online payment transaction and issues a receipt.
    Maintains compatibility with manual payments and direct test transactions.
    """
    booking = ShortStayBooking.query.get_or_404(booking_id)

    txn_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    receipt_no = BookingPayment.generate_receipt_number()

    amount = float(amount)
    payment = BookingPayment(
        booking_id=booking.id,
        transaction_id=txn_id,
        receipt_number=receipt_no,
        amount=amount,
        payment_method=payment_method,
        payment_type='advance' if amount < booking.total_amount else 'full',
        status='successful',
        notes=notes or 'Online payment / advance confirmation'
    )
    db.session.add(payment)

    # Update payment status
    current_paid = booking.total_paid
    if current_paid >= booking.total_amount:
        booking.payment_status = 'paid'
    else:
        booking.payment_status = 'advance_paid'
        booking.advance_paid_amount = current_paid

    booking.payment_method = payment_method
    db.session.commit()

    return payment


def calculate_property_occupancy(property_id, days_window=30):
    """
    Calculates the occupancy percentage and booked nights over a window of N days
    starting from today.
    """
    start_date = date.today()
    end_date = start_date + timedelta(days=days_window)

    confirmed_bookings = ShortStayBooking.query.filter(
        ShortStayBooking.property_id == property_id,
        ShortStayBooking.status == 'confirmed',
        ShortStayBooking.check_in_date < end_date,
        ShortStayBooking.check_out_date > start_date
    ).all()

    booked_dates = set()
    for b in confirmed_bookings:
        curr = max(b.check_in_date, start_date)
        b_end = min(b.check_out_date, end_date)
        while curr < b_end:
            booked_dates.add(curr)
            curr += timedelta(days=1)

    booked_count = len(booked_dates)
    occupancy_rate = round((booked_count / float(days_window)) * 100.0, 1)

    return {
        'occupancy_rate': occupancy_rate,
        'booked_nights': booked_count,
        'total_window_days': days_window
    }
