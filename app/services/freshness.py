from datetime import datetime, timedelta
from flask import current_app
from app import db


def time_ago_str(dt):
    if not dt:
        return 'Never'
    now = datetime.utcnow()
    diff = now - dt
    if diff.total_seconds() < 60:
        return 'Just now'
    elif diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() // 60)
        return f'{mins}m ago'
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() // 3600)
        return f'{hours}h ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 30:
        return f'{diff.days} days ago'
    else:
        return dt.strftime('%b %d, %Y')


def get_freshness_status(property_obj):
    """
    Computes transparent, timestamp-derived freshness labels.
    Never presents stale data as verified or fresh.
    """
    now = datetime.utcnow()
    today_hours = current_app.config.get('FRESHNESS_TODAY_HOURS', 24)
    recent_days = current_app.config.get('FRESHNESS_RECENT_DAYS', 7)

    # Availability Freshness
    avail_dt = property_obj.availability_last_confirmed_at
    avail_diff = now - avail_dt if avail_dt else timedelta(days=999)
    if avail_diff.total_seconds() <= today_hours * 3600:
        avail_label = 'Availability confirmed today'
        avail_class = 'badge-fresh-today'
        avail_is_stale = False
    elif avail_diff.days <= recent_days:
        avail_label = 'Confirmed within last 7 days'
        avail_class = 'badge-fresh-week'
        avail_is_stale = False
    else:
        avail_label = 'Not recently confirmed'
        avail_class = 'badge-fresh-stale'
        avail_is_stale = True

    # Pricing Freshness
    price_dt = property_obj.price_last_confirmed_at
    price_diff = now - price_dt if price_dt else timedelta(days=999)
    if price_diff.total_seconds() <= today_hours * 3600:
        price_label = 'Price confirmed today'
        price_class = 'badge-fresh-today'
        price_is_stale = False
    elif price_diff.days <= recent_days:
        price_label = 'Price confirmed this week'
        price_class = 'badge-fresh-week'
        price_is_stale = False
    else:
        price_label = 'Price update overdue'
        price_class = 'badge-fresh-stale'
        price_is_stale = True

    # Food Menu Freshness
    menu_dt = property_obj.menu_last_updated_at
    menu_diff = now - menu_dt if menu_dt else timedelta(days=999)
    if menu_diff.days <= 7:
        menu_label = 'Menu active this week'
        menu_class = 'badge-fresh-week'
    elif menu_diff.days <= 30:
        menu_label = 'Menu updated this month'
        menu_class = 'badge-fresh-month'
    else:
        menu_label = 'Menu needs reconfirmation'
        menu_class = 'badge-fresh-stale'

    # Verification status based on real verification records
    verified_records = [
        v for v in property_obj.verification_records if v.status == 'verified'
    ] if hasattr(property_obj, 'verification_records') else []

    if verified_records:
        ver_label = 'Verified by Team'
        ver_class = 'badge-verified'
        is_verified = True
    else:
        ver_label = 'Verification Pending'
        ver_class = 'badge-pending'
        is_verified = False

    return {
        'availability': {
            'label': avail_label,
            'badge_class': avail_class,
            'time_ago': time_ago_str(avail_dt),
            'timestamp': avail_dt.strftime('%d %b %Y, %I:%M %p') if avail_dt else 'Never',
            'is_stale': avail_is_stale
        },
        'pricing': {
            'label': price_label,
            'badge_class': price_class,
            'time_ago': time_ago_str(price_dt),
            'timestamp': price_dt.strftime('%d %b %Y, %I:%M %p') if price_dt else 'Never',
            'is_stale': price_is_stale
        },
        'menu': {
            'label': menu_label,
            'badge_class': menu_class,
            'time_ago': time_ago_str(menu_dt),
            'timestamp': menu_dt.strftime('%d %b %Y, %I:%M %p') if menu_dt else 'Never',
        },
        'verification': {
            'label': ver_label,
            'badge_class': ver_class,
            'is_verified': is_verified
        }
    }


def reconfirm_property_freshness(property_obj):
    """Updates availability and pricing confirmation timestamp to now."""
    now = datetime.utcnow()
    property_obj.availability_last_confirmed_at = now
    property_obj.price_last_confirmed_at = now
    db.session.commit()
    return True
