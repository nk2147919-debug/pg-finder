import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from app.models.property import Property, Amenity, PropertyAmenity, PropertyMedia
from app.models.room import RoomType
from app.models.food import FoodMenu
from app.models.gym import GymFacility, GymPhoto, GYM_EQUIPMENT_CHOICES, GYM_EQUIPMENT_LABELS
from app.models.interaction import Enquiry, VisitRequest, Notification
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment, BlockedDate
from app.routes.auth import owner_required
from app.forms.property_forms import PropertyForm, RoomTypeForm, FoodMenuForm
from app.forms.short_stay_forms import ShortStayConfigForm, BlockedDateForm
from app.forms.gym_forms import GymFacilityForm
from app.models.roommate import RoommateRequest, RoommateProfile
from app.models.community import PGResident, PGCommunityPost, PGCommunityComment
from app.services.roommate_service import owner_approve_shared_room, owner_reject_shared_room
from app.services.community_service import create_pg_post, delete_pg_post
from app.forms.roommate_forms import CommunityPostForm
from app.services.freshness import reconfirm_property_freshness
from app.services.short_stay_service import is_property_available, calculate_property_occupancy

owner_bp = Blueprint('owner', __name__)


def check_property_ownership(property_obj):
    """Enforce server-side property ownership."""
    if not property_obj or property_obj.owner_id != current_user.id:
        abort(403)


@owner_bp.route('/dashboard')
@login_required
@owner_required
def dashboard():
    my_properties = Property.query.filter_by(owner_id=current_user.id).all()
    property_ids = [p.id for p in my_properties]

    total_properties = len(my_properties)
    published_count = len([p for p in my_properties if p.status == 'approved'])
    pending_count = len([p for p in my_properties if p.status == 'pending_approval'])
    total_vacant_beds = sum(p.total_vacant_beds for p in my_properties)

    recent_enquiries = Enquiry.query.filter(Enquiry.property_id.in_(property_ids)).order_by(Enquiry.created_at.desc()).limit(5).all() if property_ids else []
    upcoming_visits = VisitRequest.query.filter(VisitRequest.property_id.in_(property_ids), VisitRequest.status.in_(['requested', 'accepted'])).order_by(VisitRequest.preferred_date.asc()).limit(5).all() if property_ids else []

    total_enquiries_count = Enquiry.query.filter(Enquiry.property_id.in_(property_ids)).count() if property_ids else 0
    total_views = sum(p.views_count or 0 for p in my_properties)
    gym_count = len([p for p in my_properties if p.has_gym])

    pending_shared_requests_count = RoommateRequest.query.filter(
        RoommateRequest.property_id.in_(property_ids),
        RoommateRequest.status == 'accepted'
    ).count() if property_ids else 0

    return render_template(
        'owner/dashboard.html',
        properties=my_properties,
        total_properties=total_properties,
        published_count=published_count,
        pending_count=pending_count,
        total_vacant_beds=total_vacant_beds,
        gym_count=gym_count,
        recent_enquiries=recent_enquiries,
        upcoming_visits=upcoming_visits,
        total_enquiries_count=total_enquiries_count,
        total_views=total_views,
        pending_shared_requests_count=pending_shared_requests_count
    )


@owner_bp.route('/properties')
@login_required
@owner_required
def properties():
    my_properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.created_at.desc()).all()
    return render_template('owner/properties.html', properties=my_properties)


