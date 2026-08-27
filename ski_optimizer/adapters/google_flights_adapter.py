"""
Flight search via the `fast-flights` library (github.com/AWeirdDev/flights),
which scrapes Google Flights directly by decoding its internal protobuf
query/response format -- NOT the SerpApi-mediated version in
flight_adapter.py.

WHY THIS EXISTS ALONGSIDE flight_adapter.py, NOT INSTEAD OF IT AS A
FILE: same boundary-type contract (FlightOption, FlightSearchResult),
same public shape (search_flights / cheapest_price_eur / clear_cache),
so engine/cost_calculator.py swapping which adapter it imports is a
one-line change, not a rewrite -- see adapters/base.py and every other
adapter's own docstring on why that boundary exists. The old file is
kept, unswapped, as the fallback this project's adapter pattern was
built to make cheap.

WHY THIS PROVIDER (recorded so future-us doesn't relitigate it): no API
key, no metered quota -- SerpApi's free tier (250 calls/month) was the
binding constraint on how much of this product's core "cheapest week"
search could actually be live-priced (see api/rate_limit.py's docstring
on the daily live-pricing budget that exists specifically because of
that quota). This library needs none of that for FLIGHTS specifically.

RISK, stated as plainly as flight_adapter.py's own SerpApi warning:
this is ALSO a scraper -- of Google Flights' internal, undocumented
`GetShoppingResults` endpoint, decoded from a protobuf the library's
own README calls "dangerous" and warns may get the caller banned. Two
mitigations, same shape as flight_adapter.py's: (a) nothing from this
library escapes this module -- engine/ only ever sees FlightOption; (b)
the response cache in front of this (adapters/response_cache.py) means
a repeated identical query within its TTL costs nothing further.

CURRENCY IS TRUSTED, NOT VERIFIED PER-ENTRY: same limitation as
serpapi_hotel_adapter.py -- the library's `Flights.price` is a bare
number with no currency field attached to confirm what the `currency`
query param actually got honored as. We ask for EUR and trust it.

ONE LEG PER QUERY, UNLIKE SERPAPI: `flight_adapter.search_flights` can
search several destination airports in ONE call (SerpApi's
comma-separated arrival_id). This library's FlightQuery takes exactly
one to_airport, so a multi-airport resort (e.g. "Geneva (GVA) /
Chambery (CMF)") costs one query PER airport here -- more requests, but
each one a true single-route search rather than a provider-side merge.

ROUND-TRIP RESULTS ARE OUTBOUND-LEG CARDS, NOT FULL ITINERARIES: for a
trip="round-trip" query, get_flights() returns one card per OUTBOUND
option, each already priced at the ROUND-TRIP TOTAL (verified live,
2026-08: a one-way TLV-GVA query returned ~EUR170-235 per option; the
matching round-trip query returned ~EUR335-460 -- consistent with a
full round-trip total, not a doubled one-way misread). The RETURN leg's
own flight details are not exposed by this call shape, so
total_duration_minutes below covers only the OUTBOUND leg group's span
(first departure to last arrival), not the full round trip -- a
narrower duration figure than flight_adapter.py's SerpApi-sourced one,
which does cover the whole itinerary. total_duration_minutes isn't
consumed anywhere downstream today (checked: only stops/price/airline
are persisted, by db/fare_history.py, which isn't wired into the live
call path either), so this gap is real but currently inert.
"""
import base64
import datetime
import random
import time
import json
from typing import List, Optional

from ..models import FlightOption, FlightSearchResult
from .base import AdapterError, ProviderBlockedError
from .response_cache import get_cache
from ._wire_format import field_bytes, field_str, field_varint


def _cache_key(origin: str, destinations: List[str], outbound: datetime.date,
               ret: Optional[datetime.date], adults: int, max_connections: Optional[int],
               currency: str) -> str:
    return "|".join([
        "google-flights", origin, ",".join(sorted(destinations)), str(outbound), str(ret),
        str(adults), str(max_connections), currency,
    ])


