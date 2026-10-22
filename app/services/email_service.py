import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from flask import current_app
from app.models.user import User

logger = logging.getLogger('pg_finder.auth')

RESET_TOKEN_SALT = 'pgfinder-password-reset-salt'
RESET_MAX_AGE_SECONDS = 900  # 15 minutes


def get_serializer():
    secret = current_app.config.get('SECRET_KEY', 'default-dev-secret-key-pg-bengaluru')
    return URLSafeTimedSerializer(secret)


def generate_password_reset_token(user_id: int) -> str:
    """Generates a secure cryptographically signed token valid for 15 minutes."""
    s = get_serializer()
    return s.dumps({'user_id': user_id}, salt=RESET_TOKEN_SALT)


def verify_password_reset_token(token: str, max_age: int = RESET_MAX_AGE_SECONDS) -> User | None:
    """Verifies the reset token and returns the corresponding User, or None if invalid/expired."""
    s = get_serializer()
    try:
        data = s.loads(token, salt=RESET_TOKEN_SALT, max_age=max_age)
        user_id = data.get('user_id')
        if not user_id:
            return None
        return User.query.get(user_id)
    except (SignatureExpired, BadTimeSignature, BadSignature, Exception) as e:
        logger.warning(f"Password reset token verification failed: {e}")
        return None


def send_password_reset_email(user: User, reset_url: str) -> bool:
    """Dispatches password reset instructions via SMTP when configured."""
    mail_server = os.getenv('MAIL_SERVER')
    mail_port = int(os.getenv('MAIL_PORT', 587))
    mail_user = os.getenv('MAIL_USERNAME')
    mail_pass = os.getenv('MAIL_PASSWORD')
    mail_sender = os.getenv('MAIL_DEFAULT_SENDER', 'no-reply@pgfinder.in')
    mail_use_tls = os.getenv('MAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')

    subject = "Reset Your PG Finder Account Password"
    body_text = (
        f"Hello {user.name},\n\n"
        f"We received a request to reset your PG Finder account password.\n"
        f"Click the link below or copy and paste it into your browser to set a new password:\n\n"
        f"{reset_url}\n\n"
        f"This link is valid for 15 minutes. If you did not request this, you can safely ignore this email.\n\n"
        f"Best regards,\nThe PG Finder Bengaluru Team"
    )

    if mail_server and mail_user and mail_pass:
        try:
            msg = MIMEMultipart()
            msg['From'] = mail_sender
            msg['To'] = user.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body_text, 'plain'))

            server = smtplib.SMTP(mail_server, mail_port, timeout=10)
            if mail_use_tls:
                server.starttls()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_sender, [user.email], msg.as_string())
            server.quit()
            logger.info(f"Password reset email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email via SMTP: {e}")
            return False

    # Development fallback
    logger.info(f"[DEV EMAIL FALLBACK] Password reset for {user.email}: {reset_url}")
    return True
