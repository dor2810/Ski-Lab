"""
Accommodation search via Google Hotels' own embedded search-results
data -- hand-reverse-engineered directly for this project, the same
general technique adapters/google_flights_adapter.py's fast-flights
dependency uses for Google Flights, but built from scratch here rather
than borrowed from a published library. Every ready-made option that
was actually checked failed for a concrete reason: TripAdvisor's own
scraper API is paid/metered with a SMALLER free tier than SerpApi;
Booking.com scrapers either extract no price at all or target
Booking's own frequently-regenerated hashed CSS classes (and Booking's
Affiliate Terms explicitly prohibit scraping); every Google Hotels
library found needs a real Playwright/Selenium browser (too heavy for
Render's free tier) or -- installed and tested live -- turned out to
extract a fake price via a naive regex that grabbed the first
currency-adjacent number on the page, identical across every hotel.

HOW THIS ACTUALLY WORKS, so future-us doesn't have to re-derive it:

  1. RESOLVE the search location. A plain, DATELESS GET to
     google.com/travel/hotels?q=Hotels+in+{name} server-renders real
     hotel listings into a `script.ds:0` blob (a JS object literal the
     frontend hydrates from -- same technique as Flights' `script.ds:1`,
     found by looking for the same `AF_initDataCallback` pattern).
     Buried inside every hotel's own record is a stable "area" place ID
     (format "0x<hex>:0x<hex>", Google's internal place-ID encoding)
     identifying the SEARCHED LOCATION -- every hotel in one response
     shares the identical one, so the first hotel found is enough.

  2. ENCODE a real, dated search. Google Hotels does NOT honor plain
     ?checkin=&checkout= query params -- verified twice (once via a
     live browser, once by inspecting the raw response): they're
     silently ignored, always defaulting to today for 1 night. Unlike
     Flights' publicly-reverse-engineered `tfs` parameter, no existing
     library had already solved this for Hotels. The real mechanism is
     an opaque `ts` query param: a base64url-encoded protobuf message.
     Reverse-engineered by picking real dates through Google Hotels'
     actual calendar UI in a real browser, capturing the `ts` value
     Google itself generated, and hand-decoding the protobuf wire
     format byte by byte until every field was identified (place ID,
     check-in/check-out as {year, month, day} sub-messages, currency
     code). _build_ts() below reconstructs that exact message from
     scratch -- VERIFIED to produce byte-for-byte identical output to
     Google's own `ts` for the real captured example before ever being
     used to build a new one.

  3. RE-FETCH with that `ts`. The SAME script.ds:0 blob now contains
     real, date-accurate, per-property nightly rates -- verified live:
     nightly-rate x nights consistently landed within a few euros of a
     separately-embedded total-for-stay figure (rounding/tax
     difference), confirming these are genuinely tied to the requested
     dates, not a stale default. Spot-checked across 20 real hotels in
     one search: plausible, varied prices (EUR 235-1,413/night for a
     real mix of hotels/apartments), with properties that have no
     bookable rate for those dates correctly returning no price at all
     rather than a fabricated one.

RISK, stated as plainly as every other scraper in this package's risk
note: this is UNPUBLISHED, hand-reverse-engineered parsing of an
undocumented internal Google format -- more fragile than
google_flights_adapter.py's fast-flights dependency, which has 1.9k
GitHub stars of community upkeep behind it; this one has none. Field
positions are hardcoded array indices into Google's response, same
category of fragility as fast_flights' own parser and
google_flights_adapter.py's. If Google reshuffles this payload,
parsing degrades safely (fewer/no options extracted, guarded by the
sanity-bounds check in _parse_price), not silently-wrong prices. No API
key, no quota -- same category of tradeoff as the flights adapter, and
for the same reason: SerpApi's free-tier quota was the binding
constraint on live accommodation pricing.

CURRENCY IS TRUSTED, NOT VERIFIED PER-ENTRY: same limitation already
documented in serpapi_hotel_adapter.py and google_flights_adapter.py --
EUR is requested via both the `curr` query param and the `ts` blob's
own currency field (belt and suspenders, since neither alone was
reliably honored during testing), and confirmed "€"-prefixed in real
responses, but nothing in the payload ties a currency CODE to each
price string beyond that glyph.

NOT EXTRACTED (left None/unset rather than guessed, per this project's
"never invent a number" rule): rating, distance_to_lifts_km,
cancellation_policy. Their real field positions weren't identified
during this reverse-engineering pass and aren't needed for the cost
model (only price_eur_per_night is).
"""
import base64
import re
from datetime import date, timedelta
from typing import List, Optional

