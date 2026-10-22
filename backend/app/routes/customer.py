import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import current_user, login_required
from app import db
from app.models.property import Property, Amenity, PropertyAmenity, PropertyMedia
from app.models.room import RoomType
from app.models.food import FoodMenu
from app.models.interaction import Enquiry, VisitRequest, Favourite, Review, Complaint, Notification
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment, BlockedDate
from app.services.search_service import search_properties
from app.services.short_stay_service import search_short_stay, calculate_quote, is_property_available, create_booking, process_payment
from app.services.receipt_service import generate_booking_receipt_pdf
from app.services.payment_service import (
    create_payment_order, record_verified_payment, verify_payment_signature,
    process_booking_refund, get_razorpay_keys, generate_sandbox_signature
)
from app.services.freshness import get_freshness_status
from app.forms.interaction_forms import EnquiryForm, VisitRequestForm, ReviewForm, ComplaintForm
from app.forms.short_stay_forms import ShortStayBookingForm, PaymentConfirmationForm
from app.models.roommate import RoommateProfile, RoommateInterest, RoommateRequest, UserBlock, UserReport
from app.models.community import PGResident, PGCommunityPost, PGCommunityComment, PGCommunityReport
from app.services.roommate_service import (
    calculate_compatibility_score, get_recommended_roommates, record_roommate_interest,
    send_roommate_request, respond_roommate_request, block_user, report_user
)
from app.services.community_service import (
    is_user_authorized_for_community, get_user_communities, get_pg_posts,
    create_pg_post, add_post_comment, delete_pg_post, report_pg_post
)
from app.forms.roommate_forms import (
    RoommateProfileForm, RoommateRequestForm, CommunityPostForm,
    CommunityCommentForm, SafetyReportForm
)

customer_bp = Blueprint('customer', __name__)

POPULAR_LOCALITIES = [
    {'name': 'Koramangala', 'tag': 'Startup Hub', 'icon': 'bi-building'},
    {'name': 'HSR Layout', 'tag': 'Tree-lined & Calm', 'icon': 'bi-tree'},
    {'name': 'Indiranagar', 'tag': 'Nightlife & Metro', 'icon': 'bi-cup-hot'},
    {'name': 'Whitefield', 'tag': 'ITPL & Tech Parks', 'icon': 'bi-laptop'},
    {'name': 'Electronic City', 'tag': 'Infosys & Wipro', 'icon': 'bi-cpu'},
    {'name': 'BTM Layout', 'tag': 'Budget & Students', 'icon': 'bi-wallet2'},
    {'name': 'Marathahalli', 'tag': 'Outer Ring Road', 'icon': 'bi-compass'},
    {'name': 'Bellandur', 'tag': 'EcoSpace Hub', 'icon': 'bi-briefcase'},
]


@customer_bp.route('/')
def index():
    if not current_user.is_authenticated and not request.args.get('explore') and not session.get('guest_browsing'):
        return redirect(url_for('auth.login'))
    if request.args.get('explore'):
        session['guest_browsing'] = True

    # Fetch featured and recently confirmed properties
    featured_properties = Property.query.filter_by(status='approved', is_featured=True).limit(6).all()
    if not featured_properties:
        featured_properties = Property.query.filter_by(status='approved').order_by(Property.created_at.desc()).limit(6).all()

    recently_confirmed = Property.query.filter_by(status='approved')\
        .order_by(Property.availability_last_confirmed_at.desc())\
        .limit(6).all()

    # Locality count map
    locality_counts = {}
    for loc in POPULAR_LOCALITIES:
        count = Property.query.filter(Property.status == 'approved', Property.locality.ilike(f"%{loc['name']}%")).count()
        locality_counts[loc['name']] = count

    # Fetch Short-Stay / Friends Stay properties
    short_stay_properties = Property.query.filter(
        Property.status == 'approved',
        Property.short_stay_config.has(ShortStayConfig.is_enabled == True)
    ).limit(6).all()

    return render_template(
        'index.html',
        featured_properties=featured_properties,
        recently_confirmed=recently_confirmed,
        short_stay_properties=short_stay_properties,
        popular_localities=POPULAR_LOCALITIES,
        locality_counts=locality_counts
    )


