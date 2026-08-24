"""
Accommodation search via SerpApi's Google Hotels API.

WHY THIS PROVIDER, RIGHT NOW (decision recorded so future-us doesn't
relitigate it): adapters/accommodation_adapter.py targets Booking.com's
Demand API, which is the right long-term source (real inventory, real
cancellation terms) but is gated behind a "Managed Affiliate Partner"
approval that has to be applied for and is not available today (see
PROJECT_STATE.md). SerpApi is already integrated for flights
(flight_adapter.py, same SERPAPI_API_KEY, same account) so this gets a
REAL, live-tested accommodation search working with zero new
procurement, while the Booking.com application is in flight.

THIS IS THE SAME PATTERN AS BOOKING.COM'S ADAPTER ON PURPOSE: identical
public interface (parse_response / search_accommodation /
cheapest_price_eur_per_night / clear_cache), identical return type
(models.AccommodationSearchResult). engine/ code wired against that
boundary type does not care which module it calls -- swapping providers
later is a one-line change at the call site, not a rewrite. See
adapters/accommodation_adapter.py's own docstring for the mirrored
contract.

RISK, stated plainly, same caveat as flight_adapter.py: SerpApi is a
SCRAPER of Google Hotels, not an official partner feed. ToS/fragility
risk applies here exactly as it does for flights.

KNOWN LIMITATIONS, stated honestly rather than glossed over:
  1. NO ROOMS PARAMETER. Google Hotels (and therefore this API) has no
     way to request "N rooms" -- only `adults`/`children` occupancy.
     `adults` below is sent as an occupancy signal only (rooms_needed *
     2), and the price returned is the cheapest SINGLE room's per-night
     rate at that property, not rooms_needed rooms. A caller that needs
     total room cost must multiply externally -- exactly the same
     contract as accommodation_adapter's Booking.com parsing, where the
     parsed price is also one room's rate.
  2. distance_to_lifts_km IS ALWAYS None. Google Hotels returns
     human-readable nearby-place transport durations (e.g. "Taxi, 12
     min"), not a distance in km to a specific POI like "the lifts".
     Fabricating a km figure from that would violate this project's
     "never invent a number" rule (see CLAUDE.md), so it's left
     unfilled rather than guessed.
  3. `q` IS JUST THE RESORT NAME. Untested against all 30 seed resorts
     -- some names may be ambiguous to Google Places or resolve to the
     wrong locale. Flag for follow-up once a real key is in hand.
  4. CURRENCY IS TRUSTED, NOT VERIFIED PER-ENTRY. Like flight_adapter,
     this asks SerpApi for `currency=EUR` and trusts the response is in
     that currency -- there is no per-property currency field to check
     against (unlike Booking's block-level currency, which IS checked).
"""
import os
from datetime import date, timedelta
from typing import Optional

from ..models import AccommodationOption, AccommodationSearchResult
from .base import AdapterError
from .response_cache import get_cache

SERPAPI_ENDPOINT = "https://serpapi.com/search"


def _cache_key(resort_name: str, checkin_date: date, checkout_date: date,
               adults: int, currency: str) -> str:
    return "|".join([
        "accom-serpapi", resort_name.strip().lower(),
        str(checkin_date), str(checkout_date), str(adults), currency,
    ])


# ---------------------------------------------------------------------------
# Parsing -- deliberately separate from the HTTP call so it can be tested
# against a fixture without network access or an API key. See module
# docstring: every real bug in an adapter like this lives in the parsing,
# not the GET.
# ---------------------------------------------------------------------------

