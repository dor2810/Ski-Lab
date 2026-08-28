"""
The first real, protected use of the engine over HTTP: POST /trips/search
wraps engine.scoring.rank_trips exactly as the CLI demo does, but behind
Depends(get_current_user_for_search) -- no valid Authorization: Bearer
access token, no results, UNLESS ALLOW_ANONYMOUS_SEARCH=true is set
(dev-only convenience; see that function's docstring in routes/auth.py
-- production default requires auth).

This is deliberately the search wrapped in the SAME hard/soft
constraint pipeline the CLI and the frontend prototype's ported JS use
-- nothing here recomputes scoring logic a third way. If the numbers
ever look different between the CLI, the JS prototype, and this route,
that's a bug to find, not an acceptable inconsistency.

Resort data is loaded once at import time, not per-request -- re-reading
and re-parsing the xlsx on every search would be wasteful for data that
only changes when someone edits the spreadsheet and restarts the
server. See reload_resorts() below for how to pick up spreadsheet edits
without a full restart (useful during a verification pass).
"""
import datetime
import os
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ...data.resort_repository import load_resorts
from ...models import (
    Resort, UserPreferences,
    VALID_SKILL_LEVELS, VALID_ACCOMMODATION_TIERS,
    VALID_FOOD_PROFILES, VALID_EQUIPMENT_TIERS, VALID_WEIGHT_KEYS,
)
from ...engine.cost_calculator import (
    live_flight_cost_eur, live_flight_booking_url,
    live_accommodation_cost_eur_per_person, live_accommodation_booking_url,
    live_accommodation_property_name, live_accommodation_options,
    live_flight_options,
    apply_live_flight_price, apply_live_accommodation_price,
    live_transfer_booking_url,
)
from ...engine.links import (
    google_flights_url, google_hotels_url, alps2alps_search_url,
    equipment_search_url as _equipment_search_url,
    ski_pass_search_url as _ski_pass_search_url,
)
from ...engine.scoring import rank_trips
from ...engine.transfers import get_transfer_options
from ...engine.date_search import search_date_range, candidate_start_dates, WEEKDAY_NAMES
from ...engine.weather import get_trip_weather
from ...engine.reranker import rerank_with_conditions
from ...engine.provider_status import reset_provider_status, was_provider_blocked
from ...nlp.explainer import explain
from ...db.models import User
from .auth import get_current_user_for_search
from ..rate_limit import enforce_search_rate_limit, enforce_booking_link_rate_limit, live_pricing_allowed
from .. import credits as credits_module
from ...db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/trips", tags=["trips"])

# family defaults to 0.0 on purpose: adding a dimension must not silently
# re-rank every existing caller's results. It only bites when a client
# actually asks for it (the "Families" trip style does).
_DEFAULT_WEIGHTS = {
    "ski_quality": 0.30, "price": 0.20, "snow": 0.15,
    "nightlife": 0.15, "convenience": 0.10, "accommodation": 0.10,
    "family": 0.0,
}

# Real modes present in the researched transfer-options data (see
# engine/transfers.py) -- NOT a fixed enum, so read from the data itself
# rather than hardcoding a list that could silently drift out of sync
# (e.g. if a mode is added/removed in a future spreadsheet update).
_VALID_TRANSFER_MODES = frozenset(o.mode for o in get_transfer_options())

# Loaded once at import time -- see module docstring.
_resort_cache: List[Resort] = load_resorts()


def reload_resorts() -> int:
    """
    Re-reads the spreadsheet into the in-memory cache. Not wired to any
    endpoint yet (deliberately -- an unauthenticated or under-protected
    reload endpoint is an easy way to accidentally build a DoS vector).
    Call this from a Python shell or an admin-only route added later if
    a verification-pass edit needs to show up without restarting the
    server.
    """
    global _resort_cache
    _resort_cache = load_resorts()
    return len(_resort_cache)


def _validate_resort_names(names: Optional[List[str]]) -> None:
    """
    404s clearly on any unknown resort name in a target_resort /
    include_resorts / exclude_resorts list, matching the ENGINE's
    case/whitespace-insensitive matching (narrow_resort_pool) exactly --
    so a name this rejects is also a name the engine would have silently
    matched nothing for, never a false negative. Shared by both search
    routes so the two don't drift into checking differently.
    """
    if not names:
        return
    known = {r.name.strip().lower() for r in _resort_cache}
    unknown = [n for n in names if n.strip().lower() not in known]
    if unknown:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Unknown resort(s) {unknown!r}. See GET /trips/resorts for valid names.",
        )


class SearchRequest(BaseModel):
    budget_eur_per_person: float = Field(gt=0)
    # Optional floor for "price range" requests: results cheaper than
    # this are dropped. None (default) = no floor, matching every prior
    # caller's behavior exactly. Unlike the budget ceiling, there is
    # deliberately no fallback when this empties the result set -- "I
    # don't want anything under X" is a real preference, not a feasibility
    # problem to work around the way "nothing fits my budget" is.
    min_budget_eur_per_person: Optional[float] = Field(default=None, ge=0)
    # The number of FULL days on the mountain -- see
    # models.UserPreferences.ski_days' comment for why this, not nights
    # away, is the field a client sends. Nights away (derived as
    # ski_days + 1) is what actually drives accommodation/food/flight
    # date math -- see UserPreferences.nights.
    ski_days: int = Field(gt=0, le=30)
    group_size: int = Field(default=2, gt=0, le=20)
    skill_level: str = "intermediate"
    accommodation_tier: str = "standard"
    food_profile: str = "normal"
    equipment_tier: str = "standard"
    target_resort: Optional[str] = None
    # Search ONLY these resorts (2-3, or however many). Case/whitespace-
    # insensitive, same matching as target_resort. If target_resort is
    # ALSO set, target_resort wins -- these are meant as its replacement
    # for "more than one resort", not to be combined with it.
    include_resorts: Optional[List[str]] = None
    # Search every resort EXCEPT these -- "everywhere but Val Thorens".
    # Combines with include_resorts if both are given (include narrows
    # first, exclude then removes from what's left).
    exclude_resorts: Optional[List[str]] = None
    # Optional: enables season-band cost adjustment, and live flight +
    # accommodation repricing for the top candidates (see search_trips()
    # below -- no API key needed for either any more). Omitting it
    # reproduces the previous date-agnostic behavior exactly.
    outbound_date: Optional[datetime.date] = None
    # Connections preference for live flight pricing. 0 = nonstop only,
    # 1 = up to 1 stop, 2 = up to 2 stops, None = no preference (any
    # number of stops -- the only way to express "willing to take 2+
    # stops", since SerpApi has no "at least N" filter, only "at most N"
    # or "any"; see flight_adapter._stops_param). Has no effect unless
    # outbound_date is also set and a SerpApi key is configured.
    max_connections: Optional[int] = Field(default=None, ge=0, le=2)
    # See rank_trips' over-budget-fallback docstring. True (default): if
    # NOTHING fits budget_eur_per_person, return the cheapest option(s)
    # found instead of an empty list, flagged within_budget=False. False
    # restores the old "empty means nothing fits" behavior.
    allow_over_budget_fallback: bool = True
    top_n: int = Field(default=6, gt=0, le=30)
    # None = no preference (every mode considered). Validated against
    # the REAL modes present in the researched transfer data -- see
    # _VALID_TRANSFER_MODES above -- so a typo 404s clearly instead of
    # silently matching nothing (engine/transfers.py's own fallback
    # behavior for an unmatched preference, which is correct for OTHER
    # callers but would be a confusing silent no-op for an API client).
    preferred_transfer_modes: Optional[List[str]] = None
    weights: Dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))

    @field_validator("skill_level")
    @classmethod
    def _valid_skill(cls, v: str) -> str:
        # Shared constant from models.py -- see its comment on why these
        # aren't re-declared here.
        if v not in VALID_SKILL_LEVELS:
            raise ValueError(f"skill_level must be one of {sorted(VALID_SKILL_LEVELS)}")
        return v

    @field_validator("accommodation_tier")
    @classmethod
    def _valid_accom_tier(cls, v: str) -> str:
        if v not in VALID_ACCOMMODATION_TIERS:
            raise ValueError(f"accommodation_tier must be one of {sorted(VALID_ACCOMMODATION_TIERS)}")
        return v

    @field_validator("food_profile")
    @classmethod
    def _valid_food(cls, v: str) -> str:
        if v not in VALID_FOOD_PROFILES:
            raise ValueError(f"food_profile must be one of {sorted(VALID_FOOD_PROFILES)}")
        return v

    @field_validator("equipment_tier")
    @classmethod
    def _valid_equipment(cls, v: str) -> str:
        if v not in VALID_EQUIPMENT_TIERS:
            raise ValueError(f"equipment_tier must be one of {sorted(VALID_EQUIPMENT_TIERS)}")
        return v

    @field_validator("preferred_transfer_modes")
    @classmethod
    def _valid_transfer_modes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        unknown = set(v) - _VALID_TRANSFER_MODES
        if unknown:
            raise ValueError(
                f"unknown transfer mode(s) {sorted(unknown)}; allowed: {sorted(_VALID_TRANSFER_MODES)}"
            )
        return v

    @field_validator("weights")
    @classmethod
    def _valid_weight_keys(cls, v: Dict[str, float]) -> Dict[str, float]:
        unknown = set(v) - VALID_WEIGHT_KEYS
        if unknown:
            raise ValueError(f"unknown weight key(s) {sorted(unknown)}; allowed: {sorted(VALID_WEIGHT_KEYS)}")
        if any(w < 0 for w in v.values()):
            raise ValueError("weights must be non-negative")
        if sum(v.values()) <= 0:
            raise ValueError("at least one weight must be positive")
        return v