def _to_datetime(simple, fallback_year: int) -> datetime.datetime:
    """
    Converts the library's SimpleDatetime (date=(Y,M,D) tuple that can be
    empty when Google omits a same-day date, time=(H,M) tuple) into a
    real datetime, for layover/duration arithmetic. fallback_year guards
    against a date tuple missing entirely -- shouldn't happen for a real
    result, but arithmetic on a made-up 1900 date would silently produce
    a nonsense duration rather than a loud failure.
    """
    y, m, d = (simple.date or (fallback_year, 1, 1))
    h, mi = (simple.time or (0, 0))
    return datetime.datetime(y, m, d, h, mi)


def _format_date_triplet(triplet) -> str:
    y, m, d = triplet
    return f"{y}-{m:02d}-{d:02d}"


def _extract_booking_ingredients(raw_card) -> Optional[str]:
    """
    Packs this flight card's own raw per-leg segment data (airport,
    date, marketing carrier + flight number -- NOT exposed by
    fast_flights' own parsed `Flights` dataclass, only present in the
    raw JSON payload) and its opaque per-flight selection token into a
    single compact string, stored on FlightOption.booking_token. See
    booking_url()'s own docstring for how this gets turned into a real
    deep link later, and why booking_url() -- not this function --
    does the actual protobuf encoding (kept lazy: most FlightOptions in
    a results list never get a booking link built).

    Returns None for any shape this doesn't recognize -- raw_card comes
    from an undocumented internal payload (see module docstring's risk
    note), so a shift in Google's array layout should degrade this one
    optional feature, never break the actual price/itinerary parse in
    _parse_flight_result.
    """
    try:
        token = raw_card[1][1]
        raw_legs = raw_card[0][2]
        segments = [
            (sf[3], _format_date_triplet(sf[20]), sf[6], sf[22][0], sf[22][1])
            for sf in raw_legs
        ]
        if not token or not segments:
            return None
        packed = json.dumps({"token": token, "segments": segments})
        return base64.urlsafe_b64encode(packed.encode("utf-8")).decode("ascii")
    except (IndexError, TypeError, KeyError, ValueError):
        # ValueError included per code review: a malformed date triplet
        # (e.g. missing a component) raises it during tuple unpacking in
        # _format_date_triplet, which isn't an IndexError/TypeError/
        # KeyError -- caught live, this crashed the WHOLE flight parse
        # in _parse_flight_result (no try/except wraps this call there),
        # discarding an otherwise-good price/itinerary over an optional
        # field. Contradicted this function's own "best-effort, never
        # breaks the actual parse" docstring promise.
        return None


