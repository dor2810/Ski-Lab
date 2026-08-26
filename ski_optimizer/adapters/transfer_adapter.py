"""
Airport-to-resort transfer pricing via Alps2Alps' public API
(booking.alps2alps.com) -- free, no API key, no signup: a genuinely
PUBLIC, DOCUMENTED REST API (OpenAPI spec at
booking.alps2alps.com/openapi/public-v1.json), not scraping, unlike
the flight/hotel adapters in this package.

WHY THIS PROVIDER: engine/transfers.py's own module docstring already
concluded transfer operators "rarely have public APIs" and planned
periodic manual/scraped rate-table refreshes instead of live pricing.
Re-checked (2026-08): Alps2Alps -- already one of the curated operators
in that static spreadsheet -- turns out to be the exception, with a
genuinely free, keyless, self-serve REST API using the SAME real-time
pricing engine as their booking site, plus a working booking_url
straight to checkout. (Ski-Lifts.com/"Lifts To", another curated
operator, ALSO has a live-pricing API -- but it's a gated B2B partner
integration needing a sales conversation and account approval, no
self-serve or trial access, so not usable here.)

COVERAGE IS NOT UNIVERSAL: spot-checked against this project's curated
resort list -- Chamonix, Zermatt, Bansko, and Andorra la Vella all
resolved with real quotes; Poiana Brasov (Romania) returned no match at
all. "No location match" is NOT a request failure -- it means this
provider doesn't cover that place -- so resolve_location() returns
None rather than raising, and callers should fall back to the static/
formula estimate (engine/transfers.py), matching flight_adapter.py's
same degrade-per-missing-quote philosophy.

TWO-STEP LOOKUP: callers pass a resort and its nearest-airport field as
free text; the pricing endpoint needs Alps2Alps's own opaque location
codes ("resort-11", "airport-1"), resolved via /locations/search first.
Codes are stable (a place doesn't move) but are opaque provider ids,
not researched facts -- unlike Resort.latitude/longitude (baked into
the spreadsheet, see that field's own docstring), these are resolved
live and cached rather than hardcoded.

PRICING IS PER VEHICLE, NOT PER PERSON: every TransferQuote this
returns has cost_basis="per_vehicle" -- Alps2Alps prices a shared
minivan for the whole party, not a per-seat fare. cheapest_price_eur()
divides by nothing; the CALLER divides by group_size to get a
per-person cost (same arithmetic cost_calculator.py already does for
hotel per-room rates).

GROUPS LARGER THAN ONE VEHICLE AREN'T MODELLED: unlike engine/
transfers.py's curated data (which books ceil(n/capacity) vehicles for
an oversized group), this MVP prices exactly one vehicle per request
and excludes any that can't seat the whole party -- a group of 10
simply gets no live quote (None), falling back to the static/formula
path, which DOES handle multi-vehicle booking. Real multi-vehicle
live pricing would need genuine business logic (does Alps2Alps even
support that combination, at what marginal cost) this pass didn't
attempt.

RATE LIMITED (documented, not reverse-engineered): 30 req/min per IP
on /locations/search; unpublished but real limits on /transfer-options
too (hit them firing requests back to back while researching this) --
respected here the same way flight_adapter.py respects SerpApi's, not
routed around.
"""
import datetime
from typing import List, Optional

from ..models import Resort, TransferQuote, TransferSearchResult
from .base import AdapterError
from .response_cache import get_cache

BASE_URL = "https://booking.alps2alps.com/api/public/v1"


def _cache_key(kind: str, *parts) -> str:
    return "|".join(["transfer", kind, *[str(p) for p in parts]])


def _fetch_json(path: str, params: dict) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise AdapterError("The 'requests' package is required for transfer lookups") from exc

    try:
        resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
        if resp.status_code == 429:
            raise AdapterError("Alps2Alps rate limit hit -- retry later")
        resp.raise_for_status()
        return resp.json()
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError(f"Alps2Alps request failed: {exc}") from exc


def _airport_city_name(nearest_airport_field: str) -> str:
    """
    First listed airport's city name, e.g. "Geneva (GVA) / Chambery
    (CMF)" -> "Geneva" -- matches engine/cost_calculator.airport_codes_
    for's "use the first one" convention for multi-airport resorts.
    """
    first = (nearest_airport_field or "").split("/")[0]
    return first.split("(")[0].strip()


