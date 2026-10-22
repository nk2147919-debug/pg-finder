from datetime import datetime
import re
from app import db


class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    locality = db.Column(db.String(100), nullable=False, index=True)  # Koramangala, HSR Layout, etc.
    sub_locality = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(50), default='Bengaluru', nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    nearest_landmark = db.Column(db.String(150), nullable=True)
    metro_distance_km = db.Column(db.Float, nullable=True)
    bus_distance_km = db.Column(db.Float, nullable=True)

    # Policy and category
    gender_policy = db.Column(db.String(20), nullable=False, default='unisex')  # 'gents', 'ladies', 'unisex'
    property_type = db.Column(db.String(30), nullable=False, default='standard')  # 'standard', 'premium', 'luxury'
    
    # Details & Rules
    description = db.Column(db.Text, nullable=False)
    house_rules = db.Column(db.Text, nullable=True)
    gate_closing_time = db.Column(db.String(30), nullable=True, default='11:00 PM')
    notice_period_days = db.Column(db.Integer, default=30)
    minimum_stay_months = db.Column(db.Integer, default=1)
    
    # Commercials
    deposit_months = db.Column(db.Float, default=1.0)
    maintenance_charges = db.Column(db.Float, default=0.0)
    electricity_charges_type = db.Column(db.String(50), default='included')  # 'included', 'per_unit', 'fixed'

    # Approval and listing status
    status = db.Column(db.String(30), default='pending_approval', nullable=False, index=True)  # 'pending_approval', 'approved', 'rejected', 'archived'
    rejection_reason = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    views_count = db.Column(db.Integer, default=0)

    # Freshness Timestamps
    availability_last_confirmed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    price_last_confirmed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    menu_last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    photos_last_verified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = db.relationship('User', back_populates='properties')
    room_types = db.relationship('RoomType', back_populates='property', cascade='all, delete-orphan', lazy='joined')
    amenities = db.relationship('PropertyAmenity', back_populates='property', cascade='all, delete-orphan')
    media = db.relationship('PropertyMedia', back_populates='property', cascade='all, delete-orphan')
    food_menu = db.relationship('FoodMenu', back_populates='property', uselist=False, cascade='all, delete-orphan')
    enquiries = db.relationship('Enquiry', back_populates='property', cascade='all, delete-orphan')
    visit_requests = db.relationship('VisitRequest', back_populates='property', cascade='all, delete-orphan')
    favourites = db.relationship('Favourite', back_populates='property', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='property', cascade='all, delete-orphan')
    verification_records = db.relationship('VerificationRecord', back_populates='property', cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', back_populates='property', cascade='all, delete-orphan')
    short_stay_config = db.relationship('ShortStayConfig', back_populates='property', uselist=False, cascade='all, delete-orphan')
    short_stay_bookings = db.relationship('ShortStayBooking', back_populates='property', cascade='all, delete-orphan')
    blocked_dates = db.relationship('BlockedDate', cascade='all, delete-orphan')
    gym_facility = db.relationship('GymFacility', back_populates='property', uselist=False, cascade='all, delete-orphan')
    community_posts = db.relationship('PGCommunityPost', back_populates='property', cascade='all, delete-orphan', order_by='PGCommunityPost.created_at.desc()')

    @property
    def has_short_stay(self):
        return bool(self.short_stay_config and self.short_stay_config.is_enabled)

    @property
    def has_gym(self):
        return bool(self.gym_facility and self.gym_facility.is_available)

    @property
    def short_stay_price(self):
        return self.short_stay_config.daily_rate if self.short_stay_config else 0.0

    @property
    def starting_price(self):
        rents = [rt.monthly_rent for rt in self.room_types if rt.monthly_rent]
        return min(rents) if rents else 0.0

    @property
    def total_vacant_beds(self):
        return sum(rt.vacant_beds for rt in self.room_types if rt.vacant_beds)

    @property
    def total_beds(self):
        return sum(rt.total_beds for rt in self.room_types if rt.total_beds)

    @property
    def sharing_types(self):
        types = set()
        for rt in self.room_types:
            types.add(rt.sharing_type)
        return sorted(list(types))

    @property
    def cover_image(self):
        for m in self.media:
            if m.is_cover:
                return m.file_path
        if self.media:
            return self.media[0].file_path
        return '/static/images/pg-default.svg'

    @property
    def average_rating(self):
        approved = [r for r in self.reviews if r.status == 'approved']
        if not approved:
            return None
        return round(sum(r.rating for r in approved) / len(approved), 1)

    @property
    def review_count(self):
        return len([r for r in self.reviews if r.status == 'approved'])

    @staticmethod
    def generate_slug(name, locality):
        base = f"{name}-{locality}".lower()
        base = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
        return base

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'locality': self.locality,
            'sub_locality': self.sub_locality,
            'address': self.address,
            'city': self.city,
            'pincode': self.pincode,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'nearest_landmark': self.nearest_landmark,
            'metro_distance_km': self.metro_distance_km,
            'gender_policy': self.gender_policy,
            'property_type': self.property_type,
            'description': self.description,
            'starting_price': self.starting_price,
            'total_vacant_beds': self.total_vacant_beds,
            'cover_image': self.cover_image,
            'average_rating': self.average_rating,
            'review_count': self.review_count,
            'status': self.status,
            'is_featured': self.is_featured,
            'availability_last_confirmed_at': self.availability_last_confirmed_at.isoformat() if self.availability_last_confirmed_at else None,
            'price_last_confirmed_at': self.price_last_confirmed_at.isoformat() if self.price_last_confirmed_at else None,
            'menu_last_updated_at': self.menu_last_updated_at.isoformat() if self.menu_last_updated_at else None,
            'has_short_stay': self.has_short_stay,
            'short_stay_rate': self.short_stay_price,
            'short_stay_config': self.short_stay_config.to_dict() if self.has_short_stay else None,
            'has_gym': self.has_gym,
            'gym': self.gym_facility.to_dict() if (self.gym_facility and self.gym_facility.is_available) else None,
        }


class Amenity(db.Model):
    __tablename__ = 'amenities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), nullable=False)  # bi-wifi, bi-tv, bi-snow, etc.
    category = db.Column(db.String(50), default='comfort')  # 'comfort', 'connectivity', 'utility', 'security', 'food'

    properties = db.relationship('PropertyAmenity', back_populates='amenity')


class PropertyAmenity(db.Model):
    __tablename__ = 'property_amenities'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenities.id', ondelete='CASCADE'), nullable=False)
    details = db.Column(db.String(150), nullable=True)

    property = db.relationship('Property', back_populates='amenities')
    amenity = db.relationship('Amenity', back_populates='properties')


class PropertyMedia(db.Model):
    __tablename__ = 'property_media'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(150), nullable=True)
    is_cover = db.Column(db.Boolean, default=False)
    media_type = db.Column(db.String(20), default='image')  # 'image', 'video'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    property = db.relationship('Property', back_populates='media')


class VerificationRecord(db.Model):
    __tablename__ = 'verification_records'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    document_type = db.Column(db.String(80), nullable=False)  # electricity_bill, trade_license, physical_inspection
    document_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default='pending', nullable=False)  # pending, verified, rejected
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)

    property = db.relationship('Property', back_populates='verification_records')
    verified_by = db.relationship('User', foreign_keys=[verified_by_user_id])