@owner_bp.route('/property/new', methods=['GET', 'POST'])
@login_required
@owner_required
def add_property():
    form = PropertyForm()
    all_amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()

    if form.validate_on_submit():
        slug_candidate = Property.generate_slug(form.name.data, form.locality.data)
        # Ensure unique slug
        unique_slug = slug_candidate
        counter = 1
        while Property.query.filter_by(slug=unique_slug).first():
            unique_slug = f"{slug_candidate}-{counter}"
            counter += 1

        new_property = Property(
            owner_id=current_user.id,
            name=form.name.data.strip(),
            slug=unique_slug,
            locality=form.locality.data,
            sub_locality=form.sub_locality.data.strip() if form.sub_locality.data else None,
            address=form.address.data.strip(),
            pincode=form.pincode.data.strip(),
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            nearest_landmark=form.nearest_landmark.data.strip() if form.nearest_landmark.data else None,
            metro_distance_km=form.metro_distance_km.data,
            bus_distance_km=form.bus_distance_km.data,
            gender_policy=form.gender_policy.data,
            property_type=form.property_type.data,
            description=form.description.data.strip(),
            house_rules=form.house_rules.data.strip() if form.house_rules.data else None,
            gate_closing_time=form.gate_closing_time.data.strip(),
            notice_period_days=form.notice_period_days.data,
            minimum_stay_months=form.minimum_stay_months.data,
            deposit_months=form.deposit_months.data,
            maintenance_charges=form.maintenance_charges.data or 0.0,
            electricity_charges_type=form.electricity_charges_type.data,
            status='pending_approval'  # Requires Admin verification
        )
        db.session.add(new_property)
        db.session.flush()

        # Handle Amenities checkbox list from request.form
        selected_amenity_ids = request.form.getlist('amenities')
        for amen_id in selected_amenity_ids:
            if amen_id.isdigit():
                pa = PropertyAmenity(property_id=new_property.id, amenity_id=int(amen_id))
                db.session.add(pa)

        # Handle Cover Image Upload
        if form.cover_image.data:
            file = form.cover_image.data
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"pg_{new_property.id}_{uuid.uuid4().hex[:8]}.{ext}"
            upload_dir = current_app.config['UPLOAD_FOLDER'] / 'properties'
            upload_dir.mkdir(parents=True, exist_ok=True)
            file.save(upload_dir / filename)

            media = PropertyMedia(
                property_id=new_property.id,
                file_path=f"/static/uploads/properties/{filename}",
                caption="Main Property View",
                is_cover=True
            )
            db.session.add(media)

        # Initialize Default Food Menu for Property
        default_food = FoodMenu(
            property_id=new_property.id,
            food_type='both',
            meals_provided='Breakfast, Dinner on weekdays & 3 meals on weekends',
            food_included_in_rent=True
        )
        default_food.set_menu_dict(FoodMenu.get_default_menu())
        db.session.add(default_food)

        # Initialize Gym Facility
        gym = GymFacility(
            property_id=new_property.id,
            is_available=bool(form.has_inhouse_gym.data)
        )
        db.session.add(gym)

        db.session.commit()
        flash(f"Property '{new_property.name}' created! Now add your room sharing options and pricing.", "success")
        return redirect(url_for('owner.manage_rooms', property_id=new_property.id))

    return render_template('owner/property_form.html', form=form, all_amenities=all_amenities, is_edit=False)


