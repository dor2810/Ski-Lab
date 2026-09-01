"""
Core data models for the ski trip optimizer.

Everything here is deliberately plain dataclasses (no ORM) so this module
has zero dependencies and can be swapped straight into a Postgres-backed
version later (Section 6 of the project blueprint) without touching the
calculation/scoring logic.
"""
from dataclasses import dataclass, field
from datetime import date as _date, datetime as _datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # avoids a circular import at runtime (terrain.py imports nothing from here)
    from .engine.terrain import TerrainMix


# ---------------------------------------------------------------------------
# Resort data (loaded from data/ski_resort_database_seed.xlsx)
# ---------------------------------------------------------------------------

@dataclass
class Resort:
    name: str
    country: str
    region: str
    base_elevation_m: int
    summit_elevation_m: int
    vertical_drop_m: int
    num_lifts: int
    piste_km: float
    off_piste_rating: int          # 1-5
    snow_reliability: int          # 1-5
    nightlife_rating: int          # 1-5
    family_friendliness: int       # 1-5
    nearest_airport: str
    airport_distance_km: float
    transfer_time_minutes: float   # parsed midpoint of the "typical transfer time" range
    ski_pass_6day_eur: float
    accommodation_eur_per_night: float  # per room, mid-range, from the seed data
    needs_verification: bool = False
    # Structured beginner/intermediate/advanced split, read directly from
    # the spreadsheet's numeric terrain columns (see data_loader). Always
    # populated now -- every resort has real numbers or a clearly-flagged
    # estimate; see terrain_data_quality for which.
    terrain_mix: Optional["TerrainMix"] = None
    terrain_data_quality: str = "estimated"  # 'sourced' | 'sourced_conflicting' | 'estimated'
    # Extended data (added this session): snowfall/glacier/season/terrain
    # park/Israeli flight access. All 30 seed resorts have a value for
    # each; extended_data_quality says how reliable that value is.
    avg_annual_snowfall_cm: Optional[int] = None
    glacier_access: Optional[str] = None       # free text, not boolean -- see repo README
    typical_season: Optional[str] = None
    terrain_park: Optional[str] = None
    israeli_flight_access: Optional[str] = None
    extended_data_quality: str = "estimated"  # 'sourced' | 'sourced_conflicting' | 'mixed' | 'estimated'
    # Per-airport transfer times, e.g. {"GVA": 150.0, "CMF": 105.0}.
    # transfer_time_minutes above AVERAGES across airports, which
    # describes no real journey when a resort has two -- see
    # data/resort_repository.parse_transfer_minutes_by_airport. Use
    # transfer_minutes_for(code) rather than the averaged field whenever
    # the arrival airport is known.
    transfer_minutes_by_airport: dict = field(default_factory=dict)
    # Resort-village coordinates (not the wider ski AREA's centroid) --
    # feeds adapters/weather_adapter.py, which needs real lat/lon, not a
    # geocode-per-request live dependency for something that never
    # moves. Sourced from Open-Meteo's own free geocoding API, spot-
    # checked against known real values; a few resorts needed a nearby-
    # village proxy (see resort_repository.py's own note on which and
    # why). None (not 0.0) when absent -- 0,0 is a real ocean point off
    # the African coast, the classic silent-wrong-default trap.
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def transfer_minutes_for(self, airport_iata: Optional[str] = None) -> float:
        """
        Transfer time for a SPECIFIC arrival airport, falling back to the
        averaged figure only when the airport is unknown or unlisted.
        """
        if airport_iata:
            specific = self.transfer_minutes_by_airport.get(airport_iata.strip().upper())
            if specific is not None:
                return specific
        return self.transfer_time_minutes


# ---------------------------------------------------------------------------
# User input
# ---------------------------------------------------------------------------

