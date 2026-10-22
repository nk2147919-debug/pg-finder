from datetime import datetime, timedelta
from app.services.freshness import get_freshness_status, reconfirm_property_freshness
from app.models.property import Property


def test_freshness_confirmed_today(app, test_property):
    with app.app_context():
        test_property.availability_last_confirmed_at = datetime.utcnow() - timedelta(hours=2)
        freshness = get_freshness_status(test_property)
        assert freshness['availability']['label'] == 'Availability confirmed today'
        assert freshness['availability']['badge_class'] == 'badge-fresh-today'
        assert not freshness['availability']['is_stale']


def test_freshness_confirmed_within_week(app, test_property):
    with app.app_context():
        test_property.availability_last_confirmed_at = datetime.utcnow() - timedelta(days=3)
        freshness = get_freshness_status(test_property)
        assert freshness['availability']['label'] == 'Confirmed within last 7 days'
        assert freshness['availability']['badge_class'] == 'badge-fresh-week'
        assert not freshness['availability']['is_stale']


def test_freshness_stale_alert(app, test_property):
    with app.app_context():
        test_property.availability_last_confirmed_at = datetime.utcnow() - timedelta(days=12)
        freshness = get_freshness_status(test_property)
        assert freshness['availability']['label'] == 'Not recently confirmed'
        assert freshness['availability']['badge_class'] == 'badge-fresh-stale'
        assert freshness['availability']['is_stale']


def test_reconfirm_freshness_action(app, test_property):
    with app.app_context():
        # Set old timestamp
        old_time = datetime.utcnow() - timedelta(days=10)
        test_property.availability_last_confirmed_at = old_time
        test_property.price_last_confirmed_at = old_time

        # Trigger reconfirm
        reconfirm_property_freshness(test_property)

        # Check that timestamp is now within the last minute
        diff = datetime.utcnow() - test_property.availability_last_confirmed_at
        assert diff.total_seconds() < 5
        assert get_freshness_status(test_property)['availability']['label'] == 'Availability confirmed today'
