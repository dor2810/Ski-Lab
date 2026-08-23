"""
Two-stage trip ranking, per the blueprint's optimization engine design:

  1. Hard constraint filter (deterministic, pass/fail) — eliminates
     resorts that can't possibly work before any scoring happens.
  2. Weighted multi-objective scoring (soft preferences) — ranks the
     survivors using a personalized weight vector.

Nothing here is machine learning. It's plain, explainable weighted scoring
on purpose — see the blueprint's Section 3 rationale (transparency of "why"
matters, and there's no training data yet to justify anything fancier).
"""
from typing import List, Optional

from ..models import Resort, UserPreferences, TripOption
from .cost_calculator import compute_trip_cost


def passes_hard_constraints(resort: Resort, prefs: UserPreferences, total_cost: float) -> bool:
    if total_cost > prefs.budget_eur_per_person:
        return False
    return True


def _normalize(value: float, min_v: float, max_v: float) -> float:
    if max_v == min_v:
        return 0.5
    return max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))


def _skill_terrain_match(resort: Resort, skill_level: str) -> Optional[float]:
    """
    0-1 score for how well this resort's terrain suits THIS skier.
    Returns None only if a resort somehow has no terrain data at all
    (shouldn't happen post-migration -- every resort has a real or
    estimated numeric split -- kept defensive for future resorts added
    before their terrain columns are filled in).

    Balances two things that pull in opposite directions:
      - suitability: how much terrain the skier can actually ski
      - challenge:   how much terrain will actually engage them

    Why both are needed: an advanced skier is technically "served" by
    100% of a beginner hill, but would be bored -- suitability alone
    would rank Pamporovo above Chamonix for an expert. Conversely a
    beginner at Chamonix has 46% advanced terrain "available" that they
    cannot use, so challenge alone would badly mislead in the other
    direction. The weighting shifts with skill level accordingly:
    beginners care only about what they can ski; experts care mostly
    about what will push them.
    """
    if resort.terrain_mix is None:
        return None

    suitability = resort.terrain_mix.fraction_for_skill(skill_level)
    challenge = resort.terrain_mix.challenge_for_skill(skill_level)

    if skill_level == "beginner":
        # Challenge is irrelevant (and actively misleading) for beginners.
        return suitability
    if skill_level == "intermediate":
        return 0.7 * suitability + 0.3 * challenge
    # advanced / expert
    return 0.3 * suitability + 0.7 * challenge


# How much each ski-quality ingredient matters, by skill level:
#   (piste_size, off_piste_reputation, skill_terrain_match)
#
# Off-piste weighting is deliberately skill-dependent. World-class
# off-piste is close to worthless to a beginner who will never ski it,
# so weighting it flat across skill levels was actively distorting
# beginner rankings before the terrain migration -- it pushed
# expert-oriented resorts (Chamonix, Verbier) up a beginner's list, and,
# worse, advantaged resorts that happened to be MISSING terrain data,
# since they fell back to a formula where off-piste dominated.
_SKI_QUALITY_WEIGHTS = {
    "beginner":     (0.20, 0.05, 0.75),
    "intermediate": (0.20, 0.35, 0.45),
    "advanced":     (0.20, 0.50, 0.30),
    "expert":       (0.15, 0.55, 0.30),
}


def _ski_quality_score(resort: Resort, prefs: UserPreferences, piste_score: float) -> float:
    off_piste_score = resort.off_piste_rating / 5.0
    skill_match = _skill_terrain_match(resort, prefs.skill_level)
    w_piste, w_offpiste, w_skill = _SKI_QUALITY_WEIGHTS.get(
        prefs.skill_level, _SKI_QUALITY_WEIGHTS["intermediate"])

    if skill_match is None:
        # Defensive fallback only -- see _skill_terrain_match docstring.
        # Redistributes the skill-match weight proportionally across the
        # two ingredients we DO have, rather than dropping to a
        # different formula, so a genuinely missing value stays neutral.
        remaining = w_piste + w_offpiste
        return (w_piste / remaining) * piste_score + (w_offpiste / remaining) * off_piste_score

    return w_piste * piste_score + w_offpiste * off_piste_score + w_skill * skill_match


