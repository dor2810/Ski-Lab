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
its own docstring. equipment_search_url() and ski_pass_search_url()
below are the same "always a real, working link" idea applied to the
two cost lines that have never had ANY link before -- see each one's
own docstring for what's verified about them.
"""
from datetime import date
from typing import Optional
from urllib.parse import urlencode

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

ALPS2ALPS_QUICK_CHECKOUT_URL = "https://booking.alps2alps.com/booking/quick-checkout"


def alps2alps_deeplink(resort_name: str, pickup_date, pickup_time: str,
                       adults: int, return_date=None,
                       return_time: str = None,
                       ski_bags: Optional[int] = None) -> Optional[str]:
    """
    A REAL, prefilled Alps2Alps booking page for this exact transfer --
    route, date, party size, return leg -- built OFFLINE from the
    frozen location codes (data/alps2alps_locations.py), zero API
    calls at search time.

    HOW (verified live 2026-08-29): the per-vehicle booking_url the
    /transfer-options API returns is a plain parameterized link --
    /booking/quick-checkout?from=<airport-code>&to=<resort-code>&
    date=...&time=...&adults=...[&return_date=...&return_time=...] --
    and WITHOUT a vehicle id it lands inside the live funnel (step-3)
    with the actual route, dates and party loaded, real prices on
    screen (Sofia airport -> Bansko confirmed, return leg echoed).
    Only the codes are provider-specific, and codes are stable place
    ids -- exactly the fetch-once-ship-as-data pattern of
    transfer_drive_times.py, and the only shape that survives their
    rate limits (~14 rapid quote calls then a 429 with a >10min
    cooldown, measured 2026-08-28).

    None when this resort has no frozen code pair (see UNRESOLVED in
    the data file for the exact reason per resort) or no date --
    callers fall back to the generic booking form, never a dead link.
    """
    if pickup_date is None:
        return None
    try:
        from ..data.alps2alps_locations import ALPS2ALPS_LOCATIONS
    except ImportError:
        return None
    loc = ALPS2ALPS_LOCATIONS.get(resort_name)
    if not loc:
        return None
    params = {
        "from": loc["airport_code"], "to": loc["resort_code"],
        "date": pickup_date.isoformat(), "time": pickup_time,
        "adults": adults, "currency": "EUR",
    }
    if return_date is not None:
        params["return_date"] = return_date.isoformat()
        params["return_time"] = return_time or pickup_time
    if ski_bags is not None:
        # The booking page must open on the SAME basket we priced --
        # otherwise the funnel re-applies its seasonal default and the
        # user meets a different price than the card showed.
        params["ski_bags"] = ski_bags
        params["ski"] = 1 if ski_bags > 0 else 0
    return f"{ALPS2ALPS_QUICK_CHECKOUT_URL}?{urlencode(params)}"


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


# Skiset's own front door -- confirmed live, 200. Used ONLY as the
# fallback for a resort not in data/equipment_rental_links.py's curated
# table below (e.g. one added to the spreadsheet later). An earlier
# pass wrongly assumed Skiset's resort picker only resolves through an
# internal autocomplete ID with no guessable URL slug -- real per-
# resort research (see the curated table's own docstring) found that
# was based on testing the wrong Skiset domain and a couple of bad slug
# guesses; skiset.co.uk/ski-resort/{slug} and skiset.us/ski-resort/
# {slug} both resolve directly for most resorts, hence the curated
# table now existing instead of this bare homepage being the norm.
SKISET_URL = "https://www.skiset.co.uk/"

# Countries where Skiset's front door is at least a relevant fallback
# (Skiset itself has real, verified coverage there -- see the curated
# table). This app also has resorts in Bulgaria, Romania, and Slovenia,
# where a Skiset link would be real but pointless -- a Google search
# for those instead, same fallback shape as ski_pass_search_url()
# below. This only matters for a resort missing from the curated
# table; every resort currently in this app's data has a real entry
# there and never reaches this fallback.
_SKISET_COVERED_COUNTRIES = frozenset({
    "France", "Austria", "Switzerland", "Italy", "Andorra", "Spain",
})


def equipment_search_url(resort: Resort) -> str:
    """
    Where to rent ski/snowboard equipment for this resort -- a real,
    resort-scoped rental page (Skiset, INTERSPORT Rent, Snowit, or the
    resort's own official rental page, whichever was actually found and
    verified) for every one of the 37 resorts in this project's data,
    from data/equipment_rental_links.py. See that module's own
    docstring for exactly how each entry was researched and live-
    verified.

    Falls back to Skiset's bare front door (when Skiset has real
    coverage in the resort's country) or a plain Google search
    otherwise, for any resort NOT in that table -- not resort-
    guaranteed, same tier as ski_pass_search_url()'s own fallback.
    """
    from ..data.equipment_rental_links import EQUIPMENT_RENTAL_URLS
    curated = EQUIPMENT_RENTAL_URLS.get(resort.name)
    if curated:
        return curated
    if resort.country in _SKISET_COVERED_COUNTRIES:
        return SKISET_URL
    from urllib.parse import quote
    query = f"ski equipment rental {resort.name}, {resort.country}"
    return f"https://www.google.com/search?q={quote(query)}"


def ski_pass_search_url(resort: Resort) -> str:
    """
    Where to buy this resort's lift pass -- the resort's own official
    ticketing page (or a verified authorized reseller where the
    official site itself blocks automated verification) for every one
    of the 37 resorts in this project's data, from data/
    ski_pass_links.py. See that module's own docstring for exactly how
    each entry was researched and live-verified (curl + content check,
    not a trusted search snippet), and its two documented caveats
    (Bardonecchia, Val Gardena).

    Falls back to a plain, resort-named Google search for any resort
    NOT in that table (e.g. one added to the spreadsheet later, before
    the table is extended to cover it) -- unlike the curated case this
    is not resort-guaranteed, same tier as google_flights_url's own
    dateless fallback, but still real and working.
    """
    from ..data.ski_pass_links import SKI_PASS_URLS
    curated = SKI_PASS_URLS.get(resort.name)
    if curated:
        return curated
    from urllib.parse import quote
    query = f"buy {resort.name} ski pass lift ticket"
    return f"https://www.google.com/search?q={quote(query)}"
