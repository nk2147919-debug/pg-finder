"""
Gym Facility Model
------------------
Stores in-house gym details linked to a PG property (1-to-1 relationship).
Includes equipment list, timings, capacity, access charges, photos, and rules.
"""

import json
import builtins
from datetime import datetime
from app import db


# Equipment choices available for a gym (stored as JSON array in DB)
GYM_EQUIPMENT_CHOICES = [
    'dumbbells',
    'barbells',
    'weight_benches',
    'treadmill',
    'exercise_bike',
    'cable_machine',
    'yoga_mats',
    'pull_up_bar',
    'kettlebells',
    'rowing_machine',
    'elliptical',
    'multi_gym_station',
]

GYM_EQUIPMENT_LABELS = {
    'dumbbells': 'Dumbbells',
    'barbells': 'Barbells',
    'weight_benches': 'Weight Benches',
    'treadmill': 'Treadmill',
    'exercise_bike': 'Exercise Bike',
    'cable_machine': 'Cable Machine',
    'yoga_mats': 'Yoga Mats',
    'pull_up_bar': 'Pull-Up Bar',
    'kettlebells': 'Kettlebells',
    'rowing_machine': 'Rowing Machine',
    'elliptical': 'Elliptical Trainer',
    'multi_gym_station': 'Multi-Gym Station',
}

GYM_EQUIPMENT_ICONS = {
    'dumbbells': 'bi-trophy-fill',
    'barbells': 'bi-bar-chart-fill',
    'weight_benches': 'bi-layout-three-columns',
    'treadmill': 'bi-activity',
    'exercise_bike': 'bi-bicycle',
    'cable_machine': 'bi-link-45deg',
    'yoga_mats': 'bi-grid-1x2-fill',
    'pull_up_bar': 'bi-arrows-vertical',
    'kettlebells': 'bi-droplet-fill',
    'rowing_machine': 'bi-arrow-left-right',
    'elliptical': 'bi-arrow-repeat',
    'multi_gym_station': 'bi-diagram-3-fill',
}


class GymFacility(db.Model):
    __tablename__ = 'gym_facilities'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey('properties.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True
    )

    # Master toggle — owner confirms gym exists inside the PG premises
    is_available = db.Column(db.Boolean, default=False, nullable=False)

    # Temporarily unavailable (e.g. maintenance without deleting the gym entry)
    is_temporarily_unavailable = db.Column(db.Boolean, default=False, nullable=False)
    unavailability_reason = db.Column(db.String(200), nullable=True)

    # Pricing model
    # 'free'      → included in monthly rent
    # 'paid'      → residents pay an extra fee
    access_type = db.Column(db.String(20), default='free', nullable=False)   # 'free' | 'paid'
    monthly_fee = db.Column(db.Float, default=0.0, nullable=False)           # only relevant when access_type == 'paid'

    # Capacity & timings
    capacity = db.Column(db.Integer, nullable=True)          # max concurrent users
    opening_time = db.Column(db.String(30), default='6:00 AM', nullable=False)
    closing_time = db.Column(db.String(30), default='10:00 PM', nullable=False)

    # Equipment list stored as JSON  (e.g. '["dumbbells", "treadmill"]')
    _equipment = db.Column('equipment', db.Text, default='[]', nullable=False)

    # Free-text fields
    usage_rules = db.Column(db.Text, nullable=True)           # gym-specific rules
    maintenance_schedule = db.Column(db.String(255), nullable=True)  # e.g. "Every Sunday 10 AM – 2 PM"
    description = db.Column(db.Text, nullable=True)            # short blurb about the gym

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    property = db.relationship('Property', back_populates='gym_facility')
    photos = db.relationship(
        'GymPhoto',
        back_populates='gym',
        cascade='all, delete-orphan',
        order_by='GymPhoto.display_order'
    )

    # ------------------------------------------------------------------
    # Equipment JSON helpers
    # ------------------------------------------------------------------
    @builtins.property
    def equipment(self):
        """Return equipment as a Python list."""
        try:
            return json.loads(self._equipment or '[]')
        except (ValueError, TypeError):
            return []

    @equipment.setter
    def equipment(self, value):
        """Accept a list and serialise to JSON."""
        if isinstance(value, list):
            self._equipment = json.dumps(value)
        else:
            self._equipment = '[]'

    @builtins.property
    def equipment_labels(self):
        """Return list of human-readable labels for stored equipment."""
        return [GYM_EQUIPMENT_LABELS.get(e, e.replace('_', ' ').title()) for e in self.equipment]

    @builtins.property
    def equipment_with_icons(self):
        """Return list of dicts {key, label, icon} for template use."""
        return [
            {
                'key': e,
                'label': GYM_EQUIPMENT_LABELS.get(e, e.replace('_', ' ').title()),
                'icon': GYM_EQUIPMENT_ICONS.get(e, 'bi-check-circle'),
            }
            for e in self.equipment
        ]

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @builtins.property
    def is_active(self):
        """True when gym is available AND not temporarily down."""
        return self.is_available and not self.is_temporarily_unavailable

    @builtins.property
    def access_label(self):
        if self.access_type == 'free':
            return 'Included in Rent'
        return f'₹{self.monthly_fee:,.0f}/month extra'

    @builtins.property
    def cover_photo(self):
        if self.photos:
            return self.photos[0].file_path
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'is_available': self.is_available,
            'is_temporarily_unavailable': self.is_temporarily_unavailable,
            'unavailability_reason': self.unavailability_reason,
            'access_type': self.access_type,
            'monthly_fee': self.monthly_fee,
            'capacity': self.capacity,
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'equipment': self.equipment,
            'equipment_labels': self.equipment_labels,
            'usage_rules': self.usage_rules,
            'maintenance_schedule': self.maintenance_schedule,
            'description': self.description,
            'is_active': self.is_active,
            'access_label': self.access_label,
            'cover_photo': self.cover_photo,
        }


class GymPhoto(db.Model):
    __tablename__ = 'gym_photos'

    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(
        db.Integer,
        db.ForeignKey('gym_facilities.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    file_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(150), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    gym = db.relationship('GymFacility', back_populates='photos')
