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


# A result card shaped the way fast_flights' parser actually reads one.
# The filter mirrors every index that parser accesses, so test cards must
# be realistic or they are (correctly) treated as malformed.
_VALID_LEG = [0, 1, 2, "TLV", "Ben Gurion", "Geneva", "GVA", 7, [8, 30],
              9, [10, 45], 300, 12, 13, 14, 15, 16, "A320", 18, 19,
              [2027, 1, 10], [2027, 1, 10]]


def _valid_card(price_cents=42000):
    return [[0, ["LX"], [_VALID_LEG]], [[None, price_cents]]]

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


# --- booking_url: protobuf encoding, regression-tested against a REAL
# captured booking-page URL (given by the user, not generated by this
# codebase -- the strongest possible ground truth) ---

def test_build_booking_tfs_matches_a_real_captured_round_trip_example_byte_for_byte():
    # A real booking-page URL given by the user (not generated by this
    # codebase) for TLV<->GVA via Zurich on Swiss (LX), Dec 11-18 2026.
    # This regression test is the one that caught a real bug: field 8
    # (passengers) was originally wrapped in a nested {1: n} message,
    # but Google's own encoding is a plain repeated varint -- this
    # exact captured value is what caught the mismatch.
    captured = (
        "CBwQAhphEgoyMDI2LTEyLTExIh8KA1RMVhIKMjAyNi0xMi0xMRoDWlJIKgJMWDID"
        "MjUzIiAKA1pSSBIKMjAyNi0xMi0xMRoDR1ZBKgJMWDIEMjgxOGoHCAESA1RMVnIH"
        "CAESA0dWQRphEgoyMDI2LTEyLTE4IiAKA0dWQRIKMjAyNi0xMi0xOBoDWlJIKgJM"
        "WDIEMjgxOSIfCgNaUkgSCjIwMjYtMTItMTgaA1RMVioCTFgyAzI1NmoHCAESA0dW"
        "QXIHCAESA1RMVkABSAFwAYIBCwj___________8BmAEB"
    )
    outbound = gfa._detailed_direction_bytes(
        "2026-12-11",
        [
            gfa._segment_bytes("TLV", "2026-12-11", "ZRH", "LX", "253"),
            gfa._segment_bytes("ZRH", "2026-12-11", "GVA", "LX", "2818"),
        ],
        overall_from="TLV", overall_to="GVA",
    )
    inbound = gfa._detailed_direction_bytes(
        "2026-12-18",
        [
            gfa._segment_bytes("GVA", "2026-12-18", "ZRH", "LX", "2819"),
            gfa._segment_bytes("ZRH", "2026-12-18", "TLV", "LX", "256"),
        ],
        overall_from="GVA", overall_to="TLV",
    )
    mine = gfa._build_booking_tfs([outbound, inbound], trip_enum=1)  # ROUND_TRIP
    assert mine == captured


def test_build_booking_tfs_one_way_matches_a_live_verified_example_byte_for_byte():
    # Verified live (2026-08-26): built via booking_url() from a real
    # search response and confirmed navigating to it landed on this
    # exact flight's booking page (Aegean/SWISS, TLV-ATH-GVA).
    captured = (
        "CBwQAhpgEgoyMDI2LTEyLTExIh8KA1RMVhIKMjAyNi0xMi0xMRoDQVRIKgJBMzID"
        "OTI5Ih8KA0FUSBIKMjAyNi0xMi0xMRoDR1ZBKgJBMzIDODU2agcIARIDVExWcgcI"
        "ARIDR1ZBQAFIAXABggELCP___________wGYAQI"
    )
    outbound = gfa._detailed_direction_bytes(
        "2026-12-11",
        [
            gfa._segment_bytes("TLV", "2026-12-11", "ATH", "A3", "929"),
            gfa._segment_bytes("ATH", "2026-12-11", "GVA", "A3", "856"),
        ],
        overall_from="TLV", overall_to="GVA",
    )
    mine = gfa._build_booking_tfs([outbound], trip_enum=2)  # ONE_WAY
    assert mine == captured


def test_build_tfu_round_trips_the_raw_token():
    tfu = gfa._build_tfu("some-opaque-token")
    raw = __import__("base64").urlsafe_b64decode(tfu + "=" * (-len(tfu) % 4))
    assert b"some-opaque-token" in raw


# --- _extract_booking_ingredients / booking_token round trip ---

