from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app import db
from app.models.user import User, OwnerProfile
from app.models.property import Property, VerificationRecord
from app.models.interaction import Review, Complaint, Enquiry, VisitRequest, Notification
from app.routes.auth import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_customers = User.query.filter_by(role='customer').count()
    total_owners = User.query.filter_by(role='owner').count()

    total_properties = Property.query.count()
    pending_properties = Property.query.filter_by(status='pending_approval').count()
    approved_properties = Property.query.filter_by(status='approved').count()

    pending_reviews = Review.query.filter_by(status='pending').count()
    open_complaints = Complaint.query.filter_by(status='open').count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stale_count = Property.query.filter(Property.status == 'approved', Property.availability_last_confirmed_at < seven_days_ago).count()

    recent_properties = Property.query.order_by(Property.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_customers=total_customers,
        total_owners=total_owners,
        total_properties=total_properties,
        pending_properties=pending_properties,
        approved_properties=approved_properties,
        pending_reviews=pending_reviews,
        open_complaints=open_complaints,
        stale_count=stale_count,
        recent_properties=recent_properties
    )


@admin_bp.route('/listings')
@login_required
@admin_required
def listings_queue():
    status_filter = request.args.get('status', 'pending_approval')
    if status_filter == 'all':
        properties = Property.query.order_by(Property.created_at.desc()).all()
    else:
        properties = Property.query.filter_by(status=status_filter).order_by(Property.created_at.desc()).all()

    return render_template('admin/listings_queue.html', properties=properties, current_status=status_filter)


@admin_bp.route('/listing/<int:property_id>/action', methods=['POST'])
@login_required
@admin_required
def action_listing(property_id):
    property_obj = Property.query.get_or_404(property_id)
    action = request.form.get('action')
    reason = request.form.get('reason', '')

    if action == 'approve':
        property_obj.status = 'approved'
        property_obj.rejection_reason = None
        # Add verification record if checked
        if request.form.get('mark_verified'):
            rec = VerificationRecord(
                property_id=property_obj.id,
                verified_by_user_id=current_user.id,
                document_type='platform_audit',
                status='verified',
                notes='Listing information and documents approved by admin.',
                verified_at=datetime.utcnow()
            )
            db.session.add(rec)

        notif = Notification(
            user_id=property_obj.owner_id,
            title=f"Listing Approved: {property_obj.name}",
            message="Congratulations! Your PG listing has been approved and is now live to all searchers.",
            link_url=url_for('customer.property_detail', slug=property_obj.slug)
        )
        db.session.add(notif)
        db.session.commit()
        flash(f"Property '{property_obj.name}' is now approved and live!", "success")

    elif action == 'reject':
        property_obj.status = 'rejected'
        property_obj.rejection_reason = reason or "Listing did not meet quality or verification standards."
        notif = Notification(
            user_id=property_obj.owner_id,
            title=f"Listing Requires Attention: {property_obj.name}",
            message=f"Your listing was not approved: {property_obj.rejection_reason}. Please update details.",
            link_url=url_for('owner.edit_property', property_id=property_obj.id)
        )
        db.session.add(notif)
        db.session.commit()
        flash(f"Property '{property_obj.name}' marked as rejected.", "warning")

    return redirect(url_for('admin.listings_queue'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    role_filter = request.args.get('role', 'all')
    if role_filter != 'all':
        all_users = User.query.filter_by(role=role_filter).order_by(User.created_at.desc()).all()
    else:
        all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template('admin/users.html', users=all_users, current_role=role_filter)


@admin_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot suspend your own admin account.", "danger")
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "suspended"
    flash(f"User {user.name} ({user.email}) has been {status_str}.", "info")
    return redirect(url_for('admin.users'))


@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    pending_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=pending_reviews)


@admin_bp.route('/review/<int:review_id>/action', methods=['POST'])
@login_required
@admin_required
def action_review(review_id):
    review = Review.query.get_or_404(review_id)
    action = request.form.get('action')

    if action == 'approve':
        review.status = 'approved'
        flash("Review approved and published to the listing.", "success")
    elif action == 'reject':
        review.status = 'rejected'
        flash("Review rejected and hidden.", "info")

    db.session.commit()
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    all_complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=all_complaints)


@admin_bp.route('/complaint/<int:complaint_id>/action', methods=['POST'])
@login_required
@admin_required
def action_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '')

    if status in ['under_review', 'resolved', 'dismissed']:
        complaint.status = status
        complaint.admin_notes = admin_notes
        if status in ['resolved', 'dismissed']:
            complaint.resolved_at = datetime.utcnow()
        db.session.commit()
        flash(f"Complaint #{complaint.id} status updated to {status}.", "success")

    return redirect(url_for('admin.complaints'))


@admin_bp.route('/stale-alerts')
@login_required
@admin_required
def stale_alerts():
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stale_properties = Property.query.filter(
        Property.status == 'approved',
        Property.availability_last_confirmed_at < seven_days_ago
    ).order_by(Property.availability_last_confirmed_at.asc()).all()

    return render_template('admin/stale_alerts.html', properties=stale_properties)
