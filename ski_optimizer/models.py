"""
Core data models for the ski trip optimizer.

Everything here is deliberately plain dataclasses (no ORM) so this module
has zero dependencies and can be swapped straight into a Postgres-backed
version later (Section 6 of the project blueprint) without touching the
calculation/scoring logic.
"""
from dataclasses import dataclass, field
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
VALID_WEIGHT_KEYS = frozenset({
    "ski_quality", "price", "snow", "nightlife", "convenience", "accommodation",
})

# Upper bound on people-per-room. Guards against a group_size/rooms_needed
# combination that would invent unrealistic per-person savings (12 people
# in 1 room previously priced at EUR 29/person).
MAX_OCCUPANTS_PER_ROOM = 4


@dataclass
class UserPreferences:
    # --- hard constraints ---
    budget_eur_per_person: float
    trip_nights: int
    group_size: int = 2

    # --- trip style (used by the static cost model) ---
    skill_level: str = "intermediate"      # beginner | intermediate | advanced | expert
    accommodation_tier: str = "standard"   # budget | standard | luxury
    food_profile: str = "normal"           # budget | normal | luxury
    equipment_tier: str = "standard"       # standard | premium
    rooms_needed: Optional[int] = None     # defaults to ceil(group_size / 2) if not set
    target_resort: Optional[str] = None    # set this to evaluate ONE resort only ("fixed resort" mode)
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
        if self.trip_nights <= 0:
            raise ValueError(f"trip_nights must be > 0, got {self.trip_nights}")
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
        missing = VALID_WEIGHT_KEYS - set(self.weights)
        if missing:
            raise ValueError(
                f"missing weight key(s) {sorted(missing)}; all six dimensions must be present"
            )
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(f"weights must be non-negative, got {self.weights}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total:.3f}: {self.weights}")


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
    to fetch booking options. engine/ should treat it as meaningless.
    """
    price_eur: float
    origin_airport: str          # IATA, e.g. "TLV"
    destination_airport: str     # IATA, e.g. "GVA"
    airline: str
    total_duration_minutes: int
    stops: int                   # 0 = nonstop; enforces the blueprint's max-connections hard constraint
    is_round_trip: bool = True
    booking_token: Optional[str] = None  # opaque, provider-specific; see docstring


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