def _parse_flight_result(flight, currency_is_eur: bool, raw_card=None) -> Optional[FlightOption]:
    """
    Converts one `fast_flights.model.Flights` result (one full,
    already-priced itinerary card -- see module docstring on what that
    covers for a round trip) into a FlightOption. Returns None rather
    than raising for a malformed entry (no legs, non-numeric price),
    matching flight_adapter.py's defensive parsing style -- one bad
    card in a page of several shouldn't blow away the whole search.

    raw_card, when given, is this SAME result's own entry in the raw
    JSON payload (`payload[3][0][i]`) fast_flights' own `Flights`
    dataclass discards after parsing -- see
    booking_url()'s docstring for why this is needed and how it's used.
    Booking-link construction is best-effort: any failure here (shape
    mismatch, missing fields) just leaves booking_token unset, never
    breaks the actual price/itinerary parse.
    """
    legs = flight.flights or []
    if not legs:
        return None
    try:
        price = float(flight.price)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    first, last = legs[0], legs[-1]
    origin = first.from_airport.code
    destination = last.to_airport.code
    if not origin or not destination:
        return None

    airlines = list(dict.fromkeys(flight.airlines or []))
    airline = airlines[0] if len(airlines) == 1 else (" + ".join(airlines[:2]) if airlines else "Unknown")

    try:
        dep = _to_datetime(first.departure, first.departure.date[0] if first.departure.date else 2000)
        arr = _to_datetime(last.arrival, last.arrival.date[0] if last.arrival.date else 2000)
        duration_minutes = max(0, int((arr - dep).total_seconds() // 60))
    except Exception:
        # Duration is informational only (see module docstring -- not
        # consumed downstream today) -- never let a date-arithmetic
        # hiccup take down an otherwise-good price.
        duration_minutes = sum(leg.duration or 0 for leg in legs)

    return FlightOption(
        price_eur=price if currency_is_eur else price,  # see module docstring's currency note
        origin_airport=origin,
        destination_airport=destination,
        airline=airline,
        total_duration_minutes=duration_minutes,
        stops=max(0, len(legs) - 1),
        is_round_trip=True,  # only ever called from a round-trip or one-way context; set per-query below
        booking_token=_extract_booking_ingredients(raw_card) if raw_card is not None else None,
    )


def _build_query(
    origin_airport: str,
    destination_airport: str,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date],
    adults: int,
    max_connections: Optional[int],
    currency: str,
):
    from fast_flights import FlightQuery, Passengers, create_query

    legs = [FlightQuery(date=outbound_date.isoformat(),
                        from_airport=origin_airport, to_airport=destination_airport)]
    if return_date is not None:
        legs.append(FlightQuery(date=return_date.isoformat(),
                                from_airport=destination_airport, to_airport=origin_airport))

    return create_query(
        flights=legs,
        seat="economy",
        trip="round-trip" if return_date is not None else "one-way",
        passengers=Passengers(adults=adults),
        language="en",
        currency=currency,
        max_stops=max_connections,
    )


def search_url(
    origin_airport: str,
    destination_airport: str,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date] = None,
    currency: str = "EUR",
) -> str:
    """
    A real, reliable Google Flights deep link for this exact route and
    dates -- built from the SAME structured query object real pricing
    searches use (create_query().url(), fast_flights' own URL builder,
    using the protobuf `tfs` param Google's own UI generates), not a
    natural-language `q=` guess.

    engine/links.py's google_flights_url() used a natural-language
    query ("Flights to X from Y on ... through ...") before this
    existed -- reported live to sometimes land on Google Flights'
    plain homepage instead of real results (natural-language parsing on
    that endpoint isn't 100% reliable). Verified this replacement
    lands directly on the correct route/dates every time it was tried.

    Single airport only (unlike search_flights' multi-airport fan-out
    for pricing) -- the structured query format takes exactly one
    to_airport per leg, so a multi-airport resort's link uses whichever
    airport the caller passes (engine/links.py picks the first one),
    trading the "or" flexibility of the old link for reliability.
    """
    query = _build_query(origin_airport, destination_airport, outbound_date, return_date,
                         adults=1, max_connections=None, currency=currency)
    return query.url()


