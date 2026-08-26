"""
Phase 2 cost calculator: STATIC estimates only.

IMPORTANT — read this before trusting any number this module produces:

    Flight and accommodation costs below are rough placeholder estimates,
    NOT live prices. Per the roadmap (Section 9, Phase 4/5), these are the
    two pieces meant to be swapped for real API calls:
      - flight_cost_eur()          -> Amadeus / Kiwi self-service API
      - accommodation is closer to real (comes from the seed spreadsheet's
        researched rate-card estimates) but is still not live inventory
        -> Booking.com / Expedia Rapid API

    Ski pass, equipment, and food use simple linear/profile-based models
    that are reasonable approximations but also simplifications (real ski
    passes are not linear per-day, equipment/food vary a lot by shop and
    appetite). Treat every number from this module as "good enough to
    RANK resorts against each other", not "good enough to book against".

This separation is intentional and mirrors the architecture doc: nothing
here should silently become load-bearing for an actual purchase decision
without first being replaced by a real data source.
"""
import logging
import re
from datetime import timedelta
from typing import Optional

from ..models import Resort, UserPreferences, CostBreakdown

logger = logging.getLogger(__name__)

# --- Flight estimates: round-trip EUR per person from Tel Aviv, by country. ---
# PLACEHOLDER. Real numbers depend heavily on season/dates/airline and need
# a live flight search API (see module docstring). These are ballpark
# figures for a typical winter charter/scheduled fare via the relevant hub.
FLIGHT_ESTIMATE_EUR_BY_COUNTRY = {
    "France": 280,
    "Switzerland": 320,
    "Austria": 260,
    "Italy": 240,
    "Bulgaria": 160,
    "Andorra": 300,   # via Barcelona + onward transfer
    "Romania": 150,
    "Slovenia": 220,
    "Spain": 260,
}
DEFAULT_FLIGHT_ESTIMATE_EUR = 260

# --- Transfer cost model: round-trip shared-shuttle estimate, EUR per person. ---
# Calibrated loosely against the transfer-operator prices seen in resort
# research (e.g. Val Thorens/Geneva ~€50 one-way at ~160km). PLACEHOLDER —
# a real version should pull from transfer operator rate cards per resort.
TRANSFER_BASE_FEE_EUR = 15.0
TRANSFER_PER_KM_EUR = 0.22
TRANSFER_MIN_ROUND_TRIP_EUR = 50.0

# --- Ski pass: day-count multiplier curve, NOT a flat linear rate. ---
#
# Real multi-day passes give a per-day discount: short passes cost more
# per day than the naive (6-day price / 6) rate. Anchored on real Ski
# Arlberg 2025/26 main-season pricing, where a 1-day pass is EUR 81.50
# and a 6-day pass is EUR 450 -- so the 1-day rate is ~1.09x the naive
# per-day figure, not 1.0x. A flat linear model understated short trips.
#
# Multipliers apply to (6-day price / 6) * days, normalized so that
# day 6 == 1.0 exactly, which keeps every resort's sourced 6-day
# spreadsheet price perfectly intact.
#
# This is still an APPROXIMATION -- one resort's curve applied to all
# 30, and real curves differ per operator. It is closer than linear,
# not correct. Per-resort rate cards are the proper fix (see roadmap).
_PASS_DAY_MULTIPLIER = {
    1: 1.09, 2: 1.07, 3: 1.05, 4: 1.03, 5: 1.01,
    6: 1.00, 7: 0.99, 8: 0.98, 9: 0.97, 10: 0.96,
}
_PASS_LONG_TRIP_MULTIPLIER = 0.95  # 11+ days


# --- Season bands ---
#
# Ski pass (and, less sharply, accommodation) steps up in peak weeks
# rather than varying smoothly. Anchored on Ski Arlberg 2025/26, where
# a 6-day pass is EUR380 shoulder and EUR450 main season -- an 18%
# step. Our spreadsheet stores the SHOULDER figure, so the shoulder
# multiplier is 1.0 and peak scales UP from it. Getting this backwards
# would silently discount every peak trip.
#
# Bands are (month, day) ranges, resolved without a year so they work
# across the season boundary. APPROXIMATE and broadly European -- real
# operator calendars differ by a week or two and by country school
# holidays. This is closer than ignoring seasonality entirely, not
# precise. Per-resort published calendars are the eventual fix.
SEASON_PEAK = "peak"
SEASON_HIGH = "high"
SEASON_SHOULDER = "shoulder"

