from datetime import datetime, date
from sqlalchemy import or_, and_
from app import db
from app.models.user import User
from app.models.property import Property
from app.models.room import RoomType
from app.models.roommate import RoommateProfile, RoommateInterest, RoommateRequest, UserBlock, UserReport
from app.models.community import PGResident
from app.models.interaction import Notification


def calculate_roommate_compatibility(profile_a, profile_b):
    """
    Computes a transparent 0-100% compatibility score with itemized matching factors.
    """
    breakdown = []
    total_score = 0

    # 1. Budget Compatibility (Max 25 pts)
    # Check overlap in budget range
    overlap_min = max(profile_a.min_budget, profile_b.min_budget)
    overlap_max = min(profile_a.max_budget, profile_b.max_budget)

    if overlap_min <= overlap_max:
        budget_pts = 25
        budget_note = f"Budget ranges align seamlessly (overlap: ₹{overlap_min:,.0f} - ₹{overlap_max:,.0f})"
    else:
        gap = overlap_min - overlap_max
        if gap <= 3000:
            budget_pts = 16
            budget_note = f"Close budget expectations (gap of ₹{gap:,.0f})"
        elif gap <= 6000:
            budget_pts = 8
            budget_note = f"Moderate budget gap (gap of ₹{gap:,.0f})"
        else:
            budget_pts = 2
            budget_note = "Different monthly budget expectations"

    total_score += budget_pts
    breakdown.append({'factor': 'Budget Alignment', 'points': budget_pts, 'max_points': 25, 'note': budget_note})

    # 2. Location Preference (Max 20 pts)
    loc_a = profile_a.preferred_locality.strip().lower()
    loc_b = profile_b.preferred_locality.strip().lower()

    if loc_a == loc_b or loc_a in loc_b or loc_b in loc_a:
        loc_pts = 20
        loc_note = f"Both prefer {profile_a.preferred_locality}"
    elif 'any' in loc_a or 'any' in loc_b or 'bengaluru' in loc_a or 'bengaluru' in loc_b:
        loc_pts = 14
        loc_note = "Flexible neighborhood preferences in Bengaluru"
    else:
        loc_pts = 6
        loc_note = f"Different preferred areas ({profile_a.preferred_locality} vs {profile_b.preferred_locality})"

    total_score += loc_pts
    breakdown.append({'factor': 'Location Preference', 'points': loc_pts, 'max_points': 20, 'note': loc_note})

    # 3. Cleanliness Habit (Max 15 pts)
    clean_a = profile_a.cleanliness.lower()
    clean_b = profile_b.cleanliness.lower()

    if clean_a == clean_b:
        clean_pts = 15
        clean_note = f"Identical cleanliness standard ({clean_a.capitalize()})"
    elif ('moderate' in (clean_a, clean_b)) and ('tidy' in (clean_a, clean_b) or 'relaxed' in (clean_a, clean_b)):
        clean_pts = 10
        clean_note = "Compatible day-to-day tidiness expectations"
    else:  # 'tidy' vs 'relaxed'
        clean_pts = 3
        clean_note = "Different tidiness preferences"

    total_score += clean_pts
    breakdown.append({'factor': 'Cleanliness Standard', 'points': clean_pts, 'max_points': 15, 'note': clean_note})

    # 4. Food Preference (Max 15 pts)
    food_a = profile_a.food_preference.lower()
    food_b = profile_b.food_preference.lower()

    if food_a == food_b or food_a == 'any' or food_b == 'any':
        food_pts = 15
        food_note = "Dietary habits align comfortably"
    elif ('veg' in food_a and 'vegan' in food_b) or ('vegan' in food_a and 'veg' in food_b):
        food_pts = 14
        food_note = "Plant-based / Vegetarian diet alignment"
    elif 'eggetarian' in (food_a, food_b):
        food_pts = 11
        food_note = "Vegetarian / Eggetarian dietary mix"
    else:  # Veg vs Non-veg
        food_pts = 8
        food_note = "Diverse dietary habits (Veg & Non-Veg)"

    total_score += food_pts
    breakdown.append({'factor': 'Dietary Compatibility', 'points': food_pts, 'max_points': 15, 'note': food_note})

    # 5. Sleep Schedule & Quiet Hours (Max 15 pts)
    sleep_a = profile_a.sleep_schedule.lower()
    sleep_b = profile_b.sleep_schedule.lower()

    if sleep_a == sleep_b:
        sleep_pts = 15
        sleep_note = f"Both maintain {sleep_a.replace('_', ' ').capitalize()} hours"
    elif sleep_a == 'flexible' or sleep_b == 'flexible':
        sleep_pts = 12
        sleep_note = "Flexible sleep and routine schedules"
    else:  # 'early_bird' vs 'night_owl'
        sleep_pts = 4
        sleep_note = "Opposite sleep hours (Early riser vs Night owl)"

    total_score += sleep_pts
    breakdown.append({'factor': 'Sleep Schedule', 'points': sleep_pts, 'max_points': 15, 'note': sleep_note})

    # 6. Smoking Habit (Max 10 pts)
    smoke_a = profile_a.smoking.lower()
    smoke_b = profile_b.smoking.lower()

    if smoke_a == smoke_b:
        smoke_pts = 10
        smoke_note = f"Mutual {smoke_a.replace('_', ' ')} household expectation"
    elif ('non_smoker' in (smoke_a, smoke_b)) and ('outside_only' in (smoke_a, smoke_b)):
        smoke_pts = 6
        smoke_note = "Permissible outside-only smoking standard"
    else:
        smoke_pts = 0
        smoke_note = "Conflicting smoking preferences"

    total_score += smoke_pts
    breakdown.append({'factor': 'Smoking Preference', 'points': smoke_pts, 'max_points': 10, 'note': smoke_note})

    final_score = min(100, max(0, total_score))
    return {
        'score': final_score,
        'breakdown': breakdown
    }


