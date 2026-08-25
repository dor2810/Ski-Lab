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
import datetime
from typing import List, Optional

from ..models import FlightOption, FlightSearchResult
from .base import AdapterError
from .response_cache import get_cache


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


def _parse_flight_result(flight, currency_is_eur: bool) -> Optional[FlightOption]:
    """
    Converts one `fast_flights.model.Flights` result (one full,
    already-priced itinerary card -- see module docstring on what that
    covers for a round trip) into a FlightOption. Returns None rather
    than raising for a malformed entry (no legs, non-numeric price),
    matching flight_adapter.py's defensive parsing style -- one bad
    card in a page of several shouldn't blow away the whole search.
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
        booking_token=None,  # this library exposes no provider handle equivalent -- see module docstring
    )


def _search_one_airport(
    origin_airport: str,
    destination_airport: str,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date],
    adults: int,
    max_connections: Optional[int],
    currency: str,
) -> List[FlightOption]:
    from fast_flights import FlightQuery, Passengers, create_query, get_flights
    from fast_flights.exceptions import FlightsNotFound

    legs = [FlightQuery(date=outbound_date.isoformat(),
                        from_airport=origin_airport, to_airport=destination_airport)]
    if return_date is not None:
        legs.append(FlightQuery(date=return_date.isoformat(),
                                from_airport=destination_airport, to_airport=origin_airport))

    query = create_query(
        flights=legs,
        seat="economy",
        trip="round-trip" if return_date is not None else "one-way",
        passengers=Passengers(adults=adults),
        currency=currency,
        max_stops=max_connections,
    )

    try:
        raw_results = get_flights(query)
    except FlightsNotFound:
        return []

    currency_is_eur = currency.upper() == "EUR"
    options = []
    for f in raw_results:
        parsed = _parse_flight_result(f, currency_is_eur)
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
    for dest in destination_airports:
        try:
            all_options.extend(_search_one_airport(
                origin_airport, dest, outbound_date, return_date, adults, max_connections, currency,
            ))
        except Exception as exc:  # noqa: BLE001 -- see docstring: one airport's failure shouldn't sink the rest
            errors.append(f"{dest}: {exc}")

    if not all_options and errors:
        raise AdapterError(f"Google Flights search failed for every airport: {'; '.join(errors)}")

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
