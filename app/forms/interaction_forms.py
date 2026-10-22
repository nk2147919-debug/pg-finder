from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, DateField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class EnquiryForm(FlaskForm):
    room_type_id = SelectField('Preferred Room Sharing', coerce=int, validators=[Optional()])
    move_in_date = DateField('Expected Move-in Date', validators=[DataRequired()])
    budget_max = FloatField('Your Approximate Monthly Budget (₹)', validators=[Optional(), NumberRange(min=1000)])
    message = TextAreaField('Message to PG Owner', validators=[DataRequired(), Length(min=10, max=500)], default="Hi, I am interested in this PG accommodation and would like to check availability and details.")
    submit = SubmitField('Send Enquiry')


class VisitRequestForm(FlaskForm):
    preferred_date = DateField('Preferred Visit Date', validators=[DataRequired()])
    preferred_time_slot = SelectField('Preferred Time Slot', choices=[
        ('Morning (9:00 AM - 12:00 PM)', 'Morning (9:00 AM - 12:00 PM)'),
        ('Afternoon (12:00 PM - 4:00 PM)', 'Afternoon (12:00 PM - 4:00 PM)'),
        ('Evening (4:00 PM - 8:00 PM)', 'Evening (4:00 PM - 8:00 PM)')
    ], validators=[DataRequired()])
    alternate_date = DateField('Alternate Date (Optional)', validators=[Optional()])
    notes = TextAreaField('Any specific queries / notes', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Schedule In-Person Visit')


class ReviewForm(FlaskForm):
    rating = SelectField('Overall Rating (1 to 5 Stars)', choices=[
        ('5', '⭐⭐⭐⭐⭐ 5 - Excellent'),
        ('4', '⭐⭐⭐⭐ 4 - Good'),
        ('3', '⭐⭐⭐ 3 - Average'),
        ('2', '⭐⭐ 2 - Poor'),
        ('1', '⭐ 1 - Terrible')
    ], validators=[DataRequired()])
    cleanliness_rating = SelectField('Cleanliness & Hygiene', choices=[('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')], default='4')
    food_rating = SelectField('Food Quality & Taste', choices=[('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')], default='4')
    amenities_rating = SelectField('Amenities & Wi-Fi', choices=[('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')], default='4')
    stay_duration = SelectField('How long did you stay here?', choices=[
        ('Currently Staying', 'Currently Staying'),
        ('1 - 3 months', '1 - 3 months'),
        ('3 - 6 months', '3 - 6 months'),
        ('6 - 12 months', '6 - 12 months'),
        ('More than 1 year', 'More than 1 year')
    ], default='Currently Staying')
    review_text = TextAreaField('Detailed Review & Experience', validators=[DataRequired(), Length(min=20, max=1000)])
    submit = SubmitField('Submit Review')


class ComplaintForm(FlaskForm):
    category = SelectField('Issue Category', choices=[
        ('misleading_photos', 'Misleading / Fake Room Photos'),
        ('fake_pricing', 'Incorrect Pricing or Hidden Charges'),
        ('unresponsive_owner', 'Owner Not Responding / Refused Visit'),
        ('hygiene_issue', 'Serious Hygiene or Safety Concern'),
        ('other', 'Other Issue')
    ], validators=[DataRequired()])
    description = TextAreaField('Explain the issue in detail', validators=[DataRequired(), Length(min=15, max=1000)])
    submit = SubmitField('Submit Report')
