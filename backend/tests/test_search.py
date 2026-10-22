import pytest
from app.services.search_service import search_properties


def test_search_locality_filter(app, test_property):
    with app.app_context():
        # Searching Koramangala should return test_property
        results = search_properties({'locality': 'Koramangala'})
        assert results['total'] >= 1
        assert any(p.id == test_property.id for p in results['items'])

        # Searching Whitefield should NOT return test_property
        results_wf = search_properties({'locality': 'Whitefield'})
        assert not any(p.id == test_property.id for p in results_wf['items'])


def test_search_gender_filter(app, test_property):
    with app.app_context():
        # Test property is 'gents'
        results_gents = search_properties({'gender': 'gents'})
        assert any(p.id == test_property.id for p in results_gents['items'])

        results_ladies = search_properties({'gender': 'ladies'})
        assert not any(p.id == test_property.id for p in results_ladies['items'])


def test_search_budget_filter(app, test_property):
    with app.app_context():
        # Room rent is 12,000
        results_fit = search_properties({'min_rent': '10000', 'max_rent': '15000'})
        assert any(p.id == test_property.id for p in results_fit['items'])

        # Rent below room rent
        results_low = search_properties({'max_rent': '8000'})
        assert not any(p.id == test_property.id for p in results_low['items'])


def test_search_only_available_beds(app, test_property):
    with app.app_context():
        results = search_properties({'only_available': 'true'})
        assert any(p.id == test_property.id for p in results['items'])
