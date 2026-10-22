import builtins
from datetime import datetime
from app import db
from app.models.community import PGResident, PGCommunityPost, PGCommunityComment, PGCommunityReport
from app.models.property import Property
from app.models.short_stay import ShortStayBooking
from app.models.roommate import RoommateRequest


def is_user_authorized_for_community(user, property_id):
    """
    Checks if a user is authorized to view or post in a specific PG's private community.
    Authorized if:
    1. User is an admin
    2. User is the owner of the property
    3. User has an active PGResident entry for this property
    4. User has an active/confirmed short stay booking for this property
    5. User has an accepted & owner-approved roommate request for this property
    """
    if not user or not user.is_authenticated:
        return False

    if getattr(user, 'role', None) == 'admin':
        return True

    prop = Property.query.get(property_id)
    if not prop:
        return False

    # Owner access
    if prop.owner_id == user.id:
        return True

    # 1. Check PGResident table
    active_resident = PGResident.query.filter_by(
        property_id=property_id,
        user_id=user.id,
        status='active'
    ).first()
    if active_resident:
        return True

    # 2. Check ShortStayBooking
    active_booking = ShortStayBooking.query.filter(
        ShortStayBooking.property_id == property_id,
        ShortStayBooking.customer_id == user.id,
        ShortStayBooking.status.in_(['confirmed', 'checked_in'])
    ).first()
    if active_booking:
        return True

    # 3. Check approved shared room request
    approved_request = RoommateRequest.query.filter(
        RoommateRequest.property_id == property_id,
        db.or_(RoommateRequest.sender_id == user.id, RoommateRequest.receiver_id == user.id),
        RoommateRequest.status == 'owner_approved'
    ).first()
    if approved_request:
        return True

    return False


def get_user_communities(user):
    """
    Returns list of properties whose community boards the user has access to.
    """
    if not user or not user.is_authenticated:
        return []

    if getattr(user, 'role', None) == 'admin':
        return Property.query.all()

    if getattr(user, 'role', None) == 'owner':
        return Property.query.filter_by(owner_id=user.id).all()

    # Customer residencies
    resident_prop_ids = {r.property_id for r in PGResident.query.filter_by(user_id=user.id, status='active').all()}
    booking_prop_ids = {b.property_id for b in ShortStayBooking.query.filter(
        ShortStayBooking.customer_id == user.id,
        ShortStayBooking.status.in_(['confirmed', 'checked_in'])
    ).all()}
    shared_prop_ids = {r.property_id for r in RoommateRequest.query.filter(
        db.or_(RoommateRequest.sender_id == user.id, RoommateRequest.receiver_id == user.id),
        RoommateRequest.status == 'owner_approved',
        RoommateRequest.property_id.isnot(None)
    ).all()}

    all_prop_ids = resident_prop_ids.union(booking_prop_ids).union(shared_prop_ids)
    if not all_prop_ids:
        return []

    return Property.query.filter(Property.id.in_(all_prop_ids)).all()


def get_pg_posts(property_id, post_type=None, limit=50):
    """
    Retrieves community posts for a property, sorted by pinned first, then newest.
    """
    query = PGCommunityPost.query.filter_by(property_id=property_id, is_deleted=False)
    if post_type:
        query = query.filter_by(post_type=post_type)
    
    posts = query.order_by(
        PGCommunityPost.is_pinned.desc(),
        PGCommunityPost.created_at.desc()
    ).limit(limit).all()

    return posts


def create_pg_post(property_id, user, title, content, post_type='general', is_pinned=False):
    """
    Creates a new community post if the user is authorized.
    Only property owners or admins can pin a post.
    """
    if not is_user_authorized_for_community(user, property_id):
        raise PermissionError("You must be a verified resident or owner of this PG to post.")

    prop = Property.query.get(property_id)
    can_pin = bool(prop and (prop.owner_id == user.id or getattr(user, 'role', None) == 'admin'))
    pinned = is_pinned and can_pin

    post = PGCommunityPost(
        property_id=property_id,
        user_id=user.id,
        title=title.strip(),
        content=content.strip(),
        post_type=post_type,
        is_pinned=pinned
    )
    db.session.add(post)
    db.session.commit()
    return post


def add_post_comment(post_id, user, content):
    """
    Adds a comment to an active community post.
    """
    post = PGCommunityPost.query.get_or_404(post_id)
    if not is_user_authorized_for_community(user, post.property_id):
        raise PermissionError("You must be an authorized resident or owner to comment.")

    comment = PGCommunityComment(
        post_id=post.id,
        user_id=user.id,
        content=content.strip()
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def delete_pg_post(post_id, user):
    """
    Soft-deletes a post. Permitted if author, owner of property, or admin.
    """
    post = PGCommunityPost.query.get_or_404(post_id)
    is_owner = post.property and post.property.owner_id == user.id
    is_admin = getattr(user, 'role', None) == 'admin'
    is_author = post.user_id == user.id

    if not (is_author or is_owner or is_admin):
        raise PermissionError("You do not have permission to delete this post.")

    post.is_deleted = True
    db.session.commit()
    return True


def report_pg_post(post_id, user, reason, details=None):
    """
    Submits a moderation report for a post.
    """
    post = PGCommunityPost.query.get_or_404(post_id)
    if not is_user_authorized_for_community(user, post.property_id):
        raise PermissionError("Unauthorized to interact with this community.")

    report = PGCommunityReport(
        post_id=post.id,
        reporter_id=user.id,
        reason=reason,
        details=details
    )
    db.session.add(report)
    db.session.commit()
    return report
