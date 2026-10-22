"""
Gym Facility Forms
------------------
WTForms for the Owner Dashboard gym management page.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import (
    BooleanField, SelectField, FloatField, IntegerField,
    StringField, TextAreaField, SubmitField
)
from wtforms.validators import Optional, NumberRange, Length

from app.models.gym import GYM_EQUIPMENT_CHOICES, GYM_EQUIPMENT_LABELS


class GymFacilityForm(FlaskForm):
    """Form for owner to configure/update the gym facility on their PG."""

    # --- Master toggle ---
    is_available = BooleanField(
        'My PG has an in-house gym on the premises',
        default=False
    )

    # --- Access pricing ---
    access_type = SelectField(
        'Gym Access for Residents',
        choices=[
            ('free', 'Free — Included in monthly PG rent'),
            ('paid', 'Paid — Residents pay an additional monthly fee'),
        ],
        default='free'
    )
    monthly_fee = FloatField(
        'Additional Monthly Fee (₹)',
        validators=[Optional(), NumberRange(min=0, max=50000)],
        default=0.0
    )

    # --- Timings & capacity ---
    opening_time = StringField(
        'Gym Opening Time',
        validators=[Optional(), Length(max=30)],
        default='6:00 AM'
    )
    closing_time = StringField(
        'Gym Closing Time',
        validators=[Optional(), Length(max=30)],
        default='10:00 PM'
    )
    capacity = IntegerField(
        'Maximum Capacity (concurrent users)',
        validators=[Optional(), NumberRange(min=1, max=500)],
        default=None
    )

    # --- Maintenance ---
    maintenance_schedule = StringField(
        'Maintenance Schedule',
        validators=[Optional(), Length(max=255)],
        default=''
    )

    # --- Content ---
    description = TextAreaField(
        'Gym Description',
        validators=[Optional(), Length(max=1000)]
    )
    usage_rules = TextAreaField(
        'Gym Usage Rules & Guidelines',
        validators=[Optional(), Length(max=2000)]
    )

    # --- Temporary unavailability ---
    is_temporarily_unavailable = BooleanField(
        'Temporarily mark gym as unavailable (e.g. during renovation/maintenance)',
        default=False
    )
    unavailability_reason = StringField(
        'Reason for Unavailability',
        validators=[Optional(), Length(max=200)]
    )

    # --- Photo upload ---
    photos = MultipleFileField(
        'Upload Gym Photos (JPEG/PNG, max 6)',
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')]
    )

    submit = SubmitField('Save Gym Settings')