# Single source of truth for valid enum values. api/routes/search.py and
# api/schemas.py import these rather than re-declaring their own literal
# sets -- previously the API had its own hardcoded copies, which would
# silently drift out of sync the moment a new tier or skill level was
# added in one place and not the other.
VALID_SKILL_LEVELS = frozenset({"beginner", "intermediate", "advanced", "expert"})
VALID_ACCOMMODATION_TIERS = frozenset({"budget", "standard", "luxury"})
VALID_FOOD_PROFILES = frozenset({"budget", "normal", "luxury"})
VALID_EQUIPMENT_TIERS = frozenset({"standard", "premium"})
# The original six dimensions. Every caller must supply all of these --
# a partial weights dict is a real bug class (it silently means "score
# only on the dimensions I remembered"), and this guard has caught it.
REQUIRED_WEIGHT_KEYS = frozenset({
    "ski_quality", "price", "snow", "nightlife", "convenience", "accommodation",
})

# Dimensions added after launch are OPTIONAL and default to 0.0, so that
# adding one can never break an existing caller or silently re-rank
# results that nobody asked to change.
#
# "family" was added 2026-08-27: Resort.family_friendliness had existed
# since the beginning but was never scored -- real researched data
# sitting dead, while "is this good for kids?" is one of the most common
# real questions about a ski trip (Iglu Ski and Crystal both surface
# families as a top-level filter).
OPTIONAL_WEIGHT_KEYS = frozenset({"family"})

VALID_WEIGHT_KEYS = REQUIRED_WEIGHT_KEYS | OPTIONAL_WEIGHT_KEYS

# Upper bound on people-per-room. Guards against a group_size/rooms_needed
# combination that would invent unrealistic per-person savings (12 people
# in 1 room previously priced at EUR 29/person).
MAX_OCCUPANTS_PER_ROOM = 4