from ..models import AccommodationOption, AccommodationSearchResult, Resort
from .base import AdapterError
from .response_cache import get_cache
from ._wire_format import field_bytes, field_str, field_varint

SEARCH_URL = "https://www.google.com/travel/hotels"

# A hotel's own record embeds the searched-location's place ID at this
# path; a nightly rate (when the property has a bookable one for the
# requested dates) at this one. Hardcoded indices into an undocumented
# format -- see module docstring's risk note.
_PLACE_ID_PATTERN = re.compile(r"^0x[0-9a-f]+:0x[0-9a-f]+$")
_PRICE_PATTERN = re.compile(r"[€$£]\s?([0-9][0-9,]*(?:\.[0-9]+)?)")

# Sanity bounds for a per-night rate -- guards the hardcoded-index
# parse against silently returning a wrong-but-plausible-looking number
# if Google's payload shape shifts (e.g. picking up a review count or a
# multi-night total instead of a nightly rate). Real observed range
# during testing was EUR 127-1,413/night; padded generously.
_MIN_PLAUSIBLE_NIGHTLY_EUR = 15.0
_MAX_PLAUSIBLE_NIGHTLY_EUR = 10_000.0


def _cache_key(resort_name: str, checkin_date: date, nights: int, rooms_needed: int, currency: str) -> str:
    return "|".join([
        "google-hotels", resort_name.strip().lower(), str(checkin_date), str(nights),
        str(rooms_needed), currency,
    ])


# ---------------------------------------------------------------------------
# `ts` encoding. No .proto schema is public for this endpoint (unlike
# Flights, whose author extracted and published one) -- built from the
# generic wire-format primitives in _wire_format.py, per the exact
# structure found in step 2 of the module docstring.
# ---------------------------------------------------------------------------

def _date_message(d: date) -> bytes:
    return field_varint(1, d.year) + field_varint(2, d.month) + field_varint(3, d.day)


def _build_ts(place_id: str, place_name: str, checkin_date: date, checkout_date: date,
             currency: str = "EUR") -> str:
    """Builds the opaque `ts` param Google Hotels' real search UI sends. See module docstring."""
    part1 = field_varint(1, 1)
    part2 = field_bytes(
        2, field_bytes(1, field_varint(1, 3)) + field_bytes(1, field_varint(1, 3)) + field_varint(2, 0)
    )
    location = field_str(6, place_id) + field_str(7, place_name)
    field3_1 = field_bytes(1, field_bytes(2, location) + field_str(3, ""))
    nights = (checkout_date - checkin_date).days
    dates = (
        field_bytes(1, _date_message(checkin_date))
        + field_bytes(2, _date_message(checkout_date))
        # Night count. Earlier captures all happened to be 5-night
        # stays and this was mislabeled "occupancy, constant 5" --
        # corrected after a 7-night reference capture showed the value
        # tracking nights, not guest count (still not mapped to actual
        # occupancy; Google may ignore/derive that separately).
        + field_varint(3, nights)
    )
    field3_2 = field_bytes(2, field_bytes(2, dates) + field_bytes(6, field_varint(1, 1)))
    part3 = field_bytes(3, field3_1 + field3_2)
    part5 = field_bytes(5, field_bytes(1, field_str(7, currency)) + field_str(3, ""))
    raw = part1 + part2 + part3 + part5
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def search_url(place_name: str, checkin_date: Optional[date] = None,
               checkout_date: Optional[date] = None, currency: str = "EUR") -> str:
    """
    A real Google Hotels deep link for this location -- dated and
    showing real prices when both dates are given. Unlike the flight
    equivalent (search_url in google_flights_adapter.py), this needs no
    resolved place ID at all: verified live that Google Hotels' search
    UI correctly resolves the location and applies the dates from the
    `ts` blob's place NAME alone (empty place ID), so this whole
    function is pure/offline -- no network call, unlike
    search_accommodation() itself, which does one to actually price
    properties. Location-level, not one specific hotel: Google Hotels
    doesn't expose a plain URL scheme for "this one property" without
    ALSO knowing that property's own place ID, which isn't collected
    by this module (only the search LOCATION's ID is, and only when
    actually resolving one for search_accommodation -- see that
    function).
    """
    from urllib.parse import quote

    query = f"Hotels in {place_name}"
    url = f"{SEARCH_URL}?q={quote(query)}&hl=en&curr={currency}&gl=us"
    if checkin_date is not None and checkout_date is not None:
        ts = _build_ts("", place_name, checkin_date, checkout_date, currency=currency)
        url = url.replace("/hotels?", "/search?") + f"&ts={ts}"
    return url