def resolve_location(query: str, location_type: Optional[str] = None, use_cache: bool = True) -> Optional[str]:
    """
    Resolves a free-text place name to Alps2Alps's own location code
    (e.g. "resort-11"). Returns None (never raises) when nothing
    matches -- see module docstring's coverage note on why that's not
    a failure.

    location_type ("airport" or "resort") filters the match. REAL BUG
    this caught: /locations/search?q=geneva returns "Geneva city"
    (a resort/city entry) BEFORE "Geneva Airport" -- searching for the
    airport without filtering silently resolved to the wrong location
    type and the pricing request 422'd. Bare data[0] is only safe when
    the caller doesn't care which type it gets.

    A NO-MATCH RESULT IS NEVER CACHED -- ANOTHER REAL BUG this caught
    live in production: a genuinely-covered resort (Chamonix -- verified
    directly against the provider) came back None on every search for
    over an hour, while a different resort worked fine moments later.
    The provider's own coverage doesn't change hour to hour; a single
    transient blip (network hiccup, a momentary empty response) does,
    and this function used to cache THAT as if it were a permanent
    "this place isn't covered" fact, for the same TTL as a real price
    quote. A successful resolution IS still cached (an opaque id for a
    real place is stable and cheap to trust); only "found nothing" is
    always re-checked, since this call is cheap and low-volume (at most
    one per distinct resort/airport name, not per search).
    """
    key = _cache_key("location", query.strip().lower(), location_type or "")
    if use_cache:
        cached = get_cache().get(key)
        if cached:
            return cached

    data = _fetch_json("/locations/search", {"q": query})
    if not isinstance(data, list) or not data:
        return None

    match = next((item for item in data if item.get("type") == location_type), None) \
        if location_type else data[0]
    if match is None:
        return None

    code = match["code"]
    if use_cache:
        get_cache().set(key, code)
    return code


def _parse_vehicles(data: dict) -> List[TransferQuote]:
    outbound = (data or {}).get("outbound") or {}
    vehicles = outbound.get("vehicles") or []
    duration = float((data.get("route") or {}).get("duration_minutes") or 0)
    options = []
    for v in vehicles:
        try:
            options.append(TransferQuote(
                price_eur=float(v["price"]),
                cost_basis="per_vehicle",
                vehicle_name=v["name"],
                max_passengers=int(v["max_passengers"]),
                duration_minutes=duration,
                booking_url=v.get("booking_url"),
            ))
        except (KeyError, TypeError, ValueError):
            continue  # one malformed vehicle entry shouldn't sink the rest
    return options


def search_transfer_options(
    resort: Resort,
    pickup_date: datetime.date,
    pickup_time: str,  # "HH:MM"
    adults: int,
    return_date: Optional[datetime.date] = None,
    return_time: Optional[str] = None,
    currency: str = "EUR",
    use_cache: bool = True,
) -> TransferSearchResult:
    """
    Real, live-priced transfer options for resort's nearest airport
    (the first one, for a multi-airport resort -- see
    _airport_city_name). Raises AdapterError only when the location
    genuinely can't be resolved or the pricing request itself fails --
    never substitutes the static estimate itself; that decision belongs
    to the caller (engine/cost_calculator.py), matching every other
    adapter in this package (see adapters/base.py).
    """
    if adults <= 0:
        raise AdapterError(f"adults must be > 0, got {adults}")

    origin_query = _airport_city_name(resort.nearest_airport)
    origin_code = resolve_location(origin_query, location_type="airport", use_cache=use_cache)
    if origin_code is None:
        raise AdapterError(f"Alps2Alps has no location match for airport {origin_query!r}")

    dest_code = resolve_location(resort.name, location_type="resort", use_cache=use_cache)
    if dest_code is None:
        raise AdapterError(f"Alps2Alps has no location match for resort {resort.name!r}")

    key = _cache_key("quote", origin_code, dest_code, pickup_date, pickup_time,
                     adults, return_date, return_time, currency)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return TransferSearchResult(options=cached.options, from_cache=True)

    params = {
        "from": origin_code, "to": dest_code,
        "date": pickup_date.isoformat(), "time": pickup_time,
        "adults": adults, "currency": currency,
    }
    if return_date is not None:
        params["return_date"] = return_date.isoformat()
        params["return_time"] = return_time or pickup_time

    data = _fetch_json("/transfer-options", params)
    result = TransferSearchResult(options=_parse_vehicles(data))
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur(result: TransferSearchResult, group_size: int) -> Optional[float]:
    """
    Cheapest per-VEHICLE price among options that actually fit
    group_size, or None -- a vehicle that can't seat the whole party is
    excluded, not silently priced as if it could (see module docstring
    on groups larger than one vehicle).
    """
    fitting = [o for o in result.options if o.max_passengers >= group_size]
    if not fitting:
        return None
    return min(o.price_eur for o in fitting)


def cheapest_option(result: TransferSearchResult, group_size: int) -> Optional[TransferQuote]:
    """Same selection as cheapest_price_eur, but returns the whole quote (for its booking_url)."""
    fitting = [o for o in result.options if o.max_passengers >= group_size]
    if not fitting:
        return None
    return min(fitting, key=lambda o: o.price_eur)


def clear_cache() -> None:
    """Test/ops helper, matching every other adapter's clear_cache."""
    get_cache().clear()