def _raw_card(price=129, token="tok-abc", legs=None, total_duration=None):
    # Matches the REAL raw payload shape: raw_card[0][2] is the leg
    # list (raw_card[0] carries other flight-level fields at indices 0
    # and 1 that _extract_booking_ingredients doesn't read), and each
    # leg's own index 3/6/20/22 are from_airport/to_airport/departure-
    # date/[carrier, flight_num, ..., airline_name] -- see
    # _extract_booking_ingredients's docstring and this module's own
    # docstring for how these indices were found.
    #
    # raw_card[0][9] is Google's own total journey duration in minutes
    # (see _total_duration_from_card). Padded out with None so the
    # index lands where it really does in the live payload.
    legs = legs or [
        [None, None, None, "TLV", "Ben Gurion", "Athens Intl", "ATH", None, [5, 20], None, [7, 30],
         130, None, 2, "28 in", None, 1, "Airbus A321neo", None, 0, [2026, 12, 11], [2026, 12, 11],
         ["A3", "929", None, "Aegean"]],
    ]
    flight_level = [None, None, legs, None, None, None, None, None, None, total_duration]
    return [flight_level, [[None, price], token]]


def test_total_duration_comes_from_the_payload_not_local_clock_arithmetic():
    # REGRESSION, found live 2026-08-28 against a real TLV->GVA card:
    # Google's own booking page said "7 hr 20 min" where we displayed
    # "6h20". Both clocks are LOCAL, and in January Tel Aviv is UTC+2
    # while Geneva is UTC+1, so subtracting one from the other loses
    # exactly the offset. Every westbound duration we showed was
    # understated, every eastbound one overstated.
    #
    # The payload carries the real answer at [0][9] -- 440 minutes for
    # this itinerary, which also equals 295 + 75 flying + 70 layover.
    legs = [
        _leg("TLV", "BRU", dep_time=(16, 10), arr_time=(20, 5), duration=295),
        _leg("BRU", "GVA", dep_time=(21, 15), arr_time=(22, 30), duration=75),
    ]
    opt = gfa._parse_flight_result(
        _flights_result(legs=legs), currency_is_eur=True,
        raw_card=_raw_card(legs=[], total_duration=440),
    )
    # Naive clock subtraction gives 16:10 -> 22:30 = 380. The truth is 440.
    assert opt.total_duration_minutes == 440


def test_duration_falls_back_to_clock_math_when_the_payload_omits_it():
    # The payload field is the authority, but it must never be the
    # single point of failure: an older/mocked card without it still
    # has to produce a usable duration rather than zero or a crash.
    legs = [
        _leg("TLV", "FRA", dep_time=(7, 55), arr_time=(11, 35), duration=280),
        _leg("FRA", "GVA", dep_time=(21, 10), arr_time=(22, 25), duration=75),
    ]
    opt = gfa._parse_flight_result(
        _flights_result(legs=legs), currency_is_eur=True,
        raw_card=_raw_card(legs=[], total_duration=None),
    )
    assert opt.total_duration_minutes == 870  # 07:55 -> 22:25


def test_nonsense_payload_duration_is_ignored_rather_than_displayed():
    # "Never invent a number" cuts both ways: a zero, a negative, or a
    # non-integer in that slot is not a duration, and must fall back
    # rather than be shown as "0h".
    for junk in (0, -30, "440", True, None):
        opt = gfa._parse_flight_result(
            _flights_result(), currency_is_eur=True,
            raw_card=_raw_card(legs=[], total_duration=junk),
        )
        assert opt.total_duration_minutes == 210, f"{junk!r} should not be trusted"


def test_extract_booking_ingredients_packs_token_and_segments():
    packed = gfa._extract_booking_ingredients(_raw_card())
    assert packed is not None
    token, segments = gfa._unpack_booking_token(packed)
    assert token == "tok-abc"
    assert segments == [["TLV", "2026-12-11", "ATH", "A3", "929"]]


def test_extract_booking_ingredients_is_none_for_malformed_input():
    assert gfa._extract_booking_ingredients([None, None]) is None
    assert gfa._extract_booking_ingredients([[None, []], [[None, 1], "tok"]]) is None


# --- booking_url orchestration ---

def _flight_option_with_booking_token(**overrides):
    from ski_optimizer.models import FlightOption

    kw = dict(price_eur=129.0, origin_airport="TLV", destination_airport="GVA", airline="Aegean",
              total_duration_minutes=780, stops=1,
              booking_token=gfa._extract_booking_ingredients(_raw_card()))
    kw.update(overrides)
    return FlightOption(**kw)


def test_booking_url_is_none_without_a_booking_token():
    option = _flight_option_with_booking_token(booking_token=None)
    assert gfa.booking_url(option, date(2026, 12, 11)) is None


