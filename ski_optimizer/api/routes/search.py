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
from typing import Dict, List, Optional

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
    live_transfer_booking_url,
)
from ...engine.links import google_flights_url, google_hotels_url
from ...engine.scoring import rank_trips
from ...engine.transfers import get_transfer_options
from ...engine.date_search import search_date_range, candidate_start_dates, WEEKDAY_NAMES
from ...engine.weather import get_trip_weather
from ...nlp.explainer import explain
from ...db.models import User
from .auth import get_current_user_for_search
from ..rate_limit import enforce_search_rate_limit, live_pricing_allowed

router = APIRouter(prefix="/trips", tags=["trips"])

_DEFAULT_WEIGHTS = {
    "ski_quality": 0.30, "price": 0.20, "snow": 0.15,
    "nightlife": 0.15, "convenience": 0.10, "accommodation": 0.10,
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
    # A live booking link for the cheapest real transfer quote found
    # (adapters/transfer_adapter.py, Alps2Alps) -- display only, does
    # NOT feed into cost.transfer_eur or the score, which both still
    # use the static/curated estimate (see _transfer_search_url's own
    # docstring on why this pass deliberately stops short of that).
    # None when no live quote is available (provider doesn't cover
    # this resort/airport, or this isn't the top result -- same
    # top-result-only gating as weather/flight/accommodation booking
    # links).
    transfer_search_url: Optional[str] = None
    # See WeatherOut's own docstring. Only ever populated for the single
    # top-ranked result -- see _weather_for()'s docstring on why.
    weather: Optional[WeatherOut] = None


class SearchResponse(BaseModel):
    query_resort_count: int
    live_pricing_active: bool
    results: List[TripResultOut]


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
                            description=d.description, years_sampled=d.years_sampled)
            for d in summary.days
        ],
        avg_temp_max_c=summary.avg_temp_max_c,
        avg_temp_min_c=summary.avg_temp_min_c,
        avg_snowfall_cm=summary.avg_snowfall_cm,
    )


def _accommodation_search_url(resort: Resort, checkin_date, checkout_date, nights: int,
                              rooms_needed: int, accommodation_price_is_live: bool,
                              attempt_booking_link: bool) -> str:
    """
    A deep link to ONE specific property that was just live-priced,
    when available -- falling back to the resort-level, dated search
    link (google_hotels_url()) otherwise. Same shape and same
    "automatic, not just git-revert" fallback contract as
    _flight_search_url() above -- see that function's docstring, and
    adapters/google_hotels_adapter.specific_property_url()'s own
    docstring on what's unverified about the specific-property link.

    attempt_booking_link gates this per-result for the same reason as
    _flight_search_url()'s matching parameter: specific_property_url()
    makes a genuinely separate, uncached live request to the Knowledge
    Graph Search API, not covered by response_cache.py or
    live_pricing_allowed()'s budget -- callers pass True for only the
    single top result to bound this to at most one extra live request
    per response.
    """
    if attempt_booking_link and accommodation_price_is_live and checkin_date is not None:
        booking = live_accommodation_booking_url(
            resort, checkin_date, nights, rooms_needed, f"{resort.name}, {resort.country}")
        if booking:
            return booking
    return google_hotels_url(resort, checkin_date, checkout_date)


# This app's flight search only tracks a DATE, never an arrival TIME
# (see FlightOption/search results elsewhere) -- there is no real
# flight time to quote a transfer against. A mid-afternoon pickup is a
# reasonable placeholder for "the transfer exists and is roughly this
# price", not a claim about when any specific flight actually lands.
_ASSUMED_PICKUP_TIME = "14:00"


