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
import dataclasses
import logging
import os
import re
from datetime import timedelta
from typing import List, Optional

from ..adapters.base import ProviderBlockedError
from .provider_status import note_provider_blocked
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
        if not result.options:
            # The scraper found NOTHING (null payload, unpublished
            # fares, or a fare-stripped page). Free fallback first.
            price = _kiwi_flight_fallback(
                resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)
            if price is not None:
                return price
            if getattr(result, "fares_suppressed", False):
                # Google LISTED flights but stripped every fare -- seen
                # live from the Cloud Run egress IP while the same query
                # priced fine from a residential one. Indistinguishable
                # from a hard block from the user's seat; record it so
                # the UI can explain the wall of EST.
                note_provider_blocked()
            # Paid fallback on EVERY empty outcome, not only the two
            # explicit block signals. Production evidence 2026-08-29
            # (St. Anton / Ischgl fully estimated while every provider
            # worked from a residential IP): from a datacenter egress,
            # "empty" and "blocked" are the same event wearing
            # different headers -- Kiwi's MCP refused the same IP too.
            # SerpApi calls from ITS OWN infrastructure, immune to our
            # IP's reputation, and is the whole reason the key exists.
            # Still None without a key -- the caller reports EST
            # honestly rather than inventing a number.
            price = _serpapi_flight_fallback(
                resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)
            if price is None:
                logger.warning("no flight price from ANY provider for %s (%s %s)",
                               resort.name, codes, outbound_date)
            return price
        return flight_adapter.cheapest_price_eur(result)
    except ProviderBlockedError:
        # Google served an anti-bot challenge. Retrying the same scraper
        # is pointless, but SerpApi is a real API hitting the same
        # underlying data and does not get CAPTCHA'd -- so if a key is
        # configured, use it rather than silently showing an estimate.
        # This is the ONLY situation where the paid path is worth
        # spending quota on: the free path is not merely slow, it is
        # unavailable.
        note_provider_blocked()
        price = _kiwi_flight_fallback(
            resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)
        if price is not None:
            return price
        price = _serpapi_flight_fallback(
            resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)
        if price is None:
            logger.warning("live flight pricing BLOCKED for %s and no fallback available",
                           resort.name)
        return price
    except Exception:
        # Deliberately broad: a flight-provider outage should degrade
        # the trip estimate, not take down a whole search. The caller
        # sees None and falls back visibly. Logged (not raised) so the
        # actual reason is diagnosable server-side without changing
        # that user-facing contract.
        logger.exception("live_flight_cost_eur failed for %s", resort.name)
        price = _kiwi_flight_fallback(
            resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)
        if price is not None:
            return price
        # Same full depth as the empty branch above: a scraper CRASH
        # from a datacenter IP is the same event as an empty page --
        # the paid API must get its chance here too (found because
        # this was the one branch that stopped at Kiwi).
        return _serpapi_flight_fallback(
            resort, codes, outbound_date, return_date, origin_airport, adults, max_connections)


def _kiwi_flight_fallback(resort, codes, outbound_date, return_date,
                          origin_airport, adults, max_connections):
    """
    The FREE fallback: Kiwi.com's official MCP search (see
    adapters/kiwi_mcp_adapter.py). Tried whenever the Google scraper
    finds nothing, BEFORE the metered SerpApi -- Kiwi's virtual-
    interline inventory often prices routes Google can't (TLV-LYS in
    January, measured 2026-08-28: Google zero, and this is exactly the
    user's ask: "make the kiwi a backup if our scraper doesn't find
    it"). Returns None on any failure, never raises.
    """
    try:
        from ..adapters import kiwi_mcp_adapter
        result = kiwi_mcp_adapter.search_flights(
            origin_airport=origin_airport,
            destination_airports=codes,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            max_connections=max_connections,
        )
        price = kiwi_mcp_adapter.cheapest_price_eur(result)
        if price is not None:
            logger.info("Kiwi MCP fallback rescued %s: EUR%.0f", resort.name, price)
        return price
    except Exception:
        logger.warning("Kiwi MCP fallback failed for %s", resort.name, exc_info=True)
        return None


def _serpapi_flight_fallback(resort, codes, outbound_date, return_date,
                             origin_airport, adults, max_connections):
    """
    Second-choice flight price via SerpApi, used ONLY when the free
    scraper is blocked. Returns None when no SERPAPI_API_KEY is
    configured, which is the normal state -- in that case the caller
    correctly reports "no live price" rather than inventing one.

    Both adapters share the same FlightSearchResult boundary type on
    purpose (see this function's caller), so this is a provider swap,
    not a parallel implementation.
    """
    if not os.environ.get("SERPAPI_API_KEY"):
        return None
    try:
        from ..adapters import flight_adapter as serpapi_adapter
        result = serpapi_adapter.search_flights(
            origin_airport=origin_airport,
            destination_airports=codes,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            max_connections=max_connections,
        )
        price = serpapi_adapter.cheapest_price_eur(result)
        if price is not None:
            logger.info("SerpApi fallback supplied a live flight price for %s", resort.name)
        return price
    except Exception:
        logger.exception("SerpApi flight fallback also failed for %s", resort.name)
        return None


def _kiwi_flight_result(resort, codes, outbound_date, return_date,
                        origin_airport, adults, max_connections):
    """
    The FULL Kiwi search result (not just a price), or None on any
    failure. Shares the response cache with _kiwi_flight_fallback --
    when that already rescued this trip's PRICE moments ago, this is a
    cache hit, not a second network call.
    """
    try:
        from ..adapters import kiwi_mcp_adapter
        return kiwi_mcp_adapter.search_flights(
            origin_airport=origin_airport,
            destination_airports=codes,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            max_connections=max_connections,
        )
    except Exception:
        logger.warning("Kiwi MCP result fetch failed for %s", resort.name, exc_info=True)
        return None