def test_booking_url_one_way_builds_a_booking_link_without_any_extra_fetch(monkeypatch):
    def _unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("one-way booking_url must not fetch anything extra")

    monkeypatch.setattr(gfa, "_fetch_return_options", _unexpected_fetch)
    option = _flight_option_with_booking_token()
    url = gfa.booking_url(option, date(2026, 12, 11))
    assert url is not None
    assert url.startswith("https://www.google.com/travel/flights/booking?tfs=")
    assert "&tfu=" in url


def test_booking_url_round_trip_uses_the_cheapest_return_option(monkeypatch):
    return_card = _raw_card(price=299, token="return-tok", legs=[
        [None, None, None, "GVA", "Geneva", "Zurich", "ZRH", None, [20, 15], None, [21, 30],
         75, None, 1, "28 in", None, 1, "Airbus A320", None, 0, [2026, 12, 18], [2026, 12, 18],
         ["LX", "2819", None, "SWISS"]],
    ])

    def fake_fetch_return_options(hybrid_tfs, tfu, currency):
        return [object()], [return_card]

    monkeypatch.setattr(gfa, "_fetch_return_options", fake_fetch_return_options)
    option = _flight_option_with_booking_token()
    url = gfa.booking_url(option, date(2026, 12, 11), date(2026, 12, 18))
    assert url is not None
    assert url.startswith("https://www.google.com/travel/flights/booking?tfs=")
    # The final tfu must reflect the RETURN leg's own token (the last
    # selection made), not the outbound one -- see booking_url()'s
    # docstring on why.
    decoded_tfu = __import__("base64").urlsafe_b64decode(
        url.split("&tfu=")[1].split("&")[0] + "==")
    assert b"return-tok" in decoded_tfu


def test_booking_url_round_trip_is_none_when_the_return_fetch_finds_nothing(monkeypatch):
    monkeypatch.setattr(gfa, "_fetch_return_options", lambda *a, **k: ([], []))
    option = _flight_option_with_booking_token()
    assert gfa.booking_url(option, date(2026, 12, 11), date(2026, 12, 18)) is None


def test_booking_url_degrades_to_none_on_any_unexpected_failure(monkeypatch):
    def _raises(*_args, **_kwargs):
        raise RuntimeError("network blew up")

    monkeypatch.setattr(gfa, "_fetch_return_options", _raises)
    option = _flight_option_with_booking_token()
    assert gfa.booking_url(option, date(2026, 12, 11), date(2026, 12, 18)) is None


# --- transient-failure retry (added 2026-08-27) ---

def test_a_transient_fetch_failure_is_retried_and_can_succeed(monkeypatch):
    # WHY THIS MATTERS: this is a scraper that can be transiently
    # blocked, and before the retry existed a single flaky request meant
    # that route had no live price at all -- the caller silently kept a
    # static estimate and the user saw "EST." That was a large part of
    # why so many rows were estimated even with live pricing on.
    from ski_optimizer.models import FlightOption

    calls = {"n": 0}

    def flaky(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transiently blocked")
        return [FlightOption(price_eur=250.0, origin_airport="TLV",
                             destination_airport="GVA", airline="Test Air",
                             total_duration_minutes=200, stops=0)]

    monkeypatch.setattr(gfa, "_search_one_airport", flaky)
    result = gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17),
                                use_cache=False)
    assert calls["n"] == 2, "the first failure should have been retried"
    assert result.options and result.options[0].price_eur == 250.0


def test_retries_are_bounded_and_still_fail_honestly(monkeypatch):
    # Retrying hard is how a transient block becomes a durable one, so
    # the retry must give up rather than hammer.
    calls = {"n": 0}

    def always_fails(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("blocked")

    monkeypatch.setattr(gfa, "_search_one_airport", always_fails)
    with pytest.raises(AdapterError):
        gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17),
                           use_cache=False)
    assert calls["n"] == gfa._FETCH_ATTEMPTS, (
        f"expected exactly {gfa._FETCH_ATTEMPTS} attempts, got {calls['n']}"
    )


# --- no-service vs. genuine block ---

