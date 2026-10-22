import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    curr_dir = os.path.abspath(os.path.dirname(__file__))
    candidates_templates = [
        os.path.abspath(os.path.join(curr_dir, '..', '..', 'frontend', 'templates')),
        os.path.abspath(os.path.join(curr_dir, '..', 'frontend', 'templates')),
        os.path.join(curr_dir, 'templates'),
    ]
    template_folder = next((p for p in candidates_templates if os.path.isdir(p)), None)

    candidates_static = [
        os.path.abspath(os.path.join(curr_dir, '..', '..', 'frontend', 'static')),
        os.path.abspath(os.path.join(curr_dir, '..', 'frontend', 'static')),
        os.path.join(curr_dir, 'static'),
    ]
    static_folder = next((p for p in candidates_static if os.path.isdir(p)), None)

    kwargs = {}
    if template_folder:
        kwargs['template_folder'] = template_folder
    if static_folder:
        kwargs['static_folder'] = static_folder

    app = Flask(__name__, **kwargs)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.owner import owner_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp)
    app.register_blueprint(owner_bp, url_prefix='/owner')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Register context processors & custom template filters
    from app.services.freshness import get_freshness_status
    @app.context_processor
    def utility_processor():
        return dict(get_freshness_status=get_freshness_status)

    @app.template_filter('inr')
    def inr_format(val):
        try:
            val = float(val)
            return f"₹{val:,.0f}"
        except (ValueError, TypeError):
            return f"₹{val}"

    return app
