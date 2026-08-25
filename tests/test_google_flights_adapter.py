"""
Tests for adapters/google_flights_adapter.py.

Same philosophy as test_flight_adapter.py: the parsing layer
(_parse_flight_result) is tested offline, with no network and no
`fast-flights` scraping call, against hand-built instances of that
library's own dataclasses (fast_flights.model) rather than a JSON
fixture, since this provider returns real Python objects, not JSON.
search_flights' orchestration (per-airport degradation, caching, error
handling) is tested by monkeypatching _search_one_airport directly, so
these tests never touch the network either.

What these do NOT prove: that a real scrape against Google Flights
still returns this shape. That was verified by hand, live, while
building this adapter (see the module's own docstring) -- not
something an offline test can keep proving on every run.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import google_flights_adapter as gfa
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError
from fast_flights.model import Airport, CarbonEmission, Flights, SimpleDatetime, SingleFlight


@pytest.fixture(autouse=True)
def _fresh_cache():
    response_cache.get_cache().clear()
    yield
    response_cache.get_cache().clear()


def _leg(origin="TLV", dest="GVA", dep_date=(2027, 1, 10), dep_time=(8, 0),
        arr_date=(2027, 1, 10), arr_time=(11, 30), duration=210, plane="A320"):
    return SingleFlight(
        from_airport=Airport(code=origin, name=origin),
        to_airport=Airport(code=dest, name=dest),
        departure=SimpleDatetime(date=dep_date, time=dep_time),
        arrival=SimpleDatetime(date=arr_date, time=arr_time),
        duration=duration,
        plane_type=plane,
    )


def _flights_result(price=335, airlines=None, legs=None, typ="LX"):
    return Flights(
        type=typ,
        price=price,
        airlines=airlines if airlines is not None else ["SWISS"],
        flights=legs if legs is not None else [_leg()],
        carbon=CarbonEmission(typical_on_route=200, emission=180),
    )


# --- parsing ---

def test_parses_a_direct_flight():
    opt = gfa._parse_flight_result(_flights_result(), currency_is_eur=True)
    assert opt is not None
    assert opt.price_eur == 335
    assert opt.origin_airport == "TLV"
    assert opt.destination_airport == "GVA"
    assert opt.stops == 0
    assert opt.airline == "SWISS"


def test_connecting_flight_reports_stops_and_spans_first_to_last_leg():
    legs = [
        _leg("TLV", "FRA", dep_date=(2027, 1, 10), dep_time=(7, 55), arr_date=(2027, 1, 10), arr_time=(11, 35), duration=280),
        _leg("FRA", "GVA", dep_date=(2027, 1, 10), dep_time=(21, 10), arr_date=(2027, 1, 10), arr_time=(22, 25), duration=75),
    ]
    opt = gfa._parse_flight_result(_flights_result(legs=legs, airlines=["Lufthansa", "SWISS"]), currency_is_eur=True)
    assert opt.origin_airport == "TLV"
    assert opt.destination_airport == "GVA"
    assert opt.stops == 1
    assert opt.airline == "Lufthansa + SWISS"


def test_duration_includes_layover_not_just_summed_leg_durations():
    # REGRESSION: a naive sum of leg durations (280 + 75 = 355 min) would
    # ignore the ~9.5 hour layover in FRA visible from the actual
    # departure/arrival clock times -- the whole point of using real
    # timestamps instead of the library's raw per-leg `duration` field.
    legs = [
        _leg("TLV", "FRA", dep_time=(7, 55), arr_time=(11, 35), duration=280),
        _leg("FRA", "GVA", dep_time=(21, 10), arr_time=(22, 25), duration=75),
    ]
    opt = gfa._parse_flight_result(_flights_result(legs=legs), currency_is_eur=True)
    # 07:55 -> 22:25 same day = 14h30m = 870 minutes
    assert opt.total_duration_minutes == 870


def test_rejects_zero_or_negative_price():
    assert gfa._parse_flight_result(_flights_result(price=0), currency_is_eur=True) is None
    assert gfa._parse_flight_result(_flights_result(price=-50), currency_is_eur=True) is None


def test_rejects_a_result_with_no_legs():
    assert gfa._parse_flight_result(_flights_result(legs=[]), currency_is_eur=True) is None


# --- search_flights orchestration ---

def test_search_flights_rejects_return_before_outbound():
    with pytest.raises(AdapterError):
        gfa.search_flights("TLV", "GVA", date(2027, 1, 20), date(2027, 1, 10))


def test_search_flights_rejects_when_no_destination_airports_given():
    with pytest.raises(AdapterError):
        gfa.search_flights("TLV", [], date(2027, 1, 10))


def test_search_flights_merges_results_across_destination_airports(monkeypatch):
    from ski_optimizer.models import FlightOption

    def fake_search_one(origin, dest, outbound, ret, adults, max_conn, currency):
        return [FlightOption(price_eur=100, origin_airport=origin, destination_airport=dest,
                             airline="Test", total_duration_minutes=200, stops=0)]

    monkeypatch.setattr(gfa, "_search_one_airport", fake_search_one)
    result = gfa.search_flights("TLV", ["GVA", "CMF"], date(2027, 1, 10), use_cache=False)
    assert {o.destination_airport for o in result.options} == {"GVA", "CMF"}


def test_search_flights_degrades_when_only_some_airports_fail(monkeypatch):
    from ski_optimizer.models import FlightOption

    def fake_search_one(origin, dest, outbound, ret, adults, max_conn, currency):
        if dest == "CMF":
            raise RuntimeError("no service to this airport")
        return [FlightOption(price_eur=100, origin_airport=origin, destination_airport=dest,
                             airline="Test", total_duration_minutes=200, stops=0)]

    monkeypatch.setattr(gfa, "_search_one_airport", fake_search_one)
    result = gfa.search_flights("TLV", ["GVA", "CMF"], date(2027, 1, 10), use_cache=False)
    assert len(result.options) == 1
    assert result.options[0].destination_airport == "GVA"


def test_search_flights_raises_when_every_airport_fails(monkeypatch):
    def fake_search_one(origin, dest, outbound, ret, adults, max_conn, currency):
        raise RuntimeError("blocked")

    monkeypatch.setattr(gfa, "_search_one_airport", fake_search_one)
    with pytest.raises(AdapterError):
        gfa.search_flights("TLV", ["GVA", "CMF"], date(2027, 1, 10), use_cache=False)


def test_search_flights_caches_identical_queries(monkeypatch):
    from ski_optimizer.models import FlightOption

    call_count = {"n": 0}

    def fake_search_one(origin, dest, outbound, ret, adults, max_conn, currency):
        call_count["n"] += 1
        return [FlightOption(price_eur=100, origin_airport=origin, destination_airport=dest,
                             airline="Test", total_duration_minutes=200, stops=0)]

    monkeypatch.setattr(gfa, "_search_one_airport", fake_search_one)
    gfa.search_flights("TLV", "GVA", date(2027, 1, 10), use_cache=True)
    gfa.search_flights("TLV", "GVA", date(2027, 1, 10), use_cache=True)
    assert call_count["n"] == 1  # second call served from cache


# --- cheapest_price_eur ---

def test_cheapest_price_eur_picks_the_minimum(monkeypatch):
    from ski_optimizer.models import FlightOption, FlightSearchResult

    result = FlightSearchResult(options=[
        FlightOption(price_eur=300, origin_airport="TLV", destination_airport="GVA",
                    airline="A", total_duration_minutes=100, stops=0),
        FlightOption(price_eur=180, origin_airport="TLV", destination_airport="GVA",
                    airline="B", total_duration_minutes=150, stops=1),
    ])
    assert gfa.cheapest_price_eur(result) == 180


def test_cheapest_price_eur_is_none_for_no_options():
    from ski_optimizer.models import FlightSearchResult
    assert gfa.cheapest_price_eur(FlightSearchResult(options=[])) is None


# --- search_url ---

def test_search_url_round_trip_matches_the_captured_reference_value():
    # Pure/offline -- no network call, _build_query().url() is plain
    # protobuf encoding. Reference value captured by actually calling
    # search_url() and confirming live (via browser) that navigating to
    # it lands on the correct route/dates with real prices -- see this
    # module's own docstring on search_url.
    url = gfa.search_url("TLV", "BGY", date(2027, 1, 10), date(2027, 1, 16))
    assert url == (
        "https://www.google.com/travel/flights/search?tfs="
        "GhoSCjIwMjctMDEtMTBqBRIDVExWcgUSA0JHWRoaEgoyMDI3LTAxLTE2agUSA0JHWXIFEgNUTFZCAQFIAZgBAQ=="
        "&hl=en&curr=EUR"
    )


def test_search_url_one_way_omits_the_return_leg():
    url = gfa.search_url("TLV", "BGY", date(2027, 1, 10))
    assert url == (
        "https://www.google.com/travel/flights/search?tfs="
        "GhoSCjIwMjctMDEtMTBqBRIDVExWcgUSA0JHWUIBAUgBmAEC"
        "&hl=en&curr=EUR"
    )


def test_search_url_always_specifies_language_so_google_does_not_have_to_guess():
    # Regression guard: create_query() defaults language="" (Google
    # decides), which produced a live &hl= with nothing after it --
    # caught by inspecting the actual URL fast_flights.Query.url()
    # built, not by assumption.
    url = gfa.search_url("TLV", "GVA", date(2027, 1, 10))
    assert "&hl=en&" in url