def test_a_null_flight_payload_means_no_service_not_a_block(monkeypatch):
    """
    Corrected twice; the measurements are recorded so this isn't
    re-litigated a third time.

    A null flight payload makes fast_flights raise "'NoneType' object is
    not subscriptable", and an earlier version reported that as an
    anti-bot block. It isn't: measured against real requests, GNB and
    LJU return a null payload in the SAME batch, at the same instant,
    that GVA and MXP return real prices. An IP-level block cannot be
    per-route -- those airports simply have no TLV service on that date.

    Reporting it as a block put a "live pricing blocked" banner in front
    of users whenever one small seasonal airport had no flights.
    """
    import fast_flights.fetcher as ff_fetcher
    import fast_flights.parser as ff_parser

    monkeypatch.setattr(ff_fetcher, "fetch_flights_html",
                        lambda *a, **k: '<html><script class="ds:1">data:[[],[],[],null],</script></html>')
    monkeypatch.setattr(ff_parser, "parse_js",
                        lambda _js: (_ for _ in ()).throw(TypeError("'NoneType' object is not subscriptable")))

    result = gfa.search_flights("TLV", "GNB", date(2027, 1, 10), date(2027, 1, 17),
                                use_cache=False)
    assert result.options == [], "an empty route should be an empty result, not an error"


def test_the_upstream_parser_indexerror_does_not_kill_the_route(monkeypatch):
    # Upstream defect in fast_flights 3.1.0 (parser.py: price =
    # k[1][0][1]) -- a result card with no price raises IndexError and
    # takes the whole route's results with it. We can't fix their
    # parser, but it must not surface as a hard error.
    import fast_flights.fetcher as ff_fetcher
    import fast_flights.parser as ff_parser

    monkeypatch.setattr(
        ff_fetcher, "fetch_flights_html",
        lambda *a, **k: '<html><script class="ds:1">data:[[],[],[],[[[[0,["LX"],[[0,1,2,"TLV","BG","GVA","GVA",7,[8,30],9,[10,45],300,12,13,14,15,16,"A320",18,19,[2027,1,10],[2027,1,10]]]],[[null,42000]]]]],</script></html>')
    monkeypatch.setattr(ff_parser, "parse_js",
                        lambda _js: (_ for _ in ()).throw(IndexError("list index out of range")))

    result = gfa.search_flights("TLV", "CMF", date(2027, 1, 10), date(2027, 1, 17),
                                use_cache=False)
    assert result.options == []


def test_only_the_unusual_traffic_interstitial_counts_as_a_block(monkeypatch):
    # The one signal that actually discriminates: it appeared in zero of
    # several hundred test responses, and never on a page carrying
    # flight data.
    import fast_flights.fetcher as ff_fetcher

    from ski_optimizer.adapters.base import ProviderBlockedError

    monkeypatch.setattr(
        ff_fetcher, "fetch_flights_html",
        lambda *a, **k: "<html><body>Our systems have detected unusual traffic</body></html>")
    with pytest.raises(ProviderBlockedError):
        gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17), use_cache=False)


def test_a_normal_page_containing_recaptcha_markup_is_NOT_treated_as_blocked(monkeypatch):
    """
    REGRESSION, and a production outage I caused.

    The first detector matched "recaptcha"/"captcha" in the HTML. Google
    embeds reCAPTCHA scaffolding in NORMAL Google Flights pages, so it
    fired on good responses: live flight pricing dropped to 0/12 in
    production and the UI announced "blocked" -- all self-inflicted.
    Proven by disabling it and getting 7 real options back at EUR283
    from the very same request.
    """
    import fast_flights.fetcher as ff_fetcher
    import fast_flights.parser as ff_parser

    from ski_optimizer.models import FlightOption

    monkeypatch.setattr(
        ff_fetcher, "fetch_flights_html",
        lambda *a, **k: ('<html><script src="https://www.google.com/recaptcha/api.js"></script>'
                         '<script class="ds:1">data:[[],[],[],[[[[0,["LX"],[[0,1,2,"TLV","BG","GVA","GVA",7,[8,30],9,[10,45],300,12,13,14,15,16,"A320",18,19,[2027,1,10],[2027,1,10]]]],[[null,42000]]]]],</script></html>'))
    monkeypatch.setattr(gfa, "_parse_flight_result",
                        lambda *a, **k: FlightOption(price_eur=283.0, origin_airport="TLV",
                                                     destination_airport="GVA", airline="Test Air",
                                                     total_duration_minutes=300, stops=0))
    monkeypatch.setattr(ff_parser, "parse_js", lambda _js: [object()])

    result = gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17),
                                use_cache=False)
    assert result.options, "a normal page mentioning recaptcha must not be treated as a block"
    assert result.options[0].price_eur == 283.0


def test_a_block_is_not_retried(monkeypatch):
    from ski_optimizer.adapters.base import ProviderBlockedError

    calls = {"n": 0}

    def blocked(*_a, **_k):
        calls["n"] += 1
        raise ProviderBlockedError("unusual traffic")

    monkeypatch.setattr(gfa, "_search_one_airport", blocked)
    with pytest.raises(ProviderBlockedError):
        gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17), use_cache=False)
    assert calls["n"] == 1, "a block must fail fast, not retry"


