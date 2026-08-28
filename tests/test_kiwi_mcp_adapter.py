"""
Tests for adapters/kiwi_mcp_adapter.py -- the free fallback flight
source behind the Google Flights scraper.

Parsing is tested offline against tests/fixtures/kiwi_tlv_gva.json, a
REAL response captured from Kiwi's live MCP server on 2026-08-28 (15
itineraries, TLV->GVA 9-15 Jan 2027) -- same philosophy as
test_flight_adapter.py's SerpApi fixture. Orchestration is tested by
monkeypatching the transport, never the network.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import kiwi_mcp_adapter as kma
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError

FIXTURE = json.load(open(Path(__file__).parent / "fixtures" / "kiwi_tlv_gva.json"))


@pytest.fixture(autouse=True)
def _fresh_cache():
    response_cache.get_cache().clear()
    yield
    response_cache.get_cache().clear()


# --- parsing (offline, real fixture) ---

def test_parses_the_whole_fixture_into_flight_options():
    options = [kma._parse_itinerary(it) for it in FIXTURE["itineraries"]]
    options = [o for o in options if o is not None]
    assert len(options) == FIXTURE["resultsCount"] == len(FIXTURE["itineraries"])
    for o in options:
        assert o.price_eur > 0
        assert o.origin_airport == "TLV"
        assert o.destination_airport == "GVA"
        assert o.total_duration_minutes > 0
        assert o.stops >= 0


def test_flight_numbers_match_the_project_style():
    # Kiwi writes "LX253"; the rest of this project (and every airport
    # departure board) writes "LX 253" -- the parser normalizes so the
    # frontend and the booking-link matcher see one format.
    first = kma._parse_itinerary(FIXTURE["itineraries"][0])
    assert first.flight_numbers, "segments carry flightNumber -- must not be dropped"
    assert first.flight_numbers[0] == "LX 253"
    for fn in first.flight_numbers:
        carrier, sep, number = fn.partition(" ")
        assert sep == " " and carrier and number


def test_duration_uses_the_providers_own_total_not_clock_arithmetic():
    # Same lesson the Google adapter learned the hard way (timezone
    # offsets): the provider's totalDurationSeconds is authoritative.
    it = FIXTURE["itineraries"][0]
    parsed = kma._parse_itinerary(it)
    assert parsed.total_duration_minutes == it["totalDurationSeconds"] // 60


def test_booking_url_is_preserved_on_the_option():
    it = FIXTURE["itineraries"][0]
    parsed = kma._parse_itinerary(it)
    assert parsed.booking_token == it["bookingUrl"]
    assert parsed.booking_token.startswith("https://kiwi.com/")


def test_a_malformed_itinerary_is_dropped_not_fatal():
    assert kma._parse_itinerary({"price": "not-a-number"}) is None
    assert kma._parse_itinerary({}) is None


# --- orchestration ---

def _fake_call_tool(payload):
    def call_tool(args):
        _fake_call_tool.last_args = args
        return payload
    return call_tool


def test_search_flights_returns_options_and_caches(monkeypatch):
    calls = {"n": 0}

    def fake(args):
        calls["n"] += 1
        return FIXTURE

    monkeypatch.setattr(kma, "_call_search_tool", fake)
    r1 = kma.search_flights("TLV", "GVA", date(2027, 1, 9), date(2027, 1, 15))
    r2 = kma.search_flights("TLV", "GVA", date(2027, 1, 9), date(2027, 1, 15))
    assert len(r1.options) == 15
    assert r2.from_cache is True
    assert calls["n"] == 1, "identical queries must hit the response cache"


def test_max_connections_maps_to_kiwis_own_parameter(monkeypatch):
    monkeypatch.setattr(kma, "_call_search_tool", _fake_call_tool(FIXTURE))
    kma.search_flights("TLV", "GVA", date(2027, 1, 9), date(2027, 1, 15),
                       max_connections=0, use_cache=False)
    assert _fake_call_tool.last_args.get("max_sector_stopovers") == 0


def test_provider_failure_raises_adapter_error(monkeypatch):
    def boom(args):
        raise RuntimeError("mcp server down")

    monkeypatch.setattr(kma, "_call_search_tool", boom)
    with pytest.raises(AdapterError):
        kma.search_flights("TLV", "GVA", date(2027, 1, 9), date(2027, 1, 15), use_cache=False)