# ---------------------------------------------------------------------------
# booking_url() -- a deep link to Google Flights' own booking page for ONE
# specific priced flight (search_url() above only reaches the search
# RESULTS page; the user still has to pick a flight themselves from
# there). No public schema exists for this (fast_flights' own .proto only
# covers the SEARCH `tfs`, not this richer booking one) -- hand
# reverse-engineered the same way google_hotels_adapter.py's `ts` was:
# captured a real booking-page URL from a live click-through, decoded the
# protobuf wire format byte by byte, and rebuilt it from data our own
# search response already carries (per-leg airport/date/marketing
# carrier+flight-number, from the raw JSON payload -- see
# _extract_booking_ingredients()'s docstring for exactly what
# fast_flights' own parsed model is missing) plus the opaque per-flight
# selection token Google embeds in every result card.
#
# VERIFIED LIVE (2026-08-26): built this from a real search response
# and navigated to the resulting booking URL -- landed on the exact
# priced flight (correct times/route/price) with real "Book with ..."
# provider options, not a fallback to the generic search page. Also
# confirmed the token survives being reused ~12 minutes later from a
# FRESH tab (no cookie continuity with the original request) -- not
# proof it's valid indefinitely, but strong evidence it isn't a
# single-request nonce. UNVERIFIED: validity beyond that window (hours
# or days later, the realistic case for a link handed to a user who
# searched earlier). If it ever expires, this degrades to returning
# None -- see the caller in engine/cost_calculator.py, which falls back
# to the plain search_url() link, never a broken URL.
#
# ROUND TRIP NEEDS A SECOND FETCH: a round-trip search result (see
# module docstring) only carries the OUTBOUND leg's detail -- the
# return leg isn't in that response at all, matching Google's own
# two-step picker UI (pick outbound, THEN see return options). Verified
# live: a "hybrid" tfs (outbound direction fully detailed + return
# direction still just date/route) paired with the outbound selection's
# tfu lands on Google's own "Choose return" page, whose OWN script.ds:1
# blob has the exact same shape as a normal search response -- so the
# CHEAPEST return option is picked from that second fetch the same way
# the outbound one was, and the two directions + the return leg's own
# token are combined into the final booking tfs/tfu. One extra live
# request, only paid when a round-trip booking link is actually
# requested (never during the main pricing search).
# ---------------------------------------------------------------------------

def _segment_bytes(from_airport: str, dep_date: str, to_airport: str, carrier: str, flight_num: str) -> bytes:
    return (
        field_str(1, from_airport) + field_str(2, dep_date) + field_str(3, to_airport)
        + field_str(5, carrier) + field_str(6, flight_num)
    )


def _detailed_direction_bytes(date_str: str, segments: List[bytes], overall_from: str, overall_to: str) -> bytes:
    body = field_str(2, date_str)
    for seg in segments:
        body += field_bytes(4, seg)
    body += field_bytes(13, field_varint(1, 1) + field_str(2, overall_from))
    body += field_bytes(14, field_varint(1, 1) + field_str(2, overall_to))
    return body


def _simple_direction_bytes(date_str: str, from_airport: str, to_airport: str) -> bytes:
    return field_str(2, date_str) + field_bytes(13, field_str(2, from_airport)) + field_bytes(14, field_str(2, to_airport))


def _build_booking_tfs(directions: List[bytes], trip_enum: int) -> str:
    body = field_varint(1, 28) + field_varint(2, 2)
    for d in directions:
        body += field_bytes(3, d)
    body += field_varint(8, 1)                    # passengers=[ADULT] (repeated enum, plain varint)
    body += field_varint(9, 1)                    # seat=ECONOMY
    body += field_varint(14, 1)
    body += field_bytes(16, field_varint(1, (1 << 64) - 1))
    body += field_varint(19, trip_enum)           # Trip: ROUND_TRIP=1, ONE_WAY=2
    return base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")


def _build_tfu(token: str) -> str:
    wrapper = field_str(1, token) + field_bytes(2, b"\x08\x00") + field_bytes(4, field_str(1, "0"))
    return base64.urlsafe_b64encode(wrapper).decode("ascii").rstrip("=")


def _unpack_booking_token(booking_token: str):
    packed = json.loads(base64.urlsafe_b64decode(booking_token.encode("ascii")).decode("utf-8"))
    return packed["token"], packed["segments"]


def _direction_from_segments(segments) -> bytes:
    seg_bytes = [_segment_bytes(*seg) for seg in segments]
    overall_from, overall_to = segments[0][0], segments[-1][2]
    date_str = segments[0][1]
    return _detailed_direction_bytes(date_str, seg_bytes, overall_from, overall_to)


