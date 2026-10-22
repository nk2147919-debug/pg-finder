import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-pg-bengaluru')
    
    # Database
    db_url = os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'pg_finder.db'}")
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads
    UPLOAD_FOLDER = BASE_DIR / os.getenv('UPLOAD_FOLDER', 'app/static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # Freshness thresholds
    FRESHNESS_TODAY_HOURS = int(os.getenv('FRESHNESS_TODAY_HOURS', 24))
    FRESHNESS_RECENT_DAYS = int(os.getenv('FRESHNESS_RECENT_DAYS', 7))
    FRESHNESS_STALE_DAYS = int(os.getenv('FRESHNESS_STALE_DAYS', 30))
    
    # Bengaluru Map Defaults
    MAP_DEFAULT_LAT = float(os.getenv('MAP_DEFAULT_LAT', 12.9716))
    MAP_DEFAULT_LNG = float(os.getenv('MAP_DEFAULT_LNG', 77.5946))
    MAP_DEFAULT_ZOOM = int(os.getenv('MAP_DEFAULT_ZOOM', 12))

    # Payment Gateway (Razorpay in Sandbox / Test Mode)
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_pgfinder_sandbox')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'pgfinder_secret_sandbox_key_2026')
    RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', 'pgfinder_webhook_secret_2026')
    RAZORPAY_SANDBOX_MODE = os.getenv('RAZORPAY_SANDBOX_MODE', 'True').lower() in ('true', '1', 'yes')


class TestConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RAZORPAY_KEY_ID = 'rzp_test_mock_id'
    RAZORPAY_KEY_SECRET = 'rzp_test_mock_secret'
    RAZORPAY_WEBHOOK_SECRET = 'rzp_test_webhook_secret'
    RAZORPAY_SANDBOX_MODE = True
