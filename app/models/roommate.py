from datetime import datetime, date
from app import db


class RoommateProfile(db.Model):
    __tablename__ = 'roommate_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)

    # Core Preferences
    preferred_locality = db.Column(db.String(100), nullable=False, default='Koramangala')
    min_budget = db.Column(db.Float, nullable=False, default=5000.0)
    max_budget = db.Column(db.Float, nullable=False, default=15000.0)
    occupation = db.Column(db.String(100), nullable=False, default='Software Engineer')
    preferred_sharing = db.Column(db.String(30), nullable=False, default='double')  # 'single', 'double', 'triple', 'any'

    # Lifestyle & Habits
    cleanliness = db.Column(db.String(30), nullable=False, default='moderate')  # 'tidy', 'moderate', 'relaxed'
    food_preference = db.Column(db.String(30), nullable=False, default='any')  # 'veg', 'non_veg', 'vegan', 'eggetarian', 'any'
    sleep_schedule = db.Column(db.String(30), nullable=False, default='flexible')  # 'early_bird', 'night_owl', 'flexible'
    smoking = db.Column(db.String(30), nullable=False, default='non_smoker')  # 'non_smoker', 'smoker', 'outside_only'
    move_in_date = db.Column(db.Date, nullable=False, default=date.today)
    gender_preference = db.Column(db.String(30), nullable=False, default='same_gender')  # 'same_gender', 'any'

    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'paused', 'inactive'

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    looking_for_room = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', back_populates='roommate_profile')

    @property
    def is_active(self):
        return self.status == 'active'

    @is_active.setter
    def is_active(self, value):
        self.status = 'active' if value else 'paused'

    @property
    def preferred_location(self):
        return self.preferred_locality

    @preferred_location.setter
    def preferred_location(self, value):
        self.preferred_locality = value

    @property
    def budget_min(self):
        return self.min_budget

    @budget_min.setter
    def budget_min(self, value):
        self.min_budget = float(value) if value is not None else 0.0

    @property
    def budget_max(self):
        return self.max_budget

    @budget_max.setter
    def budget_max(self, value):
        self.max_budget = float(value) if value is not None else 0.0

    @property
    def preferred_room_type(self):
        return self.preferred_sharing

    @preferred_room_type.setter
    def preferred_room_type(self, value):
        self.preferred_sharing = value

    @property
    def smoking_preference(self):
        return self.smoking

    @smoking_preference.setter
    def smoking_preference(self, value):
        self.smoking = value

    def to_dict(self, include_contact=False, viewer_user=None):
        if viewer_user is not None:
            viewer_id = viewer_user.id if hasattr(viewer_user, 'id') else int(viewer_user)
            if viewer_id == self.user_id:
                include_contact = True
            else:
                # Check mutual match
                i_liked = RoommateInterest.query.filter_by(user_id=viewer_id, target_user_id=self.user_id, action='like').first()
                they_liked = RoommateInterest.query.filter_by(user_id=self.user_id, target_user_id=viewer_id, action='like').first()
                if i_liked and they_liked:
                    include_contact = True
                else:
                    # Or accepted request
                    req = RoommateRequest.query.filter(
                        db.or_(
                            db.and_(RoommateRequest.sender_id == viewer_id, RoommateRequest.receiver_id == self.user_id),
                            db.and_(RoommateRequest.sender_id == self.user_id, RoommateRequest.receiver_id == viewer_id)
                        ),
                        RoommateRequest.status.in_(['accepted', 'owner_approved'])
                    ).first()
                    if req:
                        include_contact = True

        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else 'Anonymous',
            'preferred_locality': self.preferred_locality,
            'preferred_location': self.preferred_locality,
            'min_budget': self.min_budget,
            'max_budget': self.max_budget,
            'budget_min': self.min_budget,
            'budget_max': self.max_budget,
            'occupation': self.occupation,
            'preferred_sharing': self.preferred_sharing,
            'preferred_room_type': self.preferred_sharing,
            'cleanliness': self.cleanliness,
            'food_preference': self.food_preference,
            'sleep_schedule': self.sleep_schedule,
            'smoking': self.smoking,
            'smoking_preference': self.smoking,
            'move_in_date': self.move_in_date.isoformat() if self.move_in_date else None,
            'gender_preference': self.gender_preference,
            'bio': self.bio,
            'status': self.status,
            'is_active': self.is_active,
            'looking_for_room': self.looking_for_room,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_contact and self.user:
            data['phone'] = self.user.phone
            data['email'] = self.user.email
            data['contact_unlocked'] = True
        else:
            data['contact_unlocked'] = False
        return data


class RoommateInterest(db.Model):
    __tablename__ = 'roommate_interests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False, default='like')  # 'like', 'skip'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])
    target_user = db.relationship('User', foreign_keys=[target_user_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'target_user_id', name='uq_user_target_interest'),
    )


class RoommateRequest(db.Model):
    __tablename__ = 'roommate_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True, index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id', ondelete='SET NULL'), nullable=True)

    proposed_split_rent = db.Column(db.Float, nullable=True)
    message = db.Column(db.Text, nullable=True)

    # User Status: 'pending', 'accepted', 'rejected', 'cancelled'
    status = db.Column(db.String(30), default='pending', nullable=False, index=True)

    # Owner Status for shared PG room: 'none' (not property specific), 'pending', 'approved', 'rejected'
    owner_status = db.Column(db.String(30), default='none', nullable=False, index=True)
    owner_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    property = db.relationship('Property')
    room_type = db.relationship('RoomType')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name if self.sender else '',
            'receiver_id': self.receiver_id,
            'receiver_name': self.receiver.name if self.receiver else '',
            'property_id': self.property_id,
            'property_name': self.property.name if self.property else None,
            'room_type_id': self.room_type_id,
            'room_type_title': self.room_type.title if self.room_type else None,
            'proposed_split_rent': self.proposed_split_rent,
            'message': self.message,
            'status': self.status,
            'owner_status': self.owner_status,
            'owner_notes': self.owner_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserBlock(db.Model):
    __tablename__ = 'user_blocks'

    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    blocked_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    blocker = db.relationship('User', foreign_keys=[blocker_id])
    blocked = db.relationship('User', foreign_keys=[blocked_id])

    __table_args__ = (
        db.UniqueConstraint('blocker_id', 'blocked_id', name='uq_blocker_blocked'),
    )


class UserReport(db.Model):
    __tablename__ = 'user_reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='pending', nullable=False)  # 'pending', 'reviewed', 'dismissed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reporter = db.relationship('User', foreign_keys=[reporter_id])
    reported_user = db.relationship('User', foreign_keys=[reported_user_id])
