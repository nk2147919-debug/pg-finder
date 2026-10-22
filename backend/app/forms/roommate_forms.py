from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class RoommateProfileForm(FlaskForm):
    preferred_location = StringField('Preferred Bengaluru Locality', validators=[DataRequired(), Length(max=120)])
    budget_min = FloatField('Minimum Monthly Budget (₹)', default=5000, validators=[DataRequired(), NumberRange(min=1000)])
    budget_max = FloatField('Maximum Monthly Budget (₹)', default=15000, validators=[DataRequired(), NumberRange(min=1000)])
    occupation = StringField('Occupation / Company / College', validators=[DataRequired(), Length(max=100)])
    
    preferred_room_type = SelectField('Preferred Room Sharing', choices=[
        ('single', 'Single / Private Room'),
        ('double', 'Double Sharing (2 in a room)'),
        ('triple', 'Triple Sharing (3 in a room)'),
        ('any', 'Flexible / Any Sharing')
    ], default='double')

    cleanliness = SelectField('Cleanliness Preference', choices=[
        ('very_clean', 'Very Clean / Daily Tidy'),
        ('moderate', 'Moderate / Standard'),
        ('relaxed', 'Relaxed / Casual')
    ], default='moderate')

    food_preference = SelectField('Food / Dietary Habit', choices=[
        ('veg', 'Vegetarian Only'),
        ('eggetarian', 'Eggetarian'),
        ('non_veg', 'Non-Vegetarian'),
        ('any', 'No Food Restriction / Any')
    ], default='any')

    sleep_schedule = SelectField('Daily Sleep Schedule', choices=[
        ('early_bird', 'Early Bird (Up by 6-7 AM)'),
        ('night_owl', 'Night Owl (Active late night)'),
        ('flexible', 'Flexible / Moderate Routine')
    ], default='flexible')

    smoking_preference = SelectField('Smoking / Drinking Policy', choices=[
        ('non_smoker', 'Strict Non-Smoker'),
        ('occasional', 'Occasional / Outside Only'),
        ('smoker', 'Smoker Friendly'),
        ('flexible', 'Flexible')
    ], default='non_smoker')

    move_in_date = DateField('Expected Move-in Date', validators=[Optional()])
    bio = TextAreaField('About Yourself / What You Value in a Roommate', validators=[Optional(), Length(max=1000)])
    is_active = BooleanField('Active & Discoverable for Roommate Matching', default=True)
    looking_for_room = BooleanField('I am also actively looking for an empty PG/Room together', default=True)
    submit = SubmitField('Save Roommate Profile')


class RoommateRequestForm(FlaskForm):
    property_id = IntegerField('PG Property ID (Optional)', validators=[Optional()])
    room_type_id = IntegerField('Room Type ID (Optional)', validators=[Optional()])
    proposed_split_rent = FloatField('Proposed Monthly Split Rent (₹, Optional)', validators=[Optional(), NumberRange(min=0)])
    message = TextAreaField('Message to Potential Roommate', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Send Roommate Request')


class CommunityPostForm(FlaskForm):
    title = StringField('Post Title', validators=[DataRequired(), Length(min=3, max=200)])
    post_type = SelectField('Category', choices=[
        ('general', '💬 General Discussion'),
        ('question', '❓ Help / Question'),
        ('announcement', '📢 Official Announcement'),
        ('maintenance', '🔧 Maintenance / Notice'),
        ('event', '🎉 Social / Event')
    ], default='general')
    content = TextAreaField('Post Details', validators=[DataRequired(), Length(min=5, max=5000)])
    is_pinned = BooleanField('Pin to Top (Owners & Managers only)')
    submit = SubmitField('Publish Post')


class CommunityCommentForm(FlaskForm):
    content = TextAreaField('Write a reply...', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('Reply')


class SafetyReportForm(FlaskForm):
    reason = SelectField('Reason for Report', choices=[
        ('spam', 'Spam / Commercial advertising'),
        ('harassment', 'Harassment or offensive behavior'),
        ('inappropriate', 'Inappropriate content / language'),
        ('misleading', 'Misleading / inaccurate information'),
        ('fake_profile', 'Suspicious / fake profile'),
        ('other', 'Other policy violation')
    ], default='inappropriate')
    details = TextAreaField('Additional Details / Context', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Report')
