"""
Weather for a trip: real forecasts for the days close enough for one to
exist, historical per-day averages for the rest -- wraps
adapters/weather_adapter.py the same way cost_calculator.py wraps the
flight/hotel adapters, so engine/ never touches a provider directly.
"""
from datetime import date
from typing import Optional

from ..models import Resort, TripWeatherSummary


def get_trip_weather(
    resort: Resort, start_date: date, end_date: date, historical_years_back: int = 5,
) -> Optional[TripWeatherSummary]:
    """
    Weather for the WHOLE trip (check-in..check-out inclusive), one day
    at a time -- see adapters/weather_adapter.get_trip_weather()'s own
    docstring for the forecast-vs-historical split. Never raises,
    matching every other live_* function in this package's "degrade
    visibly, never break the search" contract (see cost_calculator.
    live_flight_cost_eur's docstring for the shared reasoning). None
    covers: no coordinates on file for this resort, or every provider
    request failing.

    historical_years_back defaults to 5, not
    weather_adapter.get_historical_daily_breakdown's own default of 10:
    each year costs one real, sequential live request, and this is
    called per search RESULT (see api/routes/search.py's own bounding
    of this to a single top result per response, for the same reason
    _flight_search_url/_accommodation_search_url are -- avoiding
    exactly the request-amplification code review caught there).
    """
    if resort.latitude is None or resort.longitude is None:
        return None
    try:
        from ..adapters import weather_adapter

        return weather_adapter.get_trip_weather(
            resort, start_date, end_date, historical_years_back=historical_years_back)
    except Exception:
        return None
