"""
Deep links to Google Flights / Google Hotels search results.

IMPORTANT -- what these are NOT: a booking link for the specific priced
itinerary shown to the user, or a link to one specific hotel's own
page. Resolving either of those needs information this project doesn't
collect for every result (a booking-provider handle, or a hotel's own
place ID -- see FlightOption/AccommodationOption's docstrings in
models.py, and google_hotels_adapter.py's search_url docstring).
Instead, these are real, working deep links to Google's OWN live
search results for the same route/resort and dates.

BOTH of these delegate to their respective adapter's own search_url()
(adapters/google_flights_adapter.py, adapters/google_hotels_adapter.py)
rather than building query strings here directly -- see each adapter's
own docstring for exactly how its URL scheme was reverse-engineered and
verified. That history matters for why this file changed shape:

  - Flights used to build a natural-language `q=` query
    ("Flights to X from Y on ... through ...") here directly. Verified
    once to work, but reported live to sometimes land on Google
    Flights' plain homepage instead of real results -- natural-language
    parsing on that endpoint isn't 100% reliable. Replaced with
    fast_flights' own structured query builder (the same protobuf `tfs`
    param Google's real UI generates), which has been reliable on every
    route/date tried since.

  - Hotels never supported plain ?checkin=&checkout= query params
    (verified: silently ignored, defaulting to today for 1 night) --
    this file used to build a location-only, dateless link because of
    that. adapters/google_hotels_adapter.py's own reverse-engineering
    of Google Hotels' opaque `ts` param (built for live pricing) turned
    out to work from a bare place NAME with no resolved place ID at
    all -- verified live -- so the link here can be dated and show real
    prices too, with no extra network call.
"""
from datetime import date
from typing import Optional

from ..models import Resort
from .cost_calculator import airport_codes_for


def google_flights_url(resort: Resort, outbound_date: Optional[date] = None,
                       return_date: Optional[date] = None,
                       origin_airport: str = "TLV") -> Optional[str]:
    """
    None when the resort's spreadsheet airport field has no parseable
    IATA code -- a link to nowhere is worse than no link. Uses the
    FIRST airport code for a multi-airport resort when dates are given
    (the structured query format takes exactly one destination per
    leg) -- see google_flights_adapter.search_url's own docstring.
    """
    codes = airport_codes_for(resort)
    if not codes:
        return None

    if outbound_date is not None and return_date is not None:
        from ..adapters import google_flights_adapter
        return google_flights_adapter.search_url(origin_airport, codes[0], outbound_date, return_date)

    # No dates: natural-language query is fine here -- there's no
    # specific route/date combination for a structured query to get
    # wrong, just "show me flights to this resort" in general.
    from urllib.parse import quote
    destination = " or ".join(codes)
    query = f"Flights to {destination} from {origin_airport}"
    return f"https://www.google.com/travel/flights?q={quote(query)}"


def google_hotels_url(resort: Resort, checkin_date: Optional[date] = None,
                      checkout_date: Optional[date] = None) -> str:
    from ..adapters import google_hotels_adapter
    return google_hotels_adapter.search_url(f"{resort.name}, {resort.country}", checkin_date, checkout_date)