def score_resort(resort: Resort, prefs: UserPreferences, total_cost: float,
                  piste_km_range: tuple, transfer_min_range: tuple, accom_price_range: tuple) -> dict:
    """Returns per-dimension 0-1 scores. Higher is always better."""
    piste_min, piste_max = piste_km_range
    transfer_min, transfer_max = transfer_min_range
    accom_min, accom_max = accom_price_range

    piste_score = _normalize(resort.piste_km, piste_min, piste_max)
    ski_quality = _ski_quality_score(resort, prefs, piste_score)

    price_score = max(0.0, min(1.0, 1.0 - (total_cost / prefs.budget_eur_per_person)))
    snow_score = resort.snow_reliability / 5.0
    nightlife_score = resort.nightlife_rating / 5.0

    # Convenience: shorter transfer = better. Invert the normalized value.
    convenience_score = 1.0 - _normalize(resort.transfer_time_minutes, transfer_min, transfer_max)

    # Accommodation comfort: how well the resort's typical nightly rate
    # matches the user's stated accommodation_tier (budget/standard/luxury)
    # relative to the rest of the dataset, rather than "expensive = good".
    accom_percentile = _normalize(resort.accommodation_eur_per_night, accom_min, accom_max)
    target_percentile = {"budget": 0.15, "standard": 0.5, "luxury": 0.85}.get(prefs.accommodation_tier, 0.5)
    accommodation_score = 1.0 - abs(accom_percentile - target_percentile)

    return {
        "ski_quality": round(ski_quality, 3),
        "price": round(price_score, 3),
        "snow": round(snow_score, 3),
        "nightlife": round(nightlife_score, 3),
        "convenience": round(convenience_score, 3),
        "accommodation": round(accommodation_score, 3),
    }


def rank_trips(resorts: List[Resort], prefs: UserPreferences, top_n: int = 5) -> List[TripOption]:
    # "Fixed resort" mode: the user already knows where they want to go —
    # evaluate that one resort's cost/fit instead of competing it against
    # everything else. Score components (esp. 'price') are still computed
    # relative to the FULL dataset's range, so they stay meaningful even
    # though nothing else is being ranked against it.
    if prefs.target_resort:
        resorts_for_ranges = resorts  # keep normalization ranges dataset-wide
        # Normalize case AND surrounding whitespace. Case-insensitive
        # matching alone still failed on a trailing space (an easy
        # real-world input from copy-paste or mobile autocomplete),
        # silently returning zero results as if the resort didn't exist.
        target = prefs.target_resort.strip().lower()
        resorts = [r for r in resorts if r.name.strip().lower() == target]
        if not resorts:
            return []
    else:
        resorts_for_ranges = resorts

    # Precompute dataset ranges for normalization (done once, not per-resort).
    piste_values = [r.piste_km for r in resorts_for_ranges]
    transfer_values = [r.transfer_time_minutes for r in resorts_for_ranges]
    accom_values = [r.accommodation_eur_per_night for r in resorts_for_ranges]
    piste_range = (min(piste_values), max(piste_values))
    transfer_range = (min(transfer_values), max(transfer_values))
    accom_range = (min(accom_values), max(accom_values))

    candidates = []
    for resort in resorts:
        cost = compute_trip_cost(resort, prefs)
        if not passes_hard_constraints(resort, prefs, cost.total_eur):
            continue
        components = score_resort(resort, prefs, cost.total_eur, piste_range, transfer_range, accom_range)
        weighted_score = sum(components[dim] * weight for dim, weight in prefs.weights.items())
        candidates.append(TripOption(
            resort=resort,
            cost=cost,
            score=round(weighted_score, 4),
            score_components=components,
        ))

    candidates.sort(key=lambda t: t.score, reverse=True)
    return candidates[:top_n]