class TerrainMixOut(BaseModel):
    beginner: float
    intermediate: float
    advanced: float
    quality: str  # 'sourced' | 'sourced_conflicting' | 'estimated'


class ResortOut(BaseModel):
    name: str
    country: str
    region: str
    piste_km: float
    off_piste_rating: int
    snow_reliability: int
    nightlife_rating: int
    family_friendliness: int
    nearest_airport: str
    transfer_time_minutes: float
    terrain: Optional[TerrainMixOut]
    needs_verification: bool


class CostBreakdownOut(BaseModel):
    flight_eur: float
    transfer_eur: float
    accommodation_eur: float
    ski_pass_eur: float
    equipment_eur: float
    food_eur: float
    misc_eur: float
    total_eur: float
    flight_price_is_live: bool
    accommodation_price_is_live: bool
    # True = ski_pass_eur is a REAL published 6-day price researched
    # from the resort's own ticketing pages (data/ski_pass_prices.py),
    # not the seed spreadsheet's estimate. Not per-request "live" like
    # the two above, but sourced rather than guessed -- which is the
    # distinction that matters to a user reading the number.
    ski_pass_price_is_researched: bool = False


class DailyWeatherOut(BaseModel):
    """
    ONE day of the trip. is_live_forecast True means a real forecast
    (only possible within adapters/weather_adapter.py's ~15-day
    horizon; description set, years_sampled None) -- False means a
    historical average for that SAME calendar day across several past
    years (description None, years_sampled set). See
    adapters/weather_adapter.get_trip_weather()'s own docstring for why
    a trip's days can be a genuine mix of both.
    """
    date: datetime.date
    is_live_forecast: bool
    temp_max_c: float
    temp_min_c: float
    snowfall_cm: float
    # Actual ground/base snow depth, NOT recent snowfall (see
    # snowfall_cm) -- adapters/weather_adapter.py's own module
    # docstring on why both matter: a mild, dry week can still have a
    # great base from earlier storms, and vice versa.
    snow_depth_cm: float
    description: Optional[str] = None
    years_sampled: Optional[int] = None


class WeatherOut(BaseModel):
    """
    A whole trip's weather: one DailyWeatherOut per day from check-in
    to check-out inclusive, plus an overall average across whichever
    days a real answer (forecast or historical) was actually available
    for -- see adapters/weather_adapter.get_trip_weather()'s own
    docstring. days can be SHORTER than the full trip length if some
    days genuinely have no data (never padded with an invented number).
    """
    days: List[DailyWeatherOut]
    avg_temp_max_c: float
    avg_temp_min_c: float
    avg_snowfall_cm: float
    avg_snow_depth_cm: float


class FlightOptionOut(BaseModel):
    """
    One real itinerary behind a result's flight price.

    Exists because the adapter was always returning a LIST of priced
    flights and we kept a single number off it. On a real TLV->GVA
    search the cheapest was EUR283 for a 14h30 journey while EUR392 got
    there in 6h -- quoting only the cheapest silently assumes the user
    will spend two days travelling to save EUR109.
    """
    price_eur: float
    airline: str
    duration_minutes: int
    stops: int
    is_cheapest: bool
    # Which of the three curated labels this itinerary won: any of
    # "cheapest" / "best" / "fastest" (engine/flight_picks.py). One
    # flight can hold several -- it is then shown ONCE with all of
    # them, never listed twice under two labels.
    roles: List[str] = []
    # Real designators per leg, e.g. ["LX 253", "LX 2802"]. Empty when
    # the provider didn't supply them -- never faked, since a wrong
    # flight number is worse than none to someone at a departure board.
    flight_numbers: List[str] = []
    # What the WHOLE trip costs if this flight is the one taken, not
    # just what the flight costs. The headline total assumes the
    # cheapest flight; this is what makes the alternatives comparable.
    trip_total_eur: float


class AccommodationOptionOut(BaseModel):
    """
    One real, named property behind a result's accommodation price --
    same reasoning as FlightOptionOut: the scrape always returned ~20
    named, priced properties and we showed ONE name off it. Cheapest
    first, no "best" pick -- the provider's rating/distance fields are
    not parsed, so there is no honest second axis to rank on (see
    cost_calculator.live_accommodation_options).
    """
    property_name: str
    price_eur_per_night: float
    # What this property costs THIS traveller for the whole stay:
    # per-night x nights x rooms / group size -- exactly the formula
    # live_accommodation_cost_eur_per_person prices the trip with.
    per_person_eur: float
    is_cheapest: bool
    # Guest rating out of 5, when the provider supplied one (the
    # `stays` backup does; our own scraper cannot parse it). None is
    # honest "unknown", never a zero.
    rating: Optional[float] = None
    # STRAIGHT-LINE km to the nearest ski lift, computed from the
    # property's coordinates against OpenStreetMap's aerialway data
    # (adapters/lift_distance.py) -- not walking distance, and None
    # whenever either side is unknown. The single most requested
    # accommodation fact on a ski trip.
    distance_to_lifts_km: Optional[float] = None
    # The whole trip's cost if this property is the one booked, via the
    # same apply_live_accommodation_price the engine prices with -- so
    # the misc buffer rescales identically, never a second formula.
    trip_total_eur: float
    # A dated Google Hotels link narrowed to THIS property -- the same
    # free (no extra network) property-narrowed search the headline
    # accommodation link already falls back to. A narrowed results
    # page with the property surfaced on top, not a guaranteed
    # single-property landing page -- see
    # google_hotels_adapter.search_url's verified-live note.
    url: str


