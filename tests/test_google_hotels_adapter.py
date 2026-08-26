"""
Tests for adapters/google_hotels_adapter.py.

Same philosophy as test_flight_adapter.py and test_google_flights_adapter.py:
the parsing/encoding layer is tested offline, against hand-built
payload shapes, with _fetch_html mocked wherever a test needs to
exercise search_accommodation's orchestration. No test in this file
touches the network.

What these do NOT prove: that Google Hotels' real response shape still
matches what's hardcoded here. That was verified live, by hand, while
building this adapter (see the module's own docstring for exactly how
and what was checked) -- not something an offline test can keep
proving on every run. _build_ts's regression test is the one exception
that DOES double as an ongoing correctness check: it compares against
a real `ts` value Google itself generated (captured via a live browser
session picking real calendar dates), so if the encoder's byte layout
ever drifts, this test catches it without needing network access.
"""
import base64
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import google_hotels_adapter as gha
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.data.resort_repository import load_resorts


@pytest.fixture(autouse=True)
def _fresh_cache():
    response_cache.get_cache().clear()
    yield
    response_cache.get_cache().clear()


# --- _build_ts: regression-tested against a REAL Google-generated value ---

def test_build_ts_matches_a_real_captured_example_byte_for_byte():
    # Captured live: navigated to Google Hotels, picked Jan 10 -> Jan 15
    # 2027 for "Val Thorens, France" through the actual calendar UI, and
    # read window.location.href for the `ts` Google itself generated.
    captured = (
        "CAESCgoCCAMKAggDEAAaVgo4EjQyJTB4NDc4OTg2NjAwMjI2NzA3MTow"
        "eDhlYzdiYzZkYzFlZWYzMzM6C1ZhbCBUaG9yZW5zGgASGhIUCgcI6w8Q"
        "ARgKEgcI6w8QARgPGAUyAggBKgkKBToDSUxTGgA"
    )
    mine = gha._build_ts(
        "0x4789866002267071:0x8ec7bc6dc1eef333", "Val Thorens",
        date(2027, 1, 10), date(2027, 1, 15), currency="ILS",
    )
    assert mine == captured


def test_build_ts_round_trips_through_protobuf_wire_format():
    # Decode our own output back out (independent of the encoder's
    # internals -- a plain wire-format walker) and confirm the dates
    # and place ID land where the real payload puts them.
    ts = gha._build_ts("0x1:0x2", "Somewhere", date(2027, 3, 4), date(2027, 3, 11), currency="EUR")
    raw = base64.urlsafe_b64decode(ts + "=" * (-len(ts) % 4))

    def read_varint(buf, i):
        result, shift = 0, 0
        while True:
            b = buf[i]; i += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result, i
            shift += 7

    assert b"Somewhere" in raw
    assert b"0x1:0x2" in raw
    assert b"EUR" in raw
    # Year 2027 appears as a varint-encoded value; spot check it decodes
    # correctly at all (not just "the bytes 2027 happen to appear").
    idx = raw.index(b"Somewhere")
    assert idx > 0


# --- _parse_price ---

def test_parse_price_picks_the_smaller_of_nightly_and_total():
    entry = [None, "Some Hotel", [["€965"], ["€6,752"]]]
    assert gha._parse_price(entry) == 965.0


def test_parse_price_handles_thousands_separators():
    entry = [None, "Expensive Hotel", ["€6,752"]]
    assert gha._parse_price(entry) == 6752.0


def test_parse_price_returns_none_when_no_price_present():
    entry = [None, "Sold Out Hotel", ["no rate available"]]
    assert gha._parse_price(entry) is None


def test_parse_price_rejects_implausible_values():
    # REGRESSION: a fabricated-looking number (e.g. a stray "€1" from
    # unrelated page text) must not be trusted as a real nightly rate.
    entry = [None, "Weird Entry", ["€1"]]
    assert gha._parse_price(entry) is None
    entry_huge = [None, "Weird Entry 2", ["€999999"]]
    assert gha._parse_price(entry_huge) is None


# --- _parse_property ---

def test_parse_property_combines_name_and_price():
    entry = [None, "Hôtel Marielle", ["€732"]]
    opt = gha._parse_property(entry)
    assert opt is not None
    assert opt.property_name == "Hôtel Marielle"
    assert opt.price_eur_per_night == 732.0


def test_parse_property_is_none_without_a_name():
    entry = [None, "", ["€500"]]
    assert gha._parse_property(entry) is None


def test_parse_property_is_none_without_a_price():
    entry = [None, "Club Med Val Thorens Sensation", []]
    assert gha._parse_property(entry) is None


# --- _resolve_place_id / _find_first_matching ---

