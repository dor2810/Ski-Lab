"""
Tests for engine/cost_calculator.live_accommodation_cost_eur_per_person and
apply_live_accommodation_price -- the glue between
adapters/serpapi_hotel_adapter and the cost model, mirroring
live_flight_cost_eur's existing tests in test_flight_adapter.py.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.models import CostBreakdown
from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.engine.cost_calculator import (
    live_accommodation_cost_eur_per_person, apply_live_accommodation_price, apply_live_flight_price,
)


def test_live_accommodation_cost_returns_none_without_api_key():
    # Degrades to None (caller falls back visibly) rather than raising
    # or inventing a number -- same contract as live_flight_cost_eur.
    import os
    from ski_optimizer.adapters import serpapi_hotel_adapter

    saved = os.environ.pop("SERPAPI_API_KEY", None)
    try:
        serpapi_hotel_adapter.clear_cache()
        resort = load_resorts()[0]
        result = live_accommodation_cost_eur_per_person(
            resort, date(2027, 1, 15), nights=5, group_size=2, rooms_needed=1)
        assert result is None
    finally:
        if saved is not None:
            os.environ["SERPAPI_API_KEY"] = saved


def test_live_accommodation_cost_divides_by_group_size():
    # Exercises the actual arithmetic against a cached result, without a
    # real key -- same trick test_serpapi_hotel_adapter.py uses for the
    # adapter's own caching test.
    from ski_optimizer.adapters import serpapi_hotel_adapter
    from ski_optimizer.adapters.response_cache import get_cache
    from ski_optimizer.models import AccommodationSearchResult, AccommodationOption

    serpapi_hotel_adapter.clear_cache()
    resort = load_resorts()[0]
    checkin = date(2027, 1, 15)
    nights, rooms_needed, group_size = 5, 2, 4

    stored = AccommodationSearchResult(
        options=[AccommodationOption(price_eur_per_night=100.0, property_name="Test Hotel")],
    )
    checkout = checkin + __import__("datetime").timedelta(days=nights)
    key = serpapi_hotel_adapter._cache_key(resort.name, checkin, checkout, rooms_needed * 2, "EUR")
    get_cache().set(key, stored)

    result = live_accommodation_cost_eur_per_person(
        resort, checkin, nights=nights, group_size=group_size, rooms_needed=rooms_needed)
    # 100 EUR/night * 5 nights * 2 rooms / 4 people = 250
    assert result == 250.0
    serpapi_hotel_adapter.clear_cache()


def _cost(**overrides):
    kw = dict(flight_eur=200.0, transfer_eur=50.0, accommodation_eur=400.0,
              ski_pass_eur=300.0, equipment_eur=110.0, food_eur=240.0, misc_eur=65.0)
    kw.update(overrides)
    return CostBreakdown(**kw)


def test_apply_live_accommodation_price_replaces_the_estimate():
    cost = _cost()
    updated = apply_live_accommodation_price(cost, 250.0)
    assert updated.accommodation_eur == 250.0
    assert updated.accommodation_price_is_live is True
    assert cost.accommodation_price_is_live is False  # input untouched
    # Every other line item is untouched except misc (buffer adjustment).
    assert updated.flight_eur == cost.flight_eur
    assert updated.transfer_eur == cost.transfer_eur
    assert updated.ski_pass_eur == cost.ski_pass_eur
    assert updated.equipment_eur == cost.equipment_eur
    assert updated.food_eur == cost.food_eur


def test_apply_live_accommodation_price_does_not_mutate_input():
    cost = _cost()
    apply_live_accommodation_price(cost, 999.0)
    assert cost.accommodation_eur == 400.0


def test_apply_live_accommodation_price_preserves_flight_live_flag():
    cost = _cost(flight_price_is_live=True)
    updated = apply_live_accommodation_price(cost, 250.0)
    assert updated.flight_price_is_live is True


def test_apply_live_flight_price_preserves_accommodation_live_flag():
    # Regression guard: if accommodation is repriced live BEFORE flight
    # (no engine module does this today, but nothing enforces the order),
    # apply_live_flight_price must not silently reset the accommodation
    # flag back to False via the dataclass default.
    cost = _cost(accommodation_price_is_live=True)
    updated = apply_live_flight_price(cost, 300.0)
    assert updated.accommodation_price_is_live is True
    assert updated.flight_eur == 300.0
