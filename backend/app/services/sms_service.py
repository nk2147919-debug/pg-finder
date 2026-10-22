import os
import re
import secrets
import logging
import requests
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.otp import OTPVerification

logger = logging.getLogger('pg_finder.auth')

OTP_EXPIRY_MINUTES = 5
MAX_VERIFICATION_ATTEMPTS = 3
RESEND_COOLDOWN_SECONDS = 60
MAX_HOURLY_REQUESTS = 5


class SMSProviderError(Exception):
    """Raised when an SMS provider fails or is unconfigured."""
    pass


class RateLimitError(Exception):
    """Raised when OTP rate limits or cooldowns are violated."""
    def __init__(self, message, remaining_seconds=0):
        super().__init__(message)
        self.remaining_seconds = remaining_seconds


def clean_phone_digits(raw: str) -> str:
    """Strips all non-digit characters from a phone number string."""
    if not raw:
        return ""
    return re.sub(r'\D', '', str(raw))


def normalize_phone(country_code: str, raw_number: str) -> tuple[str, str]:
    """
    Normalizes phone into (formatted_e164, local_10_digit).
    Supports India (+91) by default as well as international numbers.
    """
    clean_cc = clean_phone_digits(country_code) or '91'
    if not clean_cc.startswith('+'):
        cc_prefix = f"+{clean_cc}"
    else:
        cc_prefix = clean_cc

    digits = clean_phone_digits(raw_number)
    
    # Handle country code embedded in raw_number
    if clean_cc == '91':
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        
        if len(digits) != 10 or not digits[0] in '6789':
            raise ValueError("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
        
        return f"+91{digits}", digits
    else:
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Please enter a valid mobile number between 7 and 15 digits.")
        return f"{cc_prefix}{digits}", digits


def send_otp_sms(phone_e164: str, otp_code: str) -> bool:
    """
    Sends the OTP code via Twilio or Fast2SMS when configured.
    In production, raises an SMSProviderError if no valid provider credentials exist.
    In development/testing, falls back to a development logger if credentials are not set.
    """
    is_production = os.getenv('FLASK_ENV') == 'production' or (
        current_app and current_app.config.get('ENV') == 'production'
    )

    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_from = os.getenv('TWILIO_PHONE_NUMBER')

    fast2sms_key = os.getenv('FAST2SMS_API_KEY')

    message_text = f"Your PG Finder verification code is: {otp_code}. Valid for {OTP_EXPIRY_MINUTES} minutes. Never share this code."

    # 1. Try Twilio
    if twilio_sid and twilio_token and twilio_from:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            resp = requests.post(
                url,
                data={'From': twilio_from, 'To': phone_e164, 'Body': message_text},
                auth=(twilio_sid, twilio_token),
                timeout=10
            )
            if resp.status_code in (200, 201):
                logger.info(f"SMS successfully dispatched via Twilio to {phone_e164[:4]}******{phone_e164[-2:]}")
                return True
            else:
                logger.error(f"Twilio SMS delivery failed: {resp.status_code} - {resp.text}")
                raise SMSProviderError(f"SMS delivery error: {resp.status_code}")
        except requests.RequestException as e:
            logger.error(f"Twilio connection error: {e}")
            raise SMSProviderError(f"SMS gateway connection error: {str(e)}")

    # 2. Try Fast2SMS
    if fast2sms_key:
        try:
            # Fast2SMS requires 10-digit number without country code for Indian numbers
            digits = clean_phone_digits(phone_e164)[-10:]
            url = "https://www.fast2sms.com/dev/bulkV2"
            headers = {'authorization': fast2sms_key}
            payload = {
                'variables_values': otp_code,
                'route': 'otp',
                'numbers': digits
            }
            resp = requests.post(url, data=payload, headers=headers, timeout=10)
            data = resp.json()
            if data.get('return'):
                logger.info(f"SMS dispatched via Fast2SMS to {phone_e164[:4]}******{phone_e164[-2:]}")
                return True
            else:
                logger.error(f"Fast2SMS error: {data.get('message')}")
                raise SMSProviderError(f"SMS provider error: {data.get('message')}")
        except requests.RequestException as e:
            logger.error(f"Fast2SMS connection error: {e}")
            raise SMSProviderError(f"Fast2SMS network error: {str(e)}")

    # 3. Provider check in production
    if is_production:
        raise SMSProviderError(
            "SMS authentication provider not configured. Please configure TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER or FAST2SMS_API_KEY in server environment."
        )

    # 4. Development / Testing Mock Fallback
    logger.info(f"[DEV SMS FALLBACK] Destination: {phone_e164} | OTP: {otp_code}")
    return True


def request_otp(phone_raw: str, country_code: str = '+91', purpose: str = 'login') -> dict:
    """
    Validates phone number, enforces rate-limiting and cooldowns, generates 6-digit OTP,
    hashes and stores it in OTPVerification, and dispatches the SMS.
    """
    phone_e164, local_10 = normalize_phone(country_code, phone_raw)
    now = datetime.utcnow()

    # 1. Check cooldown (at least 60 seconds since last OTP request)
    latest = OTPVerification.query.filter_by(phone=phone_e164).order_by(OTPVerification.created_at.desc()).first()
    if latest:
        seconds_since_last = (now - latest.created_at).total_seconds()
        if seconds_since_last < RESEND_COOLDOWN_SECONDS:
            remaining = int(RESEND_COOLDOWN_SECONDS - seconds_since_last)
            raise RateLimitError(
                f"Please wait {remaining} seconds before requesting a new OTP.",
                remaining_seconds=remaining
            )

    # 2. Check hourly limit (max 5 requests per hour)
    one_hour_ago = now - timedelta(hours=1)
    recent_count = OTPVerification.query.filter(
        OTPVerification.phone == phone_e164,
        OTPVerification.created_at >= one_hour_ago
    ).count()
    if recent_count >= MAX_HOURLY_REQUESTS:
        raise RateLimitError("Maximum OTP requests exceeded for this hour. Please try again later.")

    # 3. Generate secure 6-digit OTP
    otp_code = f"{secrets.randbelow(1000000):06d}"
    otp_hash = OTPVerification.hash_code(otp_code)

    # 4. Save record
    expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    record = OTPVerification(
        phone=phone_e164,
        otp_hash=otp_hash,
        purpose=purpose,
        attempts=0,
        max_attempts=MAX_VERIFICATION_ATTEMPTS,
        expires_at=expires_at,
        is_verified=False,
        created_at=now
    )
    db.session.add(record)
    db.session.commit()

    # 5. Dispatch SMS
    send_otp_sms(phone_e164, otp_code)

    result = {
        'phone_e164': phone_e164,
        'local_10': local_10,
        'cooldown_seconds': RESEND_COOLDOWN_SECONDS,
        'expires_in_minutes': OTP_EXPIRY_MINUTES,
        'message': f"OTP sent to {phone_e164[:4]}******{phone_e164[-2:]}."
    }

    # For testing and dev environment convenience only
    if current_app and current_app.config.get('TESTING'):
        result['dev_otp'] = otp_code

    return result


def verify_otp_code(phone_raw: str, country_code: str, code: str) -> dict:
    """
    Verifies a 6-digit OTP code against the latest active OTPVerification record.
    Enforces maximum attempts and expiry.
    """
    phone_e164, local_10 = normalize_phone(country_code, phone_raw)
    clean_code = str(code).strip()

    if not clean_code or len(clean_code) != 6 or not clean_code.isdigit():
        raise ValueError("Please enter a valid 6-digit OTP.")

    now = datetime.utcnow()
    record = OTPVerification.query.filter_by(
        phone=phone_e164
    ).order_by(OTPVerification.created_at.desc()).first()

    if not record:
        raise ValueError("No active OTP request found for this phone number. Please request a new OTP.")

    if record.is_locked:
        raise ValueError("Too many failed verification attempts. Please request a new OTP.")

    if record.is_expired:
        raise ValueError("This OTP has expired. Please request a new OTP.")

    # Allow completing registration if already verified within valid window
    if record.is_verified and record.check_code(clean_code):
        return {
            'success': True,
            'phone_e164': phone_e164,
            'local_10': local_10
        }

    if not record.check_code(clean_code):
        record.attempts += 1
        db.session.commit()
        remaining = record.max_attempts - record.attempts
        if remaining > 0:
            raise ValueError(f"Incorrect OTP. You have {remaining} attempt{'s' if remaining > 1 else ''} remaining.")
        else:
            raise ValueError("Too many failed attempts. This OTP has been invalidated. Please request a new OTP.")

    # Mark as verified
    record.is_verified = True
    db.session.commit()

    return {
        'success': True,
        'phone_e164': phone_e164,
        'local_10': local_10
    }