@dataclass
class UserPreferences:
    # --- hard constraints ---
    budget_eur_per_person: float
    # The number of FULL days actually spent on the mountain -- what a
    # traveler is really asking for ("I want 6 ski days"), not the
    # number of nights away. Nights away is ALWAYS ski_days + 1 (see the
    # `nights` property below): you need to arrive the evening before
    # your first ski day and can fly home the day after your last one.
    #
    # This deliberately does NOT try to model the two-way dependency the
    # product spec flags -- whether that extra night is really 1 or 2
    # depends on actual flight departure/arrival CLOCK times (a redeye
    # vs. an early-morning flight can turn a ski day into a travel day
    # or vice versa) -- because adapters/flight_adapter.py's FlightOption
    # doesn't capture clock times today, only dates. +1 night is the
    # realistic, common-case default (a package advertised as "6 days
    # skiing" is almost always sold as 7 nights), documented as an
    # approximation rather than silently treated as exact.
    ski_days: int
    group_size: int = 2

    # --- trip style (used by the static cost model) ---
    skill_level: str = "intermediate"      # beginner | intermediate | advanced | expert
    accommodation_tier: str = "standard"   # budget | standard | luxury
    # WHICH property to price the trip on. accommodation_tier above only
    # nudges which RESORT scores well (engine/scoring.py), using that
    # resort's average nightly rate -- it never chose a property, which
    # is why every trip came back priced on the cheapest bed found.
    accommodation_filter: Optional["AccommodationFilter"] = None
    food_profile: str = "normal"           # budget | normal | luxury
    equipment_tier: str = "standard"       # standard | premium
    rooms_needed: Optional[int] = None     # defaults to ceil(group_size / 2) if not set
    target_resort: Optional[str] = None    # set this to evaluate ONE resort only ("fixed resort" mode)
    # Generalized versions of target_resort, for "search just these 2-3
    # resorts" or "search everywhere except Val Thorens". Matched
    # case/whitespace-insensitively, same as target_resort. If
    # target_resort is ALSO set, target_resort wins (kept for exact
    # backward compat with existing single-pin callers) -- these two are
    # meant to be used instead of it, not combined with it. include and
    # exclude CAN combine (include narrows the pool, exclude then removes
    # from what's left), though in practice a caller would normally use
    # one or the other.
    include_resorts: Optional[list] = None
    exclude_resorts: Optional[list] = None
    # When set, enables season-band cost adjustment (see cost_calculator.py)
    # and, when a flight_cost_fn is also supplied to rank_trips(), live
    # flight repricing for the top candidates. None reproduces the
    # previous date-agnostic behavior exactly.
    outbound_date: Optional[_date] = None
    # Transfer modes the user is willing to take. None = no preference.
    # Real constraints, not fussiness: some people won't drive abroad in
    # winter, some won't share a shuttle with strangers. Applied as a
    # soft filter in engine/transfers.select_transfer -- if the
    # preference would leave no viable option, it's relaxed rather than
    # returning nothing.
    preferred_transfer_modes: Optional[list] = None

    # --- soft preference weights (must sum to 1.0; see scoring.py) ---
    # ski_quality folds together piste length + off-piste reputation.
    weights: dict = field(default_factory=lambda: {
        "ski_quality": 0.30,
        "price": 0.20,
        "snow": 0.15,
        "nightlife": 0.15,
        "convenience": 0.10,
        "accommodation": 0.10,
    })

    def __post_init__(self):
        # Validate in the DOMAIN MODEL, not just at the API boundary.
        # api/routes/search.py has its own Pydantic validation, but the
        # CLI, tests, and any direct library use bypass that entirely --
        # so without these checks, `UserPreferences(trip_nights=-3)`
        # produced NEGATIVE trip costs that then sailed through the
        # budget filter and were returned as valid ranked results.
        # Validating once here means every caller is protected.
        if self.budget_eur_per_person <= 0:
            raise ValueError(f"budget_eur_per_person must be > 0, got {self.budget_eur_per_person}")
        if self.ski_days <= 0:
            raise ValueError(f"ski_days must be > 0, got {self.ski_days}")
        if self.group_size <= 0:
            # Previously a ZeroDivisionError deep inside the cost
            # calculator -- a clear message at construction is far more
            # useful than a stack trace from arithmetic three calls down.
            raise ValueError(f"group_size must be > 0, got {self.group_size}")

        # Reject unknown enum values rather than silently substituting a
        # default. Before this, a typo like skill_level='expret' was
        # quietly scored as 'intermediate' and food_profile='TYPO' was
        # quietly priced as 'normal' -- the user got plausible-looking
        # numbers for preferences they never expressed, which is worse
        # than an error because nothing looks wrong.
        for field_name, value, allowed in (
            ("skill_level", self.skill_level, VALID_SKILL_LEVELS),
            ("accommodation_tier", self.accommodation_tier, VALID_ACCOMMODATION_TIERS),
            ("food_profile", self.food_profile, VALID_FOOD_PROFILES),
            ("equipment_tier", self.equipment_tier, VALID_EQUIPMENT_TIERS),
        ):
            if value not in allowed:
                raise ValueError(
                    f"{field_name} must be one of {sorted(allowed)}, got {value!r}"
                )

        if self.rooms_needed is None:
            self.rooms_needed = max(1, -(-self.group_size // 2))  # ceil division
        elif self.rooms_needed <= 0:
            raise ValueError(f"rooms_needed must be > 0, got {self.rooms_needed}")
        elif self.rooms_needed > self.group_size:
            # Physically nonsensical and financially significant: booking
            # 100 rooms for a solo traveler was previously accepted and
            # produced a EUR 35,000 per-person accommodation cost. Nobody
            # books more rooms than people.
            raise ValueError(
                f"rooms_needed ({self.rooms_needed}) cannot exceed group_size "
                f"({self.group_size}) -- you can't book more rooms than people"
            )
        elif self.group_size / self.rooms_needed > MAX_OCCUPANTS_PER_ROOM:
            # The opposite failure: 12 people in 1 room was accepted and
            # produced an implausibly cheap EUR 29/person. Cap occupancy
            # so the model can't quietly invent unrealistic savings.
            raise ValueError(
                f"group_size {self.group_size} across {self.rooms_needed} room(s) "
                f"exceeds {MAX_OCCUPANTS_PER_ROOM} people per room"
            )

        if not self.weights:
            raise ValueError("weights must not be empty")
        unknown = set(self.weights) - VALID_WEIGHT_KEYS
        if unknown:
            raise ValueError(
                f"unknown weight key(s) {sorted(unknown)}; allowed: {sorted(VALID_WEIGHT_KEYS)}"
            )
        missing = REQUIRED_WEIGHT_KEYS - set(self.weights)
        if missing:
            raise ValueError(
                f"missing weight key(s) {sorted(missing)}; every required dimension must be present"
            )
        # Fill optional dimensions the caller didn't mention. Done BEFORE
        # the sum check so an existing six-key dict still sums to 1.0.
        for key in OPTIONAL_WEIGHT_KEYS:
            self.weights.setdefault(key, 0.0)
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(f"weights must be non-negative, got {self.weights}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total:.3f}: {self.weights}")

    @property
    def nights(self) -> int:
        """Nights away = ski_days + 1. See ski_days' field comment for why."""
        return self.ski_days + 1


# ---------------------------------------------------------------------------
# Flight data (from adapters/flight_adapter.py)
# ---------------------------------------------------------------------------

@dataclass
class FlightOption:
    """
    A real, priced flight itinerary. This is the BOUNDARY TYPE between
    adapters/ and engine/: whatever provider we're on (SerpApi today,
    Duffel later, both eventually), the adapter normalizes into this,
    and engine/ never sees a provider-specific response shape. Swapping
    or adding a provider should not require touching engine/ at all.

    Deliberately provider-neutral -- no SerpApi tokens, no Duffel offer
    IDs at this level. `booking_token` is the one concession: an opaque
    provider-specific handle the adapter can pass back to ITSELF later
    to fetch booking options. engine/ should treat it as meaningless --
    only the adapter that produced it (google_flights_adapter.py's
    booking_url()) knows how to use it.
    """
    price_eur: float
    origin_airport: str          # IATA, e.g. "TLV"
    destination_airport: str     # IATA, e.g. "GVA"
    airline: str
    total_duration_minutes: int
    stops: int                   # 0 = nonstop; enforces the blueprint's max-connections hard constraint
    is_round_trip: bool = True
    booking_token: Optional[str] = None  # opaque, provider-specific; see docstring
    # Real flight designators for each leg, in order, e.g. ["LX 253",
    # "LX 1234"]. Provider-NEUTRAL despite being scraped: a flight
    # number is a fact about the flight, not about who told us. Empty
    # when the provider didn't supply them -- never faked, since a wrong
    # flight number is worse than no flight number to someone standing
    # at a departure board.
    flight_numbers: list = field(default_factory=list)
    # When this itinerary LANDS, local time at the destination -- the
    # fact an airport transfer is booked around. Kept because the
    # transfer pickup time was otherwise a hardcoded guess (see
    # api/routes/search._pickup_time_for): quoting a 14:00 pickup for a
    # flight landing at 21:40 is a wrong number, and this project
    # treats a wrong number as worse than a missing one. None when the
    # provider didn't supply it -- never inferred from duration, since
    # that would silently reintroduce the timezone bug the duration
    # field itself was fixed for.
    arrival_time: Optional[_datetime] = None
    # When the RETURN flight departs, local time at the ski-side
    # airport. Feeds the return transfer: Alps2Alps takes a departure
    # time and computes the resort pickup itself. None unless the
    # provider gave us a real inbound leg -- never inferred.
    return_departure_time: Optional[_datetime] = None
    # How long the RETURN leg flies. total_duration_minutes above is
    # the OUTBOUND only (see the google adapter's own note: "first
    # departure to last arrival"), so a door-to-door timeline that
    # reused it for the way home would be quietly wrong on any
    # asymmetric itinerary. None when the provider didn't say.
    return_duration_minutes: Optional[int] = None


@dataclass
class PriceInsight:
    """
    Market context for a route/date: how the cheapest current fare
    compares to what's typical, plus history where available.

    This is the raw material for the blueprint's "move your trip 2 days
    and save EUR 320" feature, and it's a genuine differentiator -- a
    single-seller API (a GDS, or Duffel) can tell you ITS price, but
    not whether that price is good. Not every provider supplies this;
    it's None when unavailable, never faked.
    """
    lowest_price_eur: float
    typical_range_eur: Optional[tuple] = None   # (low, high)
    price_level: Optional[str] = None           # provider's own label, e.g. "low"/"typical"/"high"
    # [(unix_timestamp, price), ...] -- worth PERSISTING as it arrives:
    # it becomes our own asset, independent of any provider, and feeds
    # jobs/trip_watcher.py later.
    price_history: Optional[list] = None


@dataclass
class FlightSearchResult:
    """What a flight search returns: the options plus market context."""
    options: list                                # List[FlightOption]
    insight: Optional[PriceInsight] = None
    from_cache: bool = False
    # True when the provider LISTED flights but priced none of them --
    # seen live 2026-08-28 from the Cloud Run egress IP, where Google
    # serves schedule data with every fare stripped while the same
    # query from a residential IP has prices. Distinct from an empty
    # result (no service): this means "the data exists and we were
    # refused it", which callers treat like a block (paid fallback,
    # honest reporting) rather than like an empty route.
    fares_suppressed: bool = False


# ---------------------------------------------------------------------------
# Accommodation data (from adapters/accommodation_adapter.py)
# ---------------------------------------------------------------------------

@dataclass
class AccommodationOption:
    """
    A real, priced accommodation listing. Same BOUNDARY TYPE role as
    FlightOption: whatever provider we're on (Booking.com Demand API is
    the target; Expedia Rapid/Hotelbeds are the alternatives if that
    doesn't pan out -- see PROJECT_STATE.md), the adapter normalizes into
    this, and engine/ never sees a provider-specific response shape.
    """
    price_eur_per_night: float
    property_name: str
    rating: Optional[float] = None                 # provider's own scale, not normalized
    distance_to_lifts_km: Optional[float] = None
    # QUALITY ATTRIBUTES. Only the `stays` source supplies these (see
    # adapters/stays_adapter.py); the primary scraper cannot, so they
    # are None on any property that source did not also return. None
    # means UNKNOWN and must never be rendered as "1 star" or "no
    # reviews" -- a property Google has not classified is not a bad
    # property.
    star_class: Optional[int] = None               # 1-5, the hotel's own classification
    review_count: Optional[int] = None             # how many reviews `rating` averages
    amenities: Optional[list] = None               # provider's own vocabulary, e.g. ["SPA", "PARKING"]
    # WHERE a star claim comes from. "published" = the provider told us
    # this property's class. "provider_filter" = the provider filtered
    # the search to a class range but did not publish the individual
    # class, so we may say what we ASKED for and must not print stars
    # against the property. None = no claim either way.
    star_class_source: Optional[str] = None
    cancellation_policy: Optional[str] = None       # free text, e.g. "free_cancellation", "non_refundable"
    booking_token: Optional[str] = None             # opaque, provider-specific; see FlightOption's docstring


@dataclass(frozen=True)
class AccommodationFilter:
    """
    What the traveller will accept for a bed, as a constraint on WHICH
    property the trip is priced on.

    WHY IT EXISTS: every trip used to be priced on the cheapest bed the
    search returned, whatever it was, while the only accommodation knob
    in the API (accommodation_tier) merely nudged which RESORT scored
    well, using that resort's average nightly rate -- it never touched
    the property. So asking for "luxury" still costed the trip on a
    hostel.

    All fields optional; None means "no constraint". A property whose
    star_class or rating is UNKNOWN cannot satisfy a floor on that
    field -- see engine/cost_calculator.select_live_accommodation.
    """
    # A ceiling on this trip's accommodation line, per person, for the
    # WHOLE stay -- the same unit the cost breakdown shows, not a
    # nightly rate.
    max_eur_per_person: Optional[float] = None
    min_star_class: Optional[int] = None          # 1-5, the property's own classification
    min_rating: Optional[float] = None            # guest review score, provider's scale
    # NOT SURFACED IN THE PRODUCT, deliberately: the provider's amenity
    # data is a truncated, partly wrong subset (BEACH_ACCESS on 65% of
    # ALPINE properties; WIFI on 0% yet its filter matches nearly
    # everything) and its filter does not discriminate. Measurements in
    # adapters/stays_adapter._parse_hotel. Re-measure before using.
    required_amenities: Optional[list] = None     # provider vocabulary, e.g. ["SPA"]
    # Straight-line km to the nearest lift (adapters/lift_distance.py).
    # The owner's stated first question about any ski bed.
    max_distance_to_lifts_km: Optional[float] = None
    # Guards a rating floor against thin data: 4.7 from 34 reviews is
    # not the same claim as 4.4 from 1,401 (both seen live).
    min_review_count: Optional[int] = None

    def is_empty(self) -> bool:
        return (self.max_eur_per_person is None and self.min_star_class is None
                and self.min_rating is None and not self.required_amenities
                and self.max_distance_to_lifts_km is None
                and self.min_review_count is None)


@dataclass(frozen=True)
class AccommodationChoiceReport:
    """
    How a filtered pick went, so the UI can say what happened instead of
    silently showing fewer results. `unrated_set_aside` is the honest
    part: properties dropped only because the provider publishes no
    star class or rating for them, not because they failed the test.
    """
    considered: int = 0
    matched: int = 0
    unrated_set_aside: int = 0
    cheapest_available_eur_per_person: Optional[float] = None
    # True when NOTHING carried a class/rating to judge by and the pick
    # is therefore an unclassified property. The trip is real and
    # priced, but the quality floor was NOT verified -- callers must
    # say so rather than implying the filter was met.
    # Properties the PROVIDER filtered to the requested class but whose
    # individual class it does not publish. Real vetting we cannot
    # re-check -- neither a verified match nor an unknown.
    provider_vetted: int = 0
    fell_back_to_unrated: bool = False
    # True when every property WAS rated and every one sat below the
    # floor, so the pick is a real place that is known not to meet it.
    # Still better than returning nothing: returning nothing sends the
    # ranker back to a static estimate, replacing a real price with a
    # generic guess. Flagged so the UI never implies a match.
    fell_back_below_floor: bool = False


@dataclass
class AccommodationSearchResult:
    """What an accommodation search returns."""
    options: list                                # List[AccommodationOption]
    from_cache: bool = False


# ---------------------------------------------------------------------------
# Weather data (from adapters/weather_adapter.py)
# ---------------------------------------------------------------------------

@dataclass
class WeatherForecast:
    """
    A real daily forecast for one date -- BOUNDARY TYPE for
    adapters/weather_adapter.py, same role as FlightOption/
    AccommodationOption. Only exists for dates within the provider's
    actual forecast horizon (see get_forecast()'s docstring); a date
    beyond that returns None rather than this with invented numbers.
    """
    date: _date
    temp_max_c: float
    temp_min_c: float
    snowfall_cm: float
    snow_depth_cm: float  # actual ground/base snow depth, NOT recent snowfall -- see snowfall_cm
    weather_description: str  # human-readable, decoded from the provider's WMO weather code


@dataclass
class TransferQuote:
    """
    A real, live-priced airport-to-resort transfer vehicle option --
    BOUNDARY TYPE for adapters/transfer_adapter.py, same role as
    FlightOption/AccommodationOption. Deliberately NOT the same type as
    engine/transfers.TransferOption: that one models CURATED, static
    rate-card entries (round-trip discounts, day-of-week service
    availability, sourced/estimated provenance tagging) -- concepts a
    live per-request quote doesn't carry -- rather than forcing two
    genuinely different shapes into one.
    """
    price_eur: float
    cost_basis: str  # "per_vehicle" for every quote this adapter returns -- see its module docstring
    vehicle_name: str
    max_passengers: int
    duration_minutes: float
    operator: str = "Alps2Alps"
    booking_url: Optional[str] = None


@dataclass
class TransferSearchResult:
    """What a live transfer search returns."""
    options: list  # List[TransferQuote]
    from_cache: bool = False
    # The RETURN leg, when the request asked for a round trip (another
    # TransferSearchResult, or None). It rides on the SAME provider
    # response as the outbound -- Alps2Alps prices both legs in one
    # request, and cheaper together than as two one-ways -- so it is
    # attached here rather than returned separately, keeping every
    # existing single-leg caller unchanged.
    return_options: Optional["TransferSearchResult"] = None
    # The operator's OWN computed pickup timestamps ("YYYY-MM-DD
    # HH:MM:SS"). The return one is the valuable one: given the return
    # FLIGHT'S departure time, Alps2Alps works out when the coach must
    # leave the resort (measured: a 17:20 flight -> an 11:10 pickup),
    # which is its drive-time-plus-check-in logic, not ours.
    outbound_pickup: Optional[str] = None
    return_pickup: Optional[str] = None


@dataclass
class HistoricalWeatherAverage:
    """
    "What's it usually like around these dates" -- averaged across
    several past years' real recorded weather for the SAME calendar
    window, not a forecast. Useful for trips too far out for
    get_forecast() to cover (the overwhelming majority of ski-trip
    searches, booked months ahead).
    """
    avg_temp_max_c: float
    avg_temp_min_c: float
    avg_snowfall_cm: float
    avg_snow_depth_cm: float  # actual ground/base snow depth, NOT recent snowfall
    years_sampled: int  # how many past years' data actually went into the average
    date_range_label: str  # e.g. "Jan 10 - Jan 17"


@dataclass
class DailyWeather:
    """
    ONE day of a trip's weather -- a real forecast when the day falls
    within adapters/weather_adapter.py's ~16-day horizon
    (is_live_forecast True, description set), otherwise a historical
    average for that SAME calendar day across several past years
    (is_live_forecast False, years_sampled set) -- see
    get_forecast_range()/get_historical_daily_breakdown()'s own
    docstrings. Each day decides independently, so a trip whose dates
    straddle the forecast horizon gets a genuine mix, not one data
    source forced onto the whole trip.
    """
    date: _date
    temp_max_c: float
    temp_min_c: float
    snowfall_cm: float
    snow_depth_cm: float  # actual ground/base snow depth, NOT recent snowfall -- see snowfall_cm
    is_live_forecast: bool
    description: Optional[str] = None       # only ever set for a live-forecast day
    years_sampled: Optional[int] = None      # only ever set for a historical day


@dataclass
class TripWeatherSummary:
    """
    A whole trip's weather -- one DailyWeather per calendar day from
    check-in to check-out inclusive, plus an overall average across
    every one of those days (mixing forecast and historical days
    together when the trip straddles the horizon -- still an honest
    "what to expect this week" figure, since both sources answer the
    same underlying question, just for different date ranges).
    """
    days: list  # List[DailyWeather], sorted by date
    avg_temp_max_c: float
    avg_temp_min_c: float
    avg_snowfall_cm: float
    avg_snow_depth_cm: float  # actual ground/base snow depth, NOT recent snowfall


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class CostBreakdown:
    flight_eur: float
    transfer_eur: float
    accommodation_eur: float
    ski_pass_eur: float
    equipment_eur: float
    food_eur: float
    misc_eur: float
    # Data-quality tag for flight_eur specifically, matching the project's
    # sourced/estimated convention elsewhere (Resort.terrain_data_quality,
    # TransferOption.data_quality). False = the flat per-country estimate;
    # True = a real quote from adapters/flight_adapter.py.
    flight_price_is_live: bool = False
    # Same idea for accommodation_eur -- False = the seed spreadsheet's
    # season-banded estimate; True = a real quote from
    # adapters/serpapi_hotel_adapter.py via
    # cost_calculator.apply_live_accommodation_price.
    accommodation_price_is_live: bool = False
    # Same idea for ski_pass_eur -- False = the seed spreadsheet's
    # estimate; True = a REAL published 6-day price researched from the
    # resort's own ticketing pages (data/ski_pass_prices.py, 29 of 37
    # resorts). Not "live" like the two above -- nobody is quoting this
    # per-request -- but genuinely sourced rather than guessed, which is
    # the distinction that matters to a user reading the number.
    ski_pass_price_is_researched: bool = False
    # Same idea for transfer_eur -- False = the curated/formula figure
    # (engine/transfers.py); True = a per-request Alps2Alps quote for
    # THIS date, party size and pickup time, via
    # cost_calculator.apply_live_transfer_price.
    transfer_price_is_live: bool = False

    @property
    def total_eur(self) -> float:
        return (self.flight_eur + self.transfer_eur + self.accommodation_eur
                + self.ski_pass_eur + self.equipment_eur + self.food_eur + self.misc_eur)


@dataclass
class TripOption:
    resort: Resort
    cost: CostBreakdown
    score: float                 # 0-1, weighted composite
    score_components: dict       # per-dimension 0-1 scores, for the explanation
    # True unless this is a FALLBACK result: nothing fit the stated budget,
    # so rank_trips() returned the cheapest option(s) it found anyway
    # rather than an empty list -- see rank_trips' docstring. The caller
    # (API/frontend) must show this honestly, not silently present an
    # over-budget trip as if it fit.
    within_budget: bool = True
