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
import datetime
from typing import Callable, List, Optional

from ..models import Resort, UserPreferences, TripOption
from .cost_calculator import compute_trip_cost, apply_live_flight_price, apply_live_accommodation_price


def _norm_name(name: str) -> str:
    return name.strip().lower()


def narrow_resort_pool(resorts: List[Resort], prefs: UserPreferences) -> List[Resort]:
    """
    Applies target_resort / include_resorts / exclude_resorts (see their
    docstrings on UserPreferences) to a resort list. Shared by rank_trips
    and date_search.search_date_range so "pick specific resorts" /
    "everywhere except X" means the same thing in both search modes.

    Deliberately does NOT touch normalization ranges -- the caller must
    keep computing piste/transfer/accom ranges from the ORIGINAL,
    unnarrowed resort list, so a 2-resort pin still scores 'price' etc.
    against the full dataset's spread rather than a nearly-degenerate
    2-point range.
    """
    if prefs.target_resort:
        target = _norm_name(prefs.target_resort)
        return [r for r in resorts if _norm_name(r.name) == target]
    if prefs.include_resorts:
        include = {_norm_name(n) for n in prefs.include_resorts}
        resorts = [r for r in resorts if _norm_name(r.name) in include]
    if prefs.exclude_resorts:
        exclude = {_norm_name(n) for n in prefs.exclude_resorts}
        resorts = [r for r in resorts if _norm_name(r.name) not in exclude]
    return resorts


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


def rank_trips(resorts: List[Resort], prefs: UserPreferences, top_n: int = 5,
               flight_cost_fn: Optional[Callable] = None,
               accommodation_cost_fn: Optional[Callable] = None,
               live_reprice_n: int = 10,
               allow_over_budget_fallback: bool = True) -> List[TripOption]:
    """
    flight_cost_fn / accommodation_cost_fn, when given, enable live
    repricing for discovery mode's cost ranking:
    (resort, start_date, end_date, prefs) -> Optional[float], matching
    date_search.search_date_range()'s injection pattern. Both default to
    None, a NO-OP -- zero behavior change from static-only ranking for
    any existing caller that doesn't pass them.

    Only the top `live_reprice_n` candidates by STATIC score get
    live-priced (default 10, more than top_n so a resort whose live
    price undercuts its static estimate can still surface) -- repricing
    every resort on every search would spend an unacceptable fraction of
    a metered API quota on one request. Requires prefs.outbound_date to
    be set; without it there's no date to price against, so live pricing
    is skipped even if the functions are provided.

    A resort whose live price pushes it over budget is dropped, matching
    the hard-budget-constraint rule applied everywhere else -- an
    estimate that happens to fit is not grounds to show a trip that
    doesn't really fit. A resort a cost_fn can't price (returns None --
    adapter error, no route/property) keeps its static estimate rather
    than being dropped over an API hiccup.

    OVER-BUDGET FALLBACK (allow_over_budget_fallback, default True): if
    NOTHING fits the stated budget -- static estimate or live price --
    this does NOT return an empty list. It returns the cheapest
    option(s) it found instead, live-repriced the same way, each tagged
    TripOption.within_budget=False. An empty list reads as "the engine
    found nothing," which is misleading when the truth is "everything
    here costs more than you said" -- the caller (API/frontend) must
    show the within_budget flag honestly, never silently present a
    flagged result as a normal one. Pass allow_over_budget_fallback=False
    to get the old "empty means nothing fits" behavior back.
    """
    # "Fixed resort(s)" mode: the user already knows where they want to
    # go -- evaluate just target_resort / include_resorts / (all minus)
    # exclude_resorts instead of competing every resort against each
    # other. Score components (esp. 'price') are still computed relative
    # to the FULL, UNNARROWED dataset's range (resorts_for_ranges), so
    # they stay meaningful even when only 1-3 resorts are being ranked.
    resorts_for_ranges = resorts
    if prefs.target_resort or prefs.include_resorts or prefs.exclude_resorts:
        resorts = narrow_resort_pool(resorts, prefs)
        if not resorts:
            return []

    # Precompute dataset ranges for normalization (done once, not per-resort).
    piste_values = [r.piste_km for r in resorts_for_ranges]
    transfer_values = [r.transfer_time_minutes for r in resorts_for_ranges]
    accom_values = [r.accommodation_eur_per_night for r in resorts_for_ranges]
    piste_range = (min(piste_values), max(piste_values))
    transfer_range = (min(transfer_values), max(transfer_values))
    accom_range = (min(accom_values), max(accom_values))

    # Cost every resort ONCE up front (not just the affordable ones) --
    # the over-budget fallback needs the full priced set even when the
    # hard filter below drops every single one of them.
    all_priced = []
    for resort in resorts:
        cost = compute_trip_cost(resort, prefs, start_date=prefs.outbound_date)
        components = score_resort(resort, prefs, cost.total_eur, piste_range, transfer_range, accom_range)
        weighted_score = sum(components[dim] * weight for dim, weight in prefs.weights.items())
        all_priced.append(TripOption(
            resort=resort, cost=cost, score=round(weighted_score, 4),
            score_components=components,
        ))

    candidates = [t for t in all_priced if passes_hard_constraints(t.resort, prefs, t.cost.total_eur)]
    candidates.sort(key=lambda t: t.score, reverse=True)

    live_active = (flight_cost_fn is not None or accommodation_cost_fn is not None) and prefs.outbound_date is not None
    if live_active:
        candidates = (_reprice_with_live_prices(candidates[:live_reprice_n], prefs,
                                                 flight_cost_fn, accommodation_cost_fn)
                      + candidates[live_reprice_n:])
        candidates.sort(key=lambda t: t.score, reverse=True)

    if candidates or not allow_over_budget_fallback:
        return candidates[:top_n]

    # FALLBACK: nothing fit, even statically. Take the cheapest overall
    # (not score-sorted -- there's no "best fit" once nothing fits, only
    # "least bad"), live-reprice those few, and return them flagged.
    fallback_n = max(top_n, 3)
    fallback = sorted(all_priced, key=lambda t: t.cost.total_eur)[:fallback_n]
    if live_active:
        fallback = _reprice_with_live_prices(fallback, prefs, flight_cost_fn,
                                             accommodation_cost_fn, enforce_budget=False)
    fallback = [TripOption(resort=t.resort, cost=t.cost, score=t.score,
                           score_components=t.score_components, within_budget=False)
                for t in fallback]
    fallback.sort(key=lambda t: t.cost.total_eur)
    return fallback[:top_n]