def calculate_compatibility_score(profile_a, profile_b):
    res = calculate_roommate_compatibility(profile_a, profile_b)
    return res['score'], res['breakdown']


def get_recommended_roommates(user_or_id, limit=20):
    """
    Returns compatibility-ranked roommate recommendations for active users,
    excluding self, blocked profiles, and skipped users.
    """
    user_id = user_or_id.id if hasattr(user_or_id, 'id') else int(user_or_id)
    my_profile = RoommateProfile.query.filter_by(user_id=user_id).first()
    if not my_profile or not my_profile.is_active:
        return []

    # Get blocked user IDs in both directions
    blocked_by_me = [b.blocked_id for b in UserBlock.query.filter_by(blocker_id=user_id).all()]
    blocked_me = [b.blocker_id for b in UserBlock.query.filter_by(blocked_id=user_id).all()]
    all_blocked_ids = set(blocked_by_me + blocked_me + [user_id])

    # Get skipped user IDs
    skipped_ids = set([
        i.target_user_id for i in RoommateInterest.query.filter_by(user_id=user_id, action='skip').all()
    ])

    exclude_ids = all_blocked_ids.union(skipped_ids)

    # Active profiles
    candidate_profiles = RoommateProfile.query.filter(
        RoommateProfile.status == 'active',
        RoommateProfile.user_id.notin_(exclude_ids)
    ).all()

    # Check mutual matches for contact display
    my_liked_ids = set([
        i.target_user_id for i in RoommateInterest.query.filter_by(user_id=user_id, action='like').all()
    ])
    liked_me_ids = set([
        i.user_id for i in RoommateInterest.query.filter_by(target_user_id=user_id, action='like').all()
    ])
    mutual_match_ids = my_liked_ids.intersection(liked_me_ids)

    recommendations = []
    for cand in candidate_profiles:
        comp = calculate_roommate_compatibility(my_profile, cand)
        is_mutual = cand.user_id in mutual_match_ids
        has_liked = cand.user_id in my_liked_ids

        cand_dict = cand.to_dict(include_contact=is_mutual)
        cand_dict['compatibility_score'] = comp['score']
        cand_dict['compatibility_breakdown'] = comp['breakdown']
        cand_dict['is_mutual_match'] = is_mutual
        cand_dict['has_liked'] = has_liked

        recommendations.append(cand_dict)

    # Sort descending by compatibility score
    recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
    return recommendations[:limit]


def record_roommate_interest(user_id, target_user_id, action='like'):
    """
    Records a like or skip for a candidate.
    Returns (interest, is_mutual_match: bool).
    """
    if user_id == target_user_id:
        raise ValueError("You cannot express interest in your own profile.")

    interest = RoommateInterest.query.filter_by(user_id=user_id, target_user_id=target_user_id).first()
    if not interest:
        interest = RoommateInterest(user_id=user_id, target_user_id=target_user_id, action=action)
        db.session.add(interest)
    else:
        interest.action = action

    db.session.commit()

    is_mutual = False
    if action == 'like':
        # Check if target user has liked current user
        counter_like = RoommateInterest.query.filter_by(
            user_id=target_user_id,
            target_user_id=user_id,
            action='like'
        ).first()

        if counter_like:
            is_mutual = True
            current_user_obj = User.query.get(user_id)
            target_user_obj = User.query.get(target_user_id)

            # Notify target user
            notif1 = Notification(
                user_id=target_user_id,
                title="It's a Mutual Roommate Match!",
                message=f"You and {current_user_obj.name} both liked each other's roommate profiles. Contact details unlocked!",
                link_url="/roommates#matches"
            )
            # Notify current user
            notif2 = Notification(
                user_id=user_id,
                title="It's a Mutual Roommate Match!",
                message=f"You and {target_user_obj.name} are mutually connected. Contact information is now accessible!",
                link_url="/roommates#matches"
            )
            db.session.add_all([notif1, notif2])
            db.session.commit()

    msg = "It's a Mutual Match!" if is_mutual else f"Saved {action} preference."
    return RoommateInterestResult(interest, is_mutual, message=msg)