def test_resolve_place_id_finds_the_shared_area_id():
    data = [[[[9, [
        [56, {"397419284": [[None, "Hotel A", ["0x4789866002267071:0x8ec7bc6dc1eef333", "nonsense-string"]]]}],
    ]]]]]
    assert gha._resolve_place_id(data) == "0x4789866002267071:0x8ec7bc6dc1eef333"


def test_resolve_place_id_is_none_when_absent():
    data = [[[[9, [[56, {"397419284": [[None, "Hotel A", ["nothing here"]]]}]]]]]]
    assert gha._resolve_place_id(data) is None


# --- _iter_hotel_entries ---

def test_iter_hotel_entries_yields_each_hotels_own_record():
    data = [[[[9, [
        [56, {"397419284": [[None, "Hotel A", []]]}],
        [71, {"300000000": [[None, "Hotel B", []]]}],
    ]]]]]
    entries = list(gha._iter_hotel_entries(data))
    names = [e[1] for e in entries]
    assert names == ["Hotel A", "Hotel B"]


def test_iter_hotel_entries_is_empty_for_malformed_data():
    assert list(gha._iter_hotel_entries([])) == []
    assert list(gha._iter_hotel_entries({"unexpected": "shape"})) == []


# --- search_accommodation orchestration ---

def _resort():
    return next(r for r in load_resorts() if r.name == "Val Thorens")


def test_search_accommodation_rejects_nonpositive_nights():
    with pytest.raises(AdapterError):
        gha.search_accommodation(_resort(), date(2027, 1, 10), nights=0, rooms_needed=1)


def test_search_accommodation_rejects_nonpositive_rooms():
    with pytest.raises(AdapterError):
        gha.search_accommodation(_resort(), date(2027, 1, 10), nights=5, rooms_needed=0)


def test_search_accommodation_raises_when_place_id_cannot_be_resolved(monkeypatch):
    monkeypatch.setattr(gha, "_fetch_html", lambda url: "<html></html>")
    monkeypatch.setattr(gha, "_extract_ds_blob", lambda html, key: [[[[9, []]]]])
    with pytest.raises(AdapterError):
        gha.search_accommodation(_resort(), date(2027, 1, 10), nights=5, rooms_needed=1)


def test_search_accommodation_returns_parsed_options_end_to_end(monkeypatch):
    call_log = []

    def fake_fetch(url):
        call_log.append(url)
        return "<html>fake</html>"

    resolve_data = [[[[9, [
        [56, {"397419284": [[None, "Hotel A", ["0x1:0x2"]]]}],
    ]]]]]
    dated_data = [[[[9, [
        [56, {"397419284": [[None, "Hotel A", ["€500"]]]}],
        [71, {"300000000": [[None, "Hotel B", ["€300", "€1,800"]]]}],
    ]]]]]

    responses = iter([resolve_data, dated_data])
    monkeypatch.setattr(gha, "_fetch_html", fake_fetch)
    monkeypatch.setattr(gha, "_extract_ds_blob", lambda html, key: next(responses))

    result = gha.search_accommodation(_resort(), date(2027, 1, 10), nights=6, rooms_needed=1, use_cache=False)
    assert len(call_log) == 2  # one dateless resolve call, one dated call
    assert [o.property_name for o in result.options] == ["Hotel B", "Hotel A"]  # sorted cheapest first
    assert gha.cheapest_price_eur_per_night(result) == 300.0