@customer_bp.route('/search')
def search():
    page = request.args.get('page', 1, type=int)
    results = search_properties(request.args, page=page, per_page=9)
    all_amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()

    return render_template(
        'search.html',
        properties=results['items'],
        pagination=results,
        filters=request.args,
        popular_localities=POPULAR_LOCALITIES,
        all_amenities=all_amenities
    )


@customer_bp.route('/property/<slug>')
def property_detail(slug):
    property_obj = Property.query.filter_by(slug=slug).first_or_404()

    # Only show approved properties to non-owners/non-admins
    if property_obj.status != 'approved':
        if not (current_user.is_authenticated and (current_user.is_admin or (current_user.is_owner and property_obj.owner_id == current_user.id))):
            flash("This property listing is currently undergoing review.", "warning")
            return redirect(url_for('customer.index'))

    # Increment view count
    property_obj.views_count = (property_obj.views_count or 0) + 1
    db.session.commit()

    # Prepare enquiry & visit forms
    enquiry_form = EnquiryForm()
    # Populate room choices
    enquiry_form.room_type_id.choices = [(0, 'Any Available Room')] + [
        (rt.id, f"{rt.sharing_label} - ₹{rt.monthly_rent:,.0f}/mo ({rt.vacant_beds} beds left)")
        for rt in property_obj.room_types
    ]

    visit_form = VisitRequestForm()
    review_form = ReviewForm()
    complaint_form = ComplaintForm()

    # Check if favourite
    is_favourite = False
    if current_user.is_authenticated:
        is_favourite = Favourite.query.filter_by(user_id=current_user.id, property_id=property_obj.id).first() is not None

    short_stay_booking_form = ShortStayBookingForm()
    short_stay_booking_form.room_type_id.choices = [(0, 'Standard Short Stay Room')] + [
        (rt.id, f"{rt.sharing_label} - {rt.title}")
        for rt in property_obj.room_types
    ]

    freshness = get_freshness_status(property_obj)
    approved_reviews = Review.query.filter_by(property_id=property_obj.id, status='approved').order_by(Review.created_at.desc()).all()

    return render_template(
        'property_detail.html',
        property=property_obj,
        enquiry_form=enquiry_form,
        visit_form=visit_form,
        review_form=review_form,
        complaint_form=complaint_form,
        short_stay_booking_form=short_stay_booking_form,
        is_favourite=is_favourite,
        freshness=freshness,
        approved_reviews=approved_reviews
    )


@customer_bp.route('/compare')
def compare():
    raw_ids = request.args.get('ids', '')
    property_ids = []
    if raw_ids:
        for x in raw_ids.split(','):
            if x.strip().isdigit():
                property_ids.append(int(x.strip()))

    properties = []
    if property_ids:
        properties = Property.query.filter(Property.id.in_(property_ids[:4]), Property.status == 'approved').all()

    return render_template('compare.html', properties=properties)


@customer_bp.route('/map')
def map_view():
    properties = Property.query.filter_by(status='approved').all()
    property_pins = []
    for p in properties:
        property_pins.append({
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'locality': p.locality,
            'lat': p.latitude,
            'lng': p.longitude,
            'price': p.starting_price,
            'gender': p.gender_policy.capitalize(),
            'vacant_beds': p.total_vacant_beds,
            'cover_image': p.cover_image,
            'url': url_for('customer.property_detail', slug=p.slug)
        })

    return render_template('map_view.html', property_pins=property_pins)


@customer_bp.route('/property/<int:property_id>/enquiry', methods=['POST'])
@login_required
def submit_enquiry(property_id):
    property_obj = Property.query.get_or_404(property_id)
    form = EnquiryForm()
    form.room_type_id.choices = [(0, 'Any Available Room')] + [(rt.id, rt.title) for rt in property_obj.room_types]

    if form.validate_on_submit():
        selected_rt_id = form.room_type_id.data if form.room_type_id.data != 0 else None
        enquiry = Enquiry(
            customer_id=current_user.id,
            property_id=property_obj.id,
            room_type_id=selected_rt_id,
            move_in_date=form.move_in_date.data,
            budget_max=form.budget_max.data,
            message=form.message.data,
            status='new'
        )
        db.session.add(enquiry)

        # Notify Owner
        notification = Notification(
            user_id=property_obj.owner_id,
            title=f"New Enquiry for {property_obj.name}",
            message=f"{current_user.name} sent an enquiry for move-in on {form.move_in_date.data.strftime('%d %b %Y')}.",
            link_url=url_for('owner.manage_enquiries')
        )
        db.session.add(notification)
        db.session.commit()

        flash("Your enquiry has been delivered directly to the PG owner. They will contact you shortly!", "success")
        return redirect(url_for('customer.property_detail', slug=property_obj.slug))

    flash("Please check the enquiry form fields.", "danger")
    return redirect(url_for('customer.property_detail', slug=property_obj.slug))


