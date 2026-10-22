import builtins
from datetime import datetime, date
from app import db


class RoomType(db.Model):
    __tablename__ = 'room_types'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    sharing_type = db.Column(db.String(20), nullable=False)  # 'single', 'double', 'triple', 'four_plus'
    title = db.Column(db.String(100), nullable=False)
    monthly_rent = db.Column(db.Float, nullable=False)
    deposit_amount = db.Column(db.Float, nullable=False)
    total_beds = db.Column(db.Integer, nullable=False, default=1)
    occupied_beds = db.Column(db.Integer, nullable=False, default=0)
    vacant_beds = db.Column(db.Integer, nullable=False, default=1)
    has_ac = db.Column(db.Boolean, default=False)
    has_attached_bathroom = db.Column(db.Boolean, default=True)
    has_balcony = db.Column(db.Boolean, default=False)
    availability_date = db.Column(db.Date, default=date.today)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    property = db.relationship('Property', back_populates='room_types')
    enquiries = db.relationship('Enquiry', back_populates='room_type')

    @builtins.property
    def sharing_label(self):
        labels = {
            'single': 'Single Sharing (Private Room)',
            'double': '2 Sharing (Double)',
            'triple': '3 Sharing (Triple)',
            'four_plus': '4 Sharing'
        }
        return labels.get(self.sharing_type, self.sharing_type.capitalize())

    def to_dict(self):
        return {
            'id': self.id,
            'sharing_type': self.sharing_type,
            'sharing_label': self.sharing_label,
            'title': self.title,
            'monthly_rent': self.monthly_rent,
            'deposit_amount': self.deposit_amount,
            'total_beds': self.total_beds,
            'occupied_beds': self.occupied_beds,
            'vacant_beds': self.vacant_beds,
            'has_ac': self.has_ac,
            'has_attached_bathroom': self.has_attached_bathroom,
            'has_balcony': self.has_balcony,
            'availability_date': self.availability_date.isoformat() if self.availability_date else None,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None
        }