class TripResultOut(BaseModel):
    resort: ResortOut
    cost: CostBreakdownOut
    score: float
    score_components: Dict[str, float]
    explanation: str
    # False only for over-budget-fallback results (see SearchRequest's
    # allow_over_budget_fallback) -- the frontend MUST show this
    # honestly rather than presenting a flagged result as a normal one.
    within_budget: bool
    # Links to Google's own live search results, NOT a booking link for
    # this exact priced itinerary -- see engine/links.py's module
    # docstring for why. flight_search_url is None when the resort's
    # airport field has no parseable IATA code.
    flight_search_url: Optional[str] = None
    accommodation_search_url: str
    # The real name of the cheapest live-priced property this result's
    # accommodation_eur is FOR (e.g. "Hotel Marielle") -- populated for
    # every live-priced result, not just the top one (see
    # _accommodation_property_name's own docstring on why this is cheap
    # to compute broadly, unlike accommodation_search_url's specific
    # link). None when accommodation pricing isn't live for this result.
    accommodation_property_name: Optional[str] = None
    # The real itineraries behind flight_eur, cheapest first. Only
    # populated when the flight price is live (there is nothing to list
    # otherwise) and only for results that were live-repriced. Costs no
    # extra requests -- see cost_calculator.live_flight_options.
    flight_options: List[FlightOptionOut] = []
    # The real named properties behind accommodation_eur, cheapest
    # first -- same contract as flight_options: only populated when the
    # accommodation price is live, and a response-cache hit rather than
    # a second scrape (cost_calculator.live_accommodation_options).
    accommodation_options: List[AccommodationOptionOut] = []
    # The trip total spans a RANGE, because which flight you take
    # changes it. total_eur is the low end (cheapest flight); this is
    # the high end (typically the fastest or nonstop option). Equal to
    # total_eur when there is only one real choice.
    total_eur_with_fastest_flight: Optional[float] = None
    # A booking link -- always real and working, same "never nothing"
    # contract as flight/accommodation above. A live booking link for
    # the cheapest real transfer quote found (adapters/transfer_
    # adapter.py, Alps2Alps) when this is the top result and one was
    # found; Alps2Alps' own real booking form otherwise (see
    # _transfer_search_url's own docstring). Display only, does NOT
    # feed into cost.transfer_eur or the score, which both still use
    # the static/curated estimate.
    transfer_search_url: str
    # Real, working links for the two cost lines that never had any
    # link before -- see engine/links.py's equipment_search_url()/
    # ski_pass_search_url() docstrings for exactly what each is (a
    # verified rental network's front door vs. a resort-named Google
    # search) and what's NOT resort-guaranteed about them. Pure/
    # offline (no live lookup, no network call, no gating needed) --
    # populated for every result, not just the top one.
    equipment_search_url: str
    ski_pass_search_url: str
    # See WeatherOut's own docstring. Only ever populated for the single
    # top-ranked result -- see _weather_for()'s docstring on why.
    weather: Optional[WeatherOut] = None


class CreditsOut(BaseModel):
    """
    What this search cost and what's left today. None for an anonymous
    search (ALLOW_ANONYMOUS_SEARCH), which isn't metered.
    """
    cost: int
    remaining: int
    daily_allowance: int


class SearchResponse(BaseModel):
    query_resort_count: int
    live_pricing_active: bool
    results: List[TripResultOut]
    credits: Optional[CreditsOut] = None
    # True when a live-pricing provider served an anti-bot challenge
    # during THIS request. The prices fell back to estimates, which the
    # per-line flags already say -- this explains WHY, so the UI can
    # tell the user "live pricing is temporarily blocked" instead of
    # showing a wall of unexplained EST. badges.
    live_pricing_blocked: bool = False


def _to_resort_out(r: Resort) -> ResortOut:
    terrain = None
    if r.terrain_mix is not None:
        terrain = TerrainMixOut(
            beginner=round(r.terrain_mix.beginner, 3),
            intermediate=round(r.terrain_mix.intermediate, 3),
            advanced=round(r.terrain_mix.advanced, 3),
            quality=r.terrain_data_quality,
        )
    return ResortOut(
        name=r.name, country=r.country, region=r.region, piste_km=r.piste_km,
        off_piste_rating=r.off_piste_rating, snow_reliability=r.snow_reliability,
        nightlife_rating=r.nightlife_rating, family_friendliness=r.family_friendliness,
        nearest_airport=r.nearest_airport, transfer_time_minutes=r.transfer_time_minutes,
        terrain=terrain, needs_verification=r.needs_verification,
    )


def _flight_search_url(resort: Resort, outbound_date, return_date, flight_price_is_live: bool,
                       max_connections: int, attempt_booking_link: bool) -> Optional[str]:
    """
    A booking-page deep link for the specific flight that was just
    live-priced, when available -- falling back to the plain,
    reliable route/date search-results link (google_flights_url())
    for every case that isn't: no live price for this result
    (flight_price_is_live False -- nothing to build a booking link
    FROM), no outbound_date, attempt_booking_link False (see below),
    or live_flight_booking_url() itself returning None (its own
    docstring covers every reason: no booking ingredients, an expired
    selection token, a failed round-trip return-leg fetch). This
    fallback is deliberate and automatic, not just a git-revert safety
    net -- see adapters/google_flights_adapter.booking_url()'s module
    comment on what's verified vs. not about the booking link's
    long-term reliability.

    attempt_booking_link gates this per-result, not just
    flight_price_is_live: caught in code review -- for a ROUND TRIP,
    live_flight_booking_url() costs one EXTRA, uncached live request
    (booking_url()'s own "choose return" fetch, see that function's
    docstring) on top of the pricing search. Attempting that for EVERY
    live-priced result in a response (up to top_n / live_reprice_n)
    would silently multiply live Google requests per API call well
    beyond what live_pricing_allowed()'s one-shot budget spend accounts
    for -- callers pass attempt_booking_link=True for only the single
    top result to bound this to at most one extra live request per
    response, matching that budget's actual intent.

    live_flight_cost_eur() already ran search_flights() for this exact
    (resort, dates) combination moments ago when flight_price_is_live is
    True, so live_flight_booking_url() re-running the same search is a
    response-cache hit for the PRICING half -- the round-trip return-leg
    fetch above is the only genuinely new request.
    """
    if attempt_booking_link and flight_price_is_live and outbound_date is not None:
        booking = live_flight_booking_url(resort, outbound_date, return_date, origin_airport="TLV",
                                          max_connections=max_connections)
        if booking:
            return booking
    return google_flights_url(resort, outbound_date, return_date)


def _prefetch_weather(jobs) -> dict:
    """
    Trip weather for EVERY shown result, fetched CONCURRENTLY.

    jobs: {index: (resort, start_date, end_date)}. Returns
    {index: Optional[WeatherOut]}.

    WHY THIS REPLACED the attempt_weather=(i == 0) gate: the user
    noticed most results carried no weather. The gate existed because
    one lookup is several SEQUENTIAL provider requests (one per sampled
    historical year) -- but the provider (Open-Meteo) is free and
    nowhere near any quota at this volume, so the real cost was only
    LATENCY, and the honest fix is concurrency, not rationing. Twelve
    results in parallel cost roughly one result's wall-clock time.
    Same worker-pool sizing rationale as date_search's repricing pool.
    """
    if not jobs:
        return {}
    from concurrent.futures import ThreadPoolExecutor
    out: dict = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            i: pool.submit(_weather_out, resort, start, end, True)
            for i, (resort, start, end) in jobs.items()
        }
        for i, fut in futures.items():
            try:
                out[i] = fut.result()
            except Exception:
                out[i] = None  # weather is enrichment, never a search-breaker
    return out


def _weather_out(resort: Resort, start_date, end_date, attempt_weather: bool) -> Optional[WeatherOut]:
    """
    WeatherOut for the WHOLE trip (start_date..end_date inclusive), or
    None -- see engine.weather.get_trip_weather()'s own docstring for
    the forecast-vs-historical split and every reason this can come
    back empty (no coordinates, every provider request failing).

    attempt_weather gates this per-result for the SAME reason
    _flight_search_url/_accommodation_search_url's matching parameter
    does: a historical breakdown costs several real, sequential live
    requests (one per sampled year -- see get_trip_weather's own
    years_back note), so this is attempted for only the single top
    result per response, never for every result in a list.
    """
    if not attempt_weather or start_date is None or end_date is None:
        return None
    summary = get_trip_weather(resort, start_date, end_date)
    if summary is None:
        return None
    return WeatherOut(
        days=[
            DailyWeatherOut(date=d.date, is_live_forecast=d.is_live_forecast, temp_max_c=d.temp_max_c,
                            temp_min_c=d.temp_min_c, snowfall_cm=d.snowfall_cm,
                            snow_depth_cm=d.snow_depth_cm,
                            description=d.description, years_sampled=d.years_sampled)
            for d in summary.days
        ],
        avg_temp_max_c=summary.avg_temp_max_c,
        avg_temp_min_c=summary.avg_temp_min_c,
        avg_snowfall_cm=summary.avg_snowfall_cm,
        avg_snow_depth_cm=summary.avg_snow_depth_cm,
    )


