"""
The Kiwi fallback must cover the WHOLE flight surface, not just the
price. Before this existed, live_flight_cost_eur() fell back to Kiwi
for the number while live_flight_options() and
live_flight_booking_url() stayed Google-only -- so a Google outage
produced a live price with NO named itineraries and NO booking link
(owner: "if from our google flights scraper we don't get a real link
with live, we can look it up on kiwi mcp and find the exact stuff we
need").

Kiwi itineraries carry a real booking deep link (bookingUrl) directly
in the search response, so the fallback is strictly cheaper than the
Google path's click-time second fetch.
"""
from datetime import date

import pytest

from ski_optimizer.adapters import google_flights_adapter, kiwi_mcp_adapter
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.engine.cost_calculator import (
    live_flight_booking_url,
    live_flight_options,
)
from ski_optimizer.models import FlightOption, FlightSearchResult

OUT = date(2027, 1, 16)
BACK = date(2027, 1, 23)

KIWI_URL = "https://www.kiwi.com/booking?token=abc123"


def _kiwi_option(price=300.0, numbers=("LX 253",), url=KIWI_URL):
    return FlightOption(
        price_eur=price, origin_airport="TLV", destination_airport="GVA",
        airline="SWISS", total_duration_minutes=390, stops=1,
        booking_token=url, flight_numbers=list(numbers),
    )


@pytest.fixture
def resort():
    return load_resorts()[0]


@pytest.fixture
def google_empty(monkeypatch):
    monkeypatch.setattr(
        google_flights_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[]))


@pytest.fixture
def kiwi_returns_one(monkeypatch):
    option = _kiwi_option()
    monkeypatch.setattr(
        kiwi_mcp_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[option]))
    return option


def test_options_fall_back_to_kiwi_when_google_is_empty(
        resort, google_empty, kiwi_returns_one):
    picks = live_flight_options(resort, OUT, BACK)
    assert [p.option for p in picks] == [kiwi_returns_one]


def test_options_fall_back_to_kiwi_when_google_raises(
        resort, kiwi_returns_one, monkeypatch):
    def _raise(**_kw):
        raise AdapterError("scrape blocked")
    monkeypatch.setattr(google_flights_adapter, "search_flights", _raise)
    picks = live_flight_options(resort, OUT, BACK)
    assert [p.option for p in picks] == [kiwi_returns_one]


def test_options_are_empty_when_both_providers_fail(resort, google_empty):
    # conftest._no_real_kiwi_mcp already forces the kiwi transport to
    # fail offline, so "both dead" needs no extra stubbing.
    assert live_flight_options(resort, OUT, BACK) == []


def test_google_options_still_win_when_present(resort, monkeypatch):
    google_option = FlightOption(
        price_eur=250.0, origin_airport="TLV", destination_airport="GVA",
        airline="easyJet", total_duration_minutes=300, stops=0,
        booking_token="opaque-protobuf-token", flight_numbers=["U2 1234"])
    monkeypatch.setattr(
        google_flights_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[google_option]))

    def _fail(**_kw):
        raise AssertionError("kiwi must not be called when google delivered")
    monkeypatch.setattr(kiwi_mcp_adapter, "search_flights", _fail)

    picks = live_flight_options(resort, OUT, BACK)
    assert [p.option for p in picks] == [google_option]


def test_booking_url_falls_back_to_kiwi_deep_link(
        resort, google_empty, kiwi_returns_one):
    url = live_flight_booking_url(resort, OUT, BACK,
                                  flight_numbers=["LX 253"])
    assert url == KIWI_URL


def test_booking_url_kiwi_fallback_requires_a_flight_number_match(
        resort, google_empty, kiwi_returns_one):
    # A booking page for a DIFFERENT flight than the one clicked is
    # worse than no link -- same rule as the Google path.
    assert live_flight_booking_url(resort, OUT, BACK,
                                   flight_numbers=["FR 999"]) is None


def test_booking_url_kiwi_fallback_never_returns_an_opaque_token(
        resort, google_empty, monkeypatch):
    # Only a real http(s) deep link may leave the engine; an opaque
    # token would render as a dead href in the frontend.
    option = _kiwi_option(url="not-a-url-token")
    monkeypatch.setattr(
        kiwi_mcp_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[option]))
    assert live_flight_booking_url(resort, OUT, BACK,
                                   flight_numbers=["LX 253"]) is None


def test_flight_options_out_carries_the_kiwi_booking_url(
        resort, google_empty, kiwi_returns_one):
    # API layer: a Kiwi-sourced option ships its deep link inline so
    # the frontend can link it directly with no click-time fetch.
    from ski_optimizer.api.routes.search import _flight_options_out
    from ski_optimizer.engine.cost_calculator import compute_trip_cost
    from ski_optimizer.models import UserPreferences

    prefs = UserPreferences(budget_eur_per_person=1500, ski_days=5)
    cost = compute_trip_cost(resort, prefs)
    out = _flight_options_out(resort, OUT, BACK, True, 1, cost)
    assert [o.booking_url for o in out] == [KIWI_URL]


def test_flight_options_out_hides_opaque_google_tokens(resort, monkeypatch):
    google_option = FlightOption(
        price_eur=250.0, origin_airport="TLV", destination_airport="GVA",
        airline="easyJet", total_duration_minutes=300, stops=0,
        booking_token="opaque-protobuf-token", flight_numbers=["U2 1234"])
    monkeypatch.setattr(
        google_flights_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[google_option]))

    from ski_optimizer.api.routes.search import _flight_options_out
    from ski_optimizer.engine.cost_calculator import compute_trip_cost
    from ski_optimizer.models import UserPreferences

    prefs = UserPreferences(budget_eur_per_person=1500, ski_days=5)
    cost = compute_trip_cost(resort, prefs)
    out = _flight_options_out(resort, OUT, BACK, True, 1, cost)
    assert [o.booking_url for o in out] == [None]
