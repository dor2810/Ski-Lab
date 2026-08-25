"""
Deep links to Google Flights / Google Hotels search results.

IMPORTANT -- what these are NOT: a booking link for the specific priced
itinerary shown to the user. Both adapters/flight_adapter.py and
adapters/serpapi_hotel_adapter.py get back an opaque provider
`booking_token` for the option they price, and resolving THAT into an
actual bookable page requires a further live SerpApi call per result
(see FlightOption/AccommodationOption's docstrings in models.py) --
unaffordable to spend on every result in every search against this
project's rate-limited free-tier quota (see api/rate_limit.py).

Instead, these build a URL to Google's OWN live search results for the
same route/resort, which costs nothing and needs no adapter call. Their
exact query-parameter formats were verified BY HAND against the real
site (google.com/travel/flights and google.com/travel/hotels), not
assumed:
  - Google Flights DOES honor a natural-language date phrase inside
    `q` ("... on 2026-01-10 through 2026-01-17").
  - Google Hotels does NOT reliably honor checkin/checkout as URL
    params OR inside `q` -- it silently ignores them and shows its own
    default dates. So the hotels link is location-only; the user picks
    dates themselves on Google's page. Never invent a date parameter
    that doesn't actually work -- see CLAUDE.md's "never invent a
    number" rule, which applies here to a fabricated-looking dated URL
    just as much as to a fabricated price.
"""
from datetime import date
from typing import Optional
from urllib.parse import quote

from ..models import Resort
from .cost_calculator import airport_codes_for


def google_flights_url(resort: Resort, outbound_date: Optional[date] = None,
                       return_date: Optional[date] = None,
                       origin_airport: str = "TLV") -> Optional[str]:
    """
    None when the resort's spreadsheet airport field has no parseable
    IATA code -- a link to nowhere is worse than no link.
    """
    codes = airport_codes_for(resort)
    if not codes:
        return None
    destination = " or ".join(codes)
    query = f"Flights to {destination} from {origin_airport}"
    if outbound_date is not None and return_date is not None:
        query += f" on {outbound_date.isoformat()} through {return_date.isoformat()}"
    return f"https://www.google.com/travel/flights?q={quote(query)}"


def google_hotels_url(resort: Resort) -> str:
    query = f"Hotels in {resort.name}, {resort.country}"
    return f"https://www.google.com/travel/hotels?q={quote(query)}"