def _accommodation_search_url(resort: Resort, checkin_date, checkout_date, nights: int,
                              rooms_needed: int, accommodation_price_is_live: bool,
                              attempt_booking_link: bool, property_name: Optional[str] = None) -> str:
    """
    A deep link to ONE specific property that was just live-priced,
    when available -- falling back to a Google Hotels search NARROWED
    to that same property's real name (property_name, when known)
    rather than a bare resort-wide listing. Same shape and same
    "automatic, not just git-revert" fallback contract as
    _flight_search_url() above -- see that function's docstring.

    Two independent levels of specificity here, not one:
      1. live_accommodation_booking_url() -- a true single-property
         Knowledge Graph deep link. Confirmed live to have essentially
         no coverage of small independent resort hotels (see
         adapters/google_hotels_adapter._resolve_hotel_mid's
         docstring) -- available for a minority of results.
      2. google_hotels_url(..., property_name=...) -- a plain-text
         search narrowed to that property's name. Needs no Knowledge
         Graph match at all, just the name this exact search already
         scraped (_accommodation_property_name(), computed alongside
         this for the same result) -- available for every live-priced
         result, which is why it's the fallback rather than the other
         way around. Verified live to meaningfully narrow results (see
         google_hotels_adapter.search_url()'s docstring) -- a search
         page, not a guaranteed single-property landing page, but a
         real step up from a bare "Hotels in {resort}" search.

    attempt_booking_link gates level 1 per-result for the same reason
    as _flight_search_url()'s matching parameter: specific_property_
    url() makes a genuinely separate, uncached live request to the
    Knowledge Graph Search API, not covered by response_cache.py or
    live_pricing_allowed()'s budget -- callers pass True for only the
    single top result to bound this to at most one extra live request
    per response. Level 2 has no such cost (property_name is already
    computed, not fetched again here) so it applies to every result.
    """
    if attempt_booking_link and accommodation_price_is_live and checkin_date is not None:
        booking = live_accommodation_booking_url(
            resort, checkin_date, nights, rooms_needed, f"{resort.name}, {resort.country}")
        if booking:
            return booking
    return google_hotels_url(resort, checkin_date, checkout_date, property_name=property_name)


def _accommodation_property_name(resort: Resort, checkin_date, nights: int,
                                 rooms_needed: int, accommodation_price_is_live: bool) -> Optional[str]:
    """
    The real name of the cheapest live-priced property for this
    result, or None -- see engine.cost_calculator.
    live_accommodation_property_name()'s own docstring for why this
    needs NO GOOGLE_KG_API_KEY (unlike the specific booking link
    above), and is safe to compute for EVERY live-priced result, not
    just the top one: it re-runs the exact same search_accommodation()
    call the live cost estimate itself already made moments earlier
    (same resort/checkin_date/nights/rooms_needed), which is a
    response-cache hit here, not a second live request.
    """
    if not accommodation_price_is_live or checkin_date is None:
        return None
    return live_accommodation_property_name(resort, checkin_date, nights, rooms_needed)


def _accommodation_options_out(resort: Resort, checkin_date, nights: int,
                               rooms_needed: int, group_size: int,
                               accommodation_price_is_live: bool,
                               cost) -> List["AccommodationOptionOut"]:
    """
    The named properties behind this result's accommodation price.
    Empty unless the price is actually live -- with a static estimate
    there are no real properties to list, and inventing some is exactly
    the fabrication this project forbids. Same response-cache-hit
    economics as _accommodation_property_name above.
    """
    if not accommodation_price_is_live or checkin_date is None:
        return []
    checkout_date = checkin_date + datetime.timedelta(days=nights)
    options = live_accommodation_options(resort, checkin_date, nights, rooms_needed)
    out = []
    for i, o in enumerate(options):
        # The same per-person formula live_accommodation_cost_eur_per_
        # person prices the trip with -- never a second one.
        per_person = round((o.price_eur_per_night * nights * rooms_needed) / group_size, 2)
        out.append(AccommodationOptionOut(
            property_name=o.property_name,
            price_eur_per_night=round(o.price_eur_per_night, 2),
            per_person_eur=per_person,
            is_cheapest=(i == 0),
            rating=o.rating,
            distance_to_lifts_km=o.distance_to_lifts_km,
            trip_total_eur=round(apply_live_accommodation_price(cost, per_person).total_eur, 2),
            url=google_hotels_url(resort, checkin_date, checkout_date,
                                  property_name=o.property_name),
        ))
    return out


# How many top results may spend real weather requests on snow
# re-ranking. Each lookup is several sequential live requests (one per
# sampled historical year), so this is bounded for the same reason the
# booking-link lookups are gated to the top result -- see
# engine/reranker.rerank_with_conditions' own docstring. Slightly wider
# than the booking links' 1 because re-ranking only means anything if
# it can compare several candidates against each other.
_SNOW_RERANK_LOOKUPS = 5

# How many (resort, date) pairs may be live-priced per date-range search.
# See the call site for the measurement that set this.
_LIVE_REPRICE_N = int(os.environ.get("LIVE_REPRICE_N", "24"))

# Nobody books a ski trip more than two seasons out, and every extra day
# of window is real CPU and memory on a scale-to-zero instance: a
# bug-hunt pass measured a 100-year window at 36,495 candidate dates,
# 5.4s CPU and 343MB RSS in ONE request. Per-IP rate limiting bounds
# request COUNT but not the cost of a single request.
MAX_SEARCH_WINDOW_DAYS = 400


def _flight_options_out(resort: Resort, outbound_date, return_date,
                        flight_price_is_live: bool, max_connections,
                        cost) -> List["FlightOptionOut"]:
    """
    The itineraries behind this result's flight price. Empty unless the
    price is actually live -- with a static estimate there are no real
    flights to list, and inventing some would be exactly the fabrication
    this project forbids.
    """
    if not flight_price_is_live or outbound_date is None or return_date is None:
        return []
    picks = live_flight_options(resort, outbound_date, return_date, origin_airport="TLV",
                                max_connections=max_connections)
    # What the WHOLE trip costs under each choice. Uses the same
    # apply_live_flight_price the engine uses, so the misc buffer is
    # rescaled exactly as it is everywhere else rather than a second,
    # subtly different sum living here.
    return [
        FlightOptionOut(
            price_eur=p.option.price_eur, airline=p.option.airline,
            duration_minutes=p.option.total_duration_minutes, stops=p.option.stops,
            is_cheapest=("cheapest" in p.roles),
            roles=list(p.roles),
            flight_numbers=list(p.option.flight_numbers or []),
            trip_total_eur=round(apply_live_flight_price(cost, p.option.price_eur).total_eur, 2),
        )
        for p in picks
    ]


def _charge_credits(db, current_user, candidate_dates: int) -> Optional[dict]:
    """
    Spends this search's credits up front, or 402s if the user is out.

    Returns the balance to report back, or None when there is no user to
    charge (anonymous search, only possible with ALLOW_ANONYMOUS_SEARCH
    -- a dev/testing escape hatch that deliberately isn't metered).
    Charging BEFORE the work happens means a refusal costs nothing and
    the price can be quoted honestly rather than billed after the fact.
    """
    if current_user is None:
        return None
    cost = credits_module.cost_for_candidate_dates(candidate_dates)
    status_after = credits_module.try_spend(db, current_user.id, cost)
    if status_after is None:
        current = credits_module.get_status(db, current_user.id)
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"This search costs {cost} credit(s) and you have {current.remaining} left today "
            f"(daily allowance {current.daily_allowance}). Credits reset at midnight; "
            "a narrower date range costs fewer.",
        )
    return {
        "cost": cost,
        "remaining": status_after.remaining,
        "daily_allowance": status_after.daily_allowance,
    }


def _reject_past_date(value, field_name: str) -> None:
    """
    A trip in the past is never what anyone meant, and accepting one is
    not harmless: it spends real live flight/hotel scrapes that can only
    fail, and the deep links we hand back embed the past dates, so the
    user lands on a broken Google Flights search. Measured before this
    guard existed: a date 120 days ago returned HTTP 200 and attempted
    10 live flight lookups.
    """
    if value is not None and value < datetime.date.today():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{field_name} is in the past ({value.isoformat()}); ski trips must start today or later.",
        )