_SEASON_MULTIPLIER = {
    SEASON_PEAK: 1.18,      # Christmas/New Year, February half-term
    SEASON_HIGH: 1.10,      # mid-January to early March generally
    SEASON_SHOULDER: 1.00,  # early Dec, late March, April -- our stored baseline
}


def season_band(start_date) -> str:
    """
    Classifies a date into a season band. Returns SEASON_SHOULDER for
    None so that callers without a date get the unadjusted baseline.
    """
    if start_date is None:
        return SEASON_SHOULDER
    m, d = start_date.month, start_date.day

    # Christmas / New Year peak
    if (m == 12 and d >= 20) or (m == 1 and d <= 6):
        return SEASON_PEAK
    # February half-term peak (broadly; varies by country)
    if m == 2 and 8 <= d <= 28:
        return SEASON_PEAK
    # General high season
    if (m == 1 and d >= 7) or (m == 2) or (m == 3 and d <= 10):
        return SEASON_HIGH
    # Everything else in the season is shoulder
    return SEASON_SHOULDER


def season_band_multiplier(start_date) -> float:
    return _SEASON_MULTIPLIER[season_band(start_date)]


def _researched_6day_price(resort: Resort, start_date) -> Optional[float]:
    """
    The researched 6-day price for this resort at this date's season
    band, or None when the resort has no researched entry (see
    data/ski_pass_prices.py's UNPRICED_RESORTS for exactly which
    resorts and why).

    Three cases, in descending order of confidence:
      - BOTH bands published: return the band's own real price. No
        global multiplier involved at all -- this is the whole point of
        researching per-resort peaks, since real ratios run 1.06 to
        2.10 and no single constant can represent that.
      - ONE band published: scale from it with the global multiplier,
        which is what the old estimate did anyway -- but from a real
        anchor instead of a spreadsheet guess.
      - SEASON_HIGH between a published shoulder and peak: interpolate
        at the global multiplier's own relative position between its
        shoulder and peak values, so "high" stays properly bracketed by
        the two real figures rather than jumping straight to peak.
    """
    from ..data.ski_pass_prices import SKI_PASS_PRICES

    entry = SKI_PASS_PRICES.get(resort.name)
    if entry is None:
        return None

    band = season_band(start_date)
    shoulder, peak = entry.shoulder_eur, entry.peak_eur

    if shoulder is not None and peak is not None:
        if band == SEASON_PEAK:
            return peak
        if band == SEASON_SHOULDER:
            return shoulder
        # SEASON_HIGH: place it between the two REAL figures at the same
        # relative position the global multipliers put it (1.10 of the
        # way from 1.00 to 1.18, i.e. ~56%), rather than snapping to an
        # endpoint.
        span = _SEASON_MULTIPLIER[SEASON_PEAK] - _SEASON_MULTIPLIER[SEASON_SHOULDER]
        frac = (_SEASON_MULTIPLIER[SEASON_HIGH] - _SEASON_MULTIPLIER[SEASON_SHOULDER]) / span
        return shoulder + (peak - shoulder) * frac

    # Only one band researched -- scale from that anchor.
    if shoulder is not None:
        return shoulder * season_band_multiplier(start_date)
    return peak * (season_band_multiplier(start_date) / _SEASON_MULTIPLIER[SEASON_PEAK])