@customer_bp.route('/property/<int:property_id>/visit', methods=['POST'])
@login_required
def schedule_visit(property_id):
    property_obj = Property.query.get_or_404(property_id)
    form = VisitRequestForm()

    if form.validate_on_submit():
        visit = VisitRequest(
            customer_id=current_user.id,
            property_id=property_obj.id,
            preferred_date=form.preferred_date.data,
            preferred_time_slot=form.preferred_time_slot.data,
            alternate_date=form.alternate_date.data,
            status='requested'
        )
        db.session.add(visit)

        # Notify Owner
        notification = Notification(
            user_id=property_obj.owner_id,
            title=f"New Visit Request for {property_obj.name}",
            message=f"{current_user.name} requested a PG visit on {form.preferred_date.data.strftime('%d %b %Y')} ({form.preferred_time_slot.data}).",
            link_url=url_for('owner.manage_visits')
        )
        db.session.add(notification)
        db.session.commit()

        flash("Visit request sent! The owner will confirm or contact you with timing.", "success")
        return redirect(url_for('customer.property_detail', slug=property_obj.slug))

    flash("Please correct the visit request form.", "danger")
    return redirect(url_for('customer.property_detail', slug=property_obj.slug))


@customer_bp.route('/property/<int:property_id>/review', methods=['POST'])
@login_required
def submit_review(property_id):
    property_obj = Property.query.get_or_404(property_id)
    form = ReviewForm()

    if form.validate_on_submit():
        # Prevent spamming multiple reviews
        existing = Review.query.filter_by(user_id=current_user.id, property_id=property_obj.id).first()
        if existing:
            flash("You have already submitted a review for this PG.", "info")
            return redirect(url_for('customer.property_detail', slug=property_obj.slug))

        review = Review(
            user_id=current_user.id,
            property_id=property_obj.id,
            rating=int(form.rating.data),
            cleanliness_rating=int(form.cleanliness_rating.data),
            food_rating=int(form.food_rating.data),
            amenities_rating=int(form.amenities_rating.data),
            stay_duration=form.stay_duration.data,
            review_text=form.review_text.data,
            status='pending'  # Moderated by Admin to prevent fake reviews
        )
        db.session.add(review)
        db.session.commit()

        flash("Thank you for your feedback! Your review will be visible once verified by our moderation team.", "success")
        return redirect(url_for('customer.property_detail', slug=property_obj.slug))

    flash("Unable to submit review. Please ensure text is at least 20 characters.", "danger")
    return redirect(url_for('customer.property_detail', slug=property_obj.slug))


@customer_bp.route('/property/<int:property_id>/report', methods=['POST'])
@login_required
def submit_complaint(property_id):
    property_obj = Property.query.get_or_404(property_id)
    form = ComplaintForm()

    if form.validate_on_submit():
        complaint = Complaint(
            reporter_id=current_user.id,
            property_id=property_obj.id,
            category=form.category.data,
            description=form.description.data,
            status='open'
        )
        db.session.add(complaint)
        db.session.commit()

        flash("Report submitted. Our moderation team will investigate this listing immediately.", "warning")
        return redirect(url_for('customer.property_detail', slug=property_obj.slug))

    flash("Please provide details for the report.", "danger")
    return redirect(url_for('customer.property_detail', slug=property_obj.slug))