def live_flight_options(
    resort: Resort,
    outbound_date,
    return_date,
    origin_airport: str = "TLV",
    adults: int = 1,
    max_connections: int = 1,
):
    """
    The curated flight picks behind this result's flight price --
    engine/flight_picks.py's Cheapest / Best / Fastest selection,
    cheapest first, as FlightPicks (each carrying the roles it won).

    COSTS NOTHING EXTRA. live_flight_cost_eur() already ran exactly this
    search moments ago for the same (resort, dates, connections), so
    this is a response-cache hit, not a second scrape -- the same
    reasoning as live_accommodation_property_name() above. The adapter
    was always returning a full list of priced itineraries and we were
    keeping one number off it and discarding the rest.

    WHY SHOWING THEM MATTERS, not just "more data is nice": on a real
    TLV->GVA search the cheapest fare was EUR283 for a FOURTEEN AND A
    HALF HOUR journey, while EUR392 got there in six hours and a nonstop
    was 3h35. Quoting only the EUR283 makes the trip total look great
    and quietly assumes the user will spend two full days travelling.
    That is precisely the kind of technically-true-but-misleading number
    this project exists not to produce.

    Returns [] rather than raising, matching every other live_* helper.
    """
    codes = airport_codes_for(resort)
    if not codes:
        return []
    options = []
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
        options = result.options
    except Exception:
        logger.exception("live_flight_options failed for %s", resort.name)

    # Google empty or dead -> same Kiwi fallback the PRICE already
    # takes (live_flight_cost_eur), so the user never sees a live
    # number with no itineraries behind it. Kiwi options additionally
    # carry a real booking deep link each (booking_token holds the
    # itinerary's bookingUrl -- see kiwi_mcp_adapter._parse_itinerary).
    if not options:
        kiwi = _kiwi_flight_result(resort, codes, outbound_date, return_date,
                                   origin_airport, adults, max_connections)
        if kiwi is not None:
            options = kiwi.options

    # Third stage mirrors the price path exactly: SerpApi when both
    # free providers came back empty (see live_flight_cost_eur's
    # matching comment for the production evidence). Response-cached,
    # so when the price path already spent this lookup it's free here.
    if not options and os.environ.get("SERPAPI_API_KEY"):
        try:
            from ..adapters import flight_adapter as serpapi_adapter
            serp = serpapi_adapter.search_flights(
                origin_airport=origin_airport, destination_airports=codes,
                outbound_date=outbound_date, return_date=return_date,
                adults=adults, max_connections=max_connections,
            )
            options = serp.options
        except Exception:
            logger.warning("serpapi flight options fallback failed for %s",
                           resort.name, exc_info=True)

    # Selection lives in engine/flight_picks.py -- pure, offline-
    # tested maths. The earlier inline version here ("cheapest N-1
    # plus the fastest") still made the user read a list and do the
    # trade-off themselves; the picks module returns the three
    # answers every flight product already gives (Cheapest / Best /
    # Fastest), merged onto fewer options when one wins several.
    from .flight_picks import pick_flights
    return pick_flights(options)