class RoommateInterestResult(dict):
    """Result object that supports both tuple unpacking (interest, is_mutual) and dict access."""
    def __init__(self, interest, is_mutual, message=""):
        super().__init__(
            status='success',
            interest_id=interest.id,
            action=interest.action,
            is_mutual_match=is_mutual,
            is_mutual=is_mutual,
            message=message
        )
        self.interest = interest
        self.is_mutual = is_mutual
        self.is_mutual_match = is_mutual

    def __iter__(self):
        return iter((self.interest, self.is_mutual))


def get_mutual_matches(user_id):
    """
    Returns list of mutual matches with unlocked contact information (phone, email).
    """
    my_profile = RoommateProfile.query.filter_by(user_id=user_id).first()

    my_liked_ids = set([
        i.target_user_id for i in RoommateInterest.query.filter_by(user_id=user_id, action='like').all()
    ])
    liked_me_ids = set([
        i.user_id for i in RoommateInterest.query.filter_by(target_user_id=user_id, action='like').all()
    ])
    mutual_ids = my_liked_ids.intersection(liked_me_ids)

    # Exclude blocked users
    blocked_ids = set([
        b.blocked_id for b in UserBlock.query.filter_by(blocker_id=user_id).all()
    ] + [
        b.blocker_id for b in UserBlock.query.filter_by(blocked_id=user_id).all()
    ])
    valid_ids = mutual_ids.difference(blocked_ids)

    matches = []
    for uid in valid_ids:
        prof = RoommateProfile.query.filter_by(user_id=uid).first()
        if prof:
            data = prof.to_dict(include_contact=True)
            if my_profile:
                comp = calculate_roommate_compatibility(my_profile, prof)
                data['compatibility_score'] = comp['score']
                data['compatibility_breakdown'] = comp['breakdown']
            else:
                data['compatibility_score'] = 75
                data['compatibility_breakdown'] = []
            matches.append(data)

    matches.sort(key=lambda x: x.get('compatibility_score', 0), reverse=True)
    return matches


def send_roommate_request(sender_id, receiver_id, property_id=None, room_type_id=None, proposed_split_rent=None, message=None):
    """
    Creates a roommate invitation or shared-room pairing request.
    Prevents duplicate active requests and blocked interactions.
    """
    if sender_id == receiver_id:
        raise ValueError("You cannot send a roommate request to yourself.")

    # Check blocked
    blocked = UserBlock.query.filter(
        or_(
            and_(UserBlock.blocker_id == sender_id, UserBlock.blocked_id == receiver_id),
            and_(UserBlock.blocker_id == receiver_id, UserBlock.blocked_id == sender_id)
        )
    ).first()
    if blocked:
        raise ValueError("Cannot send request to this user due to privacy preferences.")

    # Duplicate active request check
    existing = RoommateRequest.query.filter(
        RoommateRequest.sender_id == sender_id,
        RoommateRequest.receiver_id == receiver_id,
        RoommateRequest.status.in_(['pending', 'accepted'])
    ).first()
    if existing:
        raise ValueError("You already have an active roommate request with this user.")

    req = RoommateRequest(
        sender_id=sender_id,
        receiver_id=receiver_id,
        property_id=property_id,
        room_type_id=room_type_id,
        proposed_split_rent=float(proposed_split_rent) if proposed_split_rent else None,
        message=message,
        status='pending',
        owner_status='pending' if property_id else 'none'
    )
    db.session.add(req)

    # Notify receiver
    sender_obj = User.query.get(sender_id)
    prop_name = Property.query.get(property_id).name if property_id else "independent pairing"
    notif = Notification(
        user_id=receiver_id,
        title="New Roommate Request",
        message=f"{sender_obj.name} invited you to pair up as roommates for {prop_name}.",
        link_url="/roommates#requests"
    )
    db.session.add(notif)
    db.session.commit()
    return req


