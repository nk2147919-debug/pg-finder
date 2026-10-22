from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class PropertyForm(FlaskForm):
    name = StringField('PG Name', validators=[DataRequired(), Length(max=150)])
    locality = SelectField('Locality in Bengaluru', choices=[
        ('Koramangala', 'Koramangala'),
        ('HSR Layout', 'HSR Layout'),
        ('Indiranagar', 'Indiranagar'),
        ('Whitefield', 'Whitefield'),
        ('Electronic City', 'Electronic City'),
        ('BTM Layout', 'BTM Layout'),
        ('Marathahalli', 'Marathahalli'),
        ('Bellandur', 'Bellandur'),
        ('JP Nagar', 'JP Nagar'),
        ('Jayanagar', 'Jayanagar'),
        ('Hebbal', 'Hebbal'),
        ('Banashankari', 'Banashankari'),
        ('Malleshwaram', 'Malleshwaram'),
        ('Sarjapur Road', 'Sarjapur Road'),
        ('Manyata Tech Park', 'Manyata Tech Park / Nagavara')
    ], validators=[DataRequired()])
    sub_locality = StringField('Sub-locality / Sector / Block (e.g. 5th Block, Sector 3)', validators=[Optional(), Length(max=100)])
    address = TextAreaField('Complete Physical Address', validators=[DataRequired()])
    pincode = StringField('PIN Code (Bengaluru)', validators=[DataRequired(), Length(min=6, max=6)])
    latitude = FloatField('Latitude (e.g. 12.9352)', validators=[DataRequired()])
    longitude = FloatField('Longitude (e.g. 77.6245)', validators=[DataRequired()])
    nearest_landmark = StringField('Nearest Landmark / Metro / Tech Park', validators=[Optional(), Length(max=150)])
    metro_distance_km = FloatField('Distance to nearest Metro Station (km)', validators=[Optional(), NumberRange(min=0)])
    bus_distance_km = FloatField('Distance to nearest Bus Stop (km)', validators=[Optional(), NumberRange(min=0)])

    gender_policy = SelectField('Gender Accommodation Policy', choices=[
        ('gents', "Gents PG / Boys PG"),
        ('ladies', "Ladies PG / Girls PG"),
        ('unisex', "Coliving / Unisex PG")
    ], validators=[DataRequired()])
    property_type = SelectField('Property Category', choices=[
        ('standard', 'Standard Budget PG'),
        ('premium', 'Premium PG'),
        ('luxury', 'Luxury Coliving Space')
    ], default='standard')

    description = TextAreaField('Property Description & Overview', validators=[DataRequired()])
    house_rules = TextAreaField('House Rules (e.g. Visitors, Curfew, Smoking)', validators=[Optional()])
    gate_closing_time = StringField('Gate Closing / Curfew Time (e.g. 11:00 PM or No curfew)', default='11:00 PM')
    notice_period_days = IntegerField('Notice Period (Days)', default=30, validators=[DataRequired(), NumberRange(min=0)])
    minimum_stay_months = IntegerField('Minimum Stay (Months)', default=1, validators=[DataRequired(), NumberRange(min=1)])

    deposit_months = FloatField('Security Deposit (in Months of Rent)', default=1.0, validators=[DataRequired(), NumberRange(min=0)])
    maintenance_charges = FloatField('Monthly Maintenance Charges (₹, if any)', default=0.0, validators=[Optional(), NumberRange(min=0)])
    electricity_charges_type = SelectField('Electricity Charges Policy', choices=[
        ('included', 'Included in Monthly Rent'),
        ('per_unit', 'As per sub-meter consumption (₹/unit)'),
        ('fixed', 'Fixed additional monthly charge')
    ], default='included')

    cover_image = FileField('Upload Cover Photograph', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    has_inhouse_gym = BooleanField('Does your PG have an in-house gym located on the premises?')
    submit = SubmitField('Save Property')


class RoomTypeForm(FlaskForm):
    sharing_type = SelectField('Sharing Type', choices=[
        ('single', 'Single Sharing (Private Room)'),
        ('double', '2 Sharing (Double Room)'),
        ('triple', '3 Sharing (Triple Room)'),
        ('four_plus', '4+ Sharing Room')
    ], validators=[DataRequired()])
    title = StringField('Room Title / Description', validators=[DataRequired(), Length(max=100)])
    monthly_rent = FloatField('Monthly Rent per Bed (₹)', validators=[DataRequired(), NumberRange(min=1000)])
    deposit_amount = FloatField('Security Deposit per Bed (₹)', validators=[DataRequired(), NumberRange(min=0)])
    total_beds = IntegerField('Total Number of Beds in this category', validators=[DataRequired(), NumberRange(min=1)])
    occupied_beds = IntegerField('Occupied Beds', default=0, validators=[Optional(), NumberRange(min=0)])
    vacant_beds = IntegerField('Currently Available / Vacant Beds', validators=[DataRequired(), NumberRange(min=0)])
    has_ac = BooleanField('Air Conditioner (AC)')
    has_attached_bathroom = BooleanField('Attached Bathroom', default=True)
    has_balcony = BooleanField('Private Balcony')
    availability_date = DateField('Available From Date', validators=[DataRequired()])
    submit = SubmitField('Save Room Option')


class FoodMenuForm(FlaskForm):
    food_type = SelectField('Food Type Offered', choices=[
        ('both', 'Veg & Non-Veg (Separate cooking/serving)'),
        ('veg', 'Pure Vegetarian'),
        ('non_veg', 'Non-Veg Friendly')
    ], default='both')
    meals_provided = StringField('Meals Provided', default='Breakfast, Dinner on weekdays & 3 meals on weekends')
    food_included_in_rent = BooleanField('Food included in rent', default=True)
    additional_food_charge = FloatField('Additional Monthly Food Charge (if optional, ₹)', default=0.0)
    breakfast_timings = StringField('Breakfast Timings', default='7:30 AM - 9:30 AM')
    lunch_timings = StringField('Lunch Timings', default='1:00 PM - 2:30 PM')
    dinner_timings = StringField('Dinner Timings', default='8:00 PM - 10:00 PM')
    special_sunday_menu = StringField('Special Weekend / Sunday Menu', default='Special Chicken / Veg Biryani with Sweet')
    submit = SubmitField('Update Food Menu')