def ski_pass_cost(resort: Resort, days: int, start_date=None) -> float:
    """
    Ski pass cost, adjusted for both day-count and (when a date is
    given) SEASON BAND.

    Prefers the REAL researched 6-day price for this resort
    (data/ski_pass_prices.py, 29 of 37 resorts) over the spreadsheet's
    `ski_pass_6day_eur` estimate. This matters more than any other cost
    line: a production search on 2026-08-27 showed the ski pass was the
    single largest component of a trip total (EUR352 of EUR1,322,
    larger than the live flight price) and was pure guesswork.

    VERIFIED DATA ISSUE the season handling addresses: Ski Arlberg
    publishes EUR450 for a 6-day main-season pass and EUR380 for
    shoulder. The spreadsheet stores EUR380 -- the CHEAPER end -- so
    without a season adjustment every peak trip is understated ~18%,
    which matters enormously for date-range search, since that is
    precisely a comparison across dates. The researched table now
    carries each resort's OWN peak figure where published, because the
    real spread (1.06 at Soelden to 2.10 at Passo Tonale) is far too
    wide for one global constant.

    start_date=None preserves the old behaviour (shoulder/baseline, no
    adjustment), so callers without a date are unaffected.
    """
    six_day = _researched_6day_price(resort, start_date)
    if six_day is not None:
        # The researched figure already reflects this date's season
        # band, so only the day-count adjustment remains.
        per_day = six_day / 6.0
        multiplier = _PASS_DAY_MULTIPLIER.get(days, _PASS_LONG_TRIP_MULTIPLIER)
        return round(per_day * days * multiplier, 2)

    per_day = resort.ski_pass_6day_eur / 6.0
    multiplier = _PASS_DAY_MULTIPLIER.get(days, _PASS_LONG_TRIP_MULTIPLIER)
    base = per_day * days * multiplier
    return round(base * season_band_multiplier(start_date), 2)


def ski_pass_price_is_researched(resort: Resort) -> bool:
    """
    Whether this resort's ski pass cost comes from a real published
    price rather than the spreadsheet estimate -- so the UI can tag it
    honestly, exactly like flight_price_is_live/
    accommodation_price_is_live already do.
    """
    from ..data.ski_pass_prices import SKI_PASS_PRICES
    return resort.name in SKI_PASS_PRICES


# --- Equipment rental: flat per-day rate by tier. ---
EQUIPMENT_EUR_PER_DAY = {"standard": 22.0, "premium": 38.0}


# --- Food: per-day rate by profile, adjusted for a country cost tier. ---
# Matches the blueprint's "food should be estimated, not ignored" requirement.
WESTERN_EUROPE_COUNTRIES = {"France", "Switzerland", "Austria", "Italy", "Andorra"}
FOOD_EUR_PER_DAY_WESTERN = {"budget": 28, "normal": 48, "luxury": 85}
FOOD_EUR_PER_DAY_EASTERN = {"budget": 16, "normal": 30, "luxury": 55}

MISC_COST_RATE = 0.05  # 5% buffer on top of the rest, matching the original spec's "other costs" line


def flight_cost_eur(resort: Resort) -> float:
    return FLIGHT_ESTIMATE_EUR_BY_COUNTRY.get(resort.country, DEFAULT_FLIGHT_ESTIMATE_EUR)


# Extracts IATA codes from the spreadsheet's free-text airport column,
# e.g. "Geneva (GVA) / Chambery (CMF)" -> ["GVA", "CMF"]. Needed because
# the adapter's multi-airport search is the main reason SerpApi was
# chosen -- one request can cover every airport serving a resort.
_IATA_PATTERN = re.compile(r"\(([A-Z]{3})\)")


def airport_codes_for(resort: Resort) -> list:
    """Returns every IATA code named in the resort's airport field."""
    return _IATA_PATTERN.findall(resort.nearest_airport or "")


def live_flight_cost_eur(
    resort: Resort,
    outbound_date,
    return_date,
    origin_airport: str = "TLV",
    adults: int = 1,
    max_connections: int = 1,
):
    """
    Real per-person flight cost for a dated trip, or None if live data
    is unavailable for any reason.

    Returns None rather than raising, and never substitutes the static
    estimate itself -- that decision belongs to the caller, which must
    also decide whether to TELL THE USER the number is estimated. A
    silent fallback would reintroduce exactly the failure this project
    keeps guarding against: a plausible-looking number that isn't real.

    Callers should treat a None as "no live price", not "free".

    PROVIDER: adapters/google_flights_adapter.py (scrapes Google Flights
    directly, no API key/quota needed), not adapters/flight_adapter.py
    (SerpApi) -- switched because SerpApi's free-tier quota was the
    binding constraint on how much of this product's search could
    actually be live-priced (see api/rate_limit.py's live-pricing budget
    docstring). Both adapters share the exact same FlightOption/
    FlightSearchResult boundary type and public shape on purpose, so
    swapping back is this one import line, not a rewrite -- see
    google_flights_adapter.py's own module docstring for the tradeoffs
    (it's also a scraper, just of a different, keyless endpoint).
    """
    codes = airport_codes_for(resort)
    if not codes:
        return None
    try:
        from ..adapters import google_flights_adapter as flight_adapter
        result = flight_adapter.search_flights(
            origin_airport=origin_airport,
            destination_airports=codes,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            max_connections=max_connections,
        )
        return flight_adapter.cheapest_price_eur(result)
    except Exception:
        # Deliberately broad: a flight-provider outage should degrade
        # the trip estimate, not take down a whole search. The caller
        # sees None and falls back visibly. Logged (not raised) so the
        # actual reason is diagnosable server-side without changing
        # that user-facing contract.
        logger.exception("live_flight_cost_eur failed for %s", resort.name)
        return None