@customer_bp.route('/favourite/toggle/<int:property_id>', methods=['POST', 'GET'])
@login_required
def toggle_favourite(property_id):
    property_obj = Property.query.get_or_404(property_id)
    fav = Favourite.query.filter_by(user_id=current_user.id, property_id=property_id).first()
    
    if fav:
        db.session.delete(fav)
        db.session.commit()
        is_fav = False
        msg = f"Removed {property_obj.name} from saved favourites."
    else:
        new_fav = Favourite(user_id=current_user.id, property_id=property_id)
        db.session.add(new_fav)
        db.session.commit()
        is_fav = True
        msg = f"Added {property_obj.name} to saved favourites!"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'is_favourite': is_fav, 'message': msg})

    flash(msg, 'success')
    return redirect(request.referrer or url_for('customer.property_detail', slug=property_obj.slug))


@customer_bp.route('/short-stay')
def short_stay_search():
    page = request.args.get('page', 1, type=int)
    results = search_short_stay(request.args, page=page, per_page=9)
    all_amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()

    return render_template(
        'short_stay_search.html',
        properties=results['items'],
        pagination=results,
        filters=request.args,
        popular_localities=POPULAR_LOCALITIES,
        all_amenities=all_amenities
    )


@customer_bp.route('/short-stay/quote', methods=['GET'])
def short_stay_quote_api():
    property_id = request.args.get('property_id', type=int)
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    num_guests = request.args.get('num_guests', 1, type=int)

    if not property_id or not check_in or not check_out:
        return jsonify({'success': False, 'error': 'Missing required dates or property ID.'}), 400

    prop = Property.query.get(property_id)
    if not prop or not prop.has_short_stay:
        return jsonify({'success': False, 'error': 'Property not found or does not offer short stays.'}), 404

    # Check date availability
    available, reason = is_property_available(property_id, check_in, check_out, num_guests=num_guests)
    if not available:
        return jsonify({'success': False, 'available': False, 'error': reason})

    try:
        quote = calculate_quote(prop.short_stay_config, check_in, check_out, num_guests=num_guests)
        return jsonify({'success': True, 'available': True, 'quote': quote})
    except ValueError as e:
        return jsonify({'success': False, 'available': False, 'error': str(e)})


@customer_bp.route('/short-stay/book/<int:property_id>', methods=['POST'])
@login_required
def book_short_stay(property_id):
    prop = Property.query.get_or_404(property_id)
    if not prop.has_short_stay:
        flash("This property does not accept short stays.", "danger")
        return redirect(url_for('customer.property_detail', slug=prop.slug))

    form = ShortStayBookingForm()
    form.room_type_id.choices = [(0, 'Standard Short Stay Room')] + [(rt.id, rt.title) for rt in prop.room_types]

    if form.validate_on_submit():
        check_in = form.check_in_date.data
        check_out = form.check_out_date.data
        num_guests = form.num_guests.data
        room_type_id = form.room_type_id.data if form.room_type_id.data != 0 else None

        guests_data = [{
            'full_name': form.primary_guest_name.data.strip(),
            'id_proof_number': form.primary_guest_id_proof.data.strip() if form.primary_guest_id_proof.data else None
        }]

        try:
            booking = create_booking(
                customer_id=current_user.id,
                property_id=prop.id,
                check_in_date=check_in,
                check_out_date=check_out,
                num_guests=num_guests,
                guests_data=guests_data,
                special_requests=form.special_requests.data.strip() if form.special_requests.data else None,
                room_type_id=room_type_id
            )
            flash(f"Booking request {booking.booking_code} sent successfully! The PG owner will confirm shortly.", "success")
            return redirect(url_for('customer.short_stay_receipt', booking_code=booking.booking_code))
        except ValueError as e:
            flash(f"Unable to book: {str(e)}", "danger")
            return redirect(url_for('customer.property_detail', slug=prop.slug))

    flash("Please review the booking form fields and dates.", "danger")
    return redirect(url_for('customer.property_detail', slug=prop.slug))


@customer_bp.route('/short-stay/booking/<booking_code>')
@login_required
def short_stay_receipt(booking_code):
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    # Authorization: Customer who booked or property owner or admin
    if booking.customer_id != current_user.id and booking.property.owner_id != current_user.id and not current_user.is_admin:
        flash("You are not authorized to view this booking.", "danger")
        return redirect(url_for('customer.dashboard'))

    payment_form = PaymentConfirmationForm()
    key_id, _, is_sandbox = get_razorpay_keys()

    return render_template(
        'short_stay_receipt.html',
        booking=booking,
        payment_form=payment_form,
        razorpay_key_id=key_id,
        is_sandbox=is_sandbox
    )


