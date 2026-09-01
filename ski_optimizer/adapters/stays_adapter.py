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
Thorens: 8 properties with NIGHTLY rates EUR175-685, ratings 4.2-4.7, review
counts up to 1,400, star classes, and coordinates good enough to place
Club Med 45m from the Cairn lift.

HONEST RISK, stated plainly per this project's rules: this is still
somebody else's reverse-engineering of an undocumented Google
endpoint -- the same fragility class as our own adapter, just
maintained by someone else. That is precisely why it is the BACKUP and
the enrichment layer rather than the primary, and why every field it
supplies is optional downstream.
"""
import dataclasses
import datetime
import logging
import math
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


# stays' min_guest_rating only accepts these three (Field(ge=3.5,
# le=4.5) in its signature). We snap DOWN to one of them so the
# provider never filters harder than asked; our own check then enforces
# the exact figure the traveller chose.
_PROVIDER_RATING_STEPS = (3.5, 4.0, 4.5)


def _provider_filters(accommodation_filter, nights: int, rooms_needed: int,
                      group_size: int) -> dict:
    """
    The traveller's constraints translated into what stays.search_hotels
    accepts, so GOOGLE narrows the inventory instead of us narrowing
    what a relevance search happened to send.

    WHY IT MATTERS, measured 2026-08-30: a plain Kitzbuehel search
    returns 12 properties, none of which publish a star class. Asking
    for hotel_class=[4,5] returns a DIFFERENT twelve. Filtering
    locally could only ever pick from the first list, so a "4 stars or
    better" search was missing real four-star inventory rather than
    finding none.

    Everything here only ever WIDENS relative to the traveller's ask
    (round the price ceiling up, snap the rating floor down): the exact
    test still runs locally in
    engine/cost_calculator.select_live_accommodation, so a loose
    provider filter costs nothing while a tight one would silently drop
    valid beds.
    """
    if accommodation_filter is None or accommodation_filter.is_empty():
        return {}
    f = accommodation_filter
    out: dict = {}
    if f.min_star_class is not None:
        out["hotel_class"] = list(range(int(f.min_star_class), 6))
    if f.max_eur_per_person is not None and nights > 0 and rooms_needed > 0:
        # Our cap is per person for the whole stay; theirs is a nightly
        # room rate. Ceil, so rounding never excludes an affordable bed.
        per_night = (f.max_eur_per_person * max(1, group_size)) / (nights * rooms_needed)
        out["price_max"] = int(math.ceil(per_night))
    if f.min_rating is not None:
        allowed = [v for v in _PROVIDER_RATING_STEPS if v <= f.min_rating]
        if allowed:
            out["min_guest_rating"] = allowed[-1]
    if f.required_amenities:
        # Dormant on purpose -- nothing in the product sets this. See
        # _parse_hotel for the measurements showing the provider's
        # amenity filter returns 18 of 20 whatever you ask for.
        out["amenities"] = [a.upper() for a in f.required_amenities]
    return out


def _search_raw(query: str, check_in: datetime.date, check_out: datetime.date,
                adults: int, **filters) -> dict:
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
        **filters,
    )


def _parse_hotel(entry: dict, nights: int, lift_points=None) -> Optional[AccommodationOption]:
    """One Google Hotels property -> AccommodationOption, or None for
    anything unusable.

    display_price IS THE NIGHTLY RATE, used as-is. It was previously
    divided by `nights` on the belief that it was the whole-stay total,
    which understated every stays-sourced price by a factor of the trip
    length. Corrected 2026-08-30 on two independent pieces of evidence:

      1. It barely moves with trip length. Same Kitzbuehel property,
         same check-in: 6 nights and 3 nights both return 230; a stay
         total would double.
      2. It matches our own independent scraper's per-night figure
         EXACTLY across nine properties -- 198/198, 206/206, 230/230,
         287/287, 304/304, 461/461, 587/587, 598/598 -- while a sixth
         of it would have priced a Kitzbuehel hotel at EUR33 a night in
         January.

    The bug mattered little while this adapter was only a fallback; it
    became load-bearing the moment filtered searches started coming
    here first."""
    try:
        name = entry.get("name")
        raw_price = entry.get("display_price")
        if not name or raw_price in (None, ""):
            return None
        per_night = float(str(raw_price).replace(",", "").replace("EUR", "").strip())
        if per_night <= 0 or nights <= 0:
            return None

        distance = None
        if lift_points:
            from .lift_distance import nearest_lift_km
            distance = nearest_lift_km(entry.get("lat"), entry.get("lng"), lift_points)

        rating = entry.get("overall_rating")

        # Verified live 2026-08-30 against Val Thorens: every property
        # carries overall_rating/review_count/amenities, and MOST carry
        # star_class -- Hotel Altapura came back without one. A missing
        # class is left None rather than inferred from the rating; a
        # 4.4-rated hotel is not thereby a 4-star hotel.
        star = entry.get("star_class")
        reviews = entry.get("review_count")

        # AMENITIES ARE PARSED BUT MUST NOT BE FILTERED OR DISPLAYED ON.
        # Measured 2026-08-30 over 78 properties across Val Thorens,
        # Kitzbuehel, Bansko and Zermatt:
        #
        #   BEACH_ACCESS  65%  -- the most common "amenity" in the ALPS
        #   INDOOR_POOL   59%
        #   SPA           41%  -- yet "Ours Blanc Hotel & Spa" is not
        #                         tagged SPA
        #   WIFI           0%  -- yet asking the provider for WIFI
        #                         returns 18 of 20 properties
        #
        # So this list is a truncated, partly wrong subset of what a
        # property actually has -- not its amenity set. And the
        # provider's own amenity filter does not discriminate either:
        # unfiltered 20, amenities=["SPA"] 18, amenities=["WIFI"] 18.
        #
        # Neither side is good enough: we cannot honestly show a
        # "beach access" badge on a hotel at 2,300m, and a "must have a
        # spa" filter that excludes two of twenty properties would feel
        # broken. Kept only so the field is ready if accommodation ever
        # moves to a documented API (Booking.com Demand is the stated
        # target). RE-MEASURE BEFORE USING IT FOR ANYTHING.
        amenities = entry.get("amenities")

        return AccommodationOption(
            price_eur_per_night=round(per_night, 2),
            property_name=name,
            rating=float(rating) if rating is not None else None,
            distance_to_lifts_km=distance,
            star_class=int(star) if star is not None else None,
            review_count=int(reviews) if reviews is not None else None,
            amenities=list(amenities) if amenities else None,
        )
    except (TypeError, ValueError):
        return None


def search_accommodation(resort, checkin_date: datetime.date, nights: int,
                         rooms_needed: int = 1, use_cache: bool = True,
                         with_lift_distance: bool = True,
                         accommodation_filter=None, group_size: int = 2,
                         property_type: str = "HOTELS") -> AccommodationSearchResult:
    """Same boundary contract as google_hotels_adapter.search_accommodation:
    AccommodationOption list out, one bad entry dropped rather than
    fatal, AdapterError only on total failure, response-cached.

    with_lift_distance=False skips the (cached, once-per-resort)
    Overpass lookup -- used by callers that only need a price."""
    checkout_date = checkin_date + datetime.timedelta(days=nights)
    provider_filters = _provider_filters(accommodation_filter, nights, rooms_needed, group_size)
    if property_type and property_type != "HOTELS":
        provider_filters["property_type"] = property_type
    # The filters are part of the identity of the request: two searches
    # for the same resort and dates but different star floors are
    # different inventory, and must not share a cache entry.
    key = _cache_key(resort.name, checkin_date, nights, rooms_needed, with_lift_distance,
                     sorted(provider_filters.items()))
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return AccommodationSearchResult(options=cached.options, from_cache=True)

    query = f"{resort.name}, {resort.country}"
    try:
        payload = _search_raw(query, checkin_date, checkout_date,
                              adults=max(1, rooms_needed) * 2, **provider_filters)
    except Exception as exc:
        raise AdapterError(f"stays search failed for {resort.name}: {exc}") from exc

    lift_points = None
    if with_lift_distance:
        from .lift_distance import lift_points_for_resort
        lift_points = lift_points_for_resort(resort)

    # When we asked Google to narrow by class, a property that comes
    # back without one was still vetted by Google -- we may say so, but
    # we may not print stars we were never given.
    asked_for_class = "hotel_class" in provider_filters
    options: List[AccommodationOption] = []
    for entry in payload.get("hotels", []) or []:
        parsed = _parse_hotel(entry, nights, lift_points)
        if parsed is None:
            continue
        if parsed.star_class is not None:
            parsed = dataclasses.replace(parsed, star_class_source="published")
        elif asked_for_class:
            parsed = dataclasses.replace(parsed, star_class_source="provider_filter")
        options.append(parsed)

    result = AccommodationSearchResult(options=options)
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur_per_night(result: AccommodationSearchResult) -> Optional[float]:
    if not result.options:
        return None
    return min(o.price_eur_per_night for o in result.options)
