"""
Accommodation search via Booking.com's Demand API.

STATUS, stated plainly: this is written and its PARSING is tested against
a realistic fixture, but it has never made a real HTTP call, because no
Booking.com API credential exists yet. That is not the same failure mode
as "planned, not started" -- the code path is real, complete, and ready;
it is specifically the credential that is missing. See
setup_context_for_claude/PROJECT_STATE.md for why: Booking.com's basic
Affiliate signup does not itself grant API access -- that requires a
separate "Managed Affiliate Partner" approval track, which is currently
paused for new applicants.

WHY THIS SHAPE, mirroring adapters/flight_adapter.py's proven pattern:
  1. Parsing is separated from the HTTP call (_parse_accommodation /
     parse_response) so it is fully testable offline, without a key or
     network access -- see tests/test_accommodation_adapter.py.
  2. The adapter raises AdapterError on any failure (missing key, HTTP
     error, malformed response) and NEVER falls back to a fabricated
     number -- the caller (engine/cost_calculator.py) decides how to
     degrade, exactly like the flight adapter's contract.
  3. Response shape below is BEST-EFFORT, built from Booking.com Demand
     API's published documentation conventions, NOT verified against a
     real response (no key = no way to verify). Expect to adjust field
     names once the first real call lands -- flag this explicitly rather
     than presenting an untested shape as proven, the same honesty the
     flight adapter's own docstring applied before its first real call.

WHAT IT CANNOT DO YET: issue or hold a booking. This is search/pricing
only, matching the product's current scope (compare options, don't
transact) -- see FlightOption's docstring for why booking is deliberately
a separate, later concern.
"""
import datetime
import os
from typing import List, Optional

from ..models import AccommodationOption, AccommodationSearchResult
from .base import AdapterError
from .response_cache import get_cache

BOOKING_DEMAND_API_ENDPOINT = "https://demandapi.booking.com/3.1/accommodations/search"


def _cache_key(resort_name: str, checkin_date: datetime.date, nights: int, rooms_needed: int) -> str:
    return "|".join(["accom", resort_name.strip().lower(), str(checkin_date), str(nights), str(rooms_needed)])


# ---------------------------------------------------------------------------
# Parsing -- deliberately separate from the HTTP call so it can be tested
# against a fixture without network access or an API key. See module
# docstring: every real bug in an adapter like this lives in the parsing,
# not the GET, and that's the part we CAN verify without a live key.
# ---------------------------------------------------------------------------

def _parse_accommodation(entry: dict) -> Optional[AccommodationOption]:
    """
    Converts one Booking.com Demand API property entry into an
    AccommodationOption. Returns None (rather than raising) for entries
    missing the fields we require -- a single malformed listing in a
    page of twenty shouldn't blow away the whole search, matching
    _parse_flight's defensive style.
    """
    name = entry.get("name")
    # Price lives under a nested "block" (rate/room offer) list per
    # Booking.com's documented convention -- a property can have several
    # room offers; we take the cheapest one, matching how a user would
    # actually shop (lowest available rate for that property).
    blocks = entry.get("block") or []
    prices = []
    for block in blocks:
        price = (block.get("price") or {}).get("amount")
        currency = (block.get("price") or {}).get("currency")
        if price is not None and currency == "EUR":
            try:
                prices.append(float(price))
            except (TypeError, ValueError):
                continue
    if name is None or not prices:
        return None

    cheapest = min(prices)
    if cheapest <= 0:
        return None

    cancellation_policy = None
    for block in blocks:
        cxl = block.get("cancellation") or {}
        if cxl.get("type"):
            cancellation_policy = cxl["type"]
            break

    rating = entry.get("review_score")
    try:
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None

    distance = entry.get("distance_to_centre")
    try:
        distance = float(distance) if distance is not None else None
    except (TypeError, ValueError):
        distance = None

    return AccommodationOption(
        price_eur_per_night=cheapest,
        property_name=name,
        rating=rating,
        distance_to_lifts_km=distance,
        cancellation_policy=cancellation_policy,
        booking_token=entry.get("id"),
    )


def parse_response(payload: dict) -> AccommodationSearchResult:
    """
    Turns a raw Booking.com Demand API payload into an
    AccommodationSearchResult. Public (no leading underscore) because
    it's the part worth testing directly, matching flight_adapter's
    parse_response.
    """
    if payload.get("error"):
        raise AdapterError(payload.get("error") or "Booking.com Demand API returned an error")

    entries = payload.get("data") or []
    options = []
    for entry in entries:
        parsed = _parse_accommodation(entry)
        if parsed is not None:
            options.append(parsed)

    options.sort(key=lambda o: o.price_eur_per_night)
    return AccommodationSearchResult(options=options)


# ---------------------------------------------------------------------------
# Live search
# ---------------------------------------------------------------------------

def search_accommodation(
    resort,
    checkin_date: datetime.date,
    nights: int,
    rooms_needed: int,
    use_cache: bool = True,
) -> AccommodationSearchResult:
    """
    Searches real accommodation options near `resort` for the given dates.
    Raises AdapterError on failure -- including, currently, ALWAYS, since
    no BOOKING_AFFILIATE_API_KEY exists yet (see module docstring). Never
    silently substitutes the seed spreadsheet's estimate; that decision
    belongs to the caller (engine/cost_calculator.py), per adapters/base.py's
    contract -- same shape as flight_adapter.search_flights.
    """
    if nights <= 0:
        raise AdapterError(f"nights must be > 0, got {nights}")
    if rooms_needed <= 0:
        raise AdapterError(f"rooms_needed must be > 0, got {rooms_needed}")

    key = _cache_key(resort.name, checkin_date, nights, rooms_needed)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return AccommodationSearchResult(options=cached.options, from_cache=True)

    api_key = os.environ.get("BOOKING_AFFILIATE_API_KEY")
    if not api_key:
        raise AdapterError(
            "BOOKING_AFFILIATE_API_KEY is not set. This requires Booking.com's "
            "Managed Affiliate Partner approval, not just the basic Affiliate "
            "signup -- see PROJECT_STATE.md for the current status. Once you "
            "have a key, add it to .env -- see .env.example."
        )

    try:
        import requests
    except ImportError as exc:
        raise AdapterError("The 'requests' package is required for live accommodation search") from exc

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "location": {"name": resort.name},
        "checkin": checkin_date.isoformat(),
        "checkout": (checkin_date + datetime.timedelta(days=nights)).isoformat(),
        "rooms": rooms_needed,
        "currency": "EUR",
    }

    try:
        response = requests.post(BOOKING_DEMAND_API_ENDPOINT, json=body, headers=headers, timeout=30)
    except Exception as exc:
        raise AdapterError(f"Booking.com Demand API request failed: {exc}") from exc

    if response.status_code == 401:
        raise AdapterError("Booking.com Demand API rejected the credentials (401)")
    if response.status_code == 429:
        raise AdapterError("Booking.com Demand API rate limit / quota exhausted (429)")
    if response.status_code >= 400:
        raise AdapterError(f"Booking.com Demand API returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise AdapterError("Booking.com Demand API returned a non-JSON response") from exc

    result = parse_response(payload)

    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur_per_night(result: AccommodationSearchResult) -> Optional[float]:
    """Convenience for the cost calculator: lowest nightly rate, or None if no options."""
    if not result.options:
        return None
    return min(o.price_eur_per_night for o in result.options)


def clear_cache() -> None:
    """Test/ops helper, matching flight_adapter.clear_cache."""
    get_cache().clear()