def _is_within_forecast_horizon(start_date) -> bool:
    """
    Whether a real weather forecast can exist for this trip at all.
    False for None, for past dates, and for anything beyond the
    provider's real horizon -- see the call site for why gating on this
    is what makes snow re-ranking affordable.
    """
    if start_date is None:
        return False
    from ...adapters.weather_adapter import MAX_FORECAST_DAYS
    delta = (start_date - datetime.date.today()).days
    return 0 <= delta <= MAX_FORECAST_DAYS


# This app's flight search only tracks a DATE, never an arrival TIME
# (see FlightOption/search results elsewhere) -- there is no real
# flight time to quote a transfer against. A mid-afternoon pickup is a
# reasonable placeholder for "the transfer exists and is roughly this
# price", not a claim about when any specific flight actually lands.
_ASSUMED_PICKUP_TIME = "14:00"


def _transfer_search_url(resort: Resort, pickup_date, group_size: int, attempt: bool) -> str:
    """
    A booking link for the cheapest real transfer quote found
    (adapters/transfer_adapter.py, Alps2Alps) when available -- falling
    back to Alps2Alps' own real booking form (alps2alps_search_url())
    otherwise. Same "always a real, working link, never nothing"
    contract as _flight_search_url/_accommodation_search_url now --
    this used to return None whenever attempt was False or the live
    quote failed, which is exactly why "View Transfer" didn't behave
    like "View Flight"/"View Accommodation": those two never disappear
    on a non-top result, this one always did.

    Unlike _flight_search_url/_accommodation_search_url, the live half
    does NOT feed a price back into cost.transfer_eur or the score:
    transfer_cost_eur_per_person() (engine/cost_calculator.py) runs for
    EVERY candidate resort during static scoring, not a capped top-N
    the way flight/accommodation costs are, so making it live there
    would multiply live requests across an entire search. Wiring that
    properly needs a transfer_cost_fn callback threaded through
    rank_trips/search_date_range the same way flight_cost_fn/
    accommodation_cost_fn already are -- a real engine change, not
    attempted this pass. This function only ever supplies a link, using
    _ASSUMED_PICKUP_TIME since no real flight time is tracked.

    attempt gates the LIVE half to the single top result, same
    reasoning as every other live lookup here -- one real request
    (cached across the two calls this makes internally), not one per
    result. The fallback has no such cost and applies to every result.
    """
    if attempt and pickup_date is not None:
        booking = live_transfer_booking_url(resort, pickup_date, _ASSUMED_PICKUP_TIME, group_size)
        if booking:
            return booking
    return alps2alps_search_url()


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search_trips(payload: SearchRequest, current_user: Optional[User] = Depends(get_current_user_for_search),
                 db: Session = Depends(get_db)):
    # Auto-normalize weights (divide by sum) rather than require the
    # client send an exact 1.0 -- matches the frontend prototype's
    # slider behavior, and floating-point client input summing to
    # exactly 1.0 shouldn't be a hard requirement for a 200 vs. a 422.
    weight_sum = sum(payload.weights.values())
    normalized_weights = {k: v / weight_sum for k, v in payload.weights.items()}
    # UserPreferences.__post_init__ requires ALL six keys present and
    # summing to 1.0 -- fill in any keys the client omitted at zero
    # before normalizing, rather than letting a partial dict reach the
    # dataclass and raise a less useful error there.
    full_weights = dict(_DEFAULT_WEIGHTS)
    full_weights.update(normalized_weights)
    weight_sum_full = sum(full_weights.values())
    full_weights = {k: v / weight_sum_full for k, v in full_weights.items()}

    try:
        prefs = UserPreferences(
            budget_eur_per_person=payload.budget_eur_per_person,
            ski_days=payload.ski_days,
            group_size=payload.group_size,
            skill_level=payload.skill_level,
            accommodation_tier=payload.accommodation_tier,
            food_profile=payload.food_profile,
            equipment_tier=payload.equipment_tier,
            target_resort=payload.target_resort,
            include_resorts=payload.include_resorts,
            exclude_resorts=payload.exclude_resorts,
            outbound_date=payload.outbound_date,
            preferred_transfer_modes=payload.preferred_transfer_modes,
            weights=full_weights,
        )
    except ValueError as e:
        # UserPreferences validates weights sum to 1.0 -- should be
        # unreachable given the normalization above, but surfaced as a
        # clean 400 instead of a 500 if some edge case gets past it.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    reset_provider_status()
    _reject_past_date(payload.outbound_date, "outbound_date")

    # One fixed date = one candidate = 1 credit. Charged after validation
    # so a rejected request is never billed.
    credit_info = _charge_credits(db, current_user, candidate_dates=1)

    # Match the ENGINE's normalization exactly (see
    # engine/scoring.narrow_resort_pool) -- case/whitespace-insensitive,
    # so a name this accepts is also a name the engine will actually
    # match, and a name this rejects would have silently matched
    # nothing there.
    _validate_resort_names([payload.target_resort] if payload.target_resort else None)
    _validate_resort_names(payload.include_resorts)
    _validate_resort_names(payload.exclude_resorts)

    # Live flight repricing (engine/cost_calculator.live_flight_cost_eur,
    # backed by adapters/google_flights_adapter.py) AND live accommodation
    # repricing (live_accommodation_cost_eur_per_person, backed by
    # adapters/google_hotels_adapter.py) both need no API key any more --
    # only a date AND the global daily live-pricing budget not being
    # exhausted (rate_limit.py; search is anonymous, so this is the real
    # cost control, not auth). SERPAPI_API_KEY is no longer read here at
    # all; both SerpApi-based adapters are kept, unswapped, as fallbacks.
    # live_pricing_allowed() has a side effect (spends one unit of the
    # daily budget) so it must be last, after the cheap checks that
    # would short-circuit anyway. Origin is hardcoded to TLV, matching
    # the product's current Israeli-traveler-only scope.
    live_reprice_allowed = payload.outbound_date is not None and live_pricing_allowed()
    flight_cost_fn = accommodation_cost_fn = None
    if live_reprice_allowed:
        def flight_cost_fn(resort, start_date, end_date, _prefs):
            return live_flight_cost_eur(resort, start_date, end_date, origin_airport="TLV",
                                        max_connections=payload.max_connections)

        def accommodation_cost_fn(resort, start_date, end_date, _prefs):
            return live_accommodation_cost_eur_per_person(
                resort, start_date, nights=prefs.nights,
                group_size=payload.group_size, rooms_needed=prefs.rooms_needed)

    live_pricing_active = flight_cost_fn is not None

    trip_options = rank_trips(
        _resort_cache, prefs, top_n=payload.top_n,
        flight_cost_fn=flight_cost_fn, accommodation_cost_fn=accommodation_cost_fn,
        allow_over_budget_fallback=payload.allow_over_budget_fallback,
    )

    if payload.min_budget_eur_per_person is not None:
        trip_options = [t for t in trip_options if t.cost.total_eur >= payload.min_budget_eur_per_person]

    # Same for every result in this route (there's one fixed outbound
    # date, not one per resort) -- computed once rather than per result.
    return_date = payload.outbound_date + datetime.timedelta(days=prefs.nights) if payload.outbound_date else None

    # Blueprint Milestone 5: re-rank on REAL snow conditions.
    #
    # HARD-GATED ON THE FORECAST HORIZON, and that gate is the whole
    # reason this is affordable. Beyond ~15 days out (weather_adapter.
    # MAX_FORECAST_DAYS) no real forecast exists, every day comes back
    # as a historical average, reranker confidence is 0, and the result
    # is provably identical to not re-ranking at all -- so running it
    # would spend up to _SNOW_RERANK_LOOKUPS x several sequential live
    # requests each to change nothing. Most searches are months out and
    # therefore cost exactly zero extra requests here.
    if _is_within_forecast_horizon(payload.outbound_date) and return_date is not None:
        trip_options = rerank_with_conditions(
            trip_options, full_weights,
            weather_fn=lambda resort: get_trip_weather(resort, payload.outbound_date, return_date),
            max_lookups=_SNOW_RERANK_LOOKUPS,
        )

    weather_by_index = _prefetch_weather({
        i: (t.resort, payload.outbound_date, return_date)
        for i, t in enumerate(trip_options)
        if payload.outbound_date is not None and return_date is not None
    })
    results = []
    for i, t in enumerate(trip_options):
        property_name = _accommodation_property_name(
            t.resort, payload.outbound_date, prefs.nights, prefs.rooms_needed,
            t.cost.accommodation_price_is_live)
        results.append(TripResultOut(
            resort=_to_resort_out(t.resort),
            cost=CostBreakdownOut(
                flight_eur=t.cost.flight_eur, transfer_eur=t.cost.transfer_eur,
                accommodation_eur=t.cost.accommodation_eur, ski_pass_eur=t.cost.ski_pass_eur,
                equipment_eur=t.cost.equipment_eur, food_eur=t.cost.food_eur,
                misc_eur=t.cost.misc_eur, total_eur=t.cost.total_eur,
                flight_price_is_live=t.cost.flight_price_is_live,
                accommodation_price_is_live=t.cost.accommodation_price_is_live,
                ski_pass_price_is_researched=t.cost.ski_pass_price_is_researched,
            ),
            score=t.score,
            score_components=t.score_components,
            explanation=explain(t, skill_level=payload.skill_level),
            within_budget=t.within_budget,
            flight_search_url=_flight_search_url(t.resort, payload.outbound_date, return_date,
                                                 t.cost.flight_price_is_live, payload.max_connections,
                                                 attempt_booking_link=(i == 0)),
            accommodation_search_url=_accommodation_search_url(
                t.resort, payload.outbound_date, return_date, prefs.nights, prefs.rooms_needed,
                t.cost.accommodation_price_is_live, attempt_booking_link=(i == 0),
                property_name=property_name),
            accommodation_property_name=property_name,
            flight_options=(_fo := _flight_options_out(
                t.resort, payload.outbound_date, return_date,
                t.cost.flight_price_is_live, payload.max_connections, t.cost)),
            accommodation_options=_accommodation_options_out(
                t.resort, payload.outbound_date, prefs.nights, prefs.rooms_needed,
                payload.group_size, t.cost.accommodation_price_is_live, t.cost),
            total_eur_with_fastest_flight=(max(o.trip_total_eur for o in _fo) if _fo else None),
            transfer_search_url=_transfer_search_url(t.resort, payload.outbound_date,
                                                     payload.group_size, attempt=(i == 0)),
            equipment_search_url=_equipment_search_url(t.resort),
            ski_pass_search_url=_ski_pass_search_url(t.resort),
            weather=weather_by_index.get(i),
        ))

    return SearchResponse(query_resort_count=len(_resort_cache),
                          live_pricing_active=live_pricing_active, results=results,
                          credits=credit_info,
                          live_pricing_blocked=was_provider_blocked())