def _reprice_with_live_prices(candidates: List[TripOption], prefs: UserPreferences,
                              flight_cost_fn: Optional[Callable],
                              accommodation_cost_fn: Optional[Callable],
                              enforce_budget: bool = True) -> List[TripOption]:
    """
    Re-quotes flight and/or accommodation cost for each candidate,
    dropping any that no longer fit the budget once the real price is
    known -- UNLESS enforce_budget=False (used by rank_trips' over-budget
    fallback path, where dropping every repriced candidate would just
    reproduce the empty result the fallback exists to avoid; the point
    there is to show the true live price, not to re-filter by it).
    """
    end_date = prefs.outbound_date + datetime.timedelta(days=prefs.trip_nights)
    repriced = []
    for trip in candidates:
        cost = trip.cost
        if flight_cost_fn is not None:
            live_flight = flight_cost_fn(trip.resort, prefs.outbound_date, end_date, prefs)
            if live_flight is not None and live_flight != cost.flight_eur:
                cost = apply_live_flight_price(cost, live_flight)
        if accommodation_cost_fn is not None:
            live_accom = accommodation_cost_fn(trip.resort, prefs.outbound_date, end_date, prefs)
            if live_accom is not None and live_accom != cost.accommodation_eur:
                cost = apply_live_accommodation_price(cost, live_accom)

        if cost is trip.cost:  # neither leg actually changed
            repriced.append(trip)
            continue
        if enforce_budget and not passes_hard_constraints(trip.resort, prefs, cost.total_eur):
            continue
        new_components = dict(trip.score_components)
        new_components["price"] = round(
            max(0.0, min(1.0, 1.0 - cost.total_eur / prefs.budget_eur_per_person)), 3)
        new_score = sum(new_components[dim] * weight for dim, weight in prefs.weights.items())
        repriced.append(TripOption(
            resort=trip.resort, cost=cost,
            score=round(new_score, 4), score_components=new_components,
            within_budget=trip.within_budget,
        ))
    return repriced
