from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # 'customer', 'owner', 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner_profile = db.relationship('OwnerProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    properties = db.relationship('Property', back_populates='owner', cascade='all, delete-orphan')
    enquiries = db.relationship('Enquiry', back_populates='customer', cascade='all, delete-orphan')
    visit_requests = db.relationship('VisitRequest', back_populates='customer', cascade='all, delete-orphan')
    favourites = db.relationship('Favourite', back_populates='user', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='user', cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', back_populates='reporter', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    short_stay_bookings = db.relationship('ShortStayBooking', back_populates='customer', cascade='all, delete-orphan')
    roommate_profile = db.relationship('RoommateProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    pg_residencies = db.relationship('PGResident', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class OwnerProfile(db.Model):
    __tablename__ = 'owner_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    business_name = db.Column(db.String(150), nullable=True)
    pan_or_gst = db.Column(db.String(50), nullable=True)
    id_proof_type = db.Column(db.String(50), nullable=True)  # Aadhaar, PAN, Passport
    id_proof_number = db.Column(db.String(50), nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_status = db.Column(db.String(30), default='unverified', nullable=False)  # 'unverified', 'pending', 'verified', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='owner_profile')