@router.get("/resorts", response_model=List[str])
def list_resort_names(current_user: Optional[User] = Depends(get_current_user_for_search),
                      mainstream_only: bool = False,
                      popular_only: bool = False):
    """
    Lets an authenticated client populate a resort picker without
    guessing names.

    popular_only=true returns the small hand-picked "most popular" set
    that the picker's one-tap button selects.

    mainstream_only=true returns just the curated shortlist (see
    data/mainstream_resorts.py) -- resorts real ski-package operators
    actually sell, plus a small marquee set. Default stays False so the
    existing contract is untouched: nothing is removed from the
    database, and any client that wants all 37 still gets all 37. The
    frontend uses the shortlist as its DEFAULT and offers "show all",
    which is a presentation choice, not a restriction.
    """
    names = sorted(r.name for r in _resort_cache)
    if popular_only:
        # The curated one-tap "most popular" set. Returned in the
        # CURATED order, not alphabetically -- the order is part of the
        # curation. Filtered against the real resort list so a rename in
        # the spreadsheet can never make the button select a name that
        # no longer exists.
        from ...data.mainstream_resorts import MOST_POPULAR_RESORTS
        known = set(names)
        return [n for n in MOST_POPULAR_RESORTS if n in known]
    if mainstream_only:
        from ...data.mainstream_resorts import is_mainstream
        return [n for n in names if is_mainstream(n)]
    return names


# ---------------------------------------------------------------------------
# Date-range search: "give me a window, tell me the best week(s) in it."
# Wraps engine/date_search.search_date_range, the same way search_trips()
# above wraps rank_trips -- no scoring/funnel logic is reimplemented here.
# ---------------------------------------------------------------------------

class FlightBookingLinkRequest(BaseModel):
    resort_name: str = Field(max_length=100)
    outbound_date: datetime.date
    return_date: datetime.date
    # The itinerary's real designators, e.g. ["A3 927", "A3 982"] --
    # the only stable identity a flight option has across fetches (see
    # cost_calculator.live_flight_booking_url's docstring).
    flight_numbers: List[Annotated[str, Field(max_length=16)]] = Field(min_length=1, max_length=8)
    # Must match what the search that showed the option used, or the
    # re-run is a different query and may not contain it.
    max_connections: Optional[int] = Field(default=None, ge=0, le=2)


class FlightBookingLinkResponse(BaseModel):
    # None whenever the deep link can't be built (itinerary no longer
    # offered, expired selection token, a failed return-leg fetch) --
    # the client falls back to the result's own flight_search_url,
    # never a broken link.
    url: Optional[str]


@router.post("/flight-booking-link", response_model=FlightBookingLinkResponse,
             dependencies=[Depends(enforce_booking_link_rate_limit)])
def flight_booking_link(payload: FlightBookingLinkRequest,
                        current_user: Optional[User] = Depends(get_current_user_for_search)):
    """
    A Google Flights booking-page deep link for ONE specific itinerary
    a search already showed, built at CLICK time.

    ON CLICK and not at search time, deliberately: each link costs one
    EXTRA, uncacheable live request (booking_url's own "choose return"
    fetch -- see adapters/google_flights_adapter.booking_url), so
    building one per shown option per result would multiply live
    traffic ~36x per search for links mostly nobody clicks. Built here,
    it costs one request for exactly the flight the user wants -- and
    is FRESHER than a link aged inside an old search response, since
    the selection token's long-term validity is unverified.

    NOT metered: the search that showed the option already paid its
    credits, and charging again for clicking what we offered would be
    punitive. Still behind the same per-IP rate limit as search.
    """
    _reject_past_date(payload.outbound_date, "outbound_date")
    if payload.return_date <= payload.outbound_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "return_date must be after outbound_date.")
    wanted = payload.resort_name.strip().lower()
    resort = next((r for r in _resort_cache if r.name.strip().lower() == wanted), None)
    if resort is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"Unknown resort: {payload.resort_name!r}")
    url = live_flight_booking_url(
        resort, payload.outbound_date, payload.return_date, origin_airport="TLV",
        max_connections=payload.max_connections, flight_numbers=payload.flight_numbers,
    )
    return FlightBookingLinkResponse(url=url)


