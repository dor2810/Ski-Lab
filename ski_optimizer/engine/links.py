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

alps2alps_search_url() below is the transfer fallback and works
differently from the two above -- it does NOT search Google at all. See
its own docstring.
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
                      checkout_date: Optional[date] = None,
                      property_name: Optional[str] = None) -> str:
    """
    property_name narrows this from a resort-wide listing to a search
    for that one property within the resort -- see
    google_hotels_adapter.search_url()'s own docstring for what this
    is (and isn't) verified to do.
    """
    from ..adapters import google_hotels_adapter
    return google_hotels_adapter.search_url(f"{resort.name}, {resort.country}", checkin_date, checkout_date,
                                            property_name=property_name)


# Confirmed live (curl, 200): the real Alps2Alps quote/booking form --
# https://booking.alps2alps.com/booking/index -- not their plain
# marketing homepage, and not a guessed resort-specific page. A
# resort-specific pattern (alps2alps.com/ski-resort-guide-{slug}/) DOES
# exist for SOME resorts but was confirmed live to 404 for most tried
# (Val d'Isere, Meribel, Courchevel, Zermatt, Verbier, St. Anton) -- not
# reliable enough to build from a slug. The booking form itself was
# also confirmed to take no query-string params for prefilling
# pickup/dropoff (no such param appears anywhere in its own served
# JS/CSS asset list), so this can't be dated or routed the way
# google_flights_url/google_hotels_url are -- it's the same kind of
# fallback in spirit (always real, always working) but reaches a
# generic search TOOL, not resort-specific results.
ALPS2ALPS_BOOKING_FORM_URL = "https://booking.alps2alps.com/booking/index"


def alps2alps_search_url() -> str:
    """
    The one part of _transfer_search_url's contract that CAN be
    unconditional -- unlike live_transfer_booking_url() (a specific,
    live-quoted vehicle for one route/date/group-size), this needs no
    resort, no date, no group size, and never fails, so it's always
    available as the fallback that keeps "View Transfer" behaving like
    "View Flight"/"View Accommodation" -- always a real, working link,
    never nothing.
    """
    return ALPS2ALPS_BOOKING_FORM_URL
