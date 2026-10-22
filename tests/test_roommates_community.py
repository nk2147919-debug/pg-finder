import pytest
from datetime import datetime, date, timedelta
from app import db
from app.models.user import User
from app.models.property import Property
from app.models.room import RoomType
from app.models.roommate import RoommateProfile, RoommateInterest, RoommateRequest, UserBlock, UserReport
from app.models.community import PGResident, PGCommunityPost, PGCommunityComment, PGCommunityReport
from app.services.roommate_service import (
    calculate_roommate_compatibility, calculate_compatibility_score,
    get_recommended_roommates, record_roommate_interest,
    send_roommate_request, respond_roommate_request,
    owner_approve_shared_room, owner_reject_shared_room,
    block_user, report_user
)
from app.services.community_service import (
    is_user_authorized_for_community, get_user_communities,
    get_pg_posts, create_pg_post, add_post_comment,
    delete_pg_post, report_pg_post
)


@pytest.fixture
def additional_users(app):
    user_b = User(name="Candidate Two", email="cand2@example.com", phone="9988776655", role="customer")
    user_b.set_password("Password@123")
    user_c = User(name="Candidate Three", email="cand3@example.com", phone="9988776656", role="customer")
    user_c.set_password("Password@123")
    db.session.add_all([user_b, user_c])
    db.session.commit()
    return {'cand2': user_b, 'cand3': user_c}


def test_profile_creation_and_editing(client, test_users):
    """Test roommate profile creation, update, pausing, and deletion."""
    user = test_users['customer']
    profile = RoommateProfile(
        user_id=user.id,
        preferred_locality="Koramangala",
        min_budget=8000.0,
        max_budget=16000.0,
        occupation="Data Analyst",
        preferred_sharing="double",
        cleanliness="very_clean",
        food_preference="veg",
        sleep_schedule="early_bird",
        smoking="non_smoker",
        bio="Clean and quiet professional seeking same."
    )
    db.session.add(profile)
    db.session.commit()

    saved = RoommateProfile.query.filter_by(user_id=user.id).first()
    assert saved is not None
    assert saved.preferred_location == "Koramangala"
    assert saved.budget_min == 8000.0
    assert saved.budget_max == 16000.0
    assert saved.is_active is True

    # Pause profile
    saved.is_active = False
    db.session.commit()
    assert saved.status == 'paused'
    assert saved.is_active is False

    # Resume
    saved.is_active = True
    db.session.commit()
    assert saved.is_active is True


def test_compatibility_scoring_breakdown(app, test_users, additional_users):
    """Verify transparent 0-100% compatibility calculation with itemized factors."""
    u1 = test_users['customer']
    u2 = additional_users['cand2']
    u3 = additional_users['cand3']

    p1 = RoommateProfile(
        user_id=u1.id,
        preferred_locality="Koramangala",
        min_budget=10000.0,
        max_budget=15000.0,
        preferred_sharing="double",
        cleanliness="very_clean",
        food_preference="veg",
        sleep_schedule="early_bird",
        smoking="non_smoker"
    )
    # Perfectly matching candidate
    p2 = RoommateProfile(
        user_id=u2.id,
        preferred_locality="Koramangala",
        min_budget=10000.0,
        max_budget=15000.0,
        preferred_sharing="double",
        cleanliness="very_clean",
        food_preference="veg",
        sleep_schedule="early_bird",
        smoking="non_smoker"
    )
    # Opposing candidate
    p3 = RoommateProfile(
        user_id=u3.id,
        preferred_locality="Whitefield",
        min_budget=2000.0,
        max_budget=4000.0,
        preferred_sharing="single",
        cleanliness="relaxed",
        food_preference="non_veg",
        sleep_schedule="night_owl",
        smoking="smoker"
    )
    db.session.add_all([p1, p2, p3])
    db.session.commit()

    score_match, breakdown_match = calculate_compatibility_score(p1, p2)
    assert score_match == 100
    assert len(breakdown_match) == 6
    factors = [b['factor'] for b in breakdown_match]
    assert 'Budget Alignment' in factors
    assert 'Location Preference' in factors
    assert 'Cleanliness Standard' in factors
    assert 'Dietary Compatibility' in factors
    assert 'Sleep Schedule' in factors
    assert 'Smoking Preference' in factors

    score_mismatch, _ = calculate_compatibility_score(p1, p3)
    assert score_mismatch < 40