def live_flight_booking_url(
    resort: Resort,
    outbound_date,
    return_date,
    origin_airport: str = "TLV",
    adults: int = 1,
    max_connections: int = 1,
) -> Optional[str]:
    """
    A deep link to Google Flights' own booking page for the SAME
    cheapest flight live_flight_cost_eur() just priced, or None if
    unavailable for any reason -- see
    adapters/google_flights_adapter.booking_url()'s own docstring for
    what "unavailable" covers (missing booking ingredients, an expired
    selection token, a failed second fetch for round trip) and why
    every one of those degrades to None rather than a broken link.

    Re-runs search_flights() rather than taking a FlightOption in --
    deliberately, so callers don't have to thread one through. This
    costs no extra network call in the common case: search_flights()
    is response-cached (see adapters/response_cache.py), so calling it
    again with identical parameters right after live_flight_cost_eur()
    already did is a cache hit.
    """
    codes = airport_codes_for(resort)
    if not codes:
        return None
    try:
        from ..adapters import google_flights_adapter as flight_adapter
        result = flight_adapter.search_flights(
            origin_airport=origin_airport,
            destination_airports=codes,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            max_connections=max_connections,
        )
        if not result.options:
            return None
        cheapest = min(result.options, key=lambda o: o.price_eur)
        return flight_adapter.booking_url(cheapest, outbound_date, return_date)
    except Exception:
        # Same "degrade visibly, never break" contract as
        # live_flight_cost_eur -- see that function's docstring.
        return None


def live_accommodation_cost_eur_per_person(
    resort: Resort,
    checkin_date,
    nights: int,
    group_size: int,
    rooms_needed: int,
) -> Optional[float]:
    """
    Real per-person accommodation cost for a dated stay, or None if live
    data is unavailable for any reason. Same contract as
    live_flight_cost_eur: never raises, never substitutes the static
    estimate itself -- the caller decides how to degrade, and whether to
    tell the user the number is estimated.

    PROVIDER: adapters/google_hotels_adapter.py (hand-reverse-engineered
    Google Hotels scraping, no API key/quota needed -- see that
    module's docstring for exactly how and why), not
    adapters/serpapi_hotel_adapter.py -- switched for the same reason
    the flight provider was: SerpApi's free-tier quota was the binding
    constraint on how much of this product's search could actually be
    live-priced (see api/rate_limit.py's live-pricing budget docstring).
    serpapi_hotel_adapter.py is kept, unswapped, as the fallback the
    adapter pattern exists to make cheap; so is
    adapters/accommodation_adapter.py (the Booking.com one, still
    waiting on Managed Affiliate Partner approval).

    Neither this provider nor SerpApi has an "N rooms" request
    parameter, so the price returned is ONE room's cheapest nightly
    rate. This function multiplies by rooms_needed and nights itself,
    matching exactly how the static estimate
    (accommodation_cost_eur_per_person, below) turns a per-night,
    per-room rate into a per-person trip cost -- so the two are directly
    comparable/swappable.
    """
    try:
        cheapest = _cheapest_live_accommodation_option(resort, checkin_date, nights, rooms_needed)
        if cheapest is None:
            return None
        return round((cheapest.price_eur_per_night * nights * rooms_needed) / group_size, 2)
    except Exception:
        # Deliberately broad, matching live_flight_cost_eur: a hotel-
        # provider outage should degrade the trip estimate, not take
        # down a whole search. Logged (not raised) for the same reason.
        logger.exception("live_accommodation_cost_eur_per_person failed for %s", resort.name)
        return None