@customer_bp.route('/short-stay/booking/<booking_code>/receipt/pdf')
@login_required
def download_short_stay_receipt_pdf(booking_code):
    """
    Downloads an official, beautifully styled PDF booking receipt and invoice.
    """
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    # Authorization check
    if booking.customer_id != current_user.id and booking.property.owner_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized access to booking receipt.", "danger")
        return redirect(url_for('customer.dashboard'))

    pdf_buffer = generate_booking_receipt_pdf(booking)
    filename = f"PG_Receipt_{booking.booking_code}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@customer_bp.route('/short-stay/booking/<booking_code>/payment/create-order', methods=['POST'])
@login_required
def create_short_stay_payment_order(booking_code):
    """
    Initializes a Razorpay payment order for the booking.
    """
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    if booking.customer_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json() or {}
    payment_type = payload.get('payment_type', 'full')
    custom_amount = payload.get('amount')

    if custom_amount:
        try:
            amount_in_rupees = float(custom_amount)
        except ValueError:
            amount_in_rupees = booking.total_amount
    else:
        amount_in_rupees = booking.advance_amount if payment_type == 'advance' else booking.total_amount

    order_data = create_payment_order(booking, amount_in_rupees=amount_in_rupees, payment_type=payment_type)
    return jsonify({'success': True, 'order': order_data})


