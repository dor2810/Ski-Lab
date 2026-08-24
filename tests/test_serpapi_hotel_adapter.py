"""
Tests for adapters/serpapi_hotel_adapter.py.

Same shape as tests/test_flight_adapter.py and
tests/test_accommodation_adapter.py, for the same reason: parsing is
separated from the HTTP call, so it's fully testable offline, without a
SerpApi key.

What these tests do NOT prove: that the live request works, that `q`
being a bare resort name actually resolves to the right property on
Google Hotels, or that field names here are correct for every property
type SerpApi returns. The fixture is built from SerpApi's published
Google Hotels response shape, NOT verified against a real response --
flagged honestly, matching how test_flight_adapter.py framed itself
before SerpApi's first real call.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import serpapi_hotel_adapter
from ski_optimizer.adapters.base import AdapterError

FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "serpapi_google_hotels_val_thorens.json").read_text()
)


def _parse():
    return serpapi_hotel_adapter.parse_response(FIXTURE)


# --- parsing ---

def test_parses_properties_with_a_valid_rate():
    # 4 entries in the fixture; "No Price Lodge" (no rate_per_night at
    # all) and "Bad Data Inn" (rate of 0) must both be skipped.
    result = _parse()
    assert len(result.options) == 2


def test_options_are_sorted_cheapest_first():
    prices = [o.price_eur_per_night for o in _parse().options]
    assert prices == sorted(prices)
    assert prices[0] == 98.5


def test_extracted_lowest_is_used_not_the_formatted_string():
    result = _parse()
    chalet = next(o for o in result.options if o.property_name == "Chalet des Cimes")
    assert chalet.price_eur_per_night == 145.0


def test_free_cancellation_flag_is_carried_through():
    result = _parse()
    chalet = next(o for o in result.options if o.property_name == "Chalet des Cimes")
    assert chalet.cancellation_policy == "free_cancellation"


def test_absence_of_free_cancellation_is_not_assumed_non_refundable():
    # Residence Alpina has no free_cancellation key at all -- must come
    # through as None, not a fabricated "non_refundable". See adapter
    # module docstring: never invent a fact we don't have.
    result = _parse()
    residence = next(o for o in result.options if o.property_name == "Residence Alpina")
    assert residence.cancellation_policy is None


def test_rating_is_parsed_on_googles_own_scale():
    result = _parse()
    residence = next(o for o in result.options if o.property_name == "Residence Alpina")
    assert residence.rating == 4.1


def test_distance_to_lifts_is_always_none():
    # Google Hotels has no direct distance-to-POI figure -- see
    # limitation #2 in the adapter's module docstring.
    result = _parse()
    assert all(o.distance_to_lifts_km is None for o in result.options)


def test_property_token_is_carried_through_as_booking_token():
    result = _parse()
    chalet = next(o for o in result.options if o.property_name == "Chalet des Cimes")
    assert chalet.booking_token == "ChcIrpjT-46QjrEnGgsvZy8xMWJ3M3o5eBAB"


# --- robustness: malformed / partial data ---

def test_error_status_raises_adapter_error():
    payload = {"search_metadata": {"status": "Error"}, "error": "quota exceeded"}
    try:
        serpapi_hotel_adapter.parse_response(payload)
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "quota" in str(exc)


def test_empty_response_yields_no_options_without_crashing():
    payload = {"search_metadata": {"status": "Success"}, "properties": []}
    result = serpapi_hotel_adapter.parse_response(payload)
    assert result.options == []


def test_property_with_no_rate_is_skipped_not_fatal():
    payload = {"search_metadata": {"status": "Success"}, "properties": [
        {"name": "No Rate At All"},
        {"name": "Real Property", "rate_per_night": {"extracted_lowest": 100.0}},
    ]}
    result = serpapi_hotel_adapter.parse_response(payload)
    assert len(result.options) == 1
    assert result.options[0].property_name == "Real Property"


def test_zero_and_negative_prices_are_rejected():
    for bad_price in (0, -50):
        payload = {"search_metadata": {"status": "Success"}, "properties": [
            {"name": "Bad Price Hotel", "rate_per_night": {"extracted_lowest": bad_price}},
        ]}
        assert serpapi_hotel_adapter.parse_response(payload).options == []


# --- request-building logic (no network needed) ---

def test_search_without_api_key_raises_clear_error():
    import os
    from ski_optimizer.data.resort_repository import load_resorts

    saved = os.environ.pop("SERPAPI_API_KEY", None)
    resort = load_resorts()[0]
    try:
        serpapi_hotel_adapter.clear_cache()
        serpapi_hotel_adapter.search_accommodation(resort, date(2027, 1, 2), 5, 1)
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "SERPAPI_API_KEY" in str(exc)
    finally:
        if saved is not None:
            os.environ["SERPAPI_API_KEY"] = saved


def test_search_rejects_nonpositive_nights_and_rooms():
    from ski_optimizer.data.resort_repository import load_resorts

    resort = load_resorts()[0]
    for kwargs in (dict(nights=0, rooms_needed=1), dict(nights=5, rooms_needed=0)):
        try:
            serpapi_hotel_adapter.search_accommodation(resort, date(2027, 1, 2), **kwargs)
            assert False, f"expected AdapterError for {kwargs}"
        except AdapterError:
            pass


# --- caching ---

def test_cache_returns_stored_result_flagged_as_cached():
    from ski_optimizer.models import AccommodationSearchResult, AccommodationOption
    from ski_optimizer.adapters.response_cache import get_cache
    from ski_optimizer.data.resort_repository import load_resorts

    serpapi_hotel_adapter.clear_cache()
    resort = load_resorts()[0]
    stored = AccommodationSearchResult(
        options=[AccommodationOption(price_eur_per_night=77.0, property_name="Cached Hotel")],
    )
    key = serpapi_hotel_adapter._cache_key(
        resort.name, date(2027, 1, 2), date(2027, 1, 7), 2, "EUR")
    get_cache().set(key, stored)

    result = serpapi_hotel_adapter.search_accommodation(resort, date(2027, 1, 2), 5, 1)
    assert result.from_cache is True
    assert result.options[0].price_eur_per_night == 77.0
    serpapi_hotel_adapter.clear_cache()


# --- helper ---

def test_cheapest_price_returns_lowest():
    assert serpapi_hotel_adapter.cheapest_price_eur_per_night(_parse()) == 98.5


def test_cheapest_price_of_empty_result_is_none():
    from ski_optimizer.models import AccommodationSearchResult
    assert serpapi_hotel_adapter.cheapest_price_eur_per_night(AccommodationSearchResult(options=[])) is None