def _cheapest_live_accommodation_option(resort: Resort, checkin_date, nights: int, rooms_needed: int):
    """
    Shared lookup for the three live_accommodation_* functions below --
    ONE search_accommodation() call (response-cached, see
    adapters/response_cache.py -- calling this again with identical
    params right after another of these three already did is a cache
    hit, not a second live scrape), several uses. Returns the cheapest
    AccommodationOption, or None if the search found nothing.
    """
    from ..adapters import google_hotels_adapter
    result = google_hotels_adapter.search_accommodation(resort, checkin_date, nights, rooms_needed)
    if not result.options:
        return None
    return min(result.options, key=lambda o: o.price_eur_per_night)


def live_accommodation_property_name(resort: Resort, checkin_date, nights: int, rooms_needed: int) -> Optional[str]:
    """
    The real name of the cheapest live-priced accommodation option for
    this trip -- e.g. "Hôtel Marielle" -- or None if live pricing itself
    is unavailable.

    UNLIKE live_accommodation_booking_url() below, this needs NO
    GOOGLE_KG_API_KEY: the property name is already scraped as part of
    live pricing itself (adapters/google_hotels_adapter.py), not
    resolved through the separate Knowledge Graph lookup that specific
    link needs. So even with no key configured -- the accommodation
    link staying a generic resort-level search -- callers can still
    show a user which real property that price is actually for.
    """
    try:
        cheapest = _cheapest_live_accommodation_option(resort, checkin_date, nights, rooms_needed)
        return cheapest.property_name if cheapest else None
    except Exception:
        return None


def live_accommodation_booking_url(
    resort: Resort, checkin_date, nights: int, rooms_needed: int, area_place_name: str,
) -> Optional[str]:
    """
    A deep link to Google Hotels' page for the SAME cheapest property
    live_accommodation_cost_eur_per_person() just priced, or None if
    unavailable -- see
    adapters/google_hotels_adapter.specific_property_url()'s own
    docstring for what "unavailable" covers (no GOOGLE_KG_API_KEY
    configured, no Knowledge Graph match, a request failure) and why
    every one of those degrades to None, never a broken link. See
    live_accommodation_property_name() above for the (key-free) real
    property name alone, when this comes back None.

    UNVERIFIED end to end -- see specific_property_url()'s docstring.
    """
    try:
        cheapest = _cheapest_live_accommodation_option(resort, checkin_date, nights, rooms_needed)
        if cheapest is None:
            return None
        from ..adapters import google_hotels_adapter
        checkout_date = checkin_date + timedelta(days=nights)
        return google_hotels_adapter.specific_property_url(
            cheapest.property_name, area_place_name, checkin_date, checkout_date)
    except Exception:
        # Same "degrade visibly, never break" contract as every other
        # live_* function in this module.
        return None


def apply_live_accommodation_price(cost: CostBreakdown, live_price_per_person: float) -> CostBreakdown:
    """
    Replaces a CostBreakdown's static accommodation estimate with a real
    quote, preserving the misc-buffer's proportionality to the rest of
    the trip rather than leaving it sized for the old total. Returns a
    NEW CostBreakdown (does not mutate the input).

    Mirrors apply_live_flight_price exactly -- see that docstring.
    """
    delta = live_price_per_person - cost.accommodation_eur
    return CostBreakdown(
        flight_eur=cost.flight_eur,
        transfer_eur=cost.transfer_eur,
        accommodation_eur=live_price_per_person,
        ski_pass_eur=cost.ski_pass_eur,
        equipment_eur=cost.equipment_eur,
        food_eur=cost.food_eur,
        misc_eur=round(cost.misc_eur + delta * MISC_COST_RATE, 2),
        flight_price_is_live=cost.flight_price_is_live,
        accommodation_price_is_live=True,
    )


def apply_live_flight_price(cost: CostBreakdown, live_price: float) -> CostBreakdown:
    """
    Replaces a CostBreakdown's static flight estimate with a real quote,
    preserving the misc-buffer's proportionality to the rest of the trip
    rather than leaving it sized for the old total. Returns a NEW
    CostBreakdown (does not mutate the input) with flight_price_is_live=True.

    Shared by date_search.search_date_range() and scoring.rank_trips() so
    the "swap in a live price" arithmetic exists in exactly one place.
    """
    delta = live_price - cost.flight_eur
    return CostBreakdown(
        flight_eur=live_price,
        transfer_eur=cost.transfer_eur,
        accommodation_eur=cost.accommodation_eur,
        ski_pass_eur=cost.ski_pass_eur,
        equipment_eur=cost.equipment_eur,
        food_eur=cost.food_eur,
        misc_eur=round(cost.misc_eur + delta * MISC_COST_RATE, 2),
        flight_price_is_live=True,
        # Preserved explicitly, not left to the dataclass default -- if a
        # caller ever applies accommodation pricing BEFORE flight pricing
        # (neither engine module does today, but nothing enforces the
        # order), relying on the default would silently reset an
        # already-live accommodation flag back to False.
        accommodation_price_is_live=cost.accommodation_price_is_live,
    )


