from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class ShortStayConfigForm(FlaskForm):
    is_enabled = BooleanField('Enable Short-Stay / Friends Stay for this Property')
    daily_rate = FloatField('Standard Price Per Night (₹)', validators=[DataRequired(), NumberRange(min=200)])
    weekly_rate = FloatField('Discounted Weekly Price (₹ for 7 nights, optional)', validators=[Optional(), NumberRange(min=500)])
    fortnightly_rate = FloatField('Discounted 15-Day Price (₹ for 14-15 nights, optional)', validators=[Optional(), NumberRange(min=1000)])
    base_guests = IntegerField('Number of Guests Included in Base Rate', default=1, validators=[DataRequired(), NumberRange(min=1, max=10)])
    max_guests = IntegerField('Maximum Permitted Occupancy / Friends (Guests)', default=4, validators=[DataRequired(), NumberRange(min=1, max=20)])
    extra_guest_charge = FloatField('Extra Guest Charge (₹ per additional guest per night)', default=350.0, validators=[DataRequired(), NumberRange(min=0)])

    min_nights = IntegerField('Minimum Stay Required (Nights)', default=1, validators=[DataRequired(), NumberRange(min=1)])
    max_nights = IntegerField('Maximum Stay Allowed (Nights)', default=30, validators=[DataRequired(), NumberRange(min=1)])

    security_deposit = FloatField('Refundable Security Deposit (₹)', default=1000.0, validators=[Optional(), NumberRange(min=0)])
    cleaning_fee = FloatField('One-time Cleaning / Linen Fee (₹)', default=200.0, validators=[Optional(), NumberRange(min=0)])
    tax_percentage = FloatField('Tax Percentage (GST %)', default=5.0, validators=[Optional(), NumberRange(min=0, max=28)])

    check_in_time = StringField('Standard Check-in Time', default='12:00 PM', validators=[DataRequired()])
    check_out_time = StringField('Standard Check-out Time', default='11:00 AM', validators=[DataRequired()])
    cancellation_policy = StringField('Cancellation & Refund Policy', default='Free cancellation up to 24 hours before check-in', validators=[DataRequired()])
    short_stay_rules = TextAreaField('Short Stay House Rules (ID proof, visitors, noise curfew)', validators=[Optional()])
    submit = SubmitField('Save Short-Stay Settings')


class ShortStayBookingForm(FlaskForm):
    check_in_date = DateField('Check-in Date', validators=[DataRequired()])
    check_out_date = DateField('Check-out Date', validators=[DataRequired()])
    num_guests = IntegerField('Number of Guests', default=1, validators=[DataRequired(), NumberRange(min=1, max=20)])
    room_type_id = SelectField('Preferred Room Option', coerce=int, validators=[Optional()])
    primary_guest_name = StringField('Full Name of Lead Guest', validators=[DataRequired(), Length(min=2, max=100)])
    primary_guest_phone = StringField('Mobile Number for Confirmation', validators=[DataRequired(), Length(min=10, max=15)])
    primary_guest_id_proof = StringField('ID Proof Number (Aadhaar / Passport / Student ID)', validators=[Optional()])
    special_requests = TextAreaField('Special Requests / Estimated Arrival Time', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit Booking Request')


class BlockedDateForm(FlaskForm):
    date = DateField('Date to Block', validators=[DataRequired()])
    reason = StringField('Reason (e.g. Maintenance, Private event)', default='Owner Blocked', validators=[Optional()])
    submit = SubmitField('Block Date')


class PaymentConfirmationForm(FlaskForm):
    amount = FloatField('Payment Amount (₹)', validators=[DataRequired(), NumberRange(min=1)])
    payment_method = SelectField('Payment Method', choices=[
        ('UPI', 'UPI (Google Pay / PhonePe / Paytm / BHIM)'),
        ('Credit Card', 'Credit / Debit Card'),
        ('Net Banking', 'Net Banking'),
        ('Advance', 'Direct Owner Advance (Cash / Bank Transfer)')
    ], default='UPI')
    notes = StringField('Transaction Ref / Notes', validators=[Optional()])
    submit = SubmitField('Confirm & Issue Official Receipt')