def _transfer_search_url(resort: Resort, pickup_date, group_size: int, attempt: bool) -> Optional[str]:
    """
    A booking link for the cheapest real transfer quote found
    (adapters/transfer_adapter.py, Alps2Alps) -- display only. Unlike
    _flight_search_url/_accommodation_search_url, this does NOT feed a
    live price back into cost.transfer_eur or the score: transfer_
    cost_eur_per_person() (engine/cost_calculator.py) runs for EVERY
    candidate resort during static scoring, not a capped top-N the way
    flight/accommodation costs are, so making it live there would
    multiply live requests across an entire search. Wiring that
    properly needs a transfer_cost_fn callback threaded through
    rank_trips/search_date_range the same way flight_cost_fn/
    accommodation_cost_fn already are -- a real engine change, not
    attempted this pass. This function only ever supplies a link, using
    _ASSUMED_PICKUP_TIME since no real flight time is tracked.

    attempt gates this to the single top result, same reasoning as
    every other live lookup here -- one real request (cached across the
    two calls this makes internally), not one per result.
    """
    if not attempt or pickup_date is None:
        return None
    return live_transfer_booking_url(resort, pickup_date, _ASSUMED_PICKUP_TIME, group_size)


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search_trips(payload: SearchRequest, current_user: Optional[User] = Depends(get_current_user_for_search)):
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

    results = [
        TripResultOut(
            resort=_to_resort_out(t.resort),
            cost=CostBreakdownOut(
                flight_eur=t.cost.flight_eur, transfer_eur=t.cost.transfer_eur,
                accommodation_eur=t.cost.accommodation_eur, ski_pass_eur=t.cost.ski_pass_eur,
                equipment_eur=t.cost.equipment_eur, food_eur=t.cost.food_eur,
                misc_eur=t.cost.misc_eur, total_eur=t.cost.total_eur,
                flight_price_is_live=t.cost.flight_price_is_live,
                accommodation_price_is_live=t.cost.accommodation_price_is_live,
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
                t.cost.accommodation_price_is_live, attempt_booking_link=(i == 0)),
            transfer_search_url=_transfer_search_url(t.resort, payload.outbound_date,
                                                     payload.group_size, attempt=(i == 0)),
            weather=_weather_out(t.resort, payload.outbound_date, return_date, attempt_weather=(i == 0)),
        )
        for i, t in enumerate(trip_options)
    ]

    return SearchResponse(query_resort_count=len(_resort_cache),
                          live_pricing_active=live_pricing_active, results=results)


@router.get("/resorts", response_model=List[str])
def list_resort_names(current_user: Optional[User] = Depends(get_current_user_for_search)):
    """Lets an authenticated client populate a 'fixed resort' dropdown without guessing names."""
    return sorted(r.name for r in _resort_cache)


# ---------------------------------------------------------------------------
# Date-range search: "give me a window, tell me the best week(s) in it."
# Wraps engine/date_search.search_date_range, the same way search_trips()
# above wraps rank_trips -- no scoring/funnel logic is reimplemented here.
# ---------------------------------------------------------------------------

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
        if v not in WEEKDAY_NAMES:
            raise ValueError(f"start_weekday must be one of {sorted(WEEKDAY_NAMES)}")
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
    # See TripResultOut's matching fields -- same contract.
    flight_search_url: Optional[str] = None
    accommodation_search_url: str
    transfer_search_url: Optional[str] = None
    weather: Optional[WeatherOut] = None


class SearchDateRangeResponse(BaseModel):
    query_resort_count: int
    candidate_dates_per_resort: int
    live_pricing_active: bool
    results: List[DatedTripResultOut]


@router.post("/search-dates", response_model=SearchDateRangeResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search_trip_dates(payload: SearchDateRangeRequest, current_user: Optional[User] = Depends(get_current_user_for_search)):
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
    if payload.latest_date <= payload.earliest_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "latest_date must be after earliest_date")

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

    start_weekday = WEEKDAY_NAMES[payload.start_weekday] if payload.start_weekday else None

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

    dated_options = search_date_range(
        _resort_cache, prefs, payload.earliest_date, payload.latest_date,
        shortlist_size=8, step_days=payload.step_days, start_weekday=start_weekday,
        top_n=payload.top_n,
        flight_cost_fn=flight_cost_fn, accommodation_cost_fn=accommodation_cost_fn,
        allow_over_budget_fallback=payload.allow_over_budget_fallback,
        # Caps live pricing to a fast number of (resort, date) pairs --
        # measured over 20s and dozens of scrape calls per request
        # without this (see search_date_range's live_reprice_n
        # docstring). Matters for LATENCY now even though flight calls
        # are no longer quota-metered -- each scrape still costs real
        # wall-clock time. Only matters when live pricing is actually
        # active; harmless/unused otherwise.
        live_reprice_n=6 if live_reprice_allowed else None,
    )

    if payload.min_budget_eur_per_person is not None:
        dated_options = [t for t in dated_options if t.cost.total_eur >= payload.min_budget_eur_per_person]

    candidate_dates = len(candidate_start_dates(
        payload.earliest_date, payload.latest_date, prefs.nights,
        payload.step_days, start_weekday))

    results = [
        DatedTripResultOut(
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
                t.cost.accommodation_price_is_live, attempt_booking_link=(i == 0)),
            transfer_search_url=_transfer_search_url(t.resort, t.start_date,
                                                     payload.group_size, attempt=(i == 0)),
            weather=_weather_out(t.resort, t.start_date, t.end_date, attempt_weather=(i == 0)),
        )
        for i, t in enumerate(dated_options)
    ]

    return SearchDateRangeResponse(
        query_resort_count=len(_resort_cache),
        candidate_dates_per_resort=candidate_dates,
        live_pricing_active=flight_cost_fn is not None,
        results=results,
    )