def transfer_cost_eur_per_person(resort: Resort, group_size: int,
                                 travel_date=None, airport_iata=None,
                                 preferred_modes=None) -> float:
    """
    Round-trip transfer cost per person.

    Prefers the CURATED TABLE (engine/transfers.py) -- real operator
    rates, correct per_person vs per_vehicle mechanics, availability by
    day of week, and mandatory modes like Zermatt's rail leg. Falls back
    to the old distance formula only for airport-resort pairs not yet
    researched (20 of 46 at time of writing).

    The fallback is visibly worse and known to be so: it charges a solo
    traveller EUR96 to Val Thorens where the real shared rate is EUR50,
    and its group_size ** 0.3 term matches no real pricing structure.
    It exists so partial data degrades rather than blocks, not because
    it is trustworthy.

    KNOWN GAP -- airport consistency. When airport_iata is None this
    returns the cheapest transfer across ALL airports serving the
    resort, which may not be the airport the flight actually lands at.
    Val Thorens is EUR85pp from Lyon but EUR100pp from Geneva; quoting
    EUR85 alongside a Geneva flight would describe a trip nobody is
    taking -- the same class of error as the transfer-time averaging bug
    fixed earlier. Properly closing this requires the flight search to
    report WHICH airport it chose and pass it through here. Until then,
    callers that know the arrival airport should pass airport_iata
    explicitly.
    """
    curated = _curated_transfer_cost(resort, group_size, travel_date,
                                     airport_iata, preferred_modes)
    if curated is not None:
        return curated
    return _formula_transfer_cost(resort, group_size)


def _curated_transfer_cost(resort: Resort, group_size: int, travel_date=None,
                           airport_iata=None, preferred_modes=None):
    """Returns the researched cost, or None when this pair isn't in the table."""
    try:
        from . import transfers as _transfers
    except ImportError:
        return None
    options = _transfers.get_transfer_options()
    if not options:
        return None
    return _transfers.transfer_cost_per_person(
        options, resort.name, group_size, airport_iata=airport_iata,
        travel_date=travel_date, preferred_modes=preferred_modes,
    )


def _formula_transfer_cost(resort: Resort, group_size: int) -> float:
    """Legacy distance-based estimate. See transfer_cost_eur_per_person."""
    round_trip_total = 2 * (TRANSFER_BASE_FEE_EUR + TRANSFER_PER_KM_EUR * resort.airport_distance_km)
    round_trip_total = max(round_trip_total, TRANSFER_MIN_ROUND_TRIP_EUR)
    return round(round_trip_total / max(1, group_size ** 0.3), 2)


def _live_transfer_quote(resort: Resort, pickup_date, pickup_time: str, group_size: int):
    """Shared lookup for the two live_transfer_* functions below -- one request, two uses."""
    from ..adapters import transfer_adapter
    result = transfer_adapter.search_transfer_options(
        resort, pickup_date, pickup_time, adults=group_size)
    return transfer_adapter.cheapest_option(result, group_size)


def live_transfer_cost_eur_per_person(
    resort: Resort, pickup_date, pickup_time: str, group_size: int,
) -> Optional[float]:
    """
    Real per-person transfer cost for a dated trip, or None if live
    data is unavailable for any reason -- same "never substitutes the
    static estimate itself" contract as live_flight_cost_eur.

    PROVIDER: adapters/transfer_adapter.py (Alps2Alps' public API, no
    key needed -- see that module's docstring). NOT wired into
    transfer_cost_eur_per_person() or rank_trips' scoring the way
    flight/accommodation live pricing is: that function runs for EVERY
    candidate resort during static scoring, not a capped top-N, so a
    live per-request call there would multiply live requests across an
    entire search -- the same class of problem code review caught for
    booking links (see api/routes/search.py's own
    attempt_booking_link gating). This function exists for DISPLAY
    only, called for a single already-chosen top result -- see
    api/routes/search.py's _transfer_search_url.

    pickup_time is a real gap: this app's flight search only tracks a
    DATE, not an arrival time, so callers pass an assumed time (see
    api/routes/search.py's own default) rather than the real flight's
    actual landing time. The transfer quote is real; the time it's
    quoted for is a guess.
    """
    try:
        quote = _live_transfer_quote(resort, pickup_date, pickup_time, group_size)
        if quote is None:
            return None
        return round(quote.price_eur / group_size, 2)
    except Exception:
        return None


