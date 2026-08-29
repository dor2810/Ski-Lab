"""
Rome2Rio route discovery -- the coverage layer under the transfer list.

WHY (owner pointed at github.com/api-evangelist/rome2rio, 2026-08-29):
Omio's discovery index carries scheduled services for only 9 of our 32
mapped resorts, and Alps2Alps covers 30 with private hire only. Neither
answers "how do I actually get to St. Anton". Rome2Rio answers it for
ALL 39 resorts (verified: every one returns priced routes).

WHAT THESE PRICES ARE, and this matters: INDICATIVE RANGES for the
journey (e.g. "Bus EUR20-38"), not bookable fares for a date. Rome2Rio
is a route-discovery engine -- this endpoint takes no date at all. So
these options are labelled indicative and never masquerade as a live
quote; the dated Omio/Alps2Alps quotes remain the bookable ones.

PROVENANCE, stated plainly: the documented partner endpoint
(free.rome2rio.com) is DEAD -- NXDOMAIN, and the api-evangelist profile
itself records callable_host: false. What works is the endpoint their
own website calls, with the web client's embedded key, found by
watching the site's network. That is the same category as this
project's Google Flights/Hotels adapters: reverse-engineered, not
sanctioned, and liable to change without notice. It degrades to None
like every other adapter here.
"""
import pytest

from ski_optimizer.adapters import rome2rio_adapter as r2r
from ski_optimizer.adapters.base import AdapterError

PAYLOAD = {
    "routes": [
        {"name": "Bus", "duration": 24000,
         "indicativePrices": [{"priceLow": 20, "priceHigh": 38, "currency": "EUR"}]},
        {"name": "Train, taxi", "duration": 10620,
         "indicativePrices": [{"priceLow": 107, "priceHigh": 177, "currency": "EUR"}]},
        {"name": "Drive", "duration": 9000, "indicativePrices": []},
        {"name": "Fly, shuttle", "duration": 8000,
         "indicativePrices": [{"priceLow": 300, "priceHigh": 400, "currency": "EUR"}]},
    ]
}


def test_routes_are_parsed_with_indicative_ranges(monkeypatch):
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: PAYLOAD)
    routes = r2r.search_routes("Geneva Airport", "Val Thorens", use_cache=False)
    bus = next(x for x in routes if x.name == "Bus")
    assert bus.price_low_eur == 20 and bus.price_high_eur == 38
    # duration arrives in SECONDS; a 400-minute bus is not 24000 minutes.
    assert bus.duration_minutes == 400
    assert bus.is_indicative is True


def test_unpriced_routes_are_dropped_not_shown_as_free(monkeypatch):
    # "Drive" has no indicative price -- it is a suggestion, not an
    # offer, and a EUR0 transfer would be a fabricated number.
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: PAYLOAD)
    routes = r2r.search_routes("A", "B", use_cache=False)
    assert all(r.price_low_eur is not None for r in routes)
    assert "Drive" not in [r.name for r in routes]


def test_flight_routes_are_excluded(monkeypatch):
    # The trip already HAS a flight; a second one from the arrival
    # airport is never the transfer a skier means (same rule as the
    # Omio adapter).
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: PAYLOAD)
    assert "Fly, shuttle" not in [r.name for r in r2r.search_routes("A", "B", use_cache=False)]


def test_cheapest_first(monkeypatch):
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: PAYLOAD)
    routes = r2r.search_routes("A", "B", use_cache=False)
    assert [r.price_low_eur for r in routes] == sorted(r.price_low_eur for r in routes)


def test_provider_failure_degrades_to_empty_never_raises(monkeypatch):
    def _boom(**_kw):
        raise AdapterError("rome2rio unreachable")
    monkeypatch.setattr(r2r, "_fetch", _boom)
    assert r2r.search_routes("A", "B", use_cache=False) == []


def test_no_routes_is_empty_not_an_error(monkeypatch):
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: {"routes": []})
    assert r2r.search_routes("A", "B", use_cache=False) == []


def test_blank_places_are_rejected():
    with pytest.raises(AdapterError):
        r2r.search_routes("", "Val Thorens")


PAYLOAD_WITH_PLACES = {
    "places": [
        {"shortName": "Innsbruck Airport", "canonicalName": "Innsbruck-Airport"},
        {"shortName": "St Anton am Arlberg", "canonicalName": "St-Anton-am-Arlberg"},
        {"shortName": "somewhere else", "canonicalName": "Ignore-Me"},
    ],
    "routes": [
        {"name": "Train", "duration": 6420,
         "indicativePrices": [{"priceLow": 12, "priceHigh": 80, "currency": "EUR"}]},
    ],
}


def test_every_route_carries_a_real_results_link(monkeypatch):
    # Owner: "i want real links for all the options." Built from the
    # provider's OWN canonical slugs (places[0]/[1]) -- slugifying our
    # spelling would give "St.-Anton-am-Arlberg", which their router
    # rejects.
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: PAYLOAD_WITH_PLACES)
    route = r2r.search_routes("Innsbruck Airport", "St. Anton am Arlberg",
                              use_cache=False)[0]
    assert route.booking_url == (
        "https://www.rome2rio.com/map/Innsbruck-Airport/St-Anton-am-Arlberg")


def test_no_link_is_invented_when_the_provider_gives_no_slugs(monkeypatch):
    # Better no link than one that lands on an empty map -- a
    # hand-built URL did exactly that once already.
    monkeypatch.setattr(r2r, "_fetch", lambda **_kw: {
        "places": [], "routes": PAYLOAD_WITH_PLACES["routes"]})
    assert r2r.search_routes("A", "B", use_cache=False)[0].booking_url is None
