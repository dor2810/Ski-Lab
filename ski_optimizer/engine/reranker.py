"""
[PHASE 7 -- not implemented yet, blocked on adapters/weather_adapter.py
and adapters/snow_adapter.py]

Adjusts an already-computed set of TripOptions when weather/snow data
changes -- per the blueprint's example: a resort that's normally #1
might drop in the ranking if current conditions are poor, even though
nothing about its static attributes changed.

Planned interface: rerank_with_conditions(trips, prefs) ->
List[TripOption]. For each trip, fetches current/forecast snow
conditions for trip.resort (via adapters.snow_adapter and
adapters.weather_adapter), recomputes the 'snow' score component using
LIVE data instead of the static snow_reliability rating, and re-sorts
by the updated weighted score. Should only matter for near-term trips
-- for dates months out, the static historical snow_reliability rating
remains more meaningful than a forecast that far ahead.
"""


def rerank_with_conditions(*args, **kwargs):
    raise NotImplementedError(
        "Weather/snow re-ranking needs weather_adapter and snow_adapter first (Phase 7). "
        "See the module docstring above for the planned interface."
    )