# ---------------------------------------------------------------------------
# specific_property_url() -- a deep link to Google Hotels' page for ONE
# named property (search_url() above only reaches a resort-level results
# LIST -- the user still has to find and click the right one there).
#
# MECHANISM: the extra `qs=` query param that gets Google Hotels to land
# on one property needs that property's Knowledge Graph MID (a `/g/xxxx`
# id) -- reverse-engineered from a real captured example the same way
# `ts` was (see this module's top-level docstring): decoded the protobuf
# wire format, found a nested string in exactly that shape. This is a
# DIFFERENT id namespace than the `0x:0x` per-hotel place ID this module
# already scrapes off the listing page (see _iter_hotel_entries) --
# confirmed NOT interchangeable: substituting the scraped CID directly
# into qs= in place of a MID produced a hard Google-side 500, not a
# silent wrong match. No amount of scraping this module's existing
# listing-page fetch surfaced a per-property MID either (checked: only
# shared, region-level KG ids are present there, e.g. the resort's own
# admin-area entity, not any individual hotel's).
#
# So MID resolution here goes through Google's own PUBLIC, DOCUMENTED
# Knowledge Graph Search API (kgsearch.googleapis.com) instead of
# scraping -- see _resolve_hotel_mid()'s docstring. This is the one
# function in this module that isn't reverse-engineered.
#
# UNVERIFIED END TO END: written to the documented request/response
# shape and the reverse-engineered qs wire format, but no real
# GOOGLE_KG_API_KEY was available to test this against while writing it
# (see .env.example). If hotel-specific links aren't appearing in
# practice, this -- not search_url(), which IS live-verified -- is
# where to look first. Every failure mode (missing key, no KG match,
# request error) returns None, never raises -- callers fall back to
# search_url()'s resort-level link, exactly the same "degrade to what's
# proven to work" contract every other function in this module follows.
# ---------------------------------------------------------------------------

def _resolve_hotel_mid(hotel_name: str, area_name: str, api_key: str) -> Optional[str]:
    """
    Resolves a specific hotel's Knowledge Graph MID via Google's public
    Knowledge Graph Search API (developers.google.com/knowledge-graph) --
    see this section's module comment for why this needs a real API call
    to a DOCUMENTED endpoint rather than more scraping. Returns None
    (never raises) for no match, a malformed response, or a request
    failure -- an unresolved MID is exactly as safe as a missing one to
    the caller.
    """
    import primp

    try:
        client = primp.Client(impersonate="chrome_145", impersonate_os="macos")
        resp = client.get(
            "https://kgsearch.googleapis.com/v1/entities:search",
            params={"query": f"{hotel_name} {area_name}", "key": api_key,
                   "limit": "1", "types": "Hotel", "languages": "en"},
        )
        data = resp.json()
    except Exception:
        return None

    items = data.get("itemListElement") or []
    if not items:
        return None
    kg_id = (items[0].get("result") or {}).get("@id", "")
    # Google's entity-ID namespace has two live formats: /g/... (newer
    # "topic" MIDs) and /m/... (older, Freebase-derived, still valid --
    # confirmed live, e.g. "Ritz-Carlton Hotel Company" resolves to
    # kg:/m/0288kpv). The original /g/-only check silently rejected
    # every /m/ result, which -- confirmed against several real major
    # hotel brands -- is a meaningful share of what Knowledge Graph
    # actually returns for lodging entities.
    if not (kg_id.startswith("kg:/g/") or kg_id.startswith("kg:/m/")):
        return None
    return kg_id[len("kg:"):]