def test_recommendation_and_filtering(app, test_users, additional_users):
    """Ensure recommendations exclude self, blocked users, and skipped users."""
    u1 = test_users['customer']
    u2 = additional_users['cand2']
    u3 = additional_users['cand3']

    p1 = RoommateProfile(user_id=u1.id, preferred_locality="HSR Layout", status='active')
    p2 = RoommateProfile(user_id=u2.id, preferred_locality="HSR Layout", status='active')
    p3 = RoommateProfile(user_id=u3.id, preferred_locality="HSR Layout", status='active')
    db.session.add_all([p1, p2, p3])
    db.session.commit()

    # Initially both u2 and u3 recommended
    recs = get_recommended_roommates(u1)
    rec_ids = [r['user_id'] for r in recs]
    assert u2.id in rec_ids
    assert u3.id in rec_ids
    assert u1.id not in rec_ids

    # u1 blocks u2
    block_user(u1.id, u2.id)
    recs_after_block = get_recommended_roommates(u1)
    rec_ids_after = [r['user_id'] for r in recs_after_block]
    assert u2.id not in rec_ids_after
    assert u3.id in rec_ids_after

    # u1 skips u3
    record_roommate_interest(u1.id, u3.id, action='skip')
    recs_after_skip = get_recommended_roommates(u1)
    assert len(recs_after_skip) == 0


def test_mutual_match_privacy(app, test_users, additional_users):
    """
    Candidate phone and email MUST remain masked unless a mutual match exists.
    """
    u1 = test_users['customer']
    u2 = additional_users['cand2']

    p1 = RoommateProfile(user_id=u1.id, preferred_locality="Indiranagar", status='active')
    p2 = RoommateProfile(user_id=u2.id, preferred_locality="Indiranagar", status='active')
    db.session.add_all([p1, p2])
    db.session.commit()

    # Before any interest
    cand_dict_masked = p2.to_dict(viewer_user=u1)
    assert 'phone' not in cand_dict_masked
    assert 'email' not in cand_dict_masked
    assert cand_dict_masked.get('contact_unlocked') is False

    # u1 likes u2 (single-sided like)
    res1 = record_roommate_interest(u1.id, u2.id, action='like')
    assert res1['is_mutual_match'] is False

    cand_dict_still_masked = p2.to_dict(viewer_user=u1)
    assert 'phone' not in cand_dict_still_masked

    # u2 likes u1 back (mutual match!)
    res2 = record_roommate_interest(u2.id, u1.id, action='like')
    assert res2['is_mutual_match'] is True

    # Now contact details are revealed to both users
    cand_dict_unlocked = p2.to_dict(viewer_user=u1)
    assert cand_dict_unlocked.get('contact_unlocked') is True
    assert cand_dict_unlocked['phone'] == u2.phone
    assert cand_dict_unlocked['email'] == u2.email


def test_roommate_request_flow_and_duplicate_prevention(app, test_users, additional_users, test_property):
    """Test roommate request creation, duplicate prevention, and response actions."""
    u1 = test_users['customer']
    u2 = additional_users['cand2']

    # Send valid request
    req = send_roommate_request(
        sender_id=u1.id,
        receiver_id=u2.id,
        property_id=test_property.id,
        proposed_split_rent=6000.0,
        message="Let's take a 2-sharing room together!"
    )
    assert req.status == 'pending'

    # Duplicate request prevention
    with pytest.raises(ValueError) as exc:
        send_roommate_request(
            sender_id=u1.id,
            receiver_id=u2.id,
            property_id=test_property.id
        )
    assert "active roommate request" in str(exc.value)

    # u2 accepts request
    accepted_req = respond_roommate_request(req.id, u2.id, action='accept')
    assert accepted_req.status == 'accepted'


def test_owner_shared_room_occupancy_approval(app, test_users, additional_users, test_property):
    """
    Test PG Owner reviewing shared occupancy, enforcing bed limits,
    updating vacancy counts, and granting community access.
    """
    owner = test_users['owner1']
    other_owner = test_users['owner2']
    u1 = test_users['customer']
    u2 = additional_users['cand2']
    room = test_property.room_types[0]

    initial_vacant = room.vacant_beds

    req = send_roommate_request(
        sender_id=u1.id,
        receiver_id=u2.id,
        property_id=test_property.id,
        room_type_id=room.id,
        proposed_split_rent=6000.0
    )
    respond_roommate_request(req.id, u2.id, action='accept')

    # Other owner unauthorized attempt
    with pytest.raises(PermissionError):
        owner_approve_shared_room(req.id, other_owner.id)

    # Authorized owner approves
    approved_req = owner_approve_shared_room(req.id, owner.id)
    assert approved_req.status == 'owner_approved'
    assert approved_req.owner_status == 'approved'

    # Room vacant beds decremented
    db.session.refresh(room)
    assert room.vacant_beds == initial_vacant - 1

    # Both residents registered in PGResident table
    res1 = PGResident.query.filter_by(property_id=test_property.id, user_id=u1.id).first()
    res2 = PGResident.query.filter_by(property_id=test_property.id, user_id=u2.id).first()
    assert res1 is not None and res1.status == 'active'
    assert res2 is not None and res2.status == 'active'

    # Exceeding occupancy test
    room.vacant_beds = 0
    db.session.commit()

    req2 = send_roommate_request(sender_id=u2.id, receiver_id=u1.id, property_id=test_property.id, room_type_id=room.id)
    req2.status = 'accepted'
    db.session.commit()

    with pytest.raises(ValueError) as exc:
        owner_approve_shared_room(req2.id, owner.id)
    assert "maximum occupancy" in str(exc.value)