@customer_bp.route('/short-stay/booking/<booking_code>/payment/verify', methods=['POST'])
@login_required
def verify_short_stay_payment(booking_code):
    """
    Verifies Razorpay payment signature and records the successful transaction.
    """
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    if booking.customer_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json() or {}
    order_id = payload.get('razorpay_order_id')
    payment_id = payload.get('razorpay_payment_id')
    signature = payload.get('razorpay_signature')
    amount = payload.get('amount')
    payment_method = payload.get('payment_method', 'Razorpay/UPI')
    payment_type = payload.get('payment_type', 'full')

    if not order_id or not payment_id or not signature:
        return jsonify({'success': False, 'error': 'Missing required payment verification tokens'}), 400

    try:
        payment = record_verified_payment(
            booking_id=booking.id,
            gateway_order_id=order_id,
            gateway_payment_id=payment_id,
            gateway_signature=signature,
            amount=amount or booking.total_amount,
            payment_method=payment_method,
            payment_type=payment_type,
            verify_signature=True
        )
        return jsonify({
            'success': True,
            'message': 'Payment verified successfully',
            'receipt_number': payment.receipt_number,
            'payment_status': booking.payment_status
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@customer_bp.route('/short-stay/booking/<booking_code>/pay', methods=['POST'])
@login_required
def pay_short_stay(booking_code):
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    # Authorization
    if booking.customer_id != current_user.id and booking.property.owner_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized payment action.", "danger")
        return redirect(url_for('customer.dashboard'))

    form = PaymentConfirmationForm()
    if form.validate_on_submit():
        amount = form.amount.data
        payment_method = form.payment_method.data
        notes = form.notes.data

        # Generate sandbox gateway credentials and signature
        order_info = create_payment_order(booking, amount_in_rupees=amount)
        gateway_order_id = order_info['order_id']
        gateway_payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        gateway_sig = generate_sandbox_signature(gateway_order_id, gateway_payment_id)

        payment = record_verified_payment(
            booking_id=booking.id,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
            gateway_signature=gateway_sig,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            payment_type='advance' if float(amount) < booking.total_amount else 'full',
            verify_signature=True
        )

        flash(f"Payment of ₹{payment.amount:,.0f} verified via {payment.payment_method}! Official receipt #{payment.receipt_number} issued.", "success")
        return redirect(url_for('customer.short_stay_receipt', booking_code=booking.booking_code))

    flash("Invalid payment details.", "danger")
    return redirect(url_for('customer.short_stay_receipt', booking_code=booking.booking_code))


@customer_bp.route('/short-stay/booking/<booking_code>/cancel', methods=['POST'])
@login_required
def cancel_short_stay_booking(booking_code):
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first_or_404()

    if booking.customer_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for('customer.dashboard'))

    if booking.status in ['cancelled', 'completed', 'rejected']:
        flash(f"Booking is already {booking.status}.", "info")
        return redirect(url_for('customer.short_stay_receipt', booking_code=booking.booking_code))

    booking.status = 'cancelled'

    # Process refundable amounts
    refund_total = 0.0
    if booking.payment_status in ['paid', 'advance_paid']:
        refund_total = process_booking_refund(booking.id, reason="Cancelled according to property policy")

    # Notify Owner of cancellation
    notif = Notification(
        user_id=booking.property.owner_id,
        title=f"Booking Cancelled: {booking.booking_code}",
        message=f"{booking.customer.name} has cancelled their short-stay booking for {booking.check_in_date.strftime('%d %b')}. Refund processed: ₹{refund_total:,.0f}.",
        link_url=url_for('owner.manage_short_stay_bookings')
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Your booking has been cancelled successfully. Refund of ₹{refund_total:,.0f} recorded according to cancellation policy.", "info")
    return redirect(url_for('customer.short_stay_receipt', booking_code=booking.booking_code))


@customer_bp.route('/dashboard')
@login_required
def dashboard():
    my_enquiries = Enquiry.query.filter_by(customer_id=current_user.id).order_by(Enquiry.created_at.desc()).all()
    my_visits = VisitRequest.query.filter_by(customer_id=current_user.id).order_by(VisitRequest.created_at.desc()).all()
    my_favourites = Favourite.query.filter_by(user_id=current_user.id).order_by(Favourite.created_at.desc()).all()
    my_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    my_short_stays = ShortStayBooking.query.filter_by(customer_id=current_user.id).order_by(ShortStayBooking.created_at.desc()).all()
    
    # Roommates & Community integrations
    roommate_profile = current_user.roommate_profile
    pending_roommate_requests_count = RoommateRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).count()
    my_communities = get_user_communities(current_user)

    return render_template(
        'customer/dashboard.html',
        enquiries=my_enquiries,
        visits=my_visits,
        favourites=my_favourites,
        reviews=my_reviews,
        short_stays=my_short_stays,
        roommate_profile=roommate_profile,
        pending_roommate_requests_count=pending_roommate_requests_count,
        my_communities=my_communities
    )


# -------------------------------------------------------------------------
# SMART ROOMMATE MATCHING ROUTES
# -------------------------------------------------------------------------

@customer_bp.route('/roommates')
@login_required
def roommates():
    tab = request.args.get('tab', 'recommended')
    profile = current_user.roommate_profile

    # Recommendations
    recommendations = []
    if profile and profile.is_active:
        recommendations = get_recommended_roommates(current_user, limit=30)

    # Mutual Matches
    # A mutual match is when user liked candidate AND candidate liked user
    sent_likes = {i.target_user_id for i in RoommateInterest.query.filter_by(user_id=current_user.id, action='like').all()}
    received_likes = {i.user_id for i in RoommateInterest.query.filter_by(target_user_id=current_user.id, action='like').all()}
    mutual_user_ids = list(sent_likes.intersection(received_likes))
    mutual_matches = []
    if mutual_user_ids:
        profiles = RoommateProfile.query.filter(RoommateProfile.user_id.in_(mutual_user_ids)).all()
        for p in profiles:
            p_data = p.to_dict(viewer_user=current_user)
            if profile:
                score, breakdown = calculate_compatibility_score(profile, p)
                p_data['compatibility_score'] = score
                p_data['compatibility_breakdown'] = breakdown
            mutual_matches.append(p_data)

    # Requests
    received_requests = RoommateRequest.query.filter_by(receiver_id=current_user.id).order_by(RoommateRequest.created_at.desc()).all()
    sent_requests = RoommateRequest.query.filter_by(sender_id=current_user.id).order_by(RoommateRequest.created_at.desc()).all()

    # Form
    profile_form = RoommateProfileForm(obj=profile)
    request_form = RoommateRequestForm()
    report_form = SafetyReportForm()

    # Communities user has access to
    user_communities = get_user_communities(current_user)

    return render_template(
        'customer/roommates.html',
        tab=tab,
        profile=profile,
        recommendations=recommendations,
        mutual_matches=mutual_matches,
        received_requests=received_requests,
        sent_requests=sent_requests,
        profile_form=profile_form,
        request_form=request_form,
        report_form=report_form,
        user_communities=user_communities
    )


@customer_bp.route('/roommates/profile', methods=['GET', 'POST'])
@login_required
def manage_roommate_profile():
    profile = current_user.roommate_profile
    form = RoommateProfileForm(obj=profile) if request.method == 'GET' else RoommateProfileForm()

    if form.validate_on_submit():
        if not profile:
            profile = RoommateProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.preferred_location = form.preferred_location.data
        profile.budget_min = form.budget_min.data
        profile.budget_max = form.budget_max.data
        profile.occupation = form.occupation.data
        profile.preferred_room_type = form.preferred_room_type.data
        profile.cleanliness = form.cleanliness.data
        profile.food_preference = form.food_preference.data
        profile.sleep_schedule = form.sleep_schedule.data
        profile.smoking_preference = form.smoking_preference.data
        profile.move_in_date = form.move_in_date.data
        profile.bio = form.bio.data
        profile.is_active = form.is_active.data
        profile.looking_for_room = form.looking_for_room.data

        db.session.commit()
        flash('Roommate profile saved successfully! You are now discoverable.', 'success')
        return redirect(url_for('customer.roommates', tab='recommended'))

    return render_template('customer/roommates.html', tab='profile', profile=profile, profile_form=form)


@customer_bp.route('/roommates/profile/pause', methods=['POST'])
@login_required
def pause_roommate_profile():
    profile = current_user.roommate_profile
    if profile:
        profile.is_active = not profile.is_active
        db.session.commit()
        status_msg = "activated" if profile.is_active else "paused"
        flash(f'Your roommate profile is now {status_msg}.', 'info')
    return redirect(url_for('customer.roommates', tab='profile'))


@customer_bp.route('/roommates/profile/delete', methods=['POST'])
@login_required
def delete_roommate_profile():
    profile = current_user.roommate_profile
    if profile:
        db.session.delete(profile)
        db.session.commit()
        flash('Your roommate profile has been deleted.', 'info')
    return redirect(url_for('customer.roommates', tab='profile'))


@customer_bp.route('/roommates/interest', methods=['POST'])
@login_required
def roommate_interest():
    target_user_id = request.form.get('target_user_id', type=int) or (request.get_json() or {}).get('target_user_id')
    action = request.form.get('action') or (request.get_json() or {}).get('action')

    if not target_user_id or action not in ['like', 'skip']:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400
        flash('Invalid action.', 'danger')
        return redirect(url_for('customer.roommates'))

    result = record_roommate_interest(current_user.id, target_user_id, action)

    if request.is_json:
        return jsonify(result)

    if result.get('is_mutual_match'):
        flash("It's a Mutual Match! Contact details are now unlocked in your Mutual Matches tab.", "success")
    else:
        flash(result.get('message', 'Saved preference.'), 'info')

    return redirect(url_for('customer.roommates', tab='recommended'))


@customer_bp.route('/roommates/request', methods=['POST'])
@login_required
def send_roommate_request_route():
    receiver_id = request.form.get('receiver_id', type=int)
    property_id = request.form.get('property_id', type=int) or None
    room_type_id = request.form.get('room_type_id', type=int) or None
    proposed_split_rent = request.form.get('proposed_split_rent', type=float) or None
    message = request.form.get('message', '').strip()

    if not receiver_id:
        flash('Please select a valid roommate to send request to.', 'danger')
        return redirect(url_for('customer.roommates'))

    try:
        req = send_roommate_request(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            property_id=property_id,
            room_type_id=room_type_id,
            proposed_split_rent=proposed_split_rent,
            message=message
        )
        flash('Roommate request sent successfully!', 'success')
    except Exception as e:
        flash(str(e), 'warning')

    return redirect(url_for('customer.roommates', tab='requests'))


@customer_bp.route('/roommates/request/<int:request_id>/<action>', methods=['POST'])
@login_required
def respond_roommate_request_route(request_id, action):
    try:
        req = respond_roommate_request(request_id, current_user.id, action)
        if action == 'accept' and req.property_id:
            flash('Request accepted! Because this is for a shared PG room, the PG Owner has been notified to verify occupancy and approve.', 'success')
        elif action == 'accept':
            flash('Roommate request accepted! You can now coordinate together.', 'success')
        elif action == 'reject':
            flash('Request declined.', 'info')
        elif action == 'cancel':
            flash('Request cancelled.', 'info')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('customer.roommates', tab='requests'))