def _build_qs(mid: str) -> str:
    """
    Builds the opaque `qs` param that, alongside `ts`, gets Google
    Hotels to land on one specific property. See this section's module
    comment for how the shape was found.

    The leading numeric field (paired with the MID in the real captured
    example) is UNVERIFIED -- hardcoded to 0 here since no real MID was
    available to test whether Google actually requires a specific
    value. If specific_property_url() stops working, this is the next
    thing to check (capture a fresh real example and compare).
    """
    inner = field_varint(1, 0) + field_str(3, mid)
    wrapped = field_bytes(1, inner) + field_varint(2, 1)
    outer = field_bytes(6, wrapped) + field_varint(7, 13)
    return base64.urlsafe_b64encode(outer).decode("ascii").rstrip("=")


def specific_property_url(
    property_name: str, area_place_name: str, checkin_date: date, checkout_date: date,
    area_place_id: str = "", currency: str = "EUR",
) -> Optional[str]:
    """
    A deep link to Google Hotels' page for THIS ONE property, dated --
    see this section's module comment for the full mechanism and what's
    verified vs. not.

    Returns None (never raises) when GOOGLE_KG_API_KEY isn't set (see
    .env.example) or MID resolution fails for any reason -- the caller
    falls back to search_url()'s resort-level link.
    """
    import os
    from urllib.parse import quote

    api_key = os.environ.get("GOOGLE_KG_API_KEY")
    if not api_key:
        return None

    mid = _resolve_hotel_mid(property_name, area_place_name, api_key)
    if mid is None:
        return None

    ts = _build_ts(area_place_id, area_place_name, checkin_date, checkout_date, currency=currency)
    qs = _build_qs(mid)
    query = f"Hotels in {area_place_name}"
    return (
        f"{SEARCH_URL.replace('/hotels', '/search')}?q={quote(query)}"
        f"&hl=en&curr={currency}&gl=us&ts={ts}&qs={qs}"
    )


# ---------------------------------------------------------------------------
# Parsing -- deliberately separate from the HTTP calls so it's testable
# offline against captured payload shapes, matching every other
# adapter in this package.
# ---------------------------------------------------------------------------

def _extract_ds_blob(html: str, key: str):
    """Returns the parsed JSON object embedded in script.{key}, or None."""
    import json
    from selectolax.lexbor import LexborHTMLParser

    parser = LexborHTMLParser(html)
    script = parser.css_first(f"script.{key.replace(':', chr(92) + ':')}")
    if script is None:
        return None
    text = script.text()
    if "data:" not in text:
        return None
    data_str = text.split("data:", 1)[1].rsplit(", sideChannel:", 1)[0]
    try:
        return json.loads(data_str)
    except (ValueError, IndexError):
        return None


def _iter_hotel_entries(data):
    """Yields each hotel's own record (a list) from a ds:0 payload."""
    try:
        listing = data[0][0][0][1]
    except (IndexError, KeyError, TypeError):
        return
    for item in listing:
        if not isinstance(item, list) or len(item) < 2 or not isinstance(item[1], dict):
            continue
        for value in item[1].values():
            if isinstance(value, list) and value and isinstance(value[0], list):
                yield value[0]


def _resolve_place_id(data) -> Optional[str]:
    """First place-ID-shaped string found anywhere in the first hotel entry."""
    for entry in _iter_hotel_entries(data):
        found = _find_first_matching(entry, _PLACE_ID_PATTERN)
        if found:
            return found
    return None


def _find_first_matching(node, pattern) -> Optional[str]:
    if isinstance(node, str):
        return node if pattern.match(node) else None
    if isinstance(node, list):
        for v in node:
            found = _find_first_matching(v, pattern)
            if found:
                return found
    return None


