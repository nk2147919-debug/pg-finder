from datetime import date, timedelta
from app import db
from app.models.interaction import Enquiry, VisitRequest, Review, Notification
from app.models.property import Property


def login_as(client, email, password='Password@123'):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def test_customer_enquiry_workflow(client, app, test_users, test_property):
    # Log in as Customer
    login_as(client, 'customer@example.com')

    # Send Enquiry
    move_in = date.today() + timedelta(days=7)
    res = client.post(f'/property/{test_property.id}/enquiry', data={
        'room_type_id': test_property.room_types[0].id,
        'move_in_date': move_in.strftime('%Y-%m-%d'),
        'budget_max': '15000',
        'message': 'Hi, I work at Embassy Golf Links. Is the room vacant for immediate move-in?'
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        enquiry = Enquiry.query.filter_by(property_id=test_property.id).first()
        assert enquiry is not None
        assert enquiry.status == 'new'
        assert enquiry.customer_id == test_users['customer'].id

        # Notification for owner
        notif = Notification.query.filter_by(user_id=test_property.owner_id).first()
        assert notif is not None
        assert "New Enquiry" in notif.title


def test_owner_updates_enquiry_status(client, app, test_users, test_property):
    # First create enquiry in DB
    with app.app_context():
        enq = Enquiry(
            customer_id=test_users['customer'].id,
            property_id=test_property.id,
            move_in_date=date.today() + timedelta(days=5),
            message="Interested in double sharing",
            status="new"
        )
        db.session.add(enq)
        db.session.commit()
        enq_id = enq.id

    # Log in as Owner 1
    login_as(client, 'owner1@example.com')

    # Update status to 'contacted'
    res = client.post(f'/owner/enquiry/{enq_id}/status', data={
        'status': 'contacted',
        'owner_notes': 'Spoke on call, interested in 1st floor'
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        enq = Enquiry.query.get(enq_id)
        assert enq.status == 'contacted'
        assert 'Spoke on call' in enq.owner_notes


def test_review_submission_and_admin_approval(client, app, test_users, test_property):
    # Customer submits review
    login_as(client, 'customer@example.com')
    res = client.post(f'/property/{test_property.id}/review', data={
        'rating': '5',
        'cleanliness_rating': '5',
        'food_rating': '5',
        'amenities_rating': '5',
        'stay_duration': '3 - 6 months',
        'review_text': 'Exceptional stay in Koramangala! Very quiet rooms, fast Wi-Fi, and tasty food.'
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        review = Review.query.filter_by(property_id=test_property.id).first()
        assert review is not None
        assert review.status == 'pending'  # Must be pending moderation!
        assert test_property.review_count == 0  # Unapproved reviews do NOT count yet!
        rev_id = review.id

    # Switch session: logout customer, login admin
    client.get('/auth/logout')
    login_as(client, 'admin@example.com')
    admin_res = client.post(f'/admin/review/{rev_id}/action', data={
        'action': 'approve'
    }, follow_redirects=True)

    assert admin_res.status_code == 200
    with app.app_context():
        review = Review.query.get(rev_id)
        assert review.status == 'approved'
        prop = Property.query.get(test_property.id)
        assert prop.review_count == 1
        assert prop.average_rating == 5.0