@customer_bp.route('/roommates/block/<int:user_id>', methods=['POST'])
@login_required
def block_user_route(user_id):
    reason = request.form.get('reason', 'Blocked by user')
    block_user(current_user.id, user_id, reason=reason)
    flash('User has been blocked. They can no longer see your profile or send you requests.', 'info')
    return redirect(url_for('customer.roommates'))


@customer_bp.route('/roommates/report/<int:user_id>', methods=['POST'])
@login_required
def report_user_route(user_id):
    reason = request.form.get('reason', 'inappropriate')
    details = request.form.get('details', '')
    report_user(current_user.id, user_id, reason=reason, details=details)
    flash('Report submitted for review. Thank you for keeping our community safe.', 'success')
    return redirect(url_for('customer.roommates'))


# -------------------------------------------------------------------------
# PG COMMUNITY ROUTES (PRIVATE TO VERIFIED RESIDENTS & OWNER)
# -------------------------------------------------------------------------

@customer_bp.route('/community/pg/<int:property_id>')
@login_required
def pg_community_board(property_id):
    property_obj = Property.query.get_or_404(property_id)
    if not is_user_authorized_for_community(current_user, property_id):
        flash('Private PG Community: Access is restricted to confirmed residents and the PG owner only.', 'danger')
        return redirect(url_for('customer.dashboard'))

    category = request.args.get('category')
    posts = get_pg_posts(property_id, post_type=category)

    post_form = CommunityPostForm()
    comment_form = CommunityCommentForm()
    report_form = SafetyReportForm()

    return render_template(
        'community/pg_board.html',
        property=property_obj,
        posts=posts,
        active_category=category,
        post_form=post_form,
        comment_form=comment_form,
        report_form=report_form
    )


