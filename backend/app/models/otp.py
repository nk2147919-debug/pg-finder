import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from app import db


class OTPVerification(db.Model):
    __tablename__ = 'otp_verifications'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    otp_hash = db.Column(db.String(128), nullable=False)
    purpose = db.Column(db.String(50), default='login', nullable=False)  # 'login', 'register', 'reset'
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=3, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(str(code).strip().encode('utf-8')).hexdigest()

    def check_code(self, code: str) -> bool:
        expected = self.otp_hash
        candidate = self.hash_code(code)
        return hmac.compare_digest(expected, candidate)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.attempts >= self.max_attempts
