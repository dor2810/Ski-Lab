"""
Accommodation search via the `stays` package -- the FREE backup behind
our own Google Hotels scraper, and the source of the quality data that
scraper cannot give us.

TWO JOBS, both requested by the project owner on 2026-08-28:

1. BACKUP. google_hotels_adapter.py is a hand-reverse-engineered
   scraper; when it returns nothing, this answers instead. Same
   fallback shape as kiwi_mcp_adapter for flights.

2. ENRICHMENT, which is arguably the bigger win. Our own scraper
   parses a name and a nightly price -- rating and distance_to_lifts_km
   have sat unpopulated on AccommodationOption since day one, which is
   exactly why the Places-to-stay list can only rank on price and
   deliberately shows no "best" pick. `stays` returns overall_rating,
   review_count, star_class, amenities AND lat/lng -- and the
   coordinates unlock the thing the owner cares most about: real
   distance to the nearest ski lift (adapters/lift_distance.py).

WHAT IT IS: github.com/him229/stays, a maintained pip package that
talks to Google's internal batchexecute RPC directly -- no HTML
scraping, no headless browser. Verified live 2026-08-28 against Val
Thorens: 8 properties with prices EUR175-685, ratings 4.2-4.7, review
counts up to 1,400, star classes, and coordinates good enough to place
Club Med 45m from the Cairn lift.

HONEST RISK, stated plainly per this project's rules: this is still
somebody else's reverse-engineering of an undocumented Google
endpoint -- the same fragility class as our own adapter, just
maintained by someone else. That is precisely why it is the BACKUP and
the enrichment layer rather than the primary, and why every field it
supplies is optional downstream.
"""
import datetime
import logging
from typing import List, Optional

from ..models import AccommodationOption, AccommodationSearchResult
from .base import AdapterError
from .response_cache import get_cache

logger = logging.getLogger(__name__)

_CURRENCY = "EUR"
# Google surfaces ~15-18 properties; more than this is noise for a
# results card that shows four.
_MAX_RESULTS = 12


def _cache_key(*parts) -> str:
    return "stays:" + "|".join(str(p) for p in parts)


def _search_raw(query: str, check_in: datetime.date, check_out: datetime.date,
                adults: int) -> dict:
    """The one call into the third-party package. Isolated so tests can
    stub the network in a single place."""
    import stays

    return stays.search_hotels(
        query,
        check_in=check_in.isoformat(),
        check_out=check_out.isoformat(),
        adults=adults,
        currency=_CURRENCY,
        max_results=_MAX_RESULTS,
    )


def _parse_hotel(entry: dict, nights: int, lift_points=None) -> Optional[AccommodationOption]:
    """One Google Hotels property -> AccommodationOption, or None for
    anything unusable. display_price is the TOTAL for the stay in the
    requested currency (verified against Val Thorens: EUR175-685 for a
    6-night search), so it is divided back to a nightly rate to match
    the per-night contract every other accommodation adapter uses."""
    try:
        name = entry.get("name")
        raw_price = entry.get("display_price")
        if not name or raw_price in (None, ""):
            return None
        total = float(str(raw_price).replace(",", "").replace("EUR", "").strip())
        if total <= 0 or nights <= 0:
            return None

        distance = None
        if lift_points:
            from .lift_distance import nearest_lift_km
            distance = nearest_lift_km(entry.get("lat"), entry.get("lng"), lift_points)

        rating = entry.get("overall_rating")
        return AccommodationOption(
            price_eur_per_night=round(total / nights, 2),
            property_name=name,
            rating=float(rating) if rating is not None else None,
            distance_to_lifts_km=distance,
        )
    except (TypeError, ValueError):
        return None


def search_accommodation(resort, checkin_date: datetime.date, nights: int,
                         rooms_needed: int = 1, use_cache: bool = True,
                         with_lift_distance: bool = True) -> AccommodationSearchResult:
    """Same boundary contract as google_hotels_adapter.search_accommodation:
    AccommodationOption list out, one bad entry dropped rather than
    fatal, AdapterError only on total failure, response-cached.

    with_lift_distance=False skips the (cached, once-per-resort)
    Overpass lookup -- used by callers that only need a price."""
    checkout_date = checkin_date + datetime.timedelta(days=nights)
    key = _cache_key(resort.name, checkin_date, nights, rooms_needed, with_lift_distance)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return AccommodationSearchResult(options=cached.options, from_cache=True)

    query = f"{resort.name}, {resort.country}"
    try:
        payload = _search_raw(query, checkin_date, checkout_date, adults=max(1, rooms_needed) * 2)
    except Exception as exc:
        raise AdapterError(f"stays search failed for {resort.name}: {exc}") from exc

    lift_points = None
    if with_lift_distance:
        from .lift_distance import lift_points_for_resort
        lift_points = lift_points_for_resort(resort)

    options: List[AccommodationOption] = []
    for entry in payload.get("hotels", []) or []:
        parsed = _parse_hotel(entry, nights, lift_points)
        if parsed is not None:
            options.append(parsed)

    result = AccommodationSearchResult(options=options)
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur_per_night(result: AccommodationSearchResult) -> Optional[float]:
    if not result.options:
        return None
    return min(o.price_eur_per_night for o in result.options)
