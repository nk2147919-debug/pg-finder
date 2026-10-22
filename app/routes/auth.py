from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User, OwnerProfile
from app.forms.auth_forms import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__)


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
                return redirect(url_for('customer.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


customer_required = role_required('customer')
owner_required = role_required('owner')
admin_required = role_required('admin')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_owner:
            return redirect(url_for('owner.dashboard'))
        elif current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Your account has been deactivated or suspended. Please contact platform support.", "danger")
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.name}!", "success")
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            if user.is_owner:
                return redirect(url_for('owner.dashboard'))
            elif user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.index'))
        else:
            flash("Invalid email address or password.", "danger")

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer.index'))

    form = RegisterForm()
    # Check if pre-selecting owner role from query params
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

        # If registering as owner, initialize OwnerProfile
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

        if user.is_owner:
            return redirect(url_for('owner.dashboard'))
        return redirect(url_for('customer.index'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out securely.", "info")
    return redirect(url_for('customer.index'))
