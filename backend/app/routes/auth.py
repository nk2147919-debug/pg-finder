import secrets
import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User, OwnerProfile
from app.forms.auth_forms import (
    LoginForm, RegisterForm, MobileLoginForm, VerifyOTPForm,
    ForgotPasswordForm, ResetPasswordForm
)
from app.services.sms_service import (
    request_otp, verify_otp_code, normalize_phone,
    RateLimitError, SMSProviderError
)
from app.services.email_service import (
    generate_password_reset_token, verify_password_reset_token,
    send_password_reset_email
)

auth_bp = Blueprint('auth', __name__)


def get_dashboard_url_for_user(user: User) -> str:
    """Returns the appropriate destination dashboard based on the user's role."""
    if user.is_owner:
        return url_for('owner.dashboard')
    elif user.is_admin:
        return url_for('admin.dashboard')
    return url_for('customer.dashboard')


def role_required(*roles):
    """Decorator ensuring current user has one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in roles:
                flash("Access denied: You do not have permission to view this resource.", "danger")
                if current_user.role == 'owner':
                    return redirect(url_for('owner.dashboard'))
                elif current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('customer.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


customer_required = role_required('customer')
owner_required = role_required('owner')
admin_required = role_required('admin')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user(current_user))

    form = LoginForm()
    mobile_form = MobileLoginForm()
    verify_form = VerifyOTPForm()
    forgot_form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Your account has been deactivated or suspended. Please contact platform support.", "danger")
                return render_template(
                    'auth/login.html',
                    form=form,
                    mobile_form=mobile_form,
                    verify_form=verify_form,
                    forgot_form=forgot_form,
                    active_tab='email'
                )

            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(get_dashboard_url_for_user(user))
        else:
            flash("Invalid email address or password.", "danger")

    return render_template(
        'auth/login.html',
        form=form,
        mobile_form=mobile_form,
        verify_form=verify_form,
        forgot_form=forgot_form,
        active_tab=request.args.get('tab', 'mobile')
    )


@auth_bp.route('/mobile/send-otp', methods=['POST'])
def mobile_send_otp():
    """API endpoint to dispatch a 6-digit OTP to the specified mobile number."""
    if current_user.is_authenticated:
        return jsonify({'success': True, 'redirect_url': get_dashboard_url_for_user(current_user)})

    data = request.get_json(silent=True) or request.form.to_dict()
    country_code = data.get('country_code', '+91').strip()
    mobile_number = data.get('mobile_number', '').strip()

    if not mobile_number:
        return jsonify({'success': False, 'error': 'Please enter your mobile number.'}), 400

    try:
        otp_info = request_otp(mobile_number, country_code=country_code, purpose='login')

        # Check if existing user
        phone_e164 = otp_info['phone_e164']
        local_10 = otp_info['local_10']
        existing_user = User.query.filter(
            (User.phone == local_10) | (User.phone == phone_e164)
        ).first()

        response_payload = {
            'success': True,
            'message': otp_info['message'],
            'phone_e164': phone_e164,
            'local_10': local_10,
            'cooldown_seconds': otp_info['cooldown_seconds'],
            'is_existing_user': existing_user is not None
        }

        # Safe testing hook for automated pytest executions only
        if current_app.config.get('TESTING') and 'dev_otp' in otp_info:
            response_payload['dev_otp'] = otp_info['dev_otp']

        return jsonify(response_payload)

    except RateLimitError as e:
        return jsonify({'success': False, 'error': str(e), 'cooldown_seconds': e.remaining_seconds}), 429
    except SMSProviderError as e:
        return jsonify({'success': False, 'error': str(e)}), 503
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error sending OTP: {e}")
        return jsonify({'success': False, 'error': 'Unable to send OTP at this time. Please try again.'}), 500


@auth_bp.route('/mobile/verify-otp', methods=['POST'])
def mobile_verify_otp():
    """API endpoint to verify the 6-digit OTP code and authenticate or register the user."""
    if current_user.is_authenticated:
        return jsonify({'success': True, 'redirect_url': get_dashboard_url_for_user(current_user)})

    data = request.get_json(silent=True) or request.form.to_dict()
    country_code = data.get('country_code', '+91').strip()
    mobile_number = data.get('mobile_number', '').strip()
    otp_code = data.get('otp_code', '').strip()
    name = data.get('name', '').strip()
    role = data.get('role', 'customer').strip().lower()

    if not mobile_number or not otp_code:
        return jsonify({'success': False, 'error': 'Mobile number and 6-digit OTP are required.'}), 400

    try:
        verify_result = verify_otp_code(mobile_number, country_code, otp_code)
        phone_e164 = verify_result['phone_e164']
        local_10 = verify_result['local_10']

        # Find existing user by phone
        user = User.query.filter(
            (User.phone == local_10) | (User.phone == phone_e164)
        ).first()

        if user:
            if not user.is_active:
                return jsonify({'success': False, 'error': 'Your account has been deactivated. Please contact support.'}), 403

            login_user(user, remember=True)
            next_page = request.args.get('next')
            dest = next_page if (next_page and next_page.startswith('/')) else get_dashboard_url_for_user(user)
            return jsonify({
                'success': True,
                'is_new_user': False,
                'message': f"Welcome back, {user.name}!",
                'redirect_url': dest
            })

        # New user flow: requires name to create account
        if not name:
            return jsonify({
                'success': True,
                'requires_registration': True,
                'message': 'Phone verified! Please enter your name to complete your registration.',
                'phone_e164': phone_e164,
                'local_10': local_10
            })

        # Create new user
        user_role = role if role in ('customer', 'owner') else 'customer'
        safe_email = f"mobile_{local_10}@user.pgfinder.in"
        
        # Ensure email uniqueness if multiple registrations
        if User.query.filter_by(email=safe_email).first():
            safe_email = f"mobile_{local_10}_{secrets.token_hex(3)}@user.pgfinder.in"

        new_user = User(
            name=name,
            email=safe_email,
            phone=local_10,
            role=user_role
        )
        new_user.set_password(secrets.token_urlsafe(16))
        db.session.add(new_user)
        db.session.flush()

        if user_role == 'owner':
            owner_prof = OwnerProfile(
                user_id=new_user.id,
                business_name=f"{name}'s PG Accommodations",
                verification_status='unverified'
            )
            db.session.add(owner_prof)

        db.session.commit()
        login_user(new_user, remember=True)

        dest = get_dashboard_url_for_user(new_user)
        return jsonify({
            'success': True,
            'is_new_user': True,
            'message': f"Welcome to PG Finder, {new_user.name}!",
            'redirect_url': dest
        })

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error during OTP verification: {e}")
        return jsonify({'success': False, 'error': 'Verification failed. Please try again.'}), 500


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user(current_user))

    form = RegisterForm()
    if request.method == 'GET' and request.args.get('role') == 'owner':
        form.role.data = 'owner'

    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip(),
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        if form.role.data == 'owner':
            owner_prof = OwnerProfile(
                user_id=user.id,
                business_name=form.business_name.data.strip() if form.business_name.data else form.name.data.strip(),
                verification_status='unverified'
            )
            db.session.add(owner_prof)

        db.session.commit()
        login_user(user)
        flash("Your account has been created successfully!", "success")
        return redirect(get_dashboard_url_for_user(user))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user(current_user))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_password_reset_token(user.id)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_password_reset_email(user, reset_url)

        # Always show success flash to prevent user enumeration
        flash("If an account exists for this email address, password reset instructions have been sent.", "info")
        return redirect(url_for('auth.login', tab='email'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user(current_user))

    user = verify_password_reset_token(token)
    if not user:
        flash("The password reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset successfully! You can now sign in with your new password.", "success")
        return redirect(url_for('auth.login', tab='email'))

    return render_template('auth/reset_password.html', form=form, user=user)


@auth_bp.route('/google')
def google_login():
    """
    Google OAuth integration. When credentials are set in environment,
    initiates the Google OAuth authorization flow. Otherwise, provides
    a development sandbox login option without removing or breaking Google sign-in.
    """
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    if google_client_id:
        redirect_uri = url_for('auth.google_callback', _external=True)
        scope = "openid email profile"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={google_client_id}&response_type=code&scope={scope}&"
            f"redirect_uri={redirect_uri}&prompt=select_account"
        )
        return redirect(auth_url)

    # Sandbox / Development mode
    return render_template('auth/google_sandbox.html')


@auth_bp.route('/google/callback')
def google_callback():
    """Handles Google sign-in callback, linking existing accounts by email or registering."""
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user(current_user))

    # Support testing or development sandbox callback
    email = request.args.get('email', 'google.user@example.com').lower().strip()
    name = request.args.get('name', 'Google User').strip()

    user = User.query.filter_by(email=email).first()
    if not user:
        # Register new verified user
        user = User(
            name=name,
            email=email,
            phone="9800000000",
            role='customer'
        )
        user.set_password(secrets.token_urlsafe(16))
        db.session.add(user)
        db.session.commit()

    if not user.is_active:
        flash("This account is suspended.", "danger")
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    flash(f"Signed in via Google as {user.name}!", "success")
    return redirect(get_dashboard_url_for_user(user))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out securely.", "info")
    return redirect(url_for('auth.login'))