@owner_bp.route('/property/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_property(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    form = PropertyForm(obj=property_obj)
    if request.method == 'GET':
        form.has_inhouse_gym.data = property_obj.has_gym

    all_amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()
    existing_amenity_ids = [pa.amenity_id for pa in property_obj.amenities]

    if form.validate_on_submit():
        form.populate_obj(property_obj)
        property_obj.price_last_confirmed_at = datetime.utcnow()

        # Update in-house gym status
        if not property_obj.gym_facility:
            property_obj.gym_facility = GymFacility(
                property_id=property_obj.id,
                is_available=bool(form.has_inhouse_gym.data)
            )
            db.session.add(property_obj.gym_facility)
        else:
            property_obj.gym_facility.is_available = bool(form.has_inhouse_gym.data)

        # Update amenities
        PropertyAmenity.query.filter_by(property_id=property_obj.id).delete()
        selected_amenity_ids = request.form.getlist('amenities')
        for amen_id in selected_amenity_ids:
            if amen_id.isdigit():
                pa = PropertyAmenity(property_id=property_obj.id, amenity_id=int(amen_id))
                db.session.add(pa)

        # Handle Cover Image if new one uploaded
        if form.cover_image.data:
            file = form.cover_image.data
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"pg_{property_obj.id}_{uuid.uuid4().hex[:8]}.{ext}"
            upload_dir = current_app.config['UPLOAD_FOLDER'] / 'properties'
            upload_dir.mkdir(parents=True, exist_ok=True)
            file.save(upload_dir / filename)

            # Unset old covers
            for m in property_obj.media:
                m.is_cover = False
            media = PropertyMedia(
                property_id=property_obj.id,
                file_path=f"/static/uploads/properties/{filename}",
                caption="Main Property View",
                is_cover=True
            )
            db.session.add(media)

        db.session.commit()
        flash("Property details updated successfully!", "success")
        return redirect(url_for('owner.properties'))

    return render_template(
        'owner/property_form.html',
        form=form,
        property=property_obj,
        all_amenities=all_amenities,
        existing_amenity_ids=existing_amenity_ids,
        is_edit=True
    )


@owner_bp.route('/property/<int:property_id>/rooms', methods=['GET', 'POST'])
@login_required
@owner_required
def manage_rooms(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    form = RoomTypeForm()
    if form.validate_on_submit():
        room = RoomType(
            property_id=property_obj.id,
            sharing_type=form.sharing_type.data,
            title=form.title.data.strip(),
            monthly_rent=form.monthly_rent.data,
            deposit_amount=form.deposit_amount.data,
            total_beds=form.total_beds.data,
            occupied_beds=form.occupied_beds.data if form.occupied_beds.data is not None else max(0, form.total_beds.data - form.vacant_beds.data),
            vacant_beds=form.vacant_beds.data,
            has_ac=form.has_ac.data,
            has_attached_bathroom=form.has_attached_bathroom.data,
            has_balcony=form.has_balcony.data,
            availability_date=form.availability_date.data
        )
        db.session.add(room)
        # Update freshness timestamps
        property_obj.availability_last_confirmed_at = datetime.utcnow()
        property_obj.price_last_confirmed_at = datetime.utcnow()
        db.session.commit()

        flash(f"Room option '{room.title}' added successfully!", "success")
        return redirect(url_for('owner.manage_rooms', property_id=property_obj.id))

    return render_template('owner/manage_rooms.html', property=property_obj, form=form)


@owner_bp.route('/property/<int:property_id>/room/<int:room_id>/delete', methods=['POST'])
@login_required
@owner_required
def delete_room(property_id, room_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    room = RoomType.query.filter_by(id=room_id, property_id=property_obj.id).first_or_404()
    db.session.delete(room)
    db.session.commit()
    flash("Room option deleted.", "info")
    return redirect(url_for('owner.manage_rooms', property_id=property_obj.id))


@owner_bp.route('/property/<int:property_id>/food', methods=['GET', 'POST'])
@login_required
@owner_required
def manage_food(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    food_menu = property_obj.food_menu
    if not food_menu:
        food_menu = FoodMenu(property_id=property_obj.id)
        food_menu.set_menu_dict(FoodMenu.get_default_menu())
        db.session.add(food_menu)
        db.session.commit()

    form = FoodMenuForm(obj=food_menu)

    if form.validate_on_submit():
        form.populate_obj(food_menu)
        
        # Read updated weekly items from form fields
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        updated_menu = {}
        for day in days:
            updated_menu[day] = {
                'breakfast': request.form.get(f'{day.lower()}_breakfast', ''),
                'lunch': request.form.get(f'{day.lower()}_lunch', ''),
                'dinner': request.form.get(f'{day.lower()}_dinner', '')
            }
        food_menu.set_menu_dict(updated_menu)
        food_menu.last_updated_at = datetime.utcnow()
        property_obj.menu_last_updated_at = datetime.utcnow()
        db.session.commit()

        flash("Food details and weekly menu schedule updated successfully!", "success")
        return redirect(url_for('owner.manage_food', property_id=property_obj.id))

    return render_template('owner/manage_food.html', property=property_obj, food_menu=food_menu, form=form)


@owner_bp.route('/property/<int:property_id>/reconfirm', methods=['POST'])
@login_required
@owner_required
def reconfirm_freshness(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    reconfirm_property_freshness(property_obj)
    flash(f"Availability & pricing for '{property_obj.name}' re-confirmed! Freshness badge updated to 'Confirmed Today'.", "success")
    return redirect(request.referrer or url_for('owner.properties'))


@owner_bp.route('/enquiries')
@login_required
@owner_required
def manage_enquiries():
    my_property_ids = [p.id for p in Property.query.filter_by(owner_id=current_user.id).all()]
    all_enquiries = Enquiry.query.filter(Enquiry.property_id.in_(my_property_ids)).order_by(Enquiry.created_at.desc()).all() if my_property_ids else []
    return render_template('owner/manage_enquiries.html', enquiries=all_enquiries)


@owner_bp.route('/enquiry/<int:enquiry_id>/status', methods=['POST'])
@login_required
@owner_required
def update_enquiry_status(enquiry_id):
    enquiry = Enquiry.query.get_or_404(enquiry_id)
    check_property_ownership(enquiry.property)

    new_status = request.form.get('status')
    if new_status in ['new', 'contacted', 'scheduled', 'closed']:
        enquiry.status = new_status
        enquiry.owner_notes = request.form.get('owner_notes', enquiry.owner_notes)
        db.session.commit()
        flash("Enquiry status updated.", "success")

    return redirect(url_for('owner.manage_enquiries'))


@owner_bp.route('/visits')
@login_required
@owner_required
def manage_visits():
    my_property_ids = [p.id for p in Property.query.filter_by(owner_id=current_user.id).all()]
    all_visits = VisitRequest.query.filter(VisitRequest.property_id.in_(my_property_ids)).order_by(VisitRequest.preferred_date.asc()).all() if my_property_ids else []
    return render_template('owner/manage_visits.html', visits=all_visits)


@owner_bp.route('/visit/<int:visit_id>/action', methods=['POST'])
@login_required
@owner_required
def action_visit_request(visit_id):
    visit = VisitRequest.query.get_or_404(visit_id)
    check_property_ownership(visit.property)

    action = request.form.get('action')
    owner_message = request.form.get('owner_message', '')

    if action == 'accept':
        visit.status = 'accepted'
        visit.owner_message = owner_message or "Your visit request has been accepted. Looking forward to meeting you!"
        msg_title = f"Visit Confirmed: {visit.property.name}"
    elif action == 'decline':
        visit.status = 'declined'
        visit.owner_message = owner_message or "Sorry, the requested time slot is unavailable."
        msg_title = f"Visit Declined: {visit.property.name}"
    elif action == 'reschedule':
        resched_date = request.form.get('rescheduled_date')
        resched_slot = request.form.get('rescheduled_time_slot')
        if resched_date:
            visit.status = 'rescheduled'
            visit.rescheduled_date = datetime.strptime(resched_date, '%Y-%m-%d').date()
            visit.rescheduled_time_slot = resched_slot
            visit.owner_message = owner_message or f"Rescheduled to {resched_date} ({resched_slot})"
            msg_title = f"Visit Rescheduled: {visit.property.name}"
    elif action == 'record_outcome':
        visit.visit_outcome = request.form.get('visit_outcome')
        visit.status = 'completed'
        db.session.commit()
        flash("Visit outcome recorded.", "success")
        return redirect(url_for('owner.manage_visits'))

    # Notify Customer of update
    notification = Notification(
        user_id=visit.customer_id,
        title=msg_title,
        message=visit.owner_message,
        link_url=url_for('customer.dashboard')
    )
    db.session.add(notification)
    db.session.commit()

    flash(f"Visit request updated to '{visit.status}'. Customer has been notified.", "success")
    return redirect(url_for('owner.manage_visits'))


@owner_bp.route('/analytics')
@login_required
@owner_required
def analytics():
    my_properties = Property.query.filter_by(owner_id=current_user.id).all()
    property_ids = [p.id for p in my_properties]

    enquiries_count = Enquiry.query.filter(Enquiry.property_id.in_(property_ids)).count() if property_ids else 0
    visits_count = VisitRequest.query.filter(VisitRequest.property_id.in_(property_ids)).count() if property_ids else 0
    total_views = sum(p.views_count or 0 for p in my_properties)

    conversion_rate = 0.0
    if total_views > 0:
        conversion_rate = round((enquiries_count / total_views) * 100, 2)

    return render_template(
        'owner/analytics.html',
        properties=my_properties,
        enquiries_count=enquiries_count,
        visits_count=visits_count,
        total_views=total_views,
        conversion_rate=conversion_rate
    )


@owner_bp.route('/property/<int:property_id>/short-stay', methods=['GET', 'POST'])
@login_required
@owner_required
def manage_short_stay(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    config = property_obj.short_stay_config
    if not config:
        config = ShortStayConfig(property_id=property_obj.id, is_enabled=False)
        db.session.add(config)
        db.session.commit()

    form = ShortStayConfigForm(obj=config)

    if form.validate_on_submit():
        form.populate_obj(config)
        config.updated_at = datetime.utcnow()
        property_obj.price_last_confirmed_at = datetime.utcnow()
        db.session.commit()

        status_str = "enabled" if config.is_enabled else "disabled"
        flash(f"Short-stay settings for '{property_obj.name}' updated! Short-stay bookings are currently {status_str}.", "success")
        return redirect(url_for('owner.manage_short_stay', property_id=property_obj.id))

    return render_template('owner/manage_short_stay.html', property=property_obj, config=config, form=form)


@owner_bp.route('/short-stay/bookings')
@login_required
@owner_required
def manage_short_stay_bookings():
    my_property_ids = [p.id for p in Property.query.filter_by(owner_id=current_user.id).all()]
    all_bookings = ShortStayBooking.query.filter(
        ShortStayBooking.property_id.in_(my_property_ids)
    ).order_by(ShortStayBooking.created_at.desc()).all() if my_property_ids else []

    pending_count = len([b for b in all_bookings if b.status == 'pending'])
    confirmed_count = len([b for b in all_bookings if b.status == 'confirmed'])
    total_earnings = sum(b.total_amount for b in all_bookings if b.payment_status in ['paid', 'advance_paid'])

    # Calculate overall occupancy metrics across owner's short stay properties
    total_booked_nights = 0
    total_available_nights = 0
    for pid in my_property_ids:
        occ = calculate_property_occupancy(pid, days_window=30)
        total_booked_nights += occ['booked_nights']
        total_available_nights += occ['total_window_days']

    overall_occupancy = round((total_booked_nights / float(total_available_nights)) * 100.0, 1) if total_available_nights else 0.0

    return render_template(
        'owner/short_stay_bookings.html',
        bookings=all_bookings,
        pending_count=pending_count,
        confirmed_count=confirmed_count,
        total_earnings=total_earnings,
        overall_occupancy=overall_occupancy,
        total_booked_nights=total_booked_nights
    )


@owner_bp.route('/short-stay/booking/<int:booking_id>/action', methods=['POST'])
@login_required
@owner_required
def action_short_stay_booking(booking_id):
    booking = ShortStayBooking.query.get_or_404(booking_id)
    check_property_ownership(booking.property)

    action = request.form.get('action')
    reason = request.form.get('rejection_reason', '')
    owner_notes = request.form.get('owner_notes', '')

    if action == 'confirm':
        # Re-check availability against confirmed bookings and owner blocked dates before confirming
        avail, reason_unavail = is_property_available(
            booking.property_id,
            booking.check_in_date,
            booking.check_out_date,
            exclude_booking_id=booking.id,
            only_confirmed=True
        )
        if not avail:
            flash(f"Cannot confirm: Property is already unavailable for those dates ({reason_unavail}).", "danger")
            return redirect(url_for('owner.manage_short_stay_bookings'))

        booking.status = 'confirmed'
        booking.owner_notes = owner_notes or "Booking confirmed by PG owner. Looking forward to hosting you!"
        msg_title = f"Short Stay Confirmed: {booking.booking_code}"
    elif action == 'reject':
        booking.status = 'rejected'
        booking.rejection_reason = reason or "Selected dates are not available."
        booking.owner_notes = owner_notes
        msg_title = f"Short Stay Update: {booking.booking_code}"
    elif action == 'complete':
        booking.status = 'completed'
        booking.owner_notes = owner_notes or "Stay completed successfully."
        msg_title = f"Stay Completed: {booking.booking_code}"
    elif action == 'mark_paid':
        booking.payment_status = 'paid'
        db.session.commit()
        flash("Marked as paid in full.", "success")
        return redirect(url_for('owner.manage_short_stay_bookings'))

    # Notify Customer
    notif = Notification(
        user_id=booking.customer_id,
        title=msg_title,
        message=f"Your booking at {booking.property.name} has been {booking.status}. Check details in dashboard.",
        link_url=url_for('customer.short_stay_receipt', booking_code=booking.booking_code)
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Booking {booking.booking_code} marked as {booking.status}. Customer has been notified.", "success")
    return redirect(url_for('owner.manage_short_stay_bookings'))


@owner_bp.route('/property/<int:property_id>/short-stay/calendar', methods=['GET', 'POST'])
@login_required
@owner_required
def manage_calendar(property_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    form = BlockedDateForm()
    if form.validate_on_submit():
        # Check if already blocked
        existing = BlockedDate.query.filter_by(property_id=property_obj.id, date=form.date.data).first()
        if not existing:
            blocked = BlockedDate(
                property_id=property_obj.id,
                date=form.date.data,
                reason=form.reason.data.strip() if form.reason.data else "Owner Blocked"
            )
            db.session.add(blocked)
            db.session.commit()
            flash(f"Date {form.date.data.strftime('%d %b %Y')} blocked successfully.", "success")
        else:
            flash("This date is already blocked.", "info")
        return redirect(url_for('owner.manage_calendar', property_id=property_obj.id))

    blocked_dates = BlockedDate.query.filter_by(property_id=property_obj.id).order_by(BlockedDate.date.asc()).all()
    active_bookings = ShortStayBooking.query.filter(
        ShortStayBooking.property_id == property_obj.id,
        ShortStayBooking.status.in_(['confirmed', 'pending'])
    ).order_by(ShortStayBooking.check_in_date.asc()).all()

    occupancy_data = calculate_property_occupancy(property_obj.id, days_window=30)

    return render_template(
        'owner/manage_calendar.html',
        property=property_obj,
        form=form,
        blocked_dates=blocked_dates,
        active_bookings=active_bookings,
        occupancy_data=occupancy_data
    )


@owner_bp.route('/property/<int:property_id>/short-stay/calendar/unblock/<int:date_id>', methods=['POST'])
@login_required
@owner_required
def unblock_date(property_id, date_id):
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    blocked = BlockedDate.query.filter_by(id=date_id, property_id=property_obj.id).first_or_404()
    db.session.delete(blocked)
    db.session.commit()
    flash(f"Date {blocked.date.strftime('%d %b %Y')} has been unblocked.", "info")
    return redirect(url_for('owner.manage_calendar', property_id=property_obj.id))


# =============================================================================
# GYM FACILITY MANAGEMENT
# =============================================================================

@owner_bp.route('/property/<int:property_id>/gym', methods=['GET', 'POST'])
@login_required
@owner_required
def manage_gym(property_id):
    """Owner page to add / edit gym facility details for a PG."""
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    gym = property_obj.gym_facility
    if not gym:
        gym = GymFacility(property_id=property_obj.id, is_available=False)
        db.session.add(gym)
        db.session.commit()

    form = GymFacilityForm(obj=gym)

    if form.validate_on_submit():
        # Scalar fields
        gym.is_available = form.is_available.data
        gym.access_type = form.access_type.data
        gym.monthly_fee = form.monthly_fee.data or 0.0
        gym.opening_time = form.opening_time.data.strip() if form.opening_time.data else '6:00 AM'
        gym.closing_time = form.closing_time.data.strip() if form.closing_time.data else '10:00 PM'
        gym.capacity = form.capacity.data
        gym.maintenance_schedule = form.maintenance_schedule.data.strip() if form.maintenance_schedule.data else None
        gym.description = form.description.data.strip() if form.description.data else None
        gym.usage_rules = form.usage_rules.data.strip() if form.usage_rules.data else None
        gym.is_temporarily_unavailable = form.is_temporarily_unavailable.data
        gym.unavailability_reason = form.unavailability_reason.data.strip() if form.unavailability_reason.data else None

        # Equipment list from checkboxes (not a WTForms field — read from request.form directly)
        selected_equipment = request.form.getlist('equipment')
        valid_equipment = [e for e in selected_equipment if e in GYM_EQUIPMENT_CHOICES]
        gym.equipment = valid_equipment

        # Photo uploads
        if form.photos.data:
            upload_dir = current_app.config['UPLOAD_FOLDER'] / 'gym'
            upload_dir.mkdir(parents=True, exist_ok=True)
            existing_count = len(gym.photos)
            for idx, photo_file in enumerate(form.photos.data):
                if photo_file and photo_file.filename:
                    # Max 6 gym photos
                    if existing_count + idx >= 6:
                        break
                    ext = photo_file.filename.rsplit('.', 1)[-1].lower() if '.' in photo_file.filename else 'jpg'
                    fname = f"gym_{property_obj.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    photo_file.save(upload_dir / fname)
                    gp = GymPhoto(
                        gym_id=gym.id,
                        file_path=f"/static/uploads/gym/{fname}",
                        caption=f"Gym Photo {existing_count + idx + 1}",
                        display_order=existing_count + idx
                    )
                    db.session.add(gp)

        db.session.commit()
        status_str = "enabled" if gym.is_available else "disabled"
        flash(f"Gym facility for '{property_obj.name}' updated! Status: {status_str}.", "success")
        return redirect(url_for('owner.manage_gym', property_id=property_obj.id))

    return render_template(
        'owner/manage_gym.html',
        property=property_obj,
        gym=gym,
        form=form,
        equipment_choices=GYM_EQUIPMENT_CHOICES,
        equipment_labels=GYM_EQUIPMENT_LABELS,
    )


@owner_bp.route('/property/<int:property_id>/gym/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
@owner_required
def delete_gym_photo(property_id, photo_id):
    """Delete a single gym photo."""
    property_obj = Property.query.get_or_404(property_id)
    check_property_ownership(property_obj)

    gym = property_obj.gym_facility
    if not gym:
        abort(404)

    photo = GymPhoto.query.filter_by(id=photo_id, gym_id=gym.id).first_or_404()
    db.session.delete(photo)
    db.session.commit()
    flash("Gym photo removed.", "info")
    return redirect(url_for('owner.manage_gym', property_id=property_obj.id))


# -------------------------------------------------------------------------
# SHARED ROOM & PG COMMUNITY OWNER MANAGEMENT
# -------------------------------------------------------------------------

@owner_bp.route('/shared-rooms')
@login_required
@owner_required
def manage_shared_rooms():
    """
    Review shared-room requests across owner's properties, verify room occupancy
    limits, approve or reject proposed arrangements.
    """
    my_properties = Property.query.filter_by(owner_id=current_user.id).all()
    prop_ids = [p.id for p in my_properties]

    status_filter = request.args.get('status')
    query = RoommateRequest.query.filter(RoommateRequest.property_id.in_(prop_ids))
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    shared_requests = query.order_by(RoommateRequest.created_at.desc()).all()

    # Calculate occupancy stats per property
    property_stats = []
    for p in my_properties:
        rooms_info = []
        for r in p.room_types:
            rooms_info.append({
                'room_type': r.sharing_type,
                'total_beds': r.total_beds,
                'vacant_beds': r.vacant_beds,
                'occupied_beds': (r.total_beds - r.vacant_beds) if r.total_beds else 0
            })
        property_stats.append({
            'property': p,
            'rooms': rooms_info,
            'total_vacant': p.total_vacant_beds,
            'active_residents_count': PGResident.query.filter_by(property_id=p.id, status='active').count()
        })

    announcement_form = CommunityPostForm()

    return render_template(
        'owner/manage_shared_rooms.html',
        properties=my_properties,
        property_stats=property_stats,
        shared_requests=shared_requests,
        status_filter=status_filter,
        announcement_form=announcement_form
    )


@owner_bp.route('/shared-room/<int:request_id>/<action>', methods=['POST'])
@login_required
@owner_required
def handle_shared_room_request(request_id, action):
    req = RoommateRequest.query.get_or_404(request_id)
    if not req.property or req.property.owner_id != current_user.id:
        abort(403)

    if action == 'approve':
        try:
            owner_approve_shared_room(request_id, current_user.id)
            flash(f'Shared room arrangement approved! Occupancy updated and residents registered.', 'success')
        except Exception as e:
            flash(f'Cannot approve: {str(e)}', 'danger')
    elif action == 'reject':
        reason = request.form.get('reason', 'Rejected by PG Owner after occupancy check.')
        try:
            owner_reject_shared_room(request_id, current_user.id, reason=reason)
            flash('Shared room arrangement rejected.', 'info')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    else:
        flash('Invalid action.', 'warning')

    return redirect(url_for('owner.manage_shared_rooms'))


@owner_bp.route('/property/<int:property_id>/community/announcement', methods=['POST'])
@login_required
@owner_required
def post_owner_announcement(property_id):
    prop = Property.query.get_or_404(property_id)
    check_property_ownership(prop)

    form = CommunityPostForm()
    if form.validate_on_submit():
        try:
            create_pg_post(
                property_id=prop.id,
                user=current_user,
                title=form.title.data,
                content=form.content.data,
                post_type='announcement',
                is_pinned=True
            )
            flash(f"Official announcement broadcast to '{prop.name}' community!", "success")
        except Exception as e:
            flash(f"Could not post announcement: {str(e)}", "danger")
    else:
        flash("Title and message are required for an announcement.", "warning")

    return redirect(url_for('owner.manage_shared_rooms'))


@owner_bp.route('/community/post/<int:post_id>/owner-delete', methods=['POST'])
@login_required
@owner_required
def owner_delete_community_post(post_id):
    post = PGCommunityPost.query.get_or_404(post_id)
    if not post.property or post.property.owner_id != current_user.id:
        abort(403)

    delete_pg_post(post_id, current_user)
    flash("Post removed by moderation.", "info")
    return redirect(url_for('customer.pg_community_board', property_id=post.property_id))