def _fetch_return_options(hybrid_tfs: str, tfu: str, currency: str):
    """One extra live request -- see booking_url()'s own docstring on
    when and why this happens. Same client config fast_flights' own
    fetcher uses internally; parses the response the same way
    _fetch_and_parse() does (this page embeds its results in the exact
    same script.ds:1 shape a normal search response does -- verified
    live)."""
    import primp
    from fast_flights import parser as ff_parser

    client = primp.Client(impersonate="chrome_145", impersonate_os="macos", referer=True, cookie_store=True)
    url = "https://www.google.com/travel/flights/search"
    resp = client.get(url, params={"tfs": hybrid_tfs, "tfu": tfu, "hl": "en", "curr": currency})

    from selectolax.lexbor import LexborHTMLParser
    page = LexborHTMLParser(resp.text)
    script = page.css_first(r"script.ds\:1")
    if script is None:
        return [], []
    js = script.text()
    parsed = ff_parser.parse_js(js)
    data_str = js.split("data:", 1)[1].rsplit(",", 1)[0]
    payload = json.loads(data_str)
    return parsed, (payload[3][0] or [])


def booking_url(
    flight_option: FlightOption,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date] = None,
    currency: str = "EUR",
) -> Optional[str]:
    """
    A deep link straight to Google Flights' booking page for THIS
    specific priced flight -- see this section's module-level comment
    for the full mechanism and what's verified vs. unverified.

    Returns None (never raises) when flight_option carries no usable
    booking_token (older/mocked FlightOption, or booking-ingredient
    extraction failed at parse time), or when anything in building or
    -- for round trip -- fetching the return leg goes wrong. Every
    failure mode here is "no booking link", which the caller degrades
    from by falling back to search_url() -- never a broken URL shown
    to a user.
    """
    if not flight_option.booking_token:
        return None
    try:
        outbound_token, outbound_segments = _unpack_booking_token(flight_option.booking_token)
        outbound_direction = _direction_from_segments(outbound_segments)

        if return_date is None:
            tfs = _build_booking_tfs([outbound_direction], trip_enum=2)  # ONE_WAY
            tfu = _build_tfu(outbound_token)
            return f"https://www.google.com/travel/flights/booking?tfs={tfs}&tfu={tfu}&hl=en&curr={currency}"

        # Round trip: fetch the "choose return" step using the outbound
        # selection, pick its cheapest option, then build the final,
        # fully-detailed two-direction booking link.
        placeholder_return = _simple_direction_bytes(
            return_date.isoformat(), flight_option.destination_airport, flight_option.origin_airport,
        )
        hybrid_tfs = _build_booking_tfs([outbound_direction, placeholder_return], trip_enum=1)  # ROUND_TRIP
        outbound_tfu = _build_tfu(outbound_token)

        return_results, return_raw_cards = _fetch_return_options(hybrid_tfs, outbound_tfu, currency)
        if not return_results or not return_raw_cards or return_raw_cards[0] is None:
            return None
        return_ingredients = _extract_booking_ingredients(return_raw_cards[0])
        if return_ingredients is None:
            return None
        return_token, return_segments = _unpack_booking_token(return_ingredients)
        return_direction = _direction_from_segments(return_segments)

        tfs = _build_booking_tfs([outbound_direction, return_direction], trip_enum=1)
        tfu = _build_tfu(return_token)
        return f"https://www.google.com/travel/flights/booking?tfs={tfs}&tfu={tfu}&hl=en&curr={currency}"
    except Exception:
        # See docstring: any failure here degrades to "no booking link,"
        # never a broken one.
        return None


