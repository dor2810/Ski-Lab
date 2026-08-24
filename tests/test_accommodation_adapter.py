"""
Tests for adapters/accommodation_adapter.py.

Same shape as tests/test_flight_adapter.py, for the same reason: parsing
is separated from the HTTP call, so it's fully testable offline, without
a Booking.com credential -- which doesn't exist yet (see the adapter's
module docstring and PROJECT_STATE.md for why: the basic Affiliate
signup doesn't grant API access).

What these tests do NOT prove: that the live request works, that the
request/response shape matches Booking.com's actual Demand API, or that
field names here are correct. The fixture is built from Booking.com's
published documentation conventions, NOT verified against a real
response -- flagged honestly, matching how test_flight_adapter.py framed
itself before SerpApi's first real call.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import accommodation_adapter
from ski_optimizer.adapters.base import AdapterError

FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "booking_demand_api_val_thorens.json").read_text()
)


def _parse():
    return accommodation_adapter.parse_response(FIXTURE)


# --- parsing ---

def test_parses_properties_with_a_valid_eur_price():
    # 4 entries in the fixture; "No Price Lodge" (empty block) and "Wrong
    # Currency Inn" (USD, not EUR) must both be skipped.
    result = _parse()
    assert len(result.options) == 2


def test_options_are_sorted_cheapest_first():
    prices = [o.price_eur_per_night for o in _parse().options]
    assert prices == sorted(prices)
    assert prices[0] == 98.5


def test_cheapest_block_is_used_when_a_property_has_several():
    # Chalet des Cimes has two rate blocks (145.0 and 189.0) -- the
    # cheaper one is what a shopper would actually see/book.
    result = _parse()
    chalet = next(o for o in result.options if o.property_name == "Chalet des Cimes")
    assert chalet.price_eur_per_night == 145.0


def test_cancellation_policy_is_carried_through():
    result = _parse()
    chalet = next(o for o in result.options if o.property_name == "Chalet des Cimes")
    assert chalet.cancellation_policy == "free_cancellation"


def test_rating_and_distance_are_parsed():
    result = _parse()
    residence = next(o for o in result.options if o.property_name == "Residence Alpina")
    assert residence.rating == 7.9
    assert residence.distance_to_lifts_km == 1.1


def test_booking_token_is_carried_through():
    result = _parse()
    residence = next(o for o in result.options if o.property_name == "Residence Alpina")
    assert residence.booking_token == "prop-002"


# --- robustness: malformed / partial data ---

def test_error_field_raises_adapter_error():
    payload = {"error": "invalid credentials"}
    try:
        accommodation_adapter.parse_response(payload)
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "invalid credentials" in str(exc)


def test_empty_response_yields_no_options_without_crashing():
    payload = {"data": []}
    result = accommodation_adapter.parse_response(payload)
    assert result.options == []


def test_property_with_no_price_blocks_is_skipped_not_fatal():
    payload = {"data": [
        {"id": "x", "name": "No Blocks At All"},
        {"id": "y", "name": "Real Property", "block": [
            {"price": {"amount": 100.0, "currency": "EUR"}},
        ]},
    ]}
    result = accommodation_adapter.parse_response(payload)
    assert len(result.options) == 1
    assert result.options[0].property_name == "Real Property"


def test_zero_and_negative_prices_are_rejected():
    for bad_price in (0, -50):
        payload = {"data": [{
            "id": "z", "name": "Bad Price Hotel",
            "block": [{"price": {"amount": bad_price, "currency": "EUR"}}],
        }]}
        assert accommodation_adapter.parse_response(payload).options == []


# --- request-building logic (no network needed) ---

def test_search_without_api_key_raises_clear_error():
    import os
    from ski_optimizer.data.resort_repository import load_resorts

    saved = os.environ.pop("BOOKING_AFFILIATE_API_KEY", None)
    resort = load_resorts()[0]
    try:
        accommodation_adapter.clear_cache()
        accommodation_adapter.search_accommodation(resort, date(2027, 1, 2), 5, 1)
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "BOOKING_AFFILIATE_API_KEY" in str(exc)
    finally:
        if saved is not None:
            os.environ["BOOKING_AFFILIATE_API_KEY"] = saved


def test_search_rejects_nonpositive_nights_and_rooms():
    from ski_optimizer.data.resort_repository import load_resorts

    resort = load_resorts()[0]
    for kwargs in (dict(nights=0, rooms_needed=1), dict(nights=5, rooms_needed=0)):
        try:
            accommodation_adapter.search_accommodation(resort, date(2027, 1, 2), **kwargs)
            assert False, f"expected AdapterError for {kwargs}"
        except AdapterError:
            pass