@customer_bp.route('/community/pg/<int:property_id>/post', methods=['POST'])
@login_required
def create_community_post(property_id):
    property_obj = Property.query.get_or_404(property_id)
    if not is_user_authorized_for_community(current_user, property_id):
        flash('Unauthorized to post in this community.', 'danger')
        return redirect(url_for('customer.dashboard'))

    form = CommunityPostForm()
    if form.validate_on_submit():
        try:
            create_pg_post(
                property_id=property_id,
                user=current_user,
                title=form.title.data,
                content=form.content.data,
                post_type=form.post_type.data,
                is_pinned=form.is_pinned.data
            )
            flash('Post published to PG community board!', 'success')
        except Exception as e:
            flash(str(e), 'danger')
    else:
        flash('Please fill in valid post title and content.', 'warning')

    return redirect(url_for('customer.pg_community_board', property_id=property_id))


@customer_bp.route('/community/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_community_comment(post_id):
    post = PGCommunityPost.query.get_or_404(post_id)
    if not is_user_authorized_for_community(current_user, post.property_id):
        flash('Unauthorized to comment.', 'danger')
        return redirect(url_for('customer.dashboard'))

    form = CommunityCommentForm()
    if form.validate_on_submit():
        try:
            add_post_comment(post_id, current_user, form.content.data)
            flash('Comment added.', 'success')
        except Exception as e:
            flash(str(e), 'danger')
    else:
        flash('Comment cannot be empty.', 'warning')

    return redirect(url_for('customer.pg_community_board', property_id=post.property_id))


@customer_bp.route('/community/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_community_post_route(post_id):
    post = PGCommunityPost.query.get_or_404(post_id)
    property_id = post.property_id
    try:
        delete_pg_post(post_id, current_user)
        flash('Post removed.', 'info')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('customer.pg_community_board', property_id=property_id))


@customer_bp.route('/community/post/<int:post_id>/report', methods=['POST'])
@login_required
def report_community_post_route(post_id):
    post = PGCommunityPost.query.get_or_404(post_id)
    reason = request.form.get('reason', 'inappropriate')
    details = request.form.get('details', '')
    try:
        report_pg_post(post_id, current_user, reason=reason, details=details)
        flash('Post reported for moderation. Thank you for your feedback.', 'info')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('customer.pg_community_board', property_id=post.property_id))