# HOW A BLOCK IS DETECTED -- and how it is NOT.
#
# The first version of this matched strings like "recaptcha"/"captcha"
# in the HTML. That was WRONG, and it caused a real production
# regression: Google embeds reCAPTCHA scaffolding in NORMAL Google
# Flights pages too, so the check fired on perfectly good responses and
# rejected them. Live flight pricing went to 0/12 in production and the
# UI reported "blocked" -- caused entirely by the detector, not by
# Google. Verified by disabling it and immediately getting 7 real
# options back at EUR283.
#
# The reliable signature is STRUCTURAL, not textual: on a real results
# page the embedded payload carries a flight array; on a challenge or
# no-data page that slot is null. That is exactly the condition that
# used to blow up several frames down inside fast_flights with
# "'NoneType' object is not subscriptable". So we check the thing that
# actually differs instead of guessing from page text.
#
# HONEST LIMIT: a null payload means "no flight data came back". It does
# NOT by itself prove a CAPTCHA -- a genuinely empty route looks the
# same from here. The user-facing message says prices could not be
# fetched, which is true either way, rather than asserting a specific
# cause we cannot actually distinguish.


def _fetch_and_parse(query):
    """
    Same end result as fast_flights' own get_flights(query) (a
    ResultList[Flights]), plus the raw JSON cards get_flights() throws
    away after parsing -- needed for booking_url() (see
    _extract_booking_ingredients()'s docstring on why the raw payload
    carries data the library's own dataclass doesn't). Duplicates only
    the few lines of get_flights()'s own data-extraction (find
    script.ds:1, split off the "data:" prefix, json.loads) so both the
    parsed and raw views come from parsing the SAME response ONCE, not
    two separate requests.

    Returns (ResultList[Flights], raw_cards) -- raw_cards is
    index-aligned with the parsed list (both come from the same
    payload[3][0] iteration), or ([], []) for the "no flights found"
    case get_flights() raises FlightsNotFound for.
    """
    from fast_flights import parser as ff_parser
    from fast_flights.exceptions import FlightsNotFound
    from fast_flights.fetcher import fetch_flights_html
    from selectolax.lexbor import LexborHTMLParser

    html = fetch_flights_html(query)
    page = LexborHTMLParser(html)
    script = page.css_first(r"script.ds\:1")
    if script is None:
        return [], []
    js = script.text()

    try:
        parsed = ff_parser.parse_js(js)
    except FlightsNotFound:
        return [], []
    except TypeError as exc:
        # The structural signature described above: fast_flights indexes
        # into the payload's flight slot, which is null on a challenge or
        # no-data response. Named rather than left as an opaque
        # TypeError, so callers can degrade visibly instead of silently.
        raise ProviderBlockedError(
            "Google Flights returned a page with no flight data "
            f"(likely an anti-bot challenge or an empty route): {exc}"
        ) from exc

    try:
        data_str = js.split("data:", 1)[1].rsplit(",", 1)[0]
        payload = json.loads(data_str)
        raw_cards = payload[3][0] or []
    except (IndexError, ValueError, TypeError):
        # Booking-link ingredients are best-effort (see
        # _extract_booking_ingredients()) -- a raw-payload shape
        # surprise here shouldn't sink the already-parsed results.
        raw_cards = [None] * len(parsed)

    return parsed, raw_cards


# This is a SCRAPER, and this module's own docstring warns it can be
# rate-limited or transiently blocked. Until 2026-08-27 a single failed
# fetch meant that route simply had no live price -- the caller kept a
# static estimate and the user saw "EST." That is a large part of why so
# many rows were estimated even with live pricing switched on: not that
# no price existed, but that one flaky request was never retried.
#
# Deliberately small and jittered. The failure mode being retried is a
# transient block, and retrying hard is how a transient block becomes a
# durable one -- so: one extra attempt, a short randomised pause, and
# then give up honestly rather than hammering.
_FETCH_ATTEMPTS = 2
_RETRY_BASE_DELAY_S = 0.6


