"""
Re-ranks an already-scored set of TripOptions using REAL snow
conditions, replacing the static `snow_reliability` rating for the
trips where live data actually says something.

Blueprint Milestone 5 ("the system re-ranks a given trip set when
snow/weather data changes"). Until 2026-08-27 this was a stub: the app
fetched snow depth and showed it on the top result's card, but it never
moved a ranking, so a resort with a great historical reputation and no
snow this week still outranked a lesser resort sitting on a metre of
base.

THE HARD PART, which the blueprint itself ranks #5 of its ten hardest
problems: deciding HOW MUCH current snow should move a ranking is a
genuine judgement call that is easy to get wrong in either direction.
Two decisions below are therefore deliberately conservative, and both
are judgement, not sourced fact -- they are labelled as such here and
in anything shown to a user:

 1. HOW CONFIDENT IS THE DATA? Live weight comes from the data's own
    self-declared confidence rather than a hardcoded horizon: the
    adapter tags each day `is_live_forecast` (a real forecast) or not
    (a historical average for that calendar day). The fraction of a
    trip's days that are real forecasts IS the confidence, scaled by
    MAX_LIVE_WEIGHT. A trip five months out is entirely historical
    averages, gets weight 0, and is left exactly as it was -- which is
    correct, not a limitation: for far-future dates the historical
    record IS the better signal, and blending it in would just be
    double-counting `snow_reliability`, which already encodes it.

 2. WHAT IS A GOOD BASE? _DEPTH_BANDS below maps snow depth in cm to a
    0-1 score. The thresholds are a considered reading of ordinary ski
    practice (below ~30cm base, cover is thin and rocks appear; beyond
    ~2m, more depth stops improving an average piste skier's day), NOT
    a figure taken from a published source. Piste operators publish no
    universal standard here.

Never raises and never drops a trip: a resort whose weather lookup
fails keeps its original score, exactly like a resort whose live flight
price fails keeps its static estimate (see cost_calculator.
live_flight_cost_eur's docstring for the shared contract).
"""
from typing import Callable, List, Optional

from ..models import Resort, TripOption, TripWeatherSummary

# Maximum share of the snow score that live conditions can take, even
# when every single day of the trip is a real forecast. Held below 1.0
# on purpose: a forecast is a forecast, one provider is one provider,
# and `snow_reliability` encodes years of accumulated truth about a
# resort that a single week's reading should inform but not erase.
MAX_LIVE_WEIGHT = 0.7

# (minimum depth cm, score) -- highest band whose threshold is met wins.
# Judgement, not a sourced standard; see this module's docstring.
_DEPTH_BANDS = [
    (200, 1.00),  # exceptional base
    (150, 0.92),
    (100, 0.82),  # comfortably good
    (70, 0.70),
    (50, 0.55),   # skiable, unremarkable
    (30, 0.38),   # thin -- lower runs likely patchy
    (15, 0.20),
    (0, 0.05),    # effectively no cover
]


def snow_depth_score(depth_cm: float) -> float:
    """Maps a real base depth in cm to 0-1. See _DEPTH_BANDS."""
    for threshold, score in _DEPTH_BANDS:
        if depth_cm >= threshold:
            return score
    return 0.05


def live_forecast_confidence(summary: TripWeatherSummary) -> float:
    """
    0-1: what share of this trip's days are REAL forecasts rather than
    historical averages. 0 for a trip far enough out that no day has a
    forecast yet -- see this module's docstring on why that correctly
    means "change nothing".
    """
    if not summary.days:
        return 0.0
    live_days = sum(1 for d in summary.days if d.is_live_forecast)
    return live_days / len(summary.days)


def blended_snow_score(static_score: float, summary: TripWeatherSummary) -> float:
    """
    The static snow score, adjusted toward what the snow is actually
    doing, in proportion to how much of the trip is really forecast.
    Returns static_score unchanged when confidence is 0.
    """
    confidence = live_forecast_confidence(summary)
    if confidence <= 0.0:
        return static_score
    weight = MAX_LIVE_WEIGHT * confidence
    return (1.0 - weight) * static_score + weight * snow_depth_score(summary.avg_snow_depth_cm)


def rerank_with_conditions(
    trips: List[TripOption],
    weights: dict,
    weather_fn: Callable[[Resort], Optional[TripWeatherSummary]],
    max_lookups: int = 5,
) -> List[TripOption]:
    """
    Returns a NEW list, re-scored and re-sorted. Never mutates the
    input (this package is immutable-by-convention -- see the rest of
    engine/).

    weather_fn is injected rather than imported, matching
    rank_trips(flight_cost_fn=...) exactly: it keeps this module pure
    and offline-testable, and it lets the caller decide the real
    cost/quota policy rather than having one baked in here.

    max_lookups BOUNDS THE DAMAGE. Each lookup is several real,
    sequential live requests (one per sampled historical year -- see
    engine/weather.get_trip_weather). Re-ranking an entire result set
    would multiply that across every resort, which is precisely the
    request-amplification problem code review already caught on the
    booking links (see api/routes/search.py's attempt-gating). Only the
    top `max_lookups` trips are ever checked; the rest keep their
    original score and simply sort below any that improved. That is a
    real limitation, not a hidden one: a resort ranked 20th with
    exceptional snow will not climb.

    Ordering is by final score descending, with the original position
    as a tiebreak so equal scores stay stable.
    """
    if not trips or max_lookups <= 0:
        return list(trips)

    snow_weight = weights.get("snow", 0.0)
    if snow_weight <= 0.0:
        # The user does not care about snow at all -- re-ranking on it
        # would be spending live requests to change nothing.
        return list(trips)

    rescored: List[tuple] = []
    for index, trip in enumerate(trips):
        if index >= max_lookups:
            rescored.append((trip.score, index, trip))
            continue

        summary = weather_fn(trip.resort)
        if summary is None:
            rescored.append((trip.score, index, trip))
            continue

        static_snow = trip.score_components.get("snow", 0.0)
        new_snow = blended_snow_score(static_snow, summary)
        if new_snow == static_snow:
            rescored.append((trip.score, index, trip))
            continue

        # Adjust the composite by only the snow dimension's own
        # contribution, rather than recomputing every dimension -- the
        # others are unchanged and re-deriving them here would risk
        # drifting out of sync with scoring.score_resort.
        new_components = dict(trip.score_components)
        new_components["snow"] = round(new_snow, 3)
        new_score = round(trip.score + snow_weight * (new_snow - static_snow), 4)

        rescored.append((
            new_score,
            index,
            TripOption(
                resort=trip.resort,
                cost=trip.cost,
                score=new_score,
                score_components=new_components,
                within_budget=trip.within_budget,
            ),
        ))

    rescored.sort(key=lambda row: (-row[0], row[1]))
    return [trip for _, _, trip in rescored]