def test_pg_community_authorization_and_posts(app, test_users, additional_users, test_property):
    """
    Test private PG community authorization, post creation, comments,
    and moderation controls.
    """
    owner = test_users['owner1']
    resident_user = test_users['customer']
    unauthorized_user = additional_users['cand3']

    # Unauthorized user check
    assert is_user_authorized_for_community(unauthorized_user, test_property.id) is False

    with pytest.raises(PermissionError):
        create_pg_post(test_property.id, unauthorized_user, "Hello", "Unauthorized attempt")

    # Authorize resident
    res = PGResident(property_id=test_property.id, user_id=resident_user.id, status='active')
    db.session.add(res)
    db.session.commit()

    assert is_user_authorized_for_community(resident_user, test_property.id) is True
    assert is_user_authorized_for_community(owner, test_property.id) is True

    # Resident creates post
    post = create_pg_post(
        property_id=test_property.id,
        user=resident_user,
        title="Wi-Fi Speed on 3rd Floor",
        content="Is anyone else experiencing slow speeds today?",
        post_type="question"
    )
    assert post.id is not None
    assert post.post_type == "question"
    assert post.is_pinned is False

    # Owner adds official comment
    comment = add_post_comment(post.id, owner, "Technician is coming at 4 PM to check the fiber line.")
    assert comment.id is not None
    assert comment.author_is_owner is True

    # Moderation: Report post
    report = report_pg_post(post.id, resident_user, reason="spam", details="Test report")
    assert report.id is not None
    assert report.status == "pending"

    # Moderation: Owner deletes post
    delete_pg_post(post.id, owner)
    db.session.refresh(post)
    assert post.is_deleted is True


def test_blocking_and_reporting_users(app, test_users, additional_users):
    """Test user blocking and safety reports."""
    u1 = test_users['customer']
    u2 = additional_users['cand2']

    block = block_user(u1.id, u2.id, reason="Unwanted solicitation")
    assert block.id is not None

    # Cannot block self
    with pytest.raises(ValueError):
        block_user(u1.id, u1.id)

    # Report user
    rep = report_user(u1.id, u2.id, reason="harassment", details="Rude messages")
    assert rep.id is not None
    assert rep.status == "pending"


def test_android_rest_api_roommates(client, app, test_users, additional_users):
    """Test Android REST API endpoints for roommate matching with privacy protection."""
    u1 = test_users['customer']
    u2 = additional_users['cand2']

    # 1. Unauthenticated request -> 401
    resp = client.get('/api/v1/roommates/recommended')
    assert resp.status_code == 401

    # 2. Authenticated create profile
    resp_create = client.post('/api/v1/roommates/profile', headers={'X-User-Id': str(u1.id)}, json={
        'preferred_location': 'Koramangala',
        'budget_min': 9000,
        'budget_max': 18000,
        'occupation': 'Mobile Developer',
        'preferred_room_type': 'double',
        'cleanliness': 'moderate',
        'food_preference': 'any',
        'sleep_schedule': 'flexible',
        'smoking_preference': 'non_smoker'
    })
    assert resp_create.status_code == 200
    assert resp_create.json['status'] == 'success'

    # Candidate 2 profile
    p2 = RoommateProfile(user_id=u2.id, preferred_locality='Koramangala', min_budget=10000, max_budget=15000, status='active')
    db.session.add(p2)
    db.session.commit()

    # 3. Get recommendations via API
    resp_recs = client.get('/api/v1/roommates/recommended', headers={'X-User-Id': str(u1.id)})
    assert resp_recs.status_code == 200
    items = resp_recs.json['data']
    assert len(items) >= 1
    target = items[0]
    assert 'compatibility_score' in target
    # Privacy check: Phone & email masked!
    assert 'phone' not in target
    assert 'email' not in target

    # 4. Express interest (Like)
    resp_like = client.post('/api/v1/roommates/interest', headers={'X-User-Id': str(u1.id)}, json={
        'target_user_id': u2.id,
        'action': 'like'
    })
    assert resp_like.status_code == 200
    assert resp_like.json['status'] == 'success'
    assert resp_like.json['is_mutual_match'] is False

    # 5. Send roommate request
    resp_req = client.post('/api/v1/roommates/request', headers={'X-User-Id': str(u1.id)}, json={
        'receiver_id': u2.id,
        'proposed_split_rent': 7500,
        'message': 'Hi from Android!'
    })
    assert resp_req.status_code == 201
    assert resp_req.json['status'] == 'success'
    req_id = resp_req.json['data']['id']

    # 6. Candidate 2 accepts via API
    resp_action = client.post(f'/api/v1/roommates/requests/{req_id}/action', headers={'X-User-Id': str(u2.id)}, json={
        'action': 'accept'
    })
    assert resp_action.status_code == 200
    assert resp_action.json['data']['status'] == 'accepted'
