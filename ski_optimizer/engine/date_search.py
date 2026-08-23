"""
Date-range search: "give me the best ski trip for EUR X, sometime in February."

This is the SECOND of the two query modes (see date-range-search-design.md).
The rest of the engine answers "fixed dates, which resort?"; this answers
"fixed budget and duration, which resort AND which dates?".

THE ORGANISING INSIGHT -- which costs move with dates:

  Tier 1, continuous:  flight, accommodation      <- the search axes
  Tier 2, season band: ski pass, accommodation    <- coarse steps
  Tier 3, fixed/resort: transfer, equipment, food <- cancel out across dates

Tier 3 costs are IDENTICAL across every candidate date for one resort, so
they cannot change which date wins. That is the whole reason a month-wide
search is tractable. Crucially this is NOT because they are small or
uniform: researched round-trip transfers range EUR22 (Obergurgl by bus) to
EUR220 (Zermatt's mandatory rail leg). Each resort's own figure is always
used; no global constant is ever assumed.

THREE-STAGE FUNNEL (naive search is 30 resorts x 25 dates = 750 flight
lookups, which is unaffordable):

  Stage 1  Prune resorts on date-independent criteria. Free, no API calls.
           Includes a feasibility floor: if Tier 2 + Tier 3 alone already
           bust the budget, no flight price can rescue that resort.
  Stage 2  Search flights across dates for the shortlist only.
  Stage 3  Price accommodation for surviving (resort, date) pairs only.

Stages 1 and 2 are implemented here and work against STATIC flight
estimates, so the funnel logic is fully testable offline with no API key.
Live pricing plugs into _flight_cost_for_date without touching the funnel.
"""
import datetime
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..models import Resort, UserPreferences, CostBreakdown
from .cost_calculator import (
    compute_trip_cost, flight_cost_eur, transfer_cost_eur_per_person,
    ski_pass_cost, food_cost_eur, season_band, EQUIPMENT_EUR_PER_DAY,
)
from .scoring import rank_trips, _normalize, _ski_quality_score


@dataclass
class DatedTripOption:
    """A candidate trip: a resort AND a specific start date."""
    resort: Resort
    start_date: datetime.date
    end_date: datetime.date
    cost: CostBreakdown
    score: float
    score_components: dict
    season: str

    @property
    def total_eur(self) -> float:
        return self.cost.total_eur


def candidate_start_dates(earliest: datetime.date, latest: datetime.date,
                          trip_nights: int, step_days: int = 1) -> List[datetime.date]:
    """
    Every valid start date whose full trip fits inside the window.

    step_days > 1 coarsens the grid. That matters for the bootstrapping
    problem: on day one we have no fare history, so every date costs a
    live API call. Searching every 3rd day first and refining around the
    winner is far cheaper than 25 blind lookups, and gets unnecessary as
    db/fare_history.py accumulates real data.
    """
    if trip_nights <= 0:
        raise ValueError(f"trip_nights must be > 0, got {trip_nights}")
    if step_days <= 0:
        raise ValueError(f"step_days must be > 0, got {step_days}")
    if latest < earliest:
        raise ValueError(f"latest {latest} is before earliest {earliest}")

    out = []
    day = earliest
    while day + datetime.timedelta(days=trip_nights) <= latest:
        out.append(day)
        day += datetime.timedelta(days=step_days)
    return out


def date_independent_cost(resort: Resort, prefs: UserPreferences) -> float:
    """
    Sum of the Tier 3 costs -- the ones identical across every date.

    Used by the Stage 1 feasibility floor. Deliberately EXCLUDES the ski
    pass, because that is Tier 2 (season-banded) and so does vary by date.
    """
    nights = prefs.trip_nights
    transfer = transfer_cost_eur_per_person(resort, prefs.group_size)
    equipment = EQUIPMENT_EUR_PER_DAY[prefs.equipment_tier] * nights
    food = food_cost_eur(resort, nights, prefs.food_profile)
    return transfer + equipment + food