def _parse_property(entry: dict) -> Optional[AccommodationOption]:
    """
    Converts one Google Hotels property entry into an AccommodationOption.
    Returns None (rather than raising) for entries missing the fields we
    require -- a single malformed listing in a page of twenty shouldn't
    blow away the whole search, matching flight_adapter's defensive style.

    Unlike Booking.com's response (a list of rate "blocks" per property
    that we scan for the cheapest), Google Hotels already surfaces the
    cheapest rate directly as rate_per_night.extracted_lowest -- no
    min() needed here.
    """
    name = entry.get("name")
    rate = (entry.get("rate_per_night") or {}).get("extracted_lowest")
    if name is None or rate is None:
        return None

    try:
        price = float(rate)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    rating = entry.get("overall_rating")
    try:
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None

    # Only asserted when the API says so explicitly -- absence does NOT
    # imply "non_refundable"; that would be inventing a fact we don't have.
    cancellation_policy = "free_cancellation" if entry.get("free_cancellation") else None

    return AccommodationOption(
        price_eur_per_night=price,
        property_name=name,
        rating=rating,
        distance_to_lifts_km=None,  # see module docstring, limitation #2
        cancellation_policy=cancellation_policy,
        booking_token=entry.get("property_token"),
    )


def parse_response(payload: dict) -> AccommodationSearchResult:
    """
    Turns a raw SerpApi Google Hotels payload into an
    AccommodationSearchResult. Public (no leading underscore) because
    it's the part worth testing directly, matching flight_adapter's
    parse_response -- same provider, same error-shape convention.
    """
    status = (payload.get("search_metadata") or {}).get("status")
    if status == "Error":
        raise AdapterError(payload.get("error") or "SerpApi returned an error status")

    entries = payload.get("properties") or []
    options = []
    for entry in entries:
        parsed = _parse_property(entry)
        if parsed is not None:
            options.append(parsed)

    options.sort(key=lambda o: o.price_eur_per_night)
    return AccommodationSearchResult(options=options)


# ---------------------------------------------------------------------------
# Live search
# ---------------------------------------------------------------------------

def search_accommodation(
    resort,
    checkin_date: date,
    nights: int,
    rooms_needed: int,
    currency: str = "EUR",
    use_cache: bool = True,
) -> AccommodationSearchResult:
    """
    Searches real accommodation options near `resort` for the given
    dates. Raises AdapterError on failure -- never silently substitutes
    the seed spreadsheet's estimate; that decision belongs to the caller
    (engine/cost_calculator.py), per adapters/base.py's contract. Same
    signature shape as accommodation_adapter.search_accommodation, minus
    the currency default being implicit there -- kept explicit here
    since SerpApi requires it as a real request parameter.
    """
    if nights <= 0:
        raise AdapterError(f"nights must be > 0, got {nights}")
    if rooms_needed <= 0:
        raise AdapterError(f"rooms_needed must be > 0, got {rooms_needed}")

    checkout_date = checkin_date + timedelta(days=nights)
    adults = rooms_needed * 2  # occupancy signal only -- see limitation #1

    key = _cache_key(resort.name, checkin_date, checkout_date, adults, currency)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return AccommodationSearchResult(options=cached.options, from_cache=True)

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise AdapterError(
            "SERPAPI_API_KEY is not set. Get a key at serpapi.com and add it "
            "to your .env -- see .env.example. (Same key as flight_adapter.py.)"
        )

    # Imported here rather than at module top so the parsing functions
    # above stay importable (and testable) without requests installed.
    try:
        import requests
    except ImportError as exc:
        raise AdapterError("The 'requests' package is required for live accommodation search") from exc

    params = {
        "engine": "google_hotels",
        "api_key": api_key,
        "q": resort.name,
        "check_in_date": checkin_date.isoformat(),
        "check_out_date": checkout_date.isoformat(),
        "adults": adults,
        "currency": currency,
        "hl": "en",
    }

    try:
        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
    except Exception as exc:
        raise AdapterError(f"SerpApi request failed: {exc}") from exc

    if response.status_code == 401:
        raise AdapterError("SerpApi rejected the API key (401)")
    if response.status_code == 429:
        raise AdapterError("SerpApi rate limit / quota exhausted (429)")
    if response.status_code >= 400:
        raise AdapterError(f"SerpApi returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise AdapterError("SerpApi returned a non-JSON response") from exc

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