def live_flight_booking_url(
    resort: Resort,
    outbound_date,
    return_date,
    origin_airport: str = "TLV",
    adults: int = 1,
    max_connections: int = 1,
    flight_numbers: Optional[List[str]] = None,
) -> Optional[str]:
    """
    A deep link to Google Flights' own booking page for the SAME
    cheapest flight live_flight_cost_eur() just priced -- or, when
    `flight_numbers` is given (e.g. ["A3 927", "A3 982"]), for that
    SPECIFIC itinerary instead. None if unavailable for any reason --
    see adapters/google_flights_adapter.booking_url()'s own docstring
    for what "unavailable" covers (missing booking ingredients, an
    expired selection token, a failed second fetch for round trip) and
    why every one of those degrades to None rather than a broken link.

    Matching by flight numbers, not by list index or price: the link
    is built at CLICK time, possibly long after the search that showed
    the option, and by then the freshly-fetched list may be ordered or
    priced differently. The flight designators are the only stable
    identity an itinerary has. No match -> None, never "the closest
    one" -- a booking page for a different flight than the one clicked
    would be worse than no link at all.

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
        if result.options:
            chosen = _match_flight_option(result.options, flight_numbers)
            if chosen is None:
                return None
            return flight_adapter.booking_url(chosen, outbound_date, return_date)
    except Exception:
        # Same "degrade visibly, never break" contract as
        # live_flight_cost_eur -- see that function's docstring. The
        # Kiwi fallback below still gets its chance.
        logger.warning("google booking-url path failed for %s", resort.name, exc_info=True)

    # Google had nothing (or died): the option shown to the user most
    # likely CAME from Kiwi (live_flight_options' own fallback), and
    # Kiwi itineraries carry their booking deep link right in the
    # search response -- no second fetch, no selection token.
    kiwi = _kiwi_flight_result(resort, codes, outbound_date, return_date,
                               origin_airport, adults, max_connections)
    if kiwi is None or not kiwi.options:
        return None
    chosen = _match_flight_option(kiwi.options, flight_numbers)
    if chosen is None:
        return None
    return _http_booking_link(chosen)


def _match_flight_option(options, flight_numbers):
    """The option these designators identify -- or the cheapest when
    none were given. No match -> None, never 'the closest one' (a
    booking page for a different flight than the one clicked is worse
    than no link at all)."""
    if not flight_numbers:
        return min(options, key=lambda o: o.price_eur)
    wanted = [n.strip().upper() for n in flight_numbers]
    return next(
        (o for o in options
         if [n.strip().upper() for n in (o.flight_numbers or [])] == wanted),
        None,
    )


def _http_booking_link(option) -> Optional[str]:
    """booking_token IF it already is a real link (Kiwi stores its
    bookingUrl there); None for opaque provider tokens (Google's
    protobuf selection token), which would render as a dead href."""
    token = option.booking_token or ""
    return token if token.startswith(("https://", "http://")) else None


def live_accommodation_cost_eur_per_person(
    resort: Resort,
    checkin_date,
    nights: int,
    group_size: int,
    rooms_needed: int,
    accommodation_filter=None,
    property_type: str = "HOTELS",
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
        # With no filter this is still the cheapest bed, unchanged; with
        # one, it is the cheapest bed that actually meets it -- and None
        # when nothing does, which the caller must NOT paper over with
        # the cheapest (see select_live_accommodation).
        _, per_person, _ = select_live_accommodation(
            resort, checkin_date, nights, rooms_needed, group_size, accommodation_filter,
            property_type)
        return per_person
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
    result = _live_accommodation_search(resort, checkin_date, nights, rooms_needed)
    if not result.options:
        return None
    return min(result.options, key=lambda o: o.price_eur_per_night)


def select_live_accommodation(resort: Resort, checkin_date, nights: int,
                              rooms_needed: int, group_size: int,
                              accommodation_filter=None,
                              property_type: str = "HOTELS"):
    """
    WHICH property this trip is priced on, given what the traveller will
    accept. Returns (option, per_person_eur, AccommodationChoiceReport).

    Cheapest-that-qualifies, never dearest-that-fits: a budget is a
    ceiling, not a target. With no filter this is exactly the old
    behaviour -- the cheapest bed -- so unfiltered searches are
    unchanged.

    UNKNOWN IS NOT A PASS. Google publishes no star class for some real
    inventory (verified live 2026-08-30: Hotel Altapura in Val Thorens
    came back unclassified beside four-star neighbours). Such a
    property cannot satisfy "4 stars or better", because we would be
    asserting something we do not know. It is set aside and COUNTED, so
    the caller can say so rather than quietly returning less.

    Returns (None, None, report) when nothing qualifies. The caller
    must not substitute the cheapest bed: that would tell the traveller
    their filter was met when it was not.
    """
    from ..models import AccommodationChoiceReport

    result = _live_accommodation_search(resort, checkin_date, nights, rooms_needed,
                                        accommodation_filter, group_size, property_type)
    options = result.options
    # ENRICH ONLY WHEN IT IS NEEDED. Pricing an unfiltered trip needs a
    # price and nothing else, and enrichment is a SECOND network call
    # (adapters/stays_adapter) whose failure would land in this
    # function's caller as None -- i.e. an ESTIMATED accommodation line
    # on a trip we could previously price live. No filter, no extra
    # dependency, no new way to lose a live price.
    if accommodation_filter is not None and not accommodation_filter.is_empty():
        try:
            options = _enrich_options(resort, checkin_date, nights, rooms_needed, options)
        except Exception:
            # Enrichment is a nice-to-have. Losing it costs us the star
            # classes; letting it raise would cost us the whole live
            # price and hand the traveller an ESTIMATE instead.
            logger.warning("accommodation enrichment failed for %s; "
                           "filtering on what we already have", resort.name, exc_info=True)
    if not options:
        return None, None, AccommodationChoiceReport()

    def per_person(option) -> float:
        # Same arithmetic as the unfiltered path and the static
        # estimate, so the three stay directly comparable.
        return round((option.price_eur_per_night * nights * rooms_needed) / group_size, 2)

    cheapest_any = min(per_person(o) for o in options)
    if accommodation_filter is None or accommodation_filter.is_empty():
        pick = min(options, key=lambda o: o.price_eur_per_night)
        return pick, per_person(pick), AccommodationChoiceReport(
            considered=len(options), matched=len(options),
            cheapest_available_eur_per_person=cheapest_any)

    f = accommodation_filter
    wanted = {a.upper() for a in (f.required_amenities or [])}
    matched, vetted, unrated = [], [], []
    for option in options:
        # The spend cap and the amenity list bind everywhere, including
        # the fallback: a budget is not a preference.
        if f.max_eur_per_person is not None and per_person(option) > f.max_eur_per_person:
            continue
        if wanted and not wanted.issubset({a.upper() for a in (option.amenities or [])}):
            continue

        # UNKNOWN is not FAILED. A property the provider never
        # classified is a gap in our data; a 3-star when 5 was asked
        # for is a known answer. Only the first is worth falling back
        # on, and only when nothing else qualifies at all.
        judged_unknown = False
        if f.min_star_class is not None:
            if option.star_class is None:
                judged_unknown = True
            elif option.star_class < f.min_star_class:
                continue
        if f.min_rating is not None:
            if option.rating is None:
                judged_unknown = True
            elif option.rating < f.min_rating:
                continue
        if f.min_review_count is not None:
            # A rating floor with no sample size behind it is thin: 4.7
            # from 34 guests and 4.4 from 1,401 are different claims
            # (both real, Val Thorens 2026-08-30).
            if option.review_count is None:
                judged_unknown = True
            elif option.review_count < f.min_review_count:
                continue
        if f.max_distance_to_lifts_km is not None:
            # Straight-line metres to the nearest lift, computed from
            # coordinates against OpenStreetMap -- unknown wherever the
            # provider gave us no coordinates, so it degrades exactly
            # like an unpublished star class.
            if option.distance_to_lifts_km is None:
                judged_unknown = True
            elif option.distance_to_lifts_km > f.max_distance_to_lifts_km:
                continue

        if not judged_unknown:
            matched.append(option)
        elif (f.min_star_class is not None and option.star_class is None
              and option.star_class_source == "provider_filter"):
            # Google narrowed the search to this class range but does
            # not publish the individual class here. Vetted, not
            # verified: better than an unknown, weaker than a published
            # class, and never printed as stars against the property.
            vetted.append(option)
        else:
            unrated.append(option)

    report = AccommodationChoiceReport(
        considered=len(options), matched=len(matched), provider_vetted=len(vetted),
        unrated_set_aside=len(unrated),
        cheapest_available_eur_per_person=cheapest_any)
    if matched:
        pick = min(matched, key=lambda o: o.price_eur_per_night)
        return pick, per_person(pick), report

    # Nothing verified. Rather than returning None -- which sends the
    # ranker back to the STATIC ESTIMATE (engine/scoring.py keeps the
    # estimate when live pricing is None), pricing the trip on a
    # generic guess -- offer the cheapest real place we did find, and
    # flag that its quality is unverified. Owner's rule, 2026-08-30:
    # "put them at the bottom, and if there is no option with rate,
    # put the options you find."
    if vetted:
        pick = min(vetted, key=lambda o: o.price_eur_per_night)
        return pick, per_person(pick), report
    if unrated:
        pick = min(unrated, key=lambda o: o.price_eur_per_night)
        return pick, per_person(pick), dataclasses.replace(report, fell_back_to_unrated=True)

    # LAST RESORT: everything was rated and everything sat below the
    # floor. Returning None here would be the regression the owner
    # named -- "previously we would find but now not" -- because the
    # ranker answers None with the static estimate, so a real EUR-priced
    # property would be replaced by a generic guess. Offer the cheapest
    # real place inside the hard constraints instead, clearly flagged
    # as not meeting the floor. Ranked after unrated on purpose:
    # "unknown" may yet be what you wanted; "below your floor" is known
    # not to be.
    below_floor = [o for o in options
                   if (f.max_eur_per_person is None or per_person(o) <= f.max_eur_per_person)
                   and (not wanted or wanted.issubset({a.upper() for a in (o.amenities or [])}))]
    if below_floor:
        pick = min(below_floor, key=lambda o: o.price_eur_per_night)
        return pick, per_person(pick), dataclasses.replace(report, fell_back_below_floor=True)
    return None, None, report


def _live_accommodation_search(resort: Resort, checkin_date, nights: int, rooms_needed: int,
                               accommodation_filter=None, group_size: int = 2,
                               property_type: str = "HOTELS"):
    """
    Our own Google Hotels scraper first, the free `stays` package
    second -- the accommodation twin of the flight chain's
    Google -> Kiwi fallback, added 2026-08-28 at the owner's request
    ("Make them a backup in a sequence you think is good").

    WHY THIS ORDER: our adapter is the one we control and can fix; it
    also needs no third-party dependency to be healthy. stays_adapter
    is someone else's reverse-engineering of the same Google endpoint,
    so it is the safety net rather than the primary -- but it carries
    RATINGS and COORDINATES our scraper cannot parse, so when it is
    the one that answers, the results are strictly richer (real
    distance to the nearest lift included).

    Both return AccommodationSearchResult, so callers see one shape.
    """
    from ..adapters import google_hotels_adapter
    # WITH A FILTER, `stays` LEADS. Our own scraper cannot filter and
    # cannot see a star class, so filtering its output means filtering
    # whatever a relevance search happened to return -- measured
    # 2026-08-30, that missed real four-star inventory in Kitzbuehel
    # entirely. `stays` asks Google to narrow the search instead.
    # Without a filter nothing changes: our scraper still leads.
    filtered = accommodation_filter is not None and not accommodation_filter.is_empty()
    if filtered or property_type != "HOTELS":
        try:
            from ..adapters import stays_adapter
            narrowed = stays_adapter.search_accommodation(
                resort, checkin_date, nights, rooms_needed,
                accommodation_filter=accommodation_filter, group_size=group_size,
                property_type=property_type)
            if narrowed.options:
                return narrowed
        except Exception:
            logger.warning("filtered accommodation search failed for %s", resort.name,
                           exc_info=True)

    try:
        result = google_hotels_adapter.search_accommodation(
            resort, checkin_date, nights, rooms_needed)
        if result.options:
            return result
    except Exception:
        logger.warning("primary accommodation search failed for %s", resort.name, exc_info=True)

    try:
        from ..adapters import stays_adapter
        backup = stays_adapter.search_accommodation(resort, checkin_date, nights, rooms_needed)
        if backup.options:
            logger.info("stays fallback rescued accommodation for %s (%d options)",
                        resort.name, len(backup.options))
            return backup
    except Exception:
        logger.warning("stays accommodation fallback failed for %s", resort.name, exc_info=True)

    # THIRD stage: SerpApi. The two scrapers above are both
    # reverse-engineerings of the SAME Google endpoint family, so from
    # a blocked datacenter IP they fail TOGETHER (measured 2026-08-29:
    # St. Anton and Ischgl estimated in production, both scrapers fine
    # from a residential IP). SerpApi is a real API calling from its
    # own infrastructure -- the one backup our egress reputation can't
    # touch. Key-gated: without SERPAPI_API_KEY this stage is silent
    # and the search degrades to the labeled estimate as before.
    if os.environ.get("SERPAPI_API_KEY"):
        try:
            from ..adapters import serpapi_hotel_adapter
            third = serpapi_hotel_adapter.search_accommodation(
                resort, checkin_date, nights, rooms_needed)
            if third.options:
                logger.info("serpapi fallback rescued accommodation for %s (%d options)",
                            resort.name, len(third.options))
                return third
        except Exception:
            logger.warning("serpapi accommodation fallback failed for %s",
                           resort.name, exc_info=True)

    from ..models import AccommodationSearchResult
    return AccommodationSearchResult(options=[])


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


def _enrich_options(resort: Resort, checkin_date, nights: int, rooms_needed: int, options):
    """
    Add RATING and DISTANCE-TO-LIFTS to options that lack them.

    THE OWNER'S PRIORITY, verbatim: "One of the most important info I
    want about the accommodation is distance from ski lifts. This is a
    ski vacation at the end of the day."

    Why this needs a second source at all: our own Google Hotels
    scraper (the primary, which usually answers) parses a name and a
    price and nothing else -- no rating, and crucially no coordinates,
    so there is nothing to measure a distance FROM. adapters/
    stays_adapter.py hits the same Google data through a different
    door and returns rating + lat/lng, which
    adapters/lift_distance.py turns into real metres against
    OpenStreetMap's lift map.

    Matched by normalized property NAME -- the only key both sources
    share. Unmatched properties simply keep their None fields: an
    honest gap, never a borrowed number from a different hotel. Both
    calls are response-cached, and lift geography is cached per resort
    for the process, so a repeat search costs nothing.
    """
    if not options:
        return options
    if all(o.rating is not None and o.distance_to_lifts_km is not None
           and o.star_class is not None for o in options):
        return options

    def norm(name: str) -> str:
        return "".join(ch for ch in (name or "").lower() if ch.isalnum())

    try:
        from ..adapters import stays_adapter
        enriched = stays_adapter.search_accommodation(
            resort, checkin_date, nights, rooms_needed)
    except Exception:
        logger.warning("accommodation enrichment unavailable for %s", resort.name, exc_info=True)
        return options

    by_name = {norm(o.property_name): o for o in enriched.options}
    if not by_name:
        return options

    out = []
    for option in options:
        match = by_name.get(norm(option.property_name))
        if match is None:
            out.append(option)
            continue
        # dataclasses.replace, not mutation -- these objects come
        # straight out of the response cache and are shared.
        out.append(dataclasses.replace(
            option,
            rating=option.rating if option.rating is not None else match.rating,
            distance_to_lifts_km=(option.distance_to_lifts_km
                                  if option.distance_to_lifts_km is not None
                                  else match.distance_to_lifts_km),
            # Star class, review count and amenities exist ONLY on this
            # side -- the primary scraper never sets them -- so an
            # unmatched property keeps None, an honest "we don't know".
            star_class=(option.star_class if option.star_class is not None
                        else match.star_class),
            review_count=(option.review_count if option.review_count is not None
                          else match.review_count),
            amenities=option.amenities if option.amenities else match.amenities,
        ))
    return out


def live_accommodation_options(
    resort: Resort,
    checkin_date,
    nights: int,
    rooms_needed: int,
    limit: int = 4,
    accommodation_filter=None,
    group_size: int = 2,
    property_type: str = "HOTELS",
):
    """
    The cheapest few real, named properties behind this result's
    accommodation price -- AccommodationOptions sorted cheapest first,
    at most `limit`.

    COSTS NOTHING EXTRA: the exact same search_accommodation() call
    live pricing already made moments ago (same resort/checkin/nights/
    rooms), so this is a response-cache hit -- the same reasoning as
    live_flight_options. The scrape always returned ~20 named, priced
    properties and we were showing ONE name off it.

    Cheapest-N and nothing cleverer, deliberately: unlike flights there
    is no second honestly-known axis to trade against -- the provider's
    rating and distance fields are not parsed (they come back None,
    verified live 2026-08-28), so a "best" pick here would be built on
    data we don't have. If those fields are ever parsed for real,
    revisit with a flight_picks-style selection.

    Returns [] rather than raising, matching every other live_* helper.
    """
    try:
        # Same filtered search the pricing used, so the list shown on
        # the card is drawn from the same inventory the trip was priced
        # against -- not a second, unfiltered set of properties.
        result = _live_accommodation_search(resort, checkin_date, nights, rooms_needed,
                                            accommodation_filter, group_size, property_type)
        options = _enrich_options(resort, checkin_date, nights, rooms_needed, result.options)
        by_price = sorted(options, key=lambda o: o.price_eur_per_night)

        # With a quality floor set, a place the provider never
        # classified sinks to the bottom rather than being deleted --
        # it cannot be judged, so it must not lead the list, but it is
        # still real inventory the traveller may want (owner's rule,
        # 2026-08-30). Without a floor there is nothing to rank
        # against, so pure price order stands, unchanged.
        if accommodation_filter is not None and not accommodation_filter.is_empty():
            def unknown_last(option) -> int:
                if accommodation_filter.min_star_class is not None and option.star_class is None:
                    return 1
                if accommodation_filter.min_rating is not None and option.rating is None:
                    return 1
                return 0
            by_price = sorted(by_price, key=unknown_last)
        return by_price[: max(1, limit)]
    except Exception:
        logger.exception("live_accommodation_options failed for %s", resort.name)
        return []


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
        # Carried forward explicitly for the same reason the flag above
        # is: this rebuilds the dataclass field by field, so anything
        # not named here silently reverts to its default.
        ski_pass_price_is_researched=cost.ski_pass_price_is_researched,
        transfer_price_is_live=cost.transfer_price_is_live,
    )


def _live_transfer_result(resort: Resort, pickup_date, pickup_time: str, group_size: int,
                          return_date=None, return_time=None, with_ski_bags: bool = True):
    """
    One live Alps2Alps quote for this route/date/party, or None.

    COST DISCIPLINE: exactly ONE provider request. The adapter's own
    two-step lookup (resolve airport, resolve resort, then quote) is
    skipped by handing it the FROZEN location codes
    (data/alps2alps_locations.py) -- which matters because their quote
    endpoint 429s after ~14 rapid calls with a >10 minute cooldown
    (measured 2026-08-28), so thirding the request count is what makes
    live transfer pricing affordable at all.

    Never raises: a rate limit or an unserved resort degrades to None
    and the caller keeps the curated figure, honestly labelled.
    """
    if pickup_date is None:
        return None
    try:
        from ..data.alps2alps_locations import ALPS2ALPS_LOCATIONS
        from ..adapters import transfer_adapter
    except ImportError:
        return None
    if resort.name not in ALPS2ALPS_LOCATIONS:
        return None
    try:
        # Round trip in ONE request -- both legs, priced together
        # (cheaper than two one-ways) and with the RETURN leg's resort
        # pickup computed by the operator from the return flight's
        # departure time. return_time is only ever sent when we truly
        # know it: return_date alone returns zero vehicles.
        return transfer_adapter.search_transfer_round_trip(
            resort=resort, pickup_date=pickup_date, pickup_time=pickup_time,
            adults=group_size,
            return_date=return_date if return_time else None,
            return_time=return_time,
            # One bag per traveller when they're bringing gear; zero
            # when they'll rent at the resort, which unlocks the
            # provider's cheaper small vehicles.
            ski_bags=group_size if with_ski_bags else 0,
        )
    except Exception:
        logger.info("live transfer quote unavailable for %s", resort.name, exc_info=True)
        return None


def live_transfer_cost_eur(resort: Resort, pickup_date, pickup_time: str,
                           group_size: int, return_date=None,
                           return_time=None, with_ski_bags: bool = True) -> Optional[float]:
    """
    Real per-PERSON airport transfer cost for this trip, or None.

    Alps2Alps prices a whole vehicle, and a ski trip needs the airport
    run in BOTH directions -- so the per-person figure is
    (vehicle price x 2) / group_size, matching exactly what
    engine/transfers.py's curated path computes. A vehicle that cannot
    seat the whole party is excluded rather than quoted as if it could.
    """
    legs = _live_transfer_result(resort, pickup_date, pickup_time, group_size,
                                 return_date, return_time, with_ski_bags)
    if legs is None:
        return None
    from ..adapters import transfer_adapter
    out = transfer_adapter.cheapest_price_eur(legs["outbound"], group_size)
    if out is None:
        return None
    back = (transfer_adapter.cheapest_price_eur(legs["return"], group_size)
            if legs.get("return") else None)
    # Both real legs when we have them; otherwise the outbound doubled
    # -- a documented approximation of the return, not a second quote
    # dressed up as one.
    vehicle_total = out + back if back is not None else out * 2
    return round(vehicle_total / group_size, 2)


def live_transfer_info(resort: Resort, pickup_date, pickup_time: str,
                       group_size: int, return_date=None,
                       return_time=None, with_ski_bags: bool = True) -> Optional[dict]:
    """
    Provenance for a LIVE transfer quote, shaped like
    transfer_source_for() so the API can substitute one for the other.
    source is "alps2alps_live" -- deliberately distinct from the frozen
    "alps2alps": both are real Alps2Alps prices, but only this one was
    quoted for the user's own date, party size and pickup time, and
    that is the difference the LIVE badge claims.

    price_eur stays the ONE-WAY VEHICLE price the operator quoted (what
    the booking page will show); the per-person trip figure is
    live_transfer_cost_eur's job.
    """
    legs = _live_transfer_result(resort, pickup_date, pickup_time, group_size,
                                 return_date, return_time, with_ski_bags)
    if legs is None:
        return None
    from ..adapters import transfer_adapter
    result = legs["outbound"]
    cheapest = transfer_adapter.cheapest_option(result, group_size)
    if cheapest is None:
        return None
    return {
        "source": "alps2alps_live",
        "price_eur": cheapest.price_eur,
        "duration_minutes": cheapest.duration_minutes or None,
        "distance_km": None,
        "vehicles_offered": len([o for o in result.options
                                 if o.max_passengers >= group_size]),
        "unavailable_reason": None,
        "vehicle_name": cheapest.vehicle_name,
        "pickup_time": pickup_time,
        # Clock time only ("11:10") off the operator's own computed
        # return pickup timestamp -- what the traveller has to be ready
        # for on departure day.
        "return_pickup_time": (legs.get("return_pickup") or "")[11:16] or None,
        # EVERY vehicle this API sells is a PRIVATE hire for the whole
        # party -- verified 2026-08-29 against their OpenAPI spec (no
        # shared/shuttle/per-seat concept anywhere in it) and against
        # live responses (only Standard/XL/Premium minivans, plus a
        # 3-seat car once ski bags are removed). Alps2Alps DOES sell
        # cheaper shared seats on their own website; the public API
        # does not expose them, so we say so rather than implying this
        # price is the cheapest way to travel.
        "is_private": True,
    }


def cheapest_public_transport(resort: Resort, travel_date, group_size: int) -> Optional[dict]:
    """
    The cheapest SCHEDULED coach/train to this resort from its arrival
    airport, per person -- Omio (adapters/omio_mcp_adapter.py), or None
    when they run no service or the lookup fails.

    WHY THIS EXISTS BESIDE the Alps2Alps quote rather than replacing
    it: they are different products. Alps2Alps is a private door-to-
    door vehicle on your schedule; this is a scheduled service from
    the airport coach bay to the resort bus station. On Geneva -> Val
    Thorens the gap was EUR423.50 vs EUR57.62 per person (measured
    2026-08-29), which is far too large to hide -- but the coach is
    not strictly better, so the user gets both and picks.

    Position ids come from the frozen table, so this is ONE provider
    call. Never raises.
    """
    if travel_date is None:
        return None
    try:
        from ..data.omio_positions import OMIO_POSITIONS
        from ..adapters import omio_mcp_adapter
    except ImportError:
        return None
    pos = OMIO_POSITIONS.get(resort.name)
    if not pos:
        return None
    quote = omio_mcp_adapter.cheapest_ground_transport(
        from_id=pos["from_id"], to_id=pos["to_id"],
        outbound_date=travel_date.isoformat(), adults=group_size)
    if quote is None:
        return None
    return {
        "price_eur_per_person": quote.price_eur_per_person,
        "mode": quote.mode,
        "options_count": quote.options_count,
        # The provider's OWN signed link, passed straight through --
        # never a URL we assemble. See GroundQuote.booking_url.
        "booking_url": quote.booking_url,
        "carrier": quote.carrier,
    }


def apply_live_transfer_price(cost: CostBreakdown, live_price: float) -> CostBreakdown:
    """
    Swaps the curated transfer figure for a real per-person quote,
    rescaling the misc buffer exactly as apply_live_flight_price does.
    Returns a NEW CostBreakdown with transfer_price_is_live=True.
    """
    delta = live_price - cost.transfer_eur
    return CostBreakdown(
        flight_eur=cost.flight_eur,
        transfer_eur=live_price,
        accommodation_eur=cost.accommodation_eur,
        ski_pass_eur=cost.ski_pass_eur,
        equipment_eur=cost.equipment_eur,
        food_eur=cost.food_eur,
        misc_eur=round(cost.misc_eur + delta * MISC_COST_RATE, 2),
        flight_price_is_live=cost.flight_price_is_live,
        accommodation_price_is_live=cost.accommodation_price_is_live,
        ski_pass_price_is_researched=cost.ski_pass_price_is_researched,
        transfer_price_is_live=True,
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
        ski_pass_price_is_researched=cost.ski_pass_price_is_researched,
        transfer_price_is_live=cost.transfer_price_is_live,
    )


def transfer_source_for(resort: Resort, airport_iata=None) -> dict:
    """
    What we actually know about this resort's airport transfer, and
    where it came from -- the honest provenance the owner asked for
    ("Make it always show real data... If for some resort it doesn't
    work I want to know exactly why").

    Returns a dict with:
      source            "alps2alps" | "drive_time_only" | "estimated"
      price_eur         real one-way Alps2Alps price, or None
      duration_minutes  real driving time (Google Maps) where known
      distance_km       real road distance where known
      unavailable_reason  for anything short of a real price, the exact
                        reason -- which airport/resort names Alps2Alps
                        did not recognise, or that they offered no
                        vehicle. Never a shrug.

    Both datasets are frozen (data/transfer_quotes.py,
    data/transfer_drive_times.py) because Alps2Alps allows ~14 calls
    before a 429 with a >10 minute cooldown -- measured -- so live
    per-search quoting is arithmetically impossible for a 12-result
    page. See those modules' own docstrings.
    """
    import re

    from ..data.transfer_drive_times import DRIVE_TIMES
    from ..data.transfer_quotes import TRANSFER_QUOTES, UNQUOTED_ROUTES

    codes = re.findall(r"\(([A-Z]{3})\)", resort.nearest_airport or "")
    code = airport_iata or (codes[0] if codes else None)
    drive = DRIVE_TIMES.get(f"{resort.name}|{code}") if code else None

    quote = TRANSFER_QUOTES.get(resort.name)
    if quote:
        return {
            "source": "alps2alps",
            "price_eur": quote["price_eur"],
            "duration_minutes": quote.get("duration_minutes") or (drive or {}).get("minutes"),
            "distance_km": (drive or {}).get("km"),
            "vehicles_offered": quote.get("vehicles_offered"),
            "unavailable_reason": None,
        }

    reason = UNQUOTED_ROUTES.get(
        resort.name, "No Alps2Alps quote was attempted for this resort.")
    return {
        "source": "drive_time_only" if drive else "estimated",
        "price_eur": None,
        "duration_minutes": (drive or {}).get("minutes"),
        "distance_km": (drive or {}).get("km"),
        "vehicles_offered": None,
        "unavailable_reason": reason,
    }


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


def all_transfer_options(resort: Resort, start_date, end_date, group_size: int,
                         pickup_time: str, return_time=None,
                         with_ski_bags: bool = True,
                         include_private: bool = True) -> list:
    """
    Every real airport-to-resort option we can price, as ONE ranked
    list (engine/transfer_options.TransferOption) -- private hire and
    scheduled coach/train together, all per person.

    This is the transfer equivalent of live_flight_options(): the card
    shows a list the traveller chooses from, and the CHEAPEST entry
    drives cost.transfer_eur. Previously the private quote drove the
    price and the cheap coach was a footnote, which the owner rightly
    called out.

    Never raises. Each provider degrades independently: a resort Omio
    does not route (their discovery index genuinely lacks many Alpine
    routes -- measured: 9 of 32 covered) still gets its private
    options, and vice versa.
    """
    from .transfer_options import TransferOption, rank_transfer_options

    options: list = []

    # --- private hire (round trip, whole vehicle) ---
    # GATED, unlike the scheduled half: Alps2Alps' quote endpoint 429s
    # after ~14 rapid calls with a >10 minute cooldown that would hit
    # every user, so only the top rows get private quotes. Omio has no
    # such limit, which is why it runs for EVERY row -- see the caller.
    legs = (_live_transfer_result(resort, start_date, pickup_time, group_size,
                                  end_date, return_time, with_ski_bags)
            if include_private else None)
    if legs and include_private:
        try:
            from ..adapters import transfer_adapter
            outbound = legs["outbound"]
            back = legs.get("return")
            for quote in outbound.options:
                if quote.max_passengers < group_size:
                    continue
                # Both real legs when the provider gave us one,
                # otherwise the outbound doubled -- the documented
                # approximation, same as live_transfer_cost_eur.
                cheapest_back = (transfer_adapter.cheapest_price_eur(back, group_size)
                                 if back else None)
                vehicle_total = (quote.price_eur + cheapest_back
                                 if cheapest_back is not None else quote.price_eur * 2)
                options.append(TransferOption(
                    resort_name=resort.name,
                    kind="private", mode="minivan",
                    price_eur_per_person=round(vehicle_total / group_size, 2),
                    duration_minutes=int(quote.duration_minutes) if quote.duration_minutes else None,
                    carrier=quote.vehicle_name,
                    booking_url=quote.booking_url,
                    is_round_trip=True,
                ))
        except Exception:
            logger.warning("private transfer options failed for %s", resort.name,
                           exc_info=True)

    # --- scheduled coach / train (seats) ---
    try:
        from ..data.omio_positions import OMIO_POSITIONS
        from ..adapters import omio_mcp_adapter
        pos = OMIO_POSITIONS.get(resort.name)
        if pos:
            found = omio_mcp_adapter.search_ground_transport(
                from_id=pos["from_id"], to_id=pos["to_id"],
                outbound_date=start_date.isoformat(), adults=group_size,
                inbound_date=end_date.isoformat() if end_date else None)
            if found:
                # Pair each outbound with the cheapest return of the
                # same mode so the quoted price is a WHOLE trip, like
                # the private option -- comparing a one-way seat with a
                # round-trip van would flatter the seat.
                inbound = found.get("inbound") or []
                for j in found.get("outbound") or []:
                    same_mode_back = [b for b in inbound if b.mode == j.mode]
                    back_price = (min(b.price_eur_per_person for b in same_mode_back)
                                  if same_mode_back else None)
                    total = (j.price_eur_per_person + back_price
                             if back_price is not None else j.price_eur_per_person)
                    options.append(TransferOption(
                        resort_name=resort.name,
                        kind="scheduled", mode=j.mode,
                        price_eur_per_person=round(total, 2),
                        duration_minutes=j.duration_minutes,
                        carrier=j.carrier, departure=j.departure,
                        booking_url=j.booking_url or found.get("link"),
                        is_round_trip=back_price is not None,
                    ))
    except Exception:
        logger.warning("scheduled transfer options failed for %s", resort.name,
                       exc_info=True)

    # --- indicative route discovery (covers EVERY resort) ---
    # Runs only when the dated providers found nothing bookable: it is
    # a price RANGE with no date, so it answers "how would I even get
    # there" rather than "what will I pay on the 16th". Without it,
    # 30 of 39 resorts showed no ground option at all.
    if not any(o.kind == "scheduled" for o in options):
        try:
            from ..adapters import rome2rio_adapter
            from ..adapters.transfer_adapter import _airport_city_name
            airport = _airport_city_name(resort.nearest_airport)
            origin = (f"{airport} Airport" if "airport" not in airport.lower() else airport)
            for route in rome2rio_adapter.search_routes(origin, resort.name)[:3]:
                options.append(TransferOption(
                    resort_name=resort.name,
                    kind="scheduled", mode=_mode_from_route_name(route.name),
                    price_eur_per_person=route.price_low_eur,
                    price_high_eur_per_person=route.price_high_eur,
                    duration_minutes=route.duration_minutes,
                    carrier=route.name,
                    is_indicative=True,
                    # The provider's own results page for this pair --
                    # verified to load, never hand-built.
                    booking_url=route.booking_url,
                ))
        except Exception:
            logger.warning("rome2rio route discovery failed for %s", resort.name,
                           exc_info=True)

    return rank_transfer_options(options)


def _mode_from_route_name(name: str) -> str:
    """Rome2Rio names a route by its legs ("Bus, train", "Shuttle").
    Map to the mode the UI shows an icon and label for; the full name
    is kept as the carrier line so nothing is lost."""
    lowered = (name or "").lower()
    for needle, mode in (("train", "train"), ("tram", "train"), ("ferry", "ferry"),
                         ("shuttle", "bus"), ("bus", "bus"), ("taxi", "minivan"),
                         ("transfer", "minivan")):
        if needle in lowered:
            return mode
    return "bus"
