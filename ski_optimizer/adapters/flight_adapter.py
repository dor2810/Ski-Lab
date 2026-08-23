"""
Flight search via SerpApi's Google Flights API.

WHY THIS PROVIDER (decision recorded so future-us doesn't relitigate it):
Amadeus Self-Service shut down 17 Jul 2026 and Kiwi/Tequila went
invite-only, so the obvious defaults are gone. SerpApi is a SCRAPER of
Google Flights -- it says so plainly in its own docs -- which carries
real ToS/fragility risk. It was chosen anyway because two of its
features map onto this product's core problems better than a
conventional flight API does:

  1. MULTI-AIRPORT SEARCH. `arrival_id` accepts comma-separated codes,
     so "TLV -> GVA,INN,MXP,CMF" is ONE request. A per-route API would
     need four. Since Ski Lab ranks ~30 resorts across a date range,
     this is the difference between a viable and an unaffordable search
     pattern.
  2. PRICE INSIGHTS. Returns typical_price_range and price_history --
     i.e. whether a fare is actually GOOD, not just what it costs. A
     single-seller API (Duffel, a GDS) structurally cannot tell you
     that. This is what makes "move your trip 2 days, save EUR 320"
     possible.

What it CANNOT do: issue tickets. Duffel gets ADDED (not swapped in)
for booking when this goes commercial -- see models.FlightOption's
docstring for why the boundary type keeps that cheap.

RISK, stated plainly: this is a scraper. If Google changes its markup
or SerpApi's terms shift, search breaks with no recourse. Two
mitigations are built in here: (a) nothing SerpApi-shaped escapes this
module -- engine/ only ever sees models.FlightOption, so a provider
swap is contained; (b) price_history should be PERSISTED as it arrives,
making it our own asset rather than a rented one.
"""
import os
from datetime import date
from typing import List, Optional

from ..models import FlightOption, PriceInsight, FlightSearchResult
from .base import AdapterError
from .response_cache import get_cache

SERPAPI_ENDPOINT = "https://serpapi.com/search"

# SerpApi's own cache serves repeat queries free for 1h and they don't
# count against quota. Our cache (see adapters/response_cache.py) sits
# IN FRONT of that to avoid even the round-trip, and matters for a
# second reason: this product fans out across many resorts, so the same
# TLV->GVA leg is requested repeatedly within one user session.
#
# NOTE: this is the EPHEMERAL cache. Durable price history goes to
# db/fare_history.py -- different job, different lifetime, kept apart.

# SerpApi `stops` parameter values (see its API docs).
_STOPS_ANY = 0
_STOPS_NONSTOP = 1
_STOPS_ONE_OR_FEWER = 2
_STOPS_TWO_OR_FEWER = 3


def _stops_param(max_connections: Optional[int]) -> int:
    """Maps our max-connections constraint onto SerpApi's enum."""
    if max_connections is None:
        return _STOPS_ANY
    if max_connections <= 0:
        return _STOPS_NONSTOP
    if max_connections == 1:
        return _STOPS_ONE_OR_FEWER
    if max_connections == 2:
        return _STOPS_TWO_OR_FEWER
    return _STOPS_ANY


def _cache_key(origin: str, destinations: List[str], outbound: date,
               ret: Optional[date], adults: int, max_connections: Optional[int],
               currency: str) -> str:
    return "|".join([
        origin, ",".join(sorted(destinations)), str(outbound), str(ret),
        str(adults), str(max_connections), currency,
    ])


# ---------------------------------------------------------------------------
# Parsing -- deliberately separate from the HTTP call so it can be tested
# against recorded fixtures without network access or an API key. Every
# real bug in an adapter like this lives in the parsing, not the GET.
# ---------------------------------------------------------------------------

def _parse_flight(entry: dict, currency_is_eur: bool) -> Optional[FlightOption]:
    """
    Converts one SerpApi flight entry into a FlightOption.
    Returns None (rather than raising) for entries missing the fields we
    require -- a single malformed itinerary in a list of twenty
    shouldn't blow away the whole search.
    """
    legs = entry.get("flights") or []
    price = entry.get("price")
    if not legs or price is None:
        return None

    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    first, last = legs[0], legs[-1]
    origin = (first.get("departure_airport") or {}).get("id")
    destination = (last.get("arrival_airport") or {}).get("id")
    if not origin or not destination:
        return None

    # Airline: a single carrier for direct itineraries; SerpApi marks
    # mixed-carrier trips with a "multi" logo and per-leg airlines.
    airlines = [leg.get("airline") for leg in legs if leg.get("airline")]
    unique_airlines = list(dict.fromkeys(airlines))
    airline = unique_airlines[0] if len(unique_airlines) == 1 else " + ".join(unique_airlines[:2])
    if not airline:
        airline = "Unknown"

    # total_duration covers flights AND layovers; fall back to summing
    # leg durations if it's absent (it isn't always present).
    total_duration = entry.get("total_duration")
    if total_duration is None:
        total_duration = sum(leg.get("duration") or 0 for leg in legs)

    return FlightOption(
        price_eur=price if currency_is_eur else price,  # see _search's currency note
        origin_airport=origin,
        destination_airport=destination,
        airline=airline,
        total_duration_minutes=int(total_duration),
        stops=max(0, len(legs) - 1),
        is_round_trip=(entry.get("type") == "Round trip"),
        booking_token=entry.get("booking_token"),
    )


