"""
Tests for adapters/flight_adapter.py.

UNLIKE tests/test_auth.py and tests/test_search.py, THESE ACTUALLY RUN
in an environment with no network and no API key. That's deliberate:
the parsing layer was separated from the HTTP call precisely so the
part where bugs actually live is testable offline, against a recorded
fixture of SerpApi's documented response shape.

What these tests do NOT prove: that the live request works, that the
params are the ones SerpApi expects, or that real responses match the
fixture. Those need a real key. The fixture is built from SerpApi's
published schema, which is a good approximation and not a guarantee --
expect to adjust when the first real call lands.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import flight_adapter
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.models import FlightOption

FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "serpapi_tlv_gva.json").read_text()
)


def _parse():
    return flight_adapter.parse_response(FIXTURE)


# --- parsing ---

def test_parses_all_itineraries_from_both_result_lists():
    # SerpApi splits results across best_flights and other_flights;
    # reading only one would silently drop cheap options -- including,
    # in this fixture, the CHEAPEST one (Wizz at 167, in other_flights).
    result = _parse()
    assert len(result.options) == 4


def test_options_are_sorted_cheapest_first():
    prices = [o.price_eur for o in _parse().options]
    assert prices == sorted(prices)
    assert prices[0] == 167


def test_direct_flight_has_zero_stops():
    result = _parse()
    wizz = next(o for o in result.options if o.airline == "Wizz Air")
    assert wizz.stops == 0
    assert wizz.origin_airport == "TLV"
    assert wizz.destination_airport == "GVA"


def test_connecting_flight_reports_one_stop():
    result = _parse()
    via_vie = next(o for o in result.options if o.destination_airport == "INN")
    assert via_vie.stops == 1
    assert via_vie.origin_airport == "TLV"


def test_multi_airport_search_returns_multiple_destinations():
    # The whole reason this provider was chosen: one request covering
    # several arrival airports. If this ever returns a single
    # destination, the multi-airport benefit has silently been lost.
    destinations = {o.destination_airport for o in _parse().options}
    assert destinations == {"GVA", "INN"}


def test_mixed_carrier_itinerary_names_both_airlines():
    result = _parse()
    via_zrh = next(o for o in result.options if o.price_eur == 331)
    assert "Swiss" in via_zrh.airline and "Edelweiss" in via_zrh.airline


def test_single_carrier_connecting_flight_is_not_double_named():
    # Both legs are Austrian -- the airline should read "Austrian",
    # not "Austrian + Austrian".
    result = _parse()
    via_vie = next(o for o in result.options if o.destination_airport == "INN")
    assert via_vie.airline == "Austrian"


def test_total_duration_includes_layovers():
    result = _parse()
    via_vie = next(o for o in result.options if o.destination_airport == "INN")
    # 195 + 55 flying = 250, but total_duration is 355 including the
    # 105-minute layover. Using the summed legs would understate the trip.
    assert via_vie.total_duration_minutes == 355


def test_booking_token_is_carried_through():
    result = _parse()
    wizz = next(o for o in result.options if o.airline == "Wizz Air")
    assert wizz.booking_token == "TOKEN_WIZZ_GVA"


# --- price insights (the differentiating feature) ---

def test_price_insights_are_parsed():
    insight = _parse().insight
    assert insight is not None
    assert insight.lowest_price_eur == 167
    assert insight.typical_range_eur == (210.0, 340.0)
    assert insight.price_level == "low"


def test_price_history_is_preserved_for_persistence():
    # This series is the raw material for "move your dates and save",
    # and is worth storing as it arrives -- see PriceInsight's docstring.
    history = _parse().insight.price_history
    assert len(history) == 4
    assert history[-1][1] == 167


def test_missing_price_insights_returns_none_not_a_fake():
    payload = {"search_metadata": {"status": "Success"}, "other_flights": []}
    assert flight_adapter.parse_response(payload).insight is None


# --- robustness: malformed / partial data ---

def test_error_status_raises_adapter_error():
    payload = {"search_metadata": {"status": "Error"}, "error": "quota exceeded"}
    try:
        flight_adapter.parse_response(payload)
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "quota" in str(exc)


def test_empty_response_yields_no_options_without_crashing():
    payload = {"search_metadata": {"status": "Success"}}
    result = flight_adapter.parse_response(payload)
    assert result.options == []


def test_malformed_entry_is_skipped_not_fatal():
    # One bad itinerary among several must not destroy the whole search.
    payload = {
        "search_metadata": {"status": "Success"},
        "other_flights": [
            {"flights": [], "price": 100},                       # no legs
            {"flights": [{"departure_airport": {"id": "TLV"}}]},  # no price
            {
                "flights": [{
                    "departure_airport": {"id": "TLV"},
                    "arrival_airport": {"id": "GVA"},
                    "duration": 275, "airline": "easyJet",
                }],
                "total_duration": 275, "price": 199, "type": "Round trip",
            },
        ],
    }
    result = flight_adapter.parse_response(payload)
    assert len(result.options) == 1
    assert result.options[0].price_eur == 199


def test_zero_and_negative_prices_are_rejected():
    # Guards the same class of bug found across the cost engine: a
    # nonsensical price must never enter the pipeline.
    for bad_price in (0, -50):
        payload = {
            "search_metadata": {"status": "Success"},
            "other_flights": [{
                "flights": [{
                    "departure_airport": {"id": "TLV"},
                    "arrival_airport": {"id": "GVA"},
                    "duration": 275, "airline": "X",
                }],
                "price": bad_price,
            }],
        }
        assert flight_adapter.parse_response(payload).options == []


# --- request-building logic (no network needed) ---

def test_stops_param_maps_max_connections_correctly():
    assert flight_adapter._stops_param(0) == 1    # nonstop only
    assert flight_adapter._stops_param(1) == 2    # 1 stop or fewer
    assert flight_adapter._stops_param(2) == 3    # 2 stops or fewer
    assert flight_adapter._stops_param(None) == 0  # any


def test_search_without_api_key_raises_clear_error():
    import os
    saved = os.environ.pop("SERPAPI_API_KEY", None)
    try:
        flight_adapter.clear_cache()
        flight_adapter.search_flights("TLV", ["GVA"], date(2027, 1, 15), date(2027, 1, 20))
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "SERPAPI_API_KEY" in str(exc)
    finally:
        if saved is not None:
            os.environ["SERPAPI_API_KEY"] = saved


def test_search_rejects_empty_destination_list():
    try:
        flight_adapter.search_flights("TLV", [], date(2027, 1, 15))
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "destination" in str(exc).lower()


def test_search_rejects_return_date_before_outbound():
    # Same validation lesson as UserPreferences: catch nonsense at the
    # boundary rather than paying for a doomed API call.
    try:
        flight_adapter.search_flights(
            "TLV", ["GVA"], date(2027, 1, 20), date(2027, 1, 15)
        )
        assert False, "expected AdapterError"
    except AdapterError as exc:
        assert "return_date" in str(exc)


# --- caching ---

def test_cache_returns_stored_result_flagged_as_cached():
    from ski_optimizer.models import FlightSearchResult
    from ski_optimizer.adapters.response_cache import get_cache
    flight_adapter.clear_cache()
    stored = FlightSearchResult(
        options=[FlightOption(price_eur=200, origin_airport="TLV",
                              destination_airport="GVA", airline="Test",
                              total_duration_minutes=275, stops=0)],
    )
    key = flight_adapter._cache_key("TLV", ["GVA"], date(2027, 1, 15),
                                    date(2027, 1, 20), 1, 1, "EUR")
    get_cache().set(key, stored)

    result = flight_adapter.search_flights(
        "TLV", ["GVA"], date(2027, 1, 15), date(2027, 1, 20),
        adults=1, max_connections=1, currency="EUR",
    )
    assert result.from_cache is True
    assert result.options[0].price_eur == 200
    flight_adapter.clear_cache()


def test_cache_key_is_order_independent_for_destinations():
    # TLV->GVA,INN and TLV->INN,GVA are the same search and must not
    # cost two API calls.
    a = flight_adapter._cache_key("TLV", ["GVA", "INN"], date(2027, 1, 15),
                                   date(2027, 1, 20), 1, 1, "EUR")
    b = flight_adapter._cache_key("TLV", ["INN", "GVA"], date(2027, 1, 15),
                                   date(2027, 1, 20), 1, 1, "EUR")
    assert a == b


def test_cache_key_distinguishes_different_dates():
    a = flight_adapter._cache_key("TLV", ["GVA"], date(2027, 1, 15),
                                   date(2027, 1, 20), 1, 1, "EUR")
    b = flight_adapter._cache_key("TLV", ["GVA"], date(2027, 1, 16),
                                   date(2027, 1, 20), 1, 1, "EUR")
    assert a != b


# --- helper ---

def test_cheapest_price_returns_lowest():
    assert flight_adapter.cheapest_price_eur(_parse()) == 167


def test_cheapest_price_of_empty_result_is_none():
    from ski_optimizer.models import FlightSearchResult
    assert flight_adapter.cheapest_price_eur(FlightSearchResult(options=[])) is None


# --- integration with the real resort data ---

def test_every_resort_yields_at_least_one_iata_code():
    # If this fails, some spreadsheet airport cell stopped matching the
    # "(XXX)" convention and that resort would silently lose live pricing.
    from ski_optimizer.data.resort_repository import load_resorts
    from ski_optimizer.engine.cost_calculator import airport_codes_for
    for r in load_resorts():
        assert airport_codes_for(r), f"{r.name}: no IATA code in {r.nearest_airport!r}"


def test_multi_airport_resorts_are_detected():
    # The multi-airport search only pays off if we actually extract
    # multiple codes where they exist (14 of 30 resorts at time of writing).
    from ski_optimizer.data.resort_repository import load_resorts
    from ski_optimizer.engine.cost_calculator import airport_codes_for
    multi = [r for r in load_resorts() if len(airport_codes_for(r)) > 1]
    assert len(multi) >= 10, "expected many resorts served by several airports"


def test_live_flight_cost_returns_none_without_api_key():
    # Degrades to None (caller falls back visibly) rather than raising
    # or inventing a number.
    import os
    from datetime import date
    from ski_optimizer.data.resort_repository import load_resorts
    from ski_optimizer.engine.cost_calculator import live_flight_cost_eur
    saved = os.environ.pop("SERPAPI_API_KEY", None)
    try:
        flight_adapter.clear_cache()
        resort = load_resorts()[0]
        assert live_flight_cost_eur(resort, date(2027, 1, 15), date(2027, 1, 20)) is None
    finally:
        if saved is not None:
            os.environ["SERPAPI_API_KEY"] = saved
