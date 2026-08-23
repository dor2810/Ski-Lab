"""
The first real, protected use of the engine over HTTP: POST /trips/search
wraps engine.scoring.rank_trips exactly as the CLI demo does, but behind
Depends(get_current_user) -- no valid access_token cookie, no results.

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
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ...data.resort_repository import load_resorts
from ...models import (
    Resort, UserPreferences,
    VALID_SKILL_LEVELS, VALID_ACCOMMODATION_TIERS,
    VALID_FOOD_PROFILES, VALID_EQUIPMENT_TIERS, VALID_WEIGHT_KEYS,
)
from ...engine.scoring import rank_trips
from ...nlp.explainer import explain
from ...db.models import User
from .auth import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])

_DEFAULT_WEIGHTS = {
    "ski_quality": 0.30, "price": 0.20, "snow": 0.15,
    "nightlife": 0.15, "convenience": 0.10, "accommodation": 0.10,
}

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


class SearchRequest(BaseModel):
    budget_eur_per_person: float = Field(gt=0)
    trip_nights: int = Field(gt=0, le=30)
    group_size: int = Field(default=2, gt=0, le=20)
    skill_level: str = "intermediate"
    accommodation_tier: str = "standard"
    food_profile: str = "normal"
    equipment_tier: str = "standard"
    target_resort: Optional[str] = None
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


class TripResultOut(BaseModel):
    resort: ResortOut
    cost: CostBreakdownOut
    score: float
    score_components: Dict[str, float]
    explanation: str


class SearchResponse(BaseModel):
    query_resort_count: int
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


@router.post("/search", response_model=SearchResponse)
def search_trips(payload: SearchRequest, current_user: User = Depends(get_current_user)):
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
            trip_nights=payload.trip_nights,
            group_size=payload.group_size,
            skill_level=payload.skill_level,
            accommodation_tier=payload.accommodation_tier,
            food_profile=payload.food_profile,
            equipment_tier=payload.equipment_tier,
            target_resort=payload.target_resort,
            weights=full_weights,
        )
    except ValueError as e:
        # UserPreferences validates weights sum to 1.0 -- should be
        # unreachable given the normalization above, but surfaced as a
        # clean 400 instead of a 500 if some edge case gets past it.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    if payload.target_resort:
        # Match the ENGINE's normalization exactly (see engine/scoring.py's
        # rank_trips). Previously this used an exact, case-SENSITIVE
        # membership test while the engine matched case-insensitively --
        # so 'krvavec' got a 404 here even though the engine would have
        # resolved it fine. Two layers disagreeing about what counts as a
        # valid resort name is a bug waiting to confuse someone.
        target = payload.target_resort.strip().lower()
        known_names = {r.name.strip().lower() for r in _resort_cache}
        if target not in known_names:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Unknown resort {payload.target_resort!r}. "
                f"See GET /trips/resorts for valid names.",
            )

    trip_options = rank_trips(_resort_cache, prefs, top_n=6)

    results = [
        TripResultOut(
            resort=_to_resort_out(t.resort),
            cost=CostBreakdownOut(
                flight_eur=t.cost.flight_eur, transfer_eur=t.cost.transfer_eur,
                accommodation_eur=t.cost.accommodation_eur, ski_pass_eur=t.cost.ski_pass_eur,
                equipment_eur=t.cost.equipment_eur, food_eur=t.cost.food_eur,
                misc_eur=t.cost.misc_eur, total_eur=t.cost.total_eur,
            ),
            score=t.score,
            score_components=t.score_components,
            explanation=explain(t, skill_level=payload.skill_level),
        )
        for t in trip_options
    ]

    return SearchResponse(query_resort_count=len(_resort_cache), results=results)


@router.get("/resorts", response_model=List[str])
def list_resort_names(current_user: User = Depends(get_current_user)):
    """Lets an authenticated client populate a 'fixed resort' dropdown without guessing names."""
    return sorted(r.name for r in _resort_cache)