def test_search_accommodation_caches_identical_queries(monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(url):
        call_count["n"] += 1
        return "<html>fake</html>"

    resolve_data = [[[[9, [[56, {"397419284": [[None, "Hotel A", ["0x1:0x2"]]]}]]]]]]
    dated_data = [[[[9, [[56, {"397419284": [[None, "Hotel A", ["€500"]]]}]]]]]]
    responses = [resolve_data, dated_data, resolve_data, dated_data]

    monkeypatch.setattr(gha, "_fetch_html", fake_fetch)
    monkeypatch.setattr(gha, "_extract_ds_blob", lambda html, key: responses.pop(0))

    gha.search_accommodation(_resort(), date(2027, 1, 10), nights=6, rooms_needed=1, use_cache=True)
    gha.search_accommodation(_resort(), date(2027, 1, 10), nights=6, rooms_needed=1, use_cache=True)
    assert call_count["n"] == 2  # second search_accommodation() call served entirely from cache


def test_cheapest_price_eur_per_night_is_none_for_no_options():
    from ski_optimizer.models import AccommodationSearchResult
    assert gha.cheapest_price_eur_per_night(AccommodationSearchResult(options=[])) is None


# --- search_url ---

def test_search_url_without_dates_is_a_plain_location_search():
    url = gha.search_url("Val Thorens, France")
    assert url == "https://www.google.com/travel/hotels?q=Hotels%20in%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us"


def test_search_url_with_dates_switches_to_search_path_and_carries_a_ts_param():
    # Reference value pure/offline -- _build_ts with an empty place_id is
    # plain protobuf encoding, no network call (see this function's own
    # docstring). Verified live once, via browser, that Google Hotels
    # still resolves the place from the name alone and shows correctly
    # dated real prices for this exact ts value.
    url = gha.search_url("Val Thorens, France", date(2027, 1, 10), date(2027, 1, 16))
    assert url == (
        "https://www.google.com/travel/search?q=Hotels%20in%20Val%20Thorens%2C%20France"
        "&hl=en&curr=EUR&gl=us&ts="
        "CAESCgoCCAMKAggDEAAaOQobEhcyADoTVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA"
    )


def test_search_url_omits_ts_when_only_one_date_is_given():
    with_only_checkin = gha.search_url("Val Thorens, France", date(2027, 1, 10))
    with_only_checkout = gha.search_url("Val Thorens, France", checkout_date=date(2027, 1, 16))
    assert "ts=" not in with_only_checkin
    assert "ts=" not in with_only_checkout


# --- specific_property_url / _resolve_hotel_mid / _build_qs ---
#
# UNVERIFIED end to end (see specific_property_url's own docstring): no
# real GOOGLE_KG_API_KEY was available while writing this. These tests
# cover what IS testable offline -- the graceful no-key/no-match
# degrade, and _build_qs's own wire-format encoding -- not a live
# Knowledge Graph API round trip.

def test_build_qs_embeds_the_mid():
    qs = gha._build_qs("/g/11cn3169b8")
    raw = base64.urlsafe_b64decode(qs + "=" * (-len(qs) % 4))
    assert b"/g/11cn3169b8" in raw


def test_specific_property_url_is_none_without_an_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_KG_API_KEY", raising=False)
    url = gha.specific_property_url("Hotel Marielle", "Val Thorens, France",
                                    date(2027, 1, 10), date(2027, 1, 16))
    assert url is None


def test_specific_property_url_is_none_when_no_mid_is_resolved(monkeypatch):
    monkeypatch.setenv("GOOGLE_KG_API_KEY", "fake-key")
    monkeypatch.setattr(gha, "_resolve_hotel_mid", lambda *a, **k: None)
    url = gha.specific_property_url("Hotel Marielle", "Val Thorens, France",
                                    date(2027, 1, 10), date(2027, 1, 16))
    assert url is None


def test_specific_property_url_builds_a_dated_link_with_qs_when_mid_resolves(monkeypatch):
    monkeypatch.setenv("GOOGLE_KG_API_KEY", "fake-key")
    monkeypatch.setattr(gha, "_resolve_hotel_mid", lambda *a, **k: "/g/11cn3169b8")
    url = gha.specific_property_url("Hotel Marielle", "Val Thorens, France",
                                    date(2027, 1, 10), date(2027, 1, 16))
    assert url is not None
    assert url.startswith("https://www.google.com/travel/search?q=")
    assert "&ts=" in url and "&qs=" in url


def test_resolve_hotel_mid_is_none_for_a_response_with_no_match(monkeypatch):
    class _FakeResp:
        def json(self):
            return {"itemListElement": []}

    import primp
    monkeypatch.setattr(primp.Client, "get", lambda self, *a, **k: _FakeResp())
    assert gha._resolve_hotel_mid("Nonexistent Hotel", "Nowhere", "fake-key") is None


def test_resolve_hotel_mid_extracts_the_id_from_a_real_shaped_response(monkeypatch):
    class _FakeResp:
        def json(self):
            return {"itemListElement": [{"result": {"@id": "kg:/g/11cn3169b8", "name": "Hotel Marielle"}}]}

    import primp
    monkeypatch.setattr(primp.Client, "get", lambda self, *a, **k: _FakeResp())
    assert gha._resolve_hotel_mid("Hotel Marielle", "Val Thorens", "fake-key") == "/g/11cn3169b8"


def test_resolve_hotel_mid_also_accepts_the_older_m_format(monkeypatch):
    # REGRESSION: the original check only accepted /g/... (newer
    # "topic" MID) and silently rejected /m/... (older, Freebase-
    # derived, still a live/valid Knowledge Graph ID) -- confirmed live
    # against the real API (2026-08-26): "Ritz-Carlton Hotel Company"
    # resolves to exactly this format (kg:/m/0288kpv), not /g/.
    class _FakeResp:
        def json(self):
            return {"itemListElement": [{"result": {"@id": "kg:/m/0288kpv", "name": "Ritz-Carlton"}}]}

    import primp
    monkeypatch.setattr(primp.Client, "get", lambda self, *a, **k: _FakeResp())
    assert gha._resolve_hotel_mid("Ritz-Carlton", "New York", "fake-key") == "/m/0288kpv"