def test_one_priceless_card_does_not_destroy_a_whole_route():
    """
    UPSTREAM DEFECT (fast_flights 3.1.0, parser.py):

        for k in payload[3][0]:
            price = k[1][0][1]        # unguarded

    A card whose price slot is empty raises IndexError, and since the
    loop has no per-card protection, EVERY flight on that route is lost
    -- including the priced ones. This was the single biggest remaining
    cause of estimated flight prices in production, logged repeatedly as
    "route skipped" while other routes in the same request succeeded.
    After filtering, TLV->INN, ->SOF and ->SZG all returned real prices
    again (EUR391 / EUR200 / EUR413).
    """
    import json

    good = _valid_card()                        # a normal, priced card
    priceless = [[0, ["LX"], [_VALID_LEG]], []]  # k[1][0][1] raises IndexError
    payload = [None, None, None, [[good, priceless]], None, None, None, None]
    js = f"AF_init(data:{json.dumps(payload)}, sideChannel: {{}})"

    cleaned = gfa._drop_priceless_cards(js)
    kept = json.loads(cleaned.split("data:", 1)[1].rsplit(",", 1)[0])[3][0]

    assert len(kept) == 1, "the priceless card should have been dropped"
    assert kept[0] == good, "the priced card must survive untouched"


def test_the_card_filter_leaves_a_healthy_payload_byte_identical():
    # Re-serializing when there's nothing to fix risks changing a payload
    # that already worked, so the healthy path returns the input as-is.
    import json

    good = _valid_card()
    payload = [None, None, None, [[good, good]], None, None, None, None]
    js = f"AF_init(data:{json.dumps(payload)}, sideChannel: {{}})"
    assert gfa._drop_priceless_cards(js) is js


def test_the_card_filter_never_breaks_a_payload_it_cannot_understand():
    # A parser worry must never be the reason a working route disappears.
    for weird in ("not json at all", "data:{{{,", "", "AF_init(data:null,x)"):
        assert gfa._drop_priceless_cards(weird) == weird


def test_the_card_filter_is_actually_wired_into_the_fetch_path(monkeypatch):
    # Testing _drop_priceless_cards directly proves the function works,
    # not that anything calls it -- removing the call left those tests
    # green. This drives a payload whose ONLY bad card would crash the
    # real upstream parser, through the real fetch path.
    import json

    import fast_flights.fetcher as ff_fetcher
    import fast_flights.parser as ff_parser

    good = _valid_card()
    priceless = [[0, ["LX"], [_VALID_LEG]], []]
    payload = [None, None, None, [[good, priceless]], None, None, None, None]
    monkeypatch.setattr(
        ff_fetcher, "fetch_flights_html",
        lambda *a, **k: f'<html><script class="ds:1">AF_init(data:{json.dumps(payload)}, x)</script></html>')

    seen = {}

    def capture(js):
        seen["cards"] = json.loads(js.split("data:", 1)[1].rsplit(",", 1)[0])[3][0]
        return []

    monkeypatch.setattr(ff_parser, "parse_js", capture)
    gfa.search_flights("TLV", "GVA", date(2027, 1, 10), date(2027, 1, 17), use_cache=False)

    assert seen["cards"] == [good], (
        "the parser should have received only the priced card -- the filter isn't wired in"
    )


def test_a_card_with_a_malformed_leg_is_also_dropped():
    # The first version of the filter only guarded the PRICE access, and
    # production kept logging "route skipped" afterwards: the same
    # upstream loop reads leg[3], [4], [5], [6], [8], [10], [11], [17],
    # [20] and [21] with no guards either, so a short leg list is just as
    # fatal as a missing price. After mirroring every access, 7 of 7 test
    # routes returned real prices (INN EUR357, SZG EUR414, SOF EUR208,
    # GVA EUR249, BGY EUR836, MXP EUR123, BCN EUR249).
    import json

    short_leg = [0, 1, 2, "TLV"]                      # blows up at leg[4]

    good = _valid_card()
    malformed = [[0, ["LX"], [short_leg]], [[None, 42000]]]   # price is fine, leg is not

    assert gfa._card_is_parseable(good) is True
    assert gfa._card_is_parseable(malformed) is False

    payload = [None, None, None, [[good, malformed]], None, None, None, None]
    js = f"AF_init(data:{json.dumps(payload)}, x)"
    kept = json.loads(gfa._drop_priceless_cards(js).split("data:", 1)[1].rsplit(",", 1)[0])[3][0]
    assert kept == [good]