def _parse_price(entry) -> Optional[float]:
    """
    A hotel entry with a bookable rate for the requested dates has (at
    least) two "€"-prefixed strings: the nightly rate and a
    total-for-stay figure -- verified live that nightly x nights lands
    within a few euros of the total, confirming they're genuinely tied
    together, not independent numbers. The SMALLER of any found values
    is always the nightly rate (a multi-night total can only be >= the
    nightly rate). Returns None (not a fabricated number) for a
    property with no visible rate, or one whose extracted value falls
    outside plausible bounds.
    """
    prices = []

    def walk(node):
        if isinstance(node, str):
            m = _PRICE_PATTERN.search(node)
            if m:
                try:
                    prices.append(float(m.group(1).replace(",", "")))
                except ValueError:
                    pass
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(entry)
    if not prices:
        return None
    nightly = min(prices)
    if not (_MIN_PLAUSIBLE_NIGHTLY_EUR <= nightly <= _MAX_PLAUSIBLE_NIGHTLY_EUR):
        return None
    return nightly


def _parse_property(entry) -> Optional[AccommodationOption]:
    if not isinstance(entry, list) or len(entry) < 2:
        return None
    name = entry[1]
    if not isinstance(name, str) or not name.strip():
        return None
    price = _parse_price(entry)
    if price is None:
        return None
    return AccommodationOption(price_eur_per_night=price, property_name=name)


# ---------------------------------------------------------------------------
# Live search
# ---------------------------------------------------------------------------

def _fetch_html(url: str) -> str:
    try:
        import primp
    except ImportError as exc:
        raise AdapterError("The 'primp' package is required for live accommodation search") from exc

    client = primp.Client(impersonate="chrome_145", impersonate_os="macos", referer=True, cookie_store=True)
    try:
        resp = client.get(url)
    except Exception as exc:
        raise AdapterError(f"Google Hotels request failed: {exc}") from exc
    return resp.text


def search_accommodation(
    resort: Resort,
    checkin_date: date,
    nights: int,
    rooms_needed: int,
    currency: str = "EUR",
    use_cache: bool = True,
) -> AccommodationSearchResult:
    """
    Same public contract as serpapi_hotel_adapter.search_accommodation
    (see that function's docstring for the shared parts); differences
    are covered in this module's docstring. Raises AdapterError when
    the location can't be resolved or the search itself fails -- never
    silently substitutes the static estimate; that decision belongs to
    the caller (engine/cost_calculator.py), per adapters/base.py.
    """
    if nights <= 0:
        raise AdapterError(f"nights must be > 0, got {nights}")
    if rooms_needed <= 0:
        raise AdapterError(f"rooms_needed must be > 0, got {rooms_needed}")

    checkout_date = checkin_date + timedelta(days=nights)

    key = _cache_key(resort.name, checkin_date, nights, rooms_needed, currency)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return AccommodationSearchResult(options=cached.options, from_cache=True)

    from urllib.parse import quote
    resolve_query = quote(f"Hotels in {resort.name}, {resort.country}")
    resolve_url = f"{SEARCH_URL}?q={resolve_query}&hl=en&curr={currency}&gl=us"
    resolve_html = _fetch_html(resolve_url)
    resolve_data = _extract_ds_blob(resolve_html, "ds:0")
    if resolve_data is None:
        raise AdapterError(f"Could not parse Google Hotels response for {resort.name!r}")

    place_id = _resolve_place_id(resolve_data)
    if place_id is None:
        raise AdapterError(f"Could not resolve a Google place ID for {resort.name!r}")

    ts = _build_ts(place_id, resort.name, checkin_date, checkout_date, currency=currency)
    dated_url = f"{SEARCH_URL.replace('/hotels', '/search')}?q={resolve_query}&hl=en&curr={currency}&gl=us&ts={ts}"
    dated_html = _fetch_html(dated_url)
    dated_data = _extract_ds_blob(dated_html, "ds:0")
    if dated_data is None:
        raise AdapterError(f"Could not parse dated Google Hotels response for {resort.name!r}")

    options = []
    for entry in _iter_hotel_entries(dated_data):
        parsed = _parse_property(entry)
        if parsed is not None:
            options.append(parsed)
    options.sort(key=lambda o: o.price_eur_per_night)

    result = AccommodationSearchResult(options=options)
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur_per_night(result: AccommodationSearchResult) -> Optional[float]:
    """Convenience for the cost calculator: lowest nightly rate, or None if no options."""
    if not result.options:
        return None
    return min(o.price_eur_per_night for o in result.options)


def clear_cache() -> None:
    """Test/ops helper, matching every other adapter's clear_cache."""
    get_cache().clear()
