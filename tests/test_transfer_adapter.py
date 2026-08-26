"""
Tests for adapters/transfer_adapter.py.

Same philosophy as the other keyless adapters: parsing/orchestration
tested offline by mocking _fetch_json (this module's own network
boundary), never the real requests.get call (blocked globally -- see
tests/conftest.py).

What these do NOT prove: that Alps2Alps' real response shape still
matches what's hardcoded here. That was verified live, by hand, while
building this adapter (see the module's own docstring) -- not something
an offline test can keep proving on every run.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import transfer_adapter as ta
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.models import Resort


@pytest.fixture(autouse=True)
def _fresh_cache():
    response_cache.get_cache().clear()
    yield
    response_cache.get_cache().clear()


def _resort(**overrides):
    kw = dict(
        name="Chamonix", country="France", region="Mont Blanc Valley",
        base_elevation_m=1035, summit_elevation_m=3842, vertical_drop_m=2807,
        num_lifts=49, piste_km=170.0, off_piste_rating=5, snow_reliability=5,
        nightlife_rating=4, family_friendliness=3, nearest_airport="Geneva (GVA)",
        airport_distance_km=100.0, transfer_time_minutes=75.0,
        ski_pass_6day_eur=380.0, accommodation_eur_per_night=140.0,
    )
    kw.update(overrides)
    return Resort(**kw)


# --- _airport_city_name ---

def test_airport_city_name_strips_the_iata_code():
    assert ta._airport_city_name("Geneva (GVA)") == "Geneva"


def test_airport_city_name_uses_the_first_airport_for_multi_airport_resorts():
    assert ta._airport_city_name("Geneva (GVA) / Chambery (CMF)") == "Geneva"


# --- resolve_location ---

def test_resolve_location_filters_by_type():
    # REGRESSION: /locations/search?q=geneva returns "Geneva city" (a
    # resort entry) BEFORE "Geneva Airport" -- caught live, resolving
    # without a type filter silently picked the wrong location and the
    # pricing request 422'd. This is the exact response shape that bit.
    data = [
        {"code": "resort-644", "name": "Geneva city", "type": "resort", "country": "Switzerland"},
        {"code": "airport-1", "name": "Geneva Airport", "type": "airport", "country": "Switzerland"},
        {"code": "city-46", "name": "Geneva city", "type": "city", "country": "Switzerland"},
    ]

    def fake_fetch(path, params):
        return data

    import ski_optimizer.adapters.transfer_adapter as mod
    orig = mod._fetch_json
    mod._fetch_json = fake_fetch
    try:
        assert ta.resolve_location("geneva", location_type="airport", use_cache=False) == "airport-1"
        assert ta.resolve_location("geneva", location_type="resort", use_cache=False) == "resort-644"
    finally:
        mod._fetch_json = orig


def test_resolve_location_is_none_for_no_match():
    import ski_optimizer.adapters.transfer_adapter as mod
    orig = mod._fetch_json
    mod._fetch_json = lambda path, params: []
    try:
        assert ta.resolve_location("nowhere", use_cache=False) is None
    finally:
        mod._fetch_json = orig


def test_resolve_location_is_none_when_the_type_filter_matches_nothing():
    import ski_optimizer.adapters.transfer_adapter as mod
    orig = mod._fetch_json
    mod._fetch_json = lambda path, params: [
        {"code": "resort-1", "name": "Somewhere", "type": "resort"},
    ]
    try:
        assert ta.resolve_location("somewhere", location_type="airport", use_cache=False) is None
    finally:
        mod._fetch_json = orig


def test_resolve_location_caches_identical_queries(monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(path, params):
        call_count["n"] += 1
        return [{"code": "resort-11", "name": "Chamonix", "type": "resort"}]

    monkeypatch.setattr(ta, "_fetch_json", fake_fetch)
    ta.resolve_location("chamonix", location_type="resort", use_cache=True)
    ta.resolve_location("chamonix", location_type="resort", use_cache=True)
    assert call_count["n"] == 1


# --- search_transfer_options ---

def test_search_transfer_options_rejects_nonpositive_adults():
    with pytest.raises(AdapterError):
        ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=0)


def test_search_transfer_options_raises_when_airport_cannot_be_resolved(monkeypatch):
    monkeypatch.setattr(ta, "resolve_location", lambda *a, **k: None)
    with pytest.raises(AdapterError, match="airport"):
        ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2)


def test_search_transfer_options_raises_when_resort_cannot_be_resolved(monkeypatch):
    def fake_resolve(query, location_type=None, use_cache=True):
        return "airport-1" if location_type == "airport" else None

    monkeypatch.setattr(ta, "resolve_location", fake_resolve)
    with pytest.raises(AdapterError, match="resort"):
        ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2)


def test_search_transfer_options_parses_a_real_shaped_response(monkeypatch):
    monkeypatch.setattr(ta, "resolve_location", lambda query, location_type=None, use_cache=True:
                        "airport-1" if location_type == "airport" else "resort-11")

    def fake_fetch(path, params):
        assert path == "/transfer-options"
        return {
            "route": {"distance_km": 99, "duration_minutes": 100},
            "outbound": {
                "vehicles": [
                    {"vehicle_type_id": 10, "name": "Standard minivan", "price": 208,
                     "max_passengers": 5, "booking_url": "https://example.com/checkout"},
                ]
            },
        }

    monkeypatch.setattr(ta, "_fetch_json", fake_fetch)
    result = ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2, use_cache=False)
    assert len(result.options) == 1
    opt = result.options[0]
    assert opt.price_eur == 208.0
    assert opt.cost_basis == "per_vehicle"
    assert opt.max_passengers == 5
    assert opt.duration_minutes == 100.0
    assert opt.booking_url == "https://example.com/checkout"


def test_search_transfer_options_skips_malformed_vehicle_entries(monkeypatch):
    monkeypatch.setattr(ta, "resolve_location", lambda query, location_type=None, use_cache=True:
                        "airport-1" if location_type == "airport" else "resort-11")
    monkeypatch.setattr(ta, "_fetch_json", lambda path, params: {
        "route": {"duration_minutes": 100},
        "outbound": {"vehicles": [
            {"name": "Missing price and passengers"},
            {"name": "Good one", "price": 100, "max_passengers": 4},
        ]},
    })
    result = ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2, use_cache=False)
    assert len(result.options) == 1
    assert result.options[0].vehicle_name == "Good one"


def test_search_transfer_options_caches_identical_queries(monkeypatch):
    monkeypatch.setattr(ta, "resolve_location", lambda query, location_type=None, use_cache=True:
                        "airport-1" if location_type == "airport" else "resort-11")
    call_count = {"n": 0}

    def fake_fetch(path, params):
        call_count["n"] += 1
        return {"route": {"duration_minutes": 100}, "outbound": {"vehicles": []}}

    monkeypatch.setattr(ta, "_fetch_json", fake_fetch)
    ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2, use_cache=True)
    ta.search_transfer_options(_resort(), date(2027, 1, 10), "14:30", adults=2, use_cache=True)
    assert call_count["n"] == 1


# --- cheapest_price_eur / cheapest_option ---

def test_cheapest_price_eur_excludes_vehicles_too_small_for_the_group():
    from ski_optimizer.models import TransferQuote, TransferSearchResult

    result = TransferSearchResult(options=[
        TransferQuote(price_eur=100.0, cost_basis="per_vehicle", vehicle_name="Small",
                     max_passengers=4, duration_minutes=60.0),
        TransferQuote(price_eur=180.0, cost_basis="per_vehicle", vehicle_name="Big",
                     max_passengers=8, duration_minutes=60.0),
    ])
    assert ta.cheapest_price_eur(result, group_size=6) == 180.0


def test_cheapest_price_eur_is_none_when_nothing_fits():
    from ski_optimizer.models import TransferQuote, TransferSearchResult

    result = TransferSearchResult(options=[
        TransferQuote(price_eur=100.0, cost_basis="per_vehicle", vehicle_name="Small",
                     max_passengers=4, duration_minutes=60.0),
    ])
    assert ta.cheapest_price_eur(result, group_size=10) is None


def test_cheapest_option_returns_the_full_quote():
    from ski_optimizer.models import TransferQuote, TransferSearchResult

    cheap = TransferQuote(price_eur=100.0, cost_basis="per_vehicle", vehicle_name="Small",
                          max_passengers=4, duration_minutes=60.0, booking_url="https://x")
    result = TransferSearchResult(options=[cheap])
    assert ta.cheapest_option(result, group_size=2) is cheap
