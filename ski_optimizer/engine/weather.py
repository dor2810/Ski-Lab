"""
Weather for a trip: a real forecast when the date is close enough for
one to exist, a historical average otherwise. Wraps
adapters/weather_adapter.py the same way cost_calculator.py wraps the
flight/hotel adapters -- engine/ never touches a provider directly, and
the caller never has to know which of the two data sources actually
answered.
"""
from datetime import date
from typing import Optional, Union

from ..models import HistoricalWeatherAverage, Resort, WeatherForecast


def get_resort_weather(
    resort: Resort, target_date: date, historical_years_back: int = 5,
) -> Optional[Union[WeatherForecast, HistoricalWeatherAverage]]:
    """
    Returns a WeatherForecast (real forecast, only possible within
    adapters/weather_adapter.py's ~16-day horizon) OR a
    HistoricalWeatherAverage (the common case for a trip booked months
    ahead) OR None -- never raises, matching every other live_* function
    in this package's "degrade visibly, never break the search"
    contract (see cost_calculator.live_flight_cost_eur's docstring for
    the shared reasoning). None covers: no coordinates on file for this
    resort, or the provider request itself failing for every attempt.

    historical_years_back defaults to 5, not
    weather_adapter.get_historical_average's own default of 10: each
    year costs one real, sequential live request, and this is called
    per search RESULT (see api/routes/search.py's own bounding of this
    to a single top result per response, for the same reason
    _flight_search_url/_accommodation_search_url are -- avoiding
    exactly the request-amplification code review caught there).
    """
    if resort.latitude is None or resort.longitude is None:
        return None
    try:
        from ..adapters import weather_adapter

        forecast = weather_adapter.get_forecast(resort, target_date)
        if forecast is not None:
            return forecast
        return weather_adapter.get_historical_average(
            resort, target_date, years_back=historical_years_back)
    except Exception:
        return None