def cheapest_possible_cost(resort: Resort, prefs: UserPreferences) -> float:
    """
    Optimistic lower bound on what this resort could ever cost in the
    window: Tier 3 costs, plus the cheapest season band for the pass and
    accommodation, plus the static flight estimate.

    Deliberately OPTIMISTIC. A resort is only dropped in Stage 1 when even
    its best case busts the budget, so pruning can never discard a trip
    that would actually have been affordable.
    """
    nights = prefs.trip_nights
    # Shoulder band = cheapest, obtained by passing no date.
    pass_cost = ski_pass_cost(resort, nights, None)
    rooms = prefs.rooms_needed or max(1, -(-prefs.group_size // 2))
    accom = (resort.accommodation_eur_per_night * nights * rooms) / prefs.group_size
    subtotal = date_independent_cost(resort, prefs) + pass_cost + accom + flight_cost_eur(resort)
    return subtotal * 1.05  # misc buffer, matching compute_trip_cost


def shortlist_resorts(resorts: List[Resort], prefs: UserPreferences,
                      top_n: int = 8) -> List[Resort]:
    """
    STAGE 1: prune on date-independent criteria. No API calls, no dates.

    Two filters:
      1. Feasibility -- drop resorts whose optimistic best case already
         exceeds the budget.
      2. Fit -- rank the rest on skill/terrain, off-piste, snow, nightlife
         and transfer convenience, and keep the top N.

    Deliberately does NOT score on price: flight prices are unknown at
    this stage, and pre-judging on the static estimate would bias the
    shortlist toward whatever the placeholder happens to say.
    """
    affordable = [r for r in resorts if cheapest_possible_cost(r, prefs) <= prefs.budget_eur_per_person]
    if not affordable:
        return []

    piste_vals = [r.piste_km for r in resorts]
    piste_range = (min(piste_vals), max(piste_vals))
    transfer_vals = [r.transfer_time_minutes for r in resorts]
    transfer_range = (min(transfer_vals), max(transfer_vals))

    weights = prefs.weights
    scored = []
    for r in affordable:
        piste_score = _normalize(r.piste_km, *piste_range)
        components = {
            "ski_quality": _ski_quality_score(r, prefs, piste_score),
            "snow": r.snow_reliability / 5.0,
            "nightlife": r.nightlife_rating / 5.0,
            "convenience": 1.0 - _normalize(r.transfer_time_minutes, *transfer_range),
        }
        # Renormalize over just the date-independent dimensions, so a user
        # who weights price heavily doesn't end up with a near-zero score
        # for every resort at this stage.
        usable = {k: weights.get(k, 0.0) for k in components}
        total_w = sum(usable.values())
        if total_w <= 0:
            fit = sum(components.values()) / len(components)
        else:
            fit = sum(components[k] * (w / total_w) for k, w in usable.items())
        scored.append((fit, r))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [r for _, r in scored[:top_n]]


def _default_flight_cost_for_date(resort: Resort, start_date: datetime.date,
                                  end_date: datetime.date, prefs: UserPreferences) -> float:
    """
    Static fallback: the flat per-country estimate, ignoring the date.

    This is a PLACEHOLDER and it is deliberately date-blind, which means
    with it the search cannot actually find a cheaper week -- it will
    rank dates only on season-banded pass and accommodation. That is
    enough to test the funnel, and nothing more. Real date-driven deals
    require passing a live flight_cost_fn (see adapters/flight_adapter).
    """
    return flight_cost_eur(resort)


def search_date_range(
    resorts: List[Resort],
    prefs: UserPreferences,
    earliest_date: datetime.date,
    latest_date: datetime.date,
    shortlist_size: int = 8,
    step_days: int = 1,
    top_n: int = 10,
    flight_cost_fn: Optional[Callable] = None,
) -> List[DatedTripOption]:
    """
    Full funnel: shortlist resorts, then evaluate each across every
    candidate start date, returning the best (resort, date) combinations.

    flight_cost_fn lets a caller inject live pricing with the signature
    (resort, start_date, end_date, prefs) -> float, or None if no price
    is available for that date. Defaults to the static estimate, which
    keeps this fully runnable and testable without an API key.
    """
    flight_cost_fn = flight_cost_fn or _default_flight_cost_for_date

    starts = candidate_start_dates(earliest_date, latest_date, prefs.trip_nights, step_days)
    if not starts:
        return []

    shortlist = shortlist_resorts(resorts, prefs, top_n=shortlist_size)
    if not shortlist:
        return []

    # Normalization ranges come from the FULL dataset, not the shortlist,
    # so scores stay comparable with the fixed-date engine's output.
    piste_vals = [r.piste_km for r in resorts]
    transfer_vals = [r.transfer_time_minutes for r in resorts]
    accom_vals = [r.accommodation_eur_per_night for r in resorts]
    ranges = {
        "piste": (min(piste_vals), max(piste_vals)),
        "transfer": (min(transfer_vals), max(transfer_vals)),
        "accom": (min(accom_vals), max(accom_vals)),
    }

    results = []
    for resort in shortlist:
        for start in starts:
            end = start + datetime.timedelta(days=prefs.trip_nights)

            cost = compute_trip_cost(resort, prefs, start_date=start)

            live_flight = flight_cost_fn(resort, start, end, prefs)
            if live_flight is None:
                # No price for this date -- skip it rather than silently
                # substituting an estimate and presenting it as a real deal.
                continue
            if live_flight != cost.flight_eur:
                delta = live_flight - cost.flight_eur
                cost = CostBreakdown(
                    flight_eur=live_flight,
                    transfer_eur=cost.transfer_eur,
                    accommodation_eur=cost.accommodation_eur,
                    ski_pass_eur=cost.ski_pass_eur,
                    equipment_eur=cost.equipment_eur,
                    food_eur=cost.food_eur,
                    misc_eur=round(cost.misc_eur + delta * 0.05, 2),
                )

            if not (0 < cost.total_eur <= prefs.budget_eur_per_person):
                continue

            piste_score = _normalize(resort.piste_km, *ranges["piste"])
            accom_pct = _normalize(resort.accommodation_eur_per_night, *ranges["accom"])
            target = {"budget": 0.15, "standard": 0.5, "luxury": 0.85}.get(
                prefs.accommodation_tier, 0.5)
            components = {
                "ski_quality": _ski_quality_score(resort, prefs, piste_score),
                "price": max(0.0, min(1.0, 1.0 - cost.total_eur / prefs.budget_eur_per_person)),
                "snow": resort.snow_reliability / 5.0,
                "nightlife": resort.nightlife_rating / 5.0,
                "convenience": 1.0 - _normalize(resort.transfer_time_minutes, *ranges["transfer"]),
                "accommodation": 1.0 - abs(accom_pct - target),
            }
            score = sum(components[k] * w for k, w in prefs.weights.items())

            results.append(DatedTripOption(
                resort=resort, start_date=start, end_date=end, cost=cost,
                score=round(score, 4),
                score_components={k: round(v, 3) for k, v in components.items()},
                season=season_band(start),
            ))

    results.sort(key=lambda t: t.score, reverse=True)
    return results[:top_n]


def best_date_per_resort(options: List[DatedTripOption]) -> List[DatedTripOption]:
    """
    Collapses to the single best date for each resort.

    Answers "if I specifically want St. Anton, when should I go?" -- and
    stops one resort with a cheap week from monopolising the whole result
    list, which a raw score sort otherwise tends to do.
    """
    best = {}
    for opt in options:
        current = best.get(opt.resort.name)
        if current is None or opt.score > current.score:
            best[opt.resort.name] = opt
    return sorted(best.values(), key=lambda t: t.score, reverse=True)


def price_sensitivity(options: List[DatedTripOption], resort_name: str) -> Optional[dict]:
    """
    How much does timing actually matter for one resort?

    Powers the genuinely differentiating output: "shifting a week saves
    EUR200" vs "timing barely matters here, book whenever suits you".
    Returns None when there aren't at least two dates to compare.
    """
    same = [o for o in options if o.resort.name == resort_name]
    if len(same) < 2:
        return None
    cheapest = min(same, key=lambda o: o.total_eur)
    dearest = max(same, key=lambda o: o.total_eur)
    return {
        "resort": resort_name,
        "cheapest_date": cheapest.start_date,
        "cheapest_eur": round(cheapest.total_eur, 2),
        "most_expensive_date": dearest.start_date,
        "most_expensive_eur": round(dearest.total_eur, 2),
        "spread_eur": round(dearest.total_eur - cheapest.total_eur, 2),
        "dates_compared": len(same),
    }
