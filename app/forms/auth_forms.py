from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp
from app.models.user import User


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(message="Email is required"), Email(message="Please enter a valid email address")])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required")])
    remember_me = BooleanField('Keep me signed in')
    submit = SubmitField('Sign In to PG Finder')


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(message="Full name is required"), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(message="Email is required"), Email(message="Please enter a valid email address"), Length(max=120)])
    phone = StringField('Mobile Number (10 Digits)', validators=[
        DataRequired(message="Mobile number is required"),
        Length(min=10, max=15),
        Regexp(r'^[0-9+ \-]+$', message="Mobile number can only contain digits, +, and -")
    ])
    role = SelectField('Register As', choices=[('customer', 'Looking for PG (Customer)'), ('owner', 'PG Owner / Property Manager')], default='customer')
    business_name = StringField('PG Name / Business Name (Owners only)', validators=[Length(max=150)])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required"), Length(min=6, message='Password must be at least 6 characters')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(message="Please confirm your password"), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('This email address is already registered. Please log in instead.')


class MobileLoginForm(FlaskForm):
    country_code = SelectField('Country', choices=[
        ('+91', '🇮🇳 India (+91)'),
        ('+1', '🇺🇸 USA / Canada (+1)'),
        ('+44', '🇬🇧 UK (+44)'),
        ('+971', '🇦🇪 UAE (+971)'),
        ('+65', '🇸🇬 Singapore (+65)'),
        ('+61', '🇦🇺 Australia (+61)')
    ], default='+91')
    mobile_number = StringField('Mobile Number', validators=[
        DataRequired(message="Please enter your mobile number"),
        Length(min=7, max=15)
    ])
    submit = SubmitField('Get Verification OTP')


class VerifyOTPForm(FlaskForm):
    country_code = HiddenField('Country Code', default='+91')
    mobile_number = HiddenField('Mobile Number')
    otp_code = StringField('6-Digit OTP', validators=[
        DataRequired(message="Please enter the 6-digit OTP"),
        Length(min=6, max=6, message="OTP must be exactly 6 digits"),
        Regexp(r'^\d{6}$', message="OTP must contain digits only")
    ])
    name = StringField('Your Name (for new accounts)', validators=[Length(max=100)])
    role = SelectField('Account Type', choices=[('customer', 'Looking for PG (Customer)'), ('owner', 'PG Owner')], default='customer')
    submit = SubmitField('Verify & Continue')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Registered Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    submit = SubmitField('Send Password Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password"),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password & Sign In')