class SearchDateRangeRequest(BaseModel):
    budget_eur_per_person: float = Field(gt=0)
    # See SearchRequest.min_budget_eur_per_person -- same contract.
    min_budget_eur_per_person: Optional[float] = Field(default=None, ge=0)
    # See SearchRequest.ski_days -- same contract.
    ski_days: int = Field(gt=0, le=30)
    earliest_date: datetime.date
    latest_date: datetime.date
    group_size: int = Field(default=2, gt=0, le=20)
    skill_level: str = "intermediate"
    accommodation_tier: str = "standard"
    food_profile: str = "normal"
    equipment_tier: str = "standard"
    # None = search across resorts (like search_trips); set this to pin
    # the search to one resort and just find the best DATES for it.
    target_resort: Optional[str] = None
    # See SearchRequest.include_resorts / exclude_resorts -- same
    # contract, generalizing target_resort to "these 2-3" or "all
    # except these".
    include_resorts: Optional[List[str]] = None
    exclude_resorts: Optional[List[str]] = None
    # See SearchRequest.max_connections -- same contract.
    max_connections: Optional[int] = Field(default=None, ge=0, le=2)
    # See rank_trips'/search_date_range's over-budget-fallback docstring.
    allow_over_budget_fallback: bool = True
    step_days: int = Field(default=1, gt=0, le=14)
    # Restrict candidate start dates to just this day of the week, e.g.
    # "saturday" -- a real, common preference (a week-long trip starting
    # mid-week splits a weekend across both ends). None = every day in
    # the window is a candidate (existing behavior, unchanged). When
    # set, step_days above is ignored -- see
    # date_search.candidate_start_dates' start_weekday docstring for why
    # the two don't combine.
    start_weekday: Optional[str] = None
    top_n: int = Field(default=10, gt=0, le=100)
    # At most this many dates from any ONE resort, so a single cheap
    # destination can't take every slot -- see
    # engine/date_search.cap_per_resort. Remaining slots are backfilled
    # by score, so pinning the search to one resort still returns a full
    # list of that resort's best dates. 0 disables the cap.
    max_results_per_resort: int = Field(default=3, ge=0, le=100)
    # See SearchRequest.preferred_transfer_modes -- same contract.
    preferred_transfer_modes: Optional[List[str]] = None
    weights: Dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))

    @field_validator("skill_level")
    @classmethod
    def _valid_skill(cls, v: str) -> str:
        if v not in VALID_SKILL_LEVELS:
            raise ValueError(f"skill_level must be one of {sorted(VALID_SKILL_LEVELS)}")
        return v

    @field_validator("accommodation_tier")
    @classmethod
    def _valid_accom_tier(cls, v: str) -> str:
        if v not in VALID_ACCOMMODATION_TIERS:
            raise ValueError(f"accommodation_tier must be one of {sorted(VALID_ACCOMMODATION_TIERS)}")
        return v

    @field_validator("food_profile")
    @classmethod
    def _valid_food(cls, v: str) -> str:
        if v not in VALID_FOOD_PROFILES:
            raise ValueError(f"food_profile must be one of {sorted(VALID_FOOD_PROFILES)}")
        return v

    @field_validator("equipment_tier")
    @classmethod
    def _valid_equipment(cls, v: str) -> str:
        if v not in VALID_EQUIPMENT_TIERS:
            raise ValueError(f"equipment_tier must be one of {sorted(VALID_EQUIPMENT_TIERS)}")
        return v

    @field_validator("preferred_transfer_modes")
    @classmethod
    def _valid_transfer_modes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        unknown = set(v) - _VALID_TRANSFER_MODES
        if unknown:
            raise ValueError(
                f"unknown transfer mode(s) {sorted(unknown)}; allowed: {sorted(_VALID_TRANSFER_MODES)}"
            )
        return v

    @field_validator("start_weekday")
    @classmethod
    def _valid_start_weekday(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        # "weekend" = Saturday-or-Sunday starts: Sat-to-Sat is the
        # classic package changeover, Sunday the established cheaper
        # one -- a weekend search needs both days as candidates.
        if v != "weekend" and v not in WEEKDAY_NAMES:
            raise ValueError(f"start_weekday must be one of {sorted(WEEKDAY_NAMES) + ['weekend']}")
        return v

    @field_validator("weights")
    @classmethod
    def _valid_weight_keys(cls, v: Dict[str, float]) -> Dict[str, float]:
        unknown = set(v) - VALID_WEIGHT_KEYS
        if unknown:
            raise ValueError(f"unknown weight key(s) {sorted(unknown)}; allowed: {sorted(VALID_WEIGHT_KEYS)}")
        if any(w < 0 for w in v.values()):
            raise ValueError("weights must be non-negative")
        if sum(v.values()) <= 0:
            raise ValueError("at least one weight must be positive")
        return v


class AlternativeDateOut(BaseModel):
    """
    One other good date for the same resort, from a different calendar
    week than the row it hangs off (the "More dates" expander -- see
    engine/date_search.spread_alternative_dates for why weeks). The
    total is the same static-or-live figure the engine ranked with;
    the *_is_live flags say which, per alternative, honestly.
    """
    start_date: datetime.date
    end_date: datetime.date
    season: str
    total_eur: float
    within_budget: bool
    flight_price_is_live: bool
    accommodation_price_is_live: bool


class DatedTripResultOut(BaseModel):
    resort: ResortOut
    start_date: datetime.date
    end_date: datetime.date
    season: str
    cost: CostBreakdownOut
    score: float
    score_components: Dict[str, float]
    explanation: str
    within_budget: bool
    # Other good dates for this resort in the searched window -- the
    # "More dates" expander. Empty for non-coverage rows.
    alternative_dates: List[AlternativeDateOut] = []
    # See TripResultOut's matching fields -- same contract.
    flight_search_url: Optional[str] = None
    accommodation_search_url: str
    accommodation_property_name: Optional[str] = None
    flight_options: List[FlightOptionOut] = []
    accommodation_options: List[AccommodationOptionOut] = []
    total_eur_with_fastest_flight: Optional[float] = None
    transfer_search_url: str
    equipment_search_url: str
    ski_pass_search_url: str
    weather: Optional[WeatherOut] = None


class SearchDateRangeResponse(BaseModel):
    query_resort_count: int
    candidate_dates_per_resort: int
    live_pricing_active: bool
    results: List[DatedTripResultOut]
    credits: Optional[CreditsOut] = None
    # See SearchResponse.live_pricing_blocked.
    live_pricing_blocked: bool = False


@router.post("/search-dates", response_model=SearchDateRangeResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search_trip_dates(payload: SearchDateRangeRequest, current_user: Optional[User] = Depends(get_current_user_for_search),
                      db: Session = Depends(get_db)):
    """
    "I want to go to resort X (or: anywhere), sometime in this window,
    for N nights -- find me the best deal(s)." Evaluates every valid
    N-night start date inside [earliest_date, latest_date] (e.g. a
    10-day window with a 7-night trip yields 4 candidate start dates:
    day 1, 2, 3, 4) and, for each, prices flight + accommodation live
    (no API key needed for either -- see google_flights_adapter.py and
    google_hotels_adapter.py), falling back to the static season-banded
    estimate for any date/resort where a live quote isn't available --
    never silently for the WHOLE search, only per missing quote,
    matching search_trips()'s existing degrade-visibly contract.
    """
    reset_provider_status()
    if payload.latest_date <= payload.earliest_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "latest_date must be after earliest_date")
    _reject_past_date(payload.latest_date, "latest_date")

    # A window that STARTS in the past but ends in the future is a real,
    # sensible request ("anytime from now on") -- clamp it to today
    # rather than rejecting, so we don't price start dates that have
    # already been and gone. Rejecting would be pedantic; silently
    # pricing the past would be wrong.
    effective_earliest = max(payload.earliest_date, datetime.date.today())
    window_days = (payload.latest_date - effective_earliest).days
    if window_days > MAX_SEARCH_WINDOW_DAYS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"date window is {window_days} days; the maximum is {MAX_SEARCH_WINDOW_DAYS}. "
            "Narrow the range -- searching further ahead than two seasons isn't meaningful.",
        )

    weight_sum = sum(payload.weights.values())
    normalized_weights = {k: v / weight_sum for k, v in payload.weights.items()}
    full_weights = dict(_DEFAULT_WEIGHTS)
    full_weights.update(normalized_weights)
    weight_sum_full = sum(full_weights.values())
    full_weights = {k: v / weight_sum_full for k, v in full_weights.items()}

    try:
        prefs = UserPreferences(
            budget_eur_per_person=payload.budget_eur_per_person,
            ski_days=payload.ski_days,
            group_size=payload.group_size,
            skill_level=payload.skill_level,
            accommodation_tier=payload.accommodation_tier,
            food_profile=payload.food_profile,
            equipment_tier=payload.equipment_tier,
            target_resort=payload.target_resort,
            include_resorts=payload.include_resorts,
            exclude_resorts=payload.exclude_resorts,
            preferred_transfer_modes=payload.preferred_transfer_modes,
            weights=full_weights,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # Same "choose resorts" contract as search_trips -- see that route's
    # comment. Narrowing itself now happens INSIDE search_date_range
    # (via prefs, see engine.scoring.narrow_resort_pool), so this route
    # always passes the full cache; it only validates names up front so
    # a typo 404s clearly instead of the engine silently matching nothing.
    _validate_resort_names([payload.target_resort] if payload.target_resort else None)
    _validate_resort_names(payload.include_resorts)
    _validate_resort_names(payload.exclude_resorts)

    if payload.start_weekday == "weekend":
        start_weekday, start_weekdays = None, {5, 6}  # Saturday + Sunday
    else:
        start_weekday = WEEKDAY_NAMES[payload.start_weekday] if payload.start_weekday else None
        start_weekdays = None

    # See search_trips' matching comment: neither live flight repricing
    # (adapters/google_flights_adapter.py) nor live accommodation
    # repricing (adapters/google_hotels_adapter.py) needs an API key any
    # more -- only a date-eligible request under the shared daily
    # live-pricing budget. live_pricing_allowed() spends budget as a
    # side effect, so it's called exactly once.
    live_reprice_allowed = live_pricing_allowed()

    flight_cost_fn = None
    accommodation_cost_fn = None
    if live_reprice_allowed:
        def flight_cost_fn(resort, start_date, end_date, _prefs):
            return live_flight_cost_eur(resort, start_date, end_date, origin_airport="TLV",
                                        max_connections=payload.max_connections)

        def accommodation_cost_fn(resort, start_date, end_date, _prefs):
            return live_accommodation_cost_eur_per_person(
                resort, start_date, nights=prefs.nights,
                group_size=payload.group_size, rooms_needed=prefs.rooms_needed,
            )

    # Charge for the REAL number of candidate start dates this search
    # will evaluate -- the same figure returned as
    # candidate_dates_per_resort, so a user can see what they paid for.
    # Computed before the engine runs, so an out-of-credits user is
    # refused without doing any of the work.
    planned_candidates = len(candidate_start_dates(
        effective_earliest, payload.latest_date, prefs.nights,
        payload.step_days, start_weekday, start_weekdays=start_weekdays))
    credit_info = _charge_credits(db, current_user, candidate_dates=planned_candidates)

    dated_options = search_date_range(
        _resort_cache, prefs, effective_earliest, payload.latest_date,
        shortlist_size=8, step_days=payload.step_days, start_weekday=start_weekday,
        start_weekdays=start_weekdays,
        top_n=payload.top_n,
        flight_cost_fn=flight_cost_fn, accommodation_cost_fn=accommodation_cost_fn,
        allow_over_budget_fallback=payload.allow_over_budget_fallback,
        # User-facing list: never pad the tail with duplicate resorts --
        # reproduced live: a two-resort pool returned Bansko x9. A
        # shorter varied list beats a padded one (see cap_per_resort).
        pad_with_duplicates=False,
        # Caps live pricing to a bounded number of (resort, date) pairs.
        #
        # RAISED FROM 6 TO 24 on 2026-08-27, once repricing was made
        # CONCURRENT (see date_search's _LIVE_PRICING_WORKERS). The old
        # cap was the single biggest reason users saw "EST." on most
        # rows: the frontend asks for 12 results, so a cap of 6 meant at
        # least half of them could never be live, no matter how well the
        # scrapers were working. Measured back to back on the same
        # window: cap 6 gave 3 of 12 live in 11.4s; cap 24 gave 12 of 12
        # live in 13.6s -- four times the real prices for two extra
        # seconds, because the lookups now overlap instead of queueing.
        #
        # Still capped rather than unbounded: the search SPACE is
        # resorts x candidate dates, easily hundreds of pairs, and each
        # one is a real scrape.
        live_reprice_n=_LIVE_REPRICE_N if live_reprice_allowed else None,
        max_results_per_resort=payload.max_results_per_resort,
    )

    if payload.min_budget_eur_per_person is not None:
        dated_options = [t for t in dated_options if t.cost.total_eur >= payload.min_budget_eur_per_person]

    # Snow re-ranking for the date-range engine too. This is the route
    # the FRONTEND ACTUALLY CALLS (components/SearchCard.tsx) -- wiring
    # it only into /trips/search meant the feature was dead code for
    # every real user, which a bug-hunt pass caught by measuring the
    # lookup count for each real frontend payload.
    #
    # Gated per result on ITS OWN start date, not one shared date: a
    # date-range search spans weeks, so some candidates fall inside the
    # forecast horizon and most do not. rerank_with_conditions returns
    # the same concrete type it was given (DatedTripOption here), so
    # start_date/end_date/season survive.
    if dated_options and _is_within_forecast_horizon(dated_options[0].start_date):
        dated_options = rerank_with_conditions(
            dated_options, full_weights,
            weather_fn=lambda resort: get_trip_weather(
                resort, dated_options[0].start_date, dated_options[0].end_date),
            max_lookups=_SNOW_RERANK_LOOKUPS,
        )

    candidate_dates = len(candidate_start_dates(
        effective_earliest, payload.latest_date, prefs.nights,
        payload.step_days, start_weekday, start_weekdays=start_weekdays))

    weather_by_index = _prefetch_weather({
        i: (t.resort, t.start_date, t.end_date) for i, t in enumerate(dated_options)
    })
    results = []
    for i, t in enumerate(dated_options):
        property_name = _accommodation_property_name(
            t.resort, t.start_date, prefs.nights, prefs.rooms_needed,
            t.cost.accommodation_price_is_live)
        results.append(DatedTripResultOut(
            alternative_dates=[AlternativeDateOut(
                start_date=a.start_date, end_date=a.end_date, season=a.season,
                total_eur=round(a.cost.total_eur, 2),
                within_budget=(a.cost.total_eur <= payload.budget_eur_per_person),
                flight_price_is_live=a.cost.flight_price_is_live,
                accommodation_price_is_live=a.cost.accommodation_price_is_live,
            ) for a in getattr(t, "alternatives", ())],
            resort=_to_resort_out(t.resort),
            start_date=t.start_date,
            end_date=t.end_date,
            season=t.season,
            cost=CostBreakdownOut(
                flight_eur=t.cost.flight_eur, transfer_eur=t.cost.transfer_eur,
                accommodation_eur=t.cost.accommodation_eur, ski_pass_eur=t.cost.ski_pass_eur,
                equipment_eur=t.cost.equipment_eur, food_eur=t.cost.food_eur,
                misc_eur=t.cost.misc_eur, total_eur=t.cost.total_eur,
                flight_price_is_live=t.cost.flight_price_is_live,
                accommodation_price_is_live=t.cost.accommodation_price_is_live,
                ski_pass_price_is_researched=t.cost.ski_pass_price_is_researched,
            ),
            score=t.score,
            score_components=t.score_components,
            explanation=explain(t, skill_level=payload.skill_level),
            within_budget=t.within_budget,
            flight_search_url=_flight_search_url(t.resort, t.start_date, t.end_date,
                                                 t.cost.flight_price_is_live, payload.max_connections,
                                                 attempt_booking_link=(i == 0)),
            accommodation_search_url=_accommodation_search_url(
                t.resort, t.start_date, t.end_date, prefs.nights, prefs.rooms_needed,
                t.cost.accommodation_price_is_live, attempt_booking_link=(i == 0),
                property_name=property_name),
            accommodation_property_name=property_name,
            flight_options=(_fo := _flight_options_out(
                t.resort, t.start_date, t.end_date,
                t.cost.flight_price_is_live, payload.max_connections, t.cost)),
            accommodation_options=_accommodation_options_out(
                t.resort, t.start_date, prefs.nights, prefs.rooms_needed,
                payload.group_size, t.cost.accommodation_price_is_live, t.cost),
            total_eur_with_fastest_flight=(max(o.trip_total_eur for o in _fo) if _fo else None),
            transfer_search_url=_transfer_search_url(t.resort, t.start_date,
                                                     payload.group_size, attempt=(i == 0)),
            equipment_search_url=_equipment_search_url(t.resort),
            ski_pass_search_url=_ski_pass_search_url(t.resort),
            weather=weather_by_index.get(i),
        ))

    return SearchDateRangeResponse(
        credits=credit_info,
        live_pricing_blocked=was_provider_blocked(),
        query_resort_count=len(_resort_cache),
        candidate_dates_per_resort=candidate_dates,
        live_pricing_active=flight_cost_fn is not None,
        results=results,
    )


@router.get("/credits", response_model=CreditsOut)
def get_search_credits(current_user: Optional[User] = Depends(get_current_user_for_search),
                       db: Session = Depends(get_db)):
    """
    Today's remaining search credits. Read-only -- checking a balance
    must never spend one. `cost` is 0 here because nothing was charged.
    """
    if current_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    st = credits_module.get_status(db, current_user.id)
    return CreditsOut(cost=0, remaining=st.remaining, daily_allowance=st.daily_allowance)