def _search_one_airport_with_retry(*args, **kwargs) -> List[FlightOption]:
    """_search_one_airport, retried once on a transient failure."""
    last_exc = None
    for attempt in range(_FETCH_ATTEMPTS):
        try:
            return _search_one_airport(*args, **kwargs)
        except ProviderBlockedError:
            # A CAPTCHA will not pass on a second identical request --
            # retrying only adds load to a provider that has already
            # decided we look automated. Fail fast and let the caller
            # report it honestly.
            raise
        except Exception as exc:  # noqa: BLE001 -- retried, then re-raised
            last_exc = exc
            if attempt < _FETCH_ATTEMPTS - 1:
                time.sleep(_RETRY_BASE_DELAY_S * (1 + random.random()))
    raise last_exc


def _search_one_airport(
    origin_airport: str,
    destination_airport: str,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date],
    adults: int,
    max_connections: Optional[int],
    currency: str,
) -> List[FlightOption]:
    query = _build_query(origin_airport, destination_airport, outbound_date, return_date,
                         adults, max_connections, currency)

    raw_results, raw_cards = _fetch_and_parse(query)

    currency_is_eur = currency.upper() == "EUR"
    options = []
    for f, raw_card in zip(raw_results, raw_cards):
        parsed = _parse_flight_result(f, currency_is_eur, raw_card)
        if parsed is not None:
            parsed.is_round_trip = return_date is not None
            options.append(parsed)
    return options


def search_flights(
    origin_airport: str,
    destination_airports,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date] = None,
    adults: int = 1,
    max_connections: Optional[int] = 1,
    currency: str = "EUR",
    use_cache: bool = True,
) -> FlightSearchResult:
    """
    Same public contract as flight_adapter.search_flights (see that
    function's own docstring for the shared parts of this contract);
    differences are covered in this module's docstring. Raises
    AdapterError only when EVERY destination airport failed -- a resort
    with 2 candidate airports where only 1 has results should still
    return that 1, not error out (matching flight_adapter's "degrade
    per-missing-quote, not per-request" philosophy from
    cost_calculator.py's module docstring).
    """
    if isinstance(destination_airports, str):
        destination_airports = [destination_airports]
    destination_airports = [d.strip().upper() for d in destination_airports if d and d.strip()]
    if not destination_airports:
        raise AdapterError("No destination airports supplied")
    origin_airport = origin_airport.strip().upper()

    if return_date is not None and return_date <= outbound_date:
        raise AdapterError(
            f"return_date {return_date} must be after outbound_date {outbound_date}"
        )

    key = _cache_key(origin_airport, destination_airports, outbound_date,
                     return_date, adults, max_connections, currency)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return FlightSearchResult(options=cached.options, insight=cached.insight,
                                      from_cache=True)

    all_options: List[FlightOption] = []
    errors: List[str] = []
    blocked = False
    for dest in destination_airports:
        try:
            all_options.extend(_search_one_airport_with_retry(
                origin_airport, dest, outbound_date, return_date, adults, max_connections, currency,
            ))
        except ProviderBlockedError as exc:
            blocked = True
            errors.append(f"{dest}: {exc}")
        except Exception as exc:  # noqa: BLE001 -- see docstring: one airport's failure shouldn't sink the rest
            errors.append(f"{dest}: {exc}")

    if not all_options and errors:
        joined = "; ".join(errors)
        if blocked:
            # Keep the block distinguishable all the way out. Flattening
            # it into a generic AdapterError here is what made a scraping
            # block look identical to "this route has no flights", which
            # is the whole reason blocked lookups silently became "EST."
            raise ProviderBlockedError(
                f"Google Flights is blocking automated requests: {joined}"
            )
        raise AdapterError(f"Google Flights search failed for every airport: {joined}")

    result = FlightSearchResult(options=all_options, insight=None)
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur(result: FlightSearchResult) -> Optional[float]:
    """Convenience for the cost calculator: lowest price, or None if no options."""
    if not result.options:
        return None
    return min(o.price_eur for o in result.options)


def clear_cache() -> None:
    """Test/ops helper, matching flight_adapter.clear_cache."""
    get_cache().clear()
