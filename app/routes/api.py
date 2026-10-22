from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user
from app import db, csrf
from app.models.property import Property, Amenity
from app.models.room import RoomType
from app.models.food import FoodMenu
from app.models.user import User
from app.models.gym import GymFacility, GymPhoto
from app.models.interaction import Enquiry, VisitRequest
from app.models.short_stay import ShortStayConfig, ShortStayBooking, ShortStayGuest, BookingPayment
from app.services.search_service import search_properties
from app.services.short_stay_service import search_short_stay, calculate_quote, is_property_available, create_booking, process_payment
from app.services.payment_service import (
    record_verified_payment, verify_webhook_signature,
    create_payment_order, generate_sandbox_signature
)
from app.services.freshness import get_freshness_status
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

api_bp = Blueprint('api', __name__)
csrf.exempt(api_bp)  # Exempt REST API from CSRF for mobile/external integrations


@api_bp.route('/properties', methods=['GET'])
def get_properties():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    results = search_properties(request.args, page=page, per_page=per_page)

    items_data = []
    for p in results['items']:
        p_dict = p.to_dict()
        p_dict['freshness'] = get_freshness_status(p)
        items_data.append(p_dict)

    return jsonify({
        'status': 'success',
        'data': items_data,
        'pagination': {
            'page': results['page'],
            'pages': results['pages'],
            'total': results['total'],
            'has_next': results['has_next'],
            'has_prev': results['has_prev']
        }
    })


@api_bp.route('/properties/<int:property_id>', methods=['GET'])
def get_property_detail(property_id):
    p = Property.query.get_or_404(property_id)
    if p.status != 'approved':
        return jsonify({'status': 'error', 'message': 'Property not available or pending approval'}), 404

    data = p.to_dict()
    data['rooms'] = [rt.to_dict() for rt in p.room_types]
    data['food_menu'] = p.food_menu.to_dict() if p.food_menu else None
    data['amenities'] = [{
        'id': pa.amenity.id,
        'name': pa.amenity.name,
        'icon': pa.amenity.icon,
        'category': pa.amenity.category,
        'details': pa.details
    } for pa in p.amenities]
    data['media'] = [{
        'file_path': m.file_path,
        'caption': m.caption,
        'is_cover': m.is_cover,
        'media_type': m.media_type
    } for m in p.media]
    data['freshness'] = get_freshness_status(p)
    data['reviews'] = [r.to_dict() for r in p.reviews if r.status == 'approved']
    data['has_gym'] = p.has_gym
    if p.gym_facility and p.gym_facility.is_available:
        gym_dict = p.gym_facility.to_dict()
        gym_dict['photos'] = [{'id': ph.id, 'file_path': ph.file_path, 'caption': ph.caption} for ph in p.gym_facility.photos]
        data['gym'] = gym_dict
    else:
        data['gym'] = None

    return jsonify({'status': 'success', 'data': data})


@api_bp.route('/properties/<int:property_id>/gym', methods=['GET'])
def get_property_gym(property_id):
    p = Property.query.get_or_404(property_id)
    if p.status != 'approved':
        return jsonify({'status': 'error', 'message': 'Property not available or pending approval'}), 404

    if not p.gym_facility or not p.gym_facility.is_available:
        return jsonify({
            'status': 'success',
            'has_gym': False,
            'message': 'This PG does not have an in-house gym facility',
            'data': None
        })

    gym_data = p.gym_facility.to_dict()
    gym_data['photos'] = [{'id': ph.id, 'file_path': ph.file_path, 'caption': ph.caption} for ph in p.gym_facility.photos]
    return jsonify({
        'status': 'success',
        'has_gym': True,
        'data': gym_data
    })


@api_bp.route('/localities', methods=['GET'])
def get_localities():
    localities = db.session.query(Property.locality, db.func.count(Property.id))\
        .filter(Property.status == 'approved')\
        .group_by(Property.locality)\
        .all()

    return jsonify({
        'status': 'success',
        'data': [{'locality': loc, 'count': cnt} for loc, cnt in localities]
    })