def respond_roommate_request(request_id, user_id, action):
    """
    Handles accept, reject, or cancel of a roommate request.
    """
    req = RoommateRequest.query.get_or_404(request_id)

    if action in ['accept', 'reject']:
        if req.receiver_id != user_id:
            raise PermissionError("Only the recipient can accept or reject this request.")
        if req.status != 'pending':
            raise ValueError(f"Request is already {req.status}.")

        if action == 'accept':
            req.status = 'accepted'
            # If property is attached, flag for owner verification
            if req.property_id:
                req.owner_status = 'pending'
                # Notify property owner
                if req.property and req.property.owner_id:
                    notif_owner = Notification(
                        user_id=req.property.owner_id,
                        title=f"Shared Room Request for {req.property.name}",
                        message=f"{req.sender.name} and {req.receiver.name} agreed to share a room. Owner approval requested.",
                        link_url="/owner/shared-rooms"
                    )
                    db.session.add(notif_owner)
            notif_sender = Notification(
                user_id=req.sender_id,
                title="Roommate Request Accepted!",
                message=f"{req.receiver.name} accepted your roommate request! Contact details unlocked.",
                link_url="/roommates#requests"
            )
            db.session.add(notif_sender)
        else:
            req.status = 'rejected'
            notif_sender = Notification(
                user_id=req.sender_id,
                title="Roommate Request Declined",
                message=f"{req.receiver.name} was unable to accept your roommate request.",
                link_url="/roommates#requests"
            )
            db.session.add(notif_sender)

    elif action == 'cancel':
        if req.sender_id != user_id:
            raise PermissionError("Only the sender can cancel this request.")
        req.status = 'cancelled'
    else:
        raise ValueError("Invalid action specified.")

    db.session.commit()
    return req


def owner_approve_shared_room(request_id, owner_id, action='approve', owner_notes=None):
    """
    PG Owner reviews and approves/rejects proposed shared occupancy,
    verifying bed availability and updating occupancy counts.
    """
    req = RoommateRequest.query.get_or_404(request_id)
    if not req.property or req.property.owner_id != owner_id:
        raise PermissionError("You do not have authorization to manage shared occupancy for this property.")

    if action == 'approve':
        # Re-check room availability & occupancy limit
        if req.room_type_id:
            room = RoomType.query.get(req.room_type_id)
            if room:
                if room.vacant_beds < 1:
                    raise ValueError(f"Cannot approve: '{room.title}' has reached maximum occupancy (0 vacant beds).")
                room.occupied_beds += 1
                room.vacant_beds = max(0, room.total_beds - room.occupied_beds)

        req.owner_status = 'approved'
        req.status = 'owner_approved'
        req.owner_notes = owner_notes or "Approved by PG Owner. Welcome to our PG community!"

        # Register residents in PGResident table if not already added
        for uid in (req.sender_id, req.receiver_id):
            existing_res = PGResident.query.filter_by(property_id=req.property_id, user_id=uid).first()
            if not existing_res:
                new_res = PGResident(property_id=req.property_id, user_id=uid, status='active')
                db.session.add(new_res)

        # Notify both residents
        for uid in (req.sender_id, req.receiver_id):
            notif = Notification(
                user_id=uid,
                title="Shared PG Room Approved by Owner!",
                message=f"The owner of {req.property.name} has approved your shared room reservation! You now have access to the private PG Community.",
                link_url=f"/community/pg/{req.property.id}"
            )
            db.session.add(notif)
    else:
        req.owner_status = 'rejected'
        req.status = 'rejected'
        req.owner_notes = owner_notes or "Declined due to occupancy restrictions or house rules."
        for uid in (req.sender_id, req.receiver_id):
            notif = Notification(
                user_id=uid,
                title="Shared PG Request Update",
                message=f"The owner of {req.property.name} was unable to approve the shared arrangement: {req.owner_notes}",
                link_url="/roommates#requests"
            )
            db.session.add(notif)

    db.session.commit()
    return req


def owner_reject_shared_room(request_id, owner_id, reason=None):
    """Convenience helper for PG Owner to reject a shared room arrangement."""
    return owner_approve_shared_room(request_id, owner_id, action='reject', owner_notes=reason)


def block_user(blocker_id, blocked_id, reason=None):
    """Blocks a user to prevent profile recommendations, requests, and interactions."""
    if blocker_id == blocked_id:
        raise ValueError("Cannot block yourself.")
    existing = UserBlock.query.filter_by(blocker_id=blocker_id, blocked_id=blocked_id).first()
    if not existing:
        b = UserBlock(blocker_id=blocker_id, blocked_id=blocked_id, reason=reason)
        db.session.add(b)
        db.session.commit()
        return b
    return existing


def report_user(reporter_id, reported_id, reason, details=None):
    """Files a user moderation report."""
    if reporter_id == reported_id:
        raise ValueError("Cannot report yourself.")
    rep = UserReport(reporter_id=reporter_id, reported_user_id=reported_id, reason=reason, details=details)
    db.session.add(rep)
    db.session.commit()
    return rep