def _parse_price_insights(payload: dict) -> Optional[PriceInsight]:
    raw = payload.get("price_insights")
    if not raw:
        return None
    lowest = raw.get("lowest_price")
    if lowest is None:
        return None
    typical = raw.get("typical_price_range")
    typical_tuple = None
    if isinstance(typical, (list, tuple)) and len(typical) == 2:
        typical_tuple = (float(typical[0]), float(typical[1]))
    return PriceInsight(
        lowest_price_eur=float(lowest),
        typical_range_eur=typical_tuple,
        price_level=raw.get("price_level"),
        price_history=raw.get("price_history"),
    )


def parse_response(payload: dict, currency_is_eur: bool = True) -> FlightSearchResult:
    """
    Turns a raw SerpApi payload into a FlightSearchResult.

    Public (no leading underscore) because it's the part worth testing
    directly and the part most likely to break when the provider changes
    its output -- see tests/test_flight_adapter.py.
    """
    status = (payload.get("search_metadata") or {}).get("status")
    if status == "Error":
        raise AdapterError(payload.get("error") or "SerpApi returned an error status")

    # SerpApi splits results into best_flights and other_flights; when
    # it doesn't rank them, everything lands in other_flights. Both must
    # be read or cheap itineraries get silently dropped.
    entries = list(payload.get("best_flights") or []) + list(payload.get("other_flights") or [])

    options = []
    for entry in entries:
        parsed = _parse_flight(entry, currency_is_eur)
        if parsed is not None:
            options.append(parsed)

    options.sort(key=lambda o: o.price_eur)
    return FlightSearchResult(options=options, insight=_parse_price_insights(payload))


# ---------------------------------------------------------------------------
# Live search
# ---------------------------------------------------------------------------

def search_flights(
    origin_airport: str,
    destination_airports,
    outbound_date: date,
    return_date: Optional[date] = None,
    adults: int = 1,
    max_connections: Optional[int] = 1,
    currency: str = "EUR",
    deep_search: bool = False,
    use_cache: bool = True,
) -> FlightSearchResult:
    """
    Searches flights, optionally across SEVERAL destination airports in
    a single request (pass a list) -- the main reason this provider was
    chosen. Raises AdapterError on failure; never silently substitutes
    an estimate. The CALLER decides how to degrade (see
    engine/cost_calculator.py), per adapters/base.py's contract.

    deep_search=true returns results identical to the Google Flights
    browser UI at the cost of latency -- worth it for a final quote,
    wasteful for a broad ranking sweep.
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

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise AdapterError(
            "SERPAPI_API_KEY is not set. Get a key at serpapi.com and add it "
            "to your .env -- see .env.example."
        )

    params = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": origin_airport,
        "arrival_id": ",".join(destination_airports),  # multi-airport in one call
        "outbound_date": outbound_date.isoformat(),
        "currency": currency,
        "adults": adults,
        "stops": _stops_param(max_connections),
        "hl": "en",
    }
    if return_date is not None:
        params["type"] = 1          # round trip
        params["return_date"] = return_date.isoformat()
    else:
        params["type"] = 2          # one way
    if deep_search:
        params["deep_search"] = "true"

    # Imported here rather than at module top so the parsing functions
    # above stay importable (and testable) without requests installed.
    try:
        import requests
    except ImportError as exc:
        raise AdapterError("The 'requests' package is required for live flight search") from exc

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

    result = parse_response(payload, currency_is_eur=(currency.upper() == "EUR"))

    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur(result: FlightSearchResult) -> Optional[float]:
    """Convenience for the cost calculator: lowest price, or None if no options."""
    if not result.options:
        return None
    return min(o.price_eur for o in result.options)


def clear_cache() -> None:
    """Test/ops helper -- not wired to any endpoint (see search.py's note on reload)."""
    get_cache().clear()