def live_transfer_booking_url(
    resort: Resort, pickup_date, pickup_time: str, group_size: int,
) -> Optional[str]:
    """A booking link for the SAME transfer live_transfer_cost_eur_per_person() just priced, or None. See that function's docstring."""
    try:
        quote = _live_transfer_quote(resort, pickup_date, pickup_time, group_size)
        return quote.booking_url if quote else None
    except Exception:
        return None


def accommodation_cost_eur_per_person(resort: Resort, nights: int, group_size: int,
                                      rooms_needed: int, start_date=None) -> float:
    """
    Accommodation adjusted for season band when a date is supplied.

    Uses a SOFTER seasonal curve than the ski pass: peak accommodation
    does rise, but the spreadsheet's stored nightly rate is a mid-range
    average rather than a published shoulder-season rate card, so
    applying the full pass multiplier would overstate it. Half the pass
    swing is a deliberate compromise -- and an approximation, not a
    researched figure. Real accommodation seasonality should come from
    the accommodation adapter (Phase 5) once live inventory exists.
    """
    nightly = resort.accommodation_eur_per_night
    if start_date is not None:
        # Half the ski-pass season swing -- see docstring.
        nightly *= 1.0 + (season_band_multiplier(start_date) - 1.0) * 0.5
    total_room_cost = nightly * nights * rooms_needed
    return round(total_room_cost / group_size, 2)


def food_cost_eur(resort: Resort, days: int, profile: str) -> float:
    table = FOOD_EUR_PER_DAY_WESTERN if resort.country in WESTERN_EUROPE_COUNTRIES else FOOD_EUR_PER_DAY_EASTERN
    per_day = table.get(profile, table["normal"])
    return round(per_day * days, 2)


def compute_trip_cost(resort: Resort, prefs: UserPreferences, start_date=None) -> CostBreakdown:
    """
    Full per-person trip cost.

    start_date is OPTIONAL and defaults to None, which reproduces the
    previous date-agnostic behaviour exactly -- existing fixed-date
    callers are unaffected. When supplied, the date-varying components
    (ski pass season band, accommodation season band) are adjusted.

    Cost tiers, per the date-range search design:
      Tier 1, varies continuously by date: flight, accommodation
      Tier 2, varies coarsely by season band: ski pass, accommodation
      Tier 3, date-independent per resort: transfer, equipment, food
    Tier 3 costs are identical across every candidate date for a given
    resort, so they cancel out when comparing dates -- but they are NOT
    small and NOT uniform across resorts (researched round-trip
    transfers range EUR22 to EUR220), so each resort's real figure is
    always used. No global constant is ever assumed.
    """
    nights = prefs.nights          # derived: ski_days + 1, see UserPreferences.nights
    ski_days = prefs.ski_days

    flight = flight_cost_eur(resort)
    transfer = transfer_cost_eur_per_person(
        resort, prefs.group_size, travel_date=start_date,
        preferred_modes=getattr(prefs, "preferred_transfer_modes", None))
    accommodation = accommodation_cost_eur_per_person(
        resort, nights, prefs.group_size, prefs.rooms_needed, start_date)
    ski_pass = ski_pass_cost(resort, ski_days, start_date)
    equipment = EQUIPMENT_EUR_PER_DAY[prefs.equipment_tier] * ski_days
    food = food_cost_eur(resort, nights, prefs.food_profile)

    subtotal = flight + transfer + accommodation + ski_pass + equipment + food
    misc = round(subtotal * MISC_COST_RATE, 2)

    return CostBreakdown(
        flight_eur=flight,
        transfer_eur=transfer,
        accommodation_eur=accommodation,
        ski_pass_eur=ski_pass,
        equipment_eur=equipment,
        food_eur=food,
        misc_eur=misc,
        ski_pass_price_is_researched=ski_pass_price_is_researched(resort),
    )
