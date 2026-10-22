from datetime import datetime
from app import db


class Enquiry(db.Model):
    __tablename__ = 'enquiries'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id', ondelete='SET NULL'), nullable=True)
    move_in_date = db.Column(db.Date, nullable=False)
    message = db.Column(db.Text, nullable=False)
    budget_max = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(30), default='new', nullable=False)  # 'new', 'contacted', 'scheduled', 'closed'
    owner_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = db.relationship('User', back_populates='enquiries')
    property = db.relationship('Property', back_populates='enquiries')
    room_type = db.relationship('RoomType', back_populates='enquiries')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer.name if self.customer else 'Anonymous',
            'customer_phone': self.customer.phone if self.customer else '',
            'property_name': self.property.name if self.property else '',
            'property_locality': self.property.locality if self.property else '',
            'move_in_date': self.move_in_date.isoformat() if self.move_in_date else None,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class VisitRequest(db.Model):
    __tablename__ = 'visit_requests'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time_slot = db.Column(db.String(50), default='Morning (9am-12pm)', nullable=False)
    alternate_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), default='requested', nullable=False)  # 'requested', 'accepted', 'declined', 'rescheduled', 'completed', 'cancelled'
    rescheduled_date = db.Column(db.Date, nullable=True)
    rescheduled_time_slot = db.Column(db.String(50), nullable=True)
    owner_message = db.Column(db.Text, nullable=True)
    visit_outcome = db.Column(db.String(50), nullable=True)  # 'moved_in', 'considering', 'declined', 'no_show'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = db.relationship('User', back_populates='visit_requests')
    property = db.relationship('Property', back_populates='visit_requests')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer.name if self.customer else 'Guest',
            'customer_phone': self.customer.phone if self.customer else '',
            'property_name': self.property.name if self.property else '',
            'preferred_date': self.preferred_date.isoformat() if self.preferred_date else None,
            'preferred_time_slot': self.preferred_time_slot,
            'status': self.status,
            'owner_message': self.owner_message,
            'visit_outcome': self.visit_outcome,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Favourite(db.Model):
    __tablename__ = 'favourites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'property_id', name='uq_user_property_favourite'),
    )

    user = db.relationship('User', back_populates='favourites')
    property = db.relationship('Property', back_populates='favourites')


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    cleanliness_rating = db.Column(db.Integer, default=4)
    food_rating = db.Column(db.Integer, default=4)
    amenities_rating = db.Column(db.Integer, default=4)
    review_text = db.Column(db.Text, nullable=False)
    stay_duration = db.Column(db.String(50), nullable=True)  # e.g. "6 months", "1 year"
    status = db.Column(db.String(30), default='pending', nullable=False)  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='reviews')
    property = db.relationship('Property', back_populates='reviews')

    def to_dict(self):
        return {
            'id': self.id,
            'author_name': self.user.name if self.user else 'Anonymous',
            'rating': self.rating,
            'cleanliness_rating': self.cleanliness_rating,
            'food_rating': self.food_rating,
            'amenities_rating': self.amenities_rating,
            'review_text': self.review_text,
            'stay_duration': self.stay_duration,
            'created_at': self.created_at.strftime('%b %d, %Y') if self.created_at else ''
        }


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'misleading_photos', 'fake_pricing', 'unresponsive_owner', 'hygiene_issue', 'other'
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='open', nullable=False)  # 'open', 'under_review', 'resolved', 'dismissed'
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    reporter = db.relationship('User', back_populates='complaints')
    property = db.relationship('Property', back_populates='complaints')


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='notifications')