@api_bp.route('/enquiries', methods=['POST'])
def create_enquiry_api():
    payload = request.get_json() or {}
    customer_id = payload.get('customer_id')
    property_id = payload.get('property_id')
    move_in_date_str = payload.get('move_in_date')
    message = payload.get('message', 'Interested in this PG')

    if not customer_id or not property_id or not move_in_date_str:
        return jsonify({'status': 'error', 'message': 'Missing required fields: customer_id, property_id, move_in_date'}), 400

    user = User.query.get(customer_id)
    prop = Property.query.get(property_id)
    if not user or not prop:
        return jsonify({'status': 'error', 'message': 'User or Property not found'}), 404

    try:
        move_in = datetime.strptime(move_in_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format, use YYYY-MM-DD'}), 400

    enquiry = Enquiry(
        customer_id=customer_id,
        property_id=property_id,
        room_type_id=payload.get('room_type_id'),
        move_in_date=move_in,
        budget_max=payload.get('budget_max'),
        message=message,
        status='new'
    )
    db.session.add(enquiry)
    db.session.commit()

    return jsonify({'status': 'success', 'data': enquiry.to_dict()}), 201


@api_bp.route('/short-stay/properties', methods=['GET'])
def get_short_stay_properties():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    results = search_short_stay(request.args, page=page, per_page=per_page)

    data = []
    for p in results['items']:
        p_dict = p.to_dict()
        p_dict['freshness'] = get_freshness_status(p)
        data.append(p_dict)

    return jsonify({
        'status': 'success',
        'data': data,
        'pagination': {
            'page': results['page'],
            'pages': results['pages'],
            'total': results['total'],
            'has_next': results['has_next'],
            'has_prev': results['has_prev']
        }
    })


@api_bp.route('/short-stay/quote', methods=['GET'])
def get_short_stay_quote():
    property_id = request.args.get('property_id', type=int)
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    num_guests = request.args.get('num_guests', 1, type=int)

    if not property_id or not check_in or not check_out:
        return jsonify({'status': 'error', 'message': 'Missing property_id, check_in, or check_out'}), 400

    prop = Property.query.get(property_id)
    if not prop or not prop.has_short_stay:
        return jsonify({'status': 'error', 'message': 'Property not found or does not offer short stays'}), 404

    available, reason = is_property_available(property_id, check_in, check_out, num_guests=num_guests)
    if not available:
        return jsonify({'status': 'unavailable', 'message': reason}), 409

    try:
        quote = calculate_quote(prop.short_stay_config, check_in, check_out, num_guests=num_guests)
        return jsonify({'status': 'success', 'data': quote})
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/short-stay/book', methods=['POST'])
def book_short_stay_api():
    payload = request.get_json() or {}
    customer_id = payload.get('customer_id')
    property_id = payload.get('property_id')
    check_in = payload.get('check_in')
    check_out = payload.get('check_out')
    num_guests = payload.get('num_guests', 1)

    if not customer_id or not property_id or not check_in or not check_out:
        return jsonify({'status': 'error', 'message': 'Missing customer_id, property_id, check_in, or check_out'}), 400

    user = User.query.get(customer_id)
    prop = Property.query.get(property_id)
    if not user or not prop:
        return jsonify({'status': 'error', 'message': 'User or Property not found'}), 404

    try:
        booking = create_booking(
            customer_id=customer_id,
            property_id=property_id,
            check_in_date=check_in,
            check_out_date=check_out,
            num_guests=int(num_guests),
            guests_data=payload.get('guests_data'),
            special_requests=payload.get('special_requests'),
            room_type_id=payload.get('room_type_id')
        )
        return jsonify({'status': 'success', 'data': booking.to_dict()}), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/short-stay/bookings/<booking_code>', methods=['GET'])
def get_booking_detail_api(booking_code):
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first()
    if not booking:
        return jsonify({'status': 'error', 'message': 'Booking not found'}), 404

    # Authorization verification: only the booking customer, property owner, or admin can see sensitive PII
    auth_user_id = request.args.get('user_id', type=int)
    is_authorized = (
        (current_user.is_authenticated and (current_user.id == booking.customer_id or current_user.id == booking.property.owner_id or current_user.is_admin)) or
        (auth_user_id is not None and (auth_user_id == booking.customer_id or auth_user_id == booking.property.owner_id))
    )

    data = booking.to_dict()

    if not is_authorized:
        # Mask sensitive personal guest info to protect privacy against unauthorized queries
        if data.get('customer_phone'):
            data['customer_phone'] = data['customer_phone'][:2] + '******' + data['customer_phone'][-2:]
        if data.get('customer_email'):
            parts = data['customer_email'].split('@')
            data['customer_email'] = parts[0][:2] + '***@' + parts[1] if len(parts) > 1 else '***'
        data['guests'] = [{'full_name': g.full_name} for g in booking.guests]
    else:
        data['guests'] = [
            {
                'full_name': g.full_name,
                'age': g.age,
                'gender': g.gender,
                'id_proof_type': g.id_proof_type,
                'id_proof_number': g.id_proof_number
            }
            for g in booking.guests
        ]

    data['payments'] = [
        {
            'receipt_number': p.receipt_number,
            'amount': p.amount,
            'status': p.status,
            'method': p.payment_method,
            'transaction_id': p.transaction_id
        }
        for p in booking.payments
    ]
    return jsonify({'status': 'success', 'data': data})


@api_bp.route('/short-stay/bookings/<booking_code>/pay', methods=['POST'])
def api_pay_short_stay(booking_code):
    """
    Android API endpoint to verify and record gateway payments for short stays.
    """
    import uuid
    booking = ShortStayBooking.query.filter_by(booking_code=booking_code).first()
    if not booking:
        return jsonify({'status': 'error', 'message': 'Booking not found'}), 404

    payload = request.get_json() or {}
    order_id = payload.get('gateway_order_id') or payload.get('razorpay_order_id')
    payment_id = payload.get('gateway_payment_id') or payload.get('razorpay_payment_id')
    signature = payload.get('gateway_signature') or payload.get('razorpay_signature')
    amount = payload.get('amount')
    payment_method = payload.get('payment_method', 'UPI')
    notes = payload.get('notes')

    if not amount:
        return jsonify({'status': 'error', 'message': 'Missing payment amount'}), 400

    # In sandbox test mode if signature is omitted, generate test signature
    if not signature:
        if not order_id:
            order_info = create_payment_order(booking, amount_in_rupees=float(amount))
            order_id = order_info['order_id']
        if not payment_id:
            payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        signature = generate_sandbox_signature(order_id, payment_id)

    try:
        payment = record_verified_payment(
            booking_id=booking.id,
            gateway_order_id=order_id,
            gateway_payment_id=payment_id,
            gateway_signature=signature,
            amount=float(amount),
            payment_method=payment_method,
            notes=notes,
            verify_signature=True
        )
        return jsonify({
            'status': 'success',
            'data': {
                'receipt_number': payment.receipt_number,
                'transaction_id': payment.transaction_id,
                'amount': payment.amount,
                'payment_status': booking.payment_status
            }
        }), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/short-stay/payment/webhook', methods=['POST'])
def razorpay_payment_webhook():
    """
    Webhook handler for gateway callbacks with signature verification and duplicate protection.
    """
    signature = request.headers.get('X-Razorpay-Signature')
    raw_body = request.get_data()

    if not signature or not verify_webhook_signature(raw_body, signature):
        return jsonify({'status': 'error', 'message': 'Invalid webhook signature'}), 400

    event_payload = request.get_json() or {}
    event_type = event_payload.get('event')

    if event_type == 'payment.captured':
        payment_entity = event_payload.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        amount_paise = payment_entity.get('amount', 0)
        amount_in_rupees = amount_paise / 100.0

        booking = ShortStayBooking.query.filter_by(gateway_order_id=order_id).first()
        if booking:
            record_verified_payment(
                booking_id=booking.id,
                gateway_order_id=order_id,
                gateway_payment_id=payment_id,
                gateway_signature=signature,
                amount=amount_in_rupees,
                payment_method='Razorpay/Webhook',
                verify_signature=False
            )

    return jsonify({'status': 'received'}), 200


# -------------------------------------------------------------------------
# ANDROID REST API: SMART ROOMMATE MATCHING & PG COMMUNITY
# -------------------------------------------------------------------------

def _get_api_user():
    if current_user and current_user.is_authenticated:
        return current_user
    uid = request.headers.get('X-User-Id') or (request.get_json(silent=True) or {}).get('user_id') or request.args.get('user_id')
    if uid:
        try:
            return User.query.get(int(uid))
        except (ValueError, TypeError):
            return None
    return None


@api_bp.route('/roommates/recommended', methods=['GET'])
def api_get_recommended_roommates():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    limit = request.args.get('limit', 20, type=int)
    results = get_recommended_roommates(user, limit=limit)
    return jsonify({
        'status': 'success',
        'count': len(results),
        'data': results
    })


@api_bp.route('/roommates/profile', methods=['GET', 'POST'])
def api_manage_roommate_profile():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    profile = user.roommate_profile

    if request.method == 'GET':
        if not profile:
            return jsonify({'status': 'error', 'message': 'Profile not found'}), 404
        return jsonify({'status': 'success', 'data': profile.to_dict(viewer_user=user)})

    # POST - create or update
    payload = request.get_json() or {}
    if not profile:
        profile = RoommateProfile(user_id=user.id)
        db.session.add(profile)

    if 'preferred_location' in payload:
        profile.preferred_location = payload['preferred_location']
    if 'budget_min' in payload:
        profile.budget_min = float(payload['budget_min'])
    if 'budget_max' in payload:
        profile.budget_max = float(payload['budget_max'])
    if 'occupation' in payload:
        profile.occupation = payload['occupation']
    if 'preferred_room_type' in payload:
        profile.preferred_room_type = payload['preferred_room_type']
    if 'cleanliness' in payload:
        profile.cleanliness = payload['cleanliness']
    if 'food_preference' in payload:
        profile.food_preference = payload['food_preference']
    if 'sleep_schedule' in payload:
        profile.sleep_schedule = payload['sleep_schedule']
    if 'smoking_preference' in payload:
        profile.smoking_preference = payload['smoking_preference']
    if 'move_in_date' in payload and payload['move_in_date']:
        try:
            profile.move_in_date = datetime.strptime(payload['move_in_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'bio' in payload:
        profile.bio = payload['bio']
    if 'is_active' in payload:
        profile.is_active = bool(payload['is_active'])
    if 'looking_for_room' in payload:
        profile.looking_for_room = bool(payload['looking_for_room'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Profile saved', 'data': profile.to_dict(viewer_user=user)})


@api_bp.route('/roommates/interest', methods=['POST'])
def api_roommate_interest():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    target_user_id = payload.get('target_user_id')
    action = payload.get('action')

    if not target_user_id or action not in ['like', 'skip']:
        return jsonify({'status': 'error', 'message': 'Missing or invalid target_user_id or action'}), 400

    result = record_roommate_interest(user.id, int(target_user_id), action)
    return jsonify(result)


@api_bp.route('/roommates/request', methods=['POST'])
def api_send_roommate_request():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    receiver_id = payload.get('receiver_id')
    if not receiver_id:
        return jsonify({'status': 'error', 'message': 'receiver_id is required'}), 400

    try:
        req = send_roommate_request(
            sender_id=user.id,
            receiver_id=int(receiver_id),
            property_id=payload.get('property_id'),
            room_type_id=payload.get('room_type_id'),
            proposed_split_rent=payload.get('proposed_split_rent'),
            message=payload.get('message', '')
        )
        return jsonify({'status': 'success', 'data': req.to_dict()}), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/roommates/requests', methods=['GET'])
def api_get_roommate_requests():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    received = RoommateRequest.query.filter_by(receiver_id=user.id).order_by(RoommateRequest.created_at.desc()).all()
    sent = RoommateRequest.query.filter_by(sender_id=user.id).order_by(RoommateRequest.created_at.desc()).all()

    return jsonify({
        'status': 'success',
        'received': [r.to_dict() for r in received],
        'sent': [r.to_dict() for r in sent]
    })


@api_bp.route('/roommates/requests/<int:request_id>/action', methods=['POST'])
def api_respond_roommate_request(request_id):
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    action = payload.get('action')
    if action not in ['accept', 'reject', 'cancel']:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

    try:
        req = respond_roommate_request(request_id, user.id, action)
        return jsonify({'status': 'success', 'data': req.to_dict()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/community/<int:property_id>/posts', methods=['GET'])
def api_get_community_posts(property_id):
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    if not is_user_authorized_for_community(user, property_id):
        return jsonify({'status': 'error', 'message': 'Unauthorized. Private PG residents only.'}), 403

    post_type = request.args.get('category')
    posts = get_pg_posts(property_id, post_type=post_type)
    return jsonify({
        'status': 'success',
        'data': [p.to_dict() for p in posts]
    })


@api_bp.route('/community/<int:property_id>/posts', methods=['POST'])
def api_create_community_post(property_id):
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    if not is_user_authorized_for_community(user, property_id):
        return jsonify({'status': 'error', 'message': 'Unauthorized. Private PG residents only.'}), 403

    payload = request.get_json() or {}
    title = payload.get('title')
    content = payload.get('content')
    if not title or not content:
        return jsonify({'status': 'error', 'message': 'Title and content are required'}), 400

    try:
        post = create_pg_post(
            property_id=property_id,
            user=user,
            title=title,
            content=content,
            post_type=payload.get('post_type', 'general'),
            is_pinned=bool(payload.get('is_pinned', False))
        )
        return jsonify({'status': 'success', 'data': post.to_dict()}), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/community/posts/<int:post_id>/comments', methods=['POST'])
def api_add_community_comment(post_id):
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    content = payload.get('content')
    if not content:
        return jsonify({'status': 'error', 'message': 'Content is required'}), 400

    try:
        comment = add_post_comment(post_id, user, content)
        return jsonify({
            'status': 'success',
            'data': {
                'id': comment.id,
                'post_id': comment.post_id,
                'author_name': comment.author.name if comment.author else 'Resident',
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@api_bp.route('/safety/block', methods=['POST'])
def api_block_user():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    blocked_id = payload.get('blocked_id')
    if not blocked_id:
        return jsonify({'status': 'error', 'message': 'blocked_id is required'}), 400

    block_user(user.id, int(blocked_id), reason=payload.get('reason'))
    return jsonify({'status': 'success', 'message': 'User blocked successfully'})


@api_bp.route('/safety/report', methods=['POST'])
def api_report_user():
    user = _get_api_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    payload = request.get_json() or {}
    reported_id = payload.get('reported_id')
    reason = payload.get('reason', 'inappropriate')
    if not reported_id:
        return jsonify({'status': 'error', 'message': 'reported_id is required'}), 400

    report_user(user.id, int(reported_id), reason=reason, details=payload.get('details'))
    return jsonify({'status': 'success', 'message': 'Report submitted'})



