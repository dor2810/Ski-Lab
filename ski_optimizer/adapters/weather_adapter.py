"""
Weather via Open-Meteo (open-meteo.com) -- free, no API key, no signup
for non-commercial use (the `apikey` param exists only for a paid
commercial tier; see .env.example). Picked over OpenWeatherMap/
WeatherAPI.com, both of which require a key even on their free tier
and have shallower/paid-gated historical data -- same "no API key,
no metered quota" reasoning as adapters/google_flights_adapter.py and
adapters/google_hotels_adapter.py, and unlike those two, this is a
genuinely PUBLIC, DOCUMENTED REST API (developer.open-meteo.com), not
scraping. Two separate endpoints, two separate jobs:

  get_forecast()            -- api.open-meteo.com/v1/forecast
    A REAL forecast, only for dates the provider actually forecasts
    (out to 16 days). Returns None for anything further out, on
    purpose -- see that function's docstring. This is the "weather at
    the time of the flight" the user asked for, but only meaningfully
    answerable once a trip is close enough for it to exist.

  get_historical_average()  -- archive-api.open-meteo.com/v1/archive
    "What's it USUALLY like around these dates" -- averages several
    past years' real recorded weather (ERA5 reanalysis, back to 1940)
    for the same calendar window. This is what actually answers "how
    good is it" for the overwhelming majority of ski trips, which get
    searched and booked months before any real forecast could cover
    them.

Needs Resort.latitude/longitude (see that field's own docstring in
models.py for how they were sourced) -- Open-Meteo takes coordinates,
not place names.

VERIFIED LIVE (2026-08-26): both endpoints tested directly against Val
Thorens' real coordinates -- the forecast endpoint returned real,
varying multi-day data (correctly resolved to the resort's actual
~2300m elevation, not sea level); the archive endpoint returned real
January 2025 temperatures/snowfall for the same location. No test in
this module hits either endpoint for real (see tests/conftest.py's
matching network-blocking fixture) -- that verification isn't
something an offline test can keep re-proving on every run.
"""
import datetime
from typing import List, Optional

from ..models import HistoricalWeatherAverage, Resort, WeatherForecast
from .base import AdapterError
from .response_cache import get_cache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo forecasts out to 16 days; a request past that just returns
# clamped/empty data rather than an error, so this is enforced here
# instead -- see get_forecast()'s docstring on why "no data" beats a
# forecast the provider can't actually stand behind.
MAX_FORECAST_DAYS = 16

# WMO weather interpretation codes (the same table Open-Meteo's own
# docs publish) -- decoded here rather than left as a bare integer,
# since "3" means nothing to a user but "Overcast" does. Collapsed to
# the cases that matter for a ski-trip forecast; anything unmapped
# falls back to the raw code rather than guessing.
_WMO_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def _describe_weather_code(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return _WMO_DESCRIPTIONS.get(int(code), f"WMO code {code}")


def _cache_key(kind: str, resort_name: str, start: datetime.date, end: datetime.date) -> str:
    return "|".join(["weather", kind, resort_name.strip().lower(), str(start), str(end)])


def _require_coordinates(resort: Resort) -> None:
    if resort.latitude is None or resort.longitude is None:
        raise AdapterError(f"{resort.name!r} has no latitude/longitude on file")


def _fetch_json(url: str, params: dict) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise AdapterError("The 'requests' package is required for weather lookups") from exc

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise AdapterError(f"Open-Meteo request failed: {exc}") from exc


def get_forecast(
    resort: Resort, target_date: datetime.date, use_cache: bool = True,
) -> Optional[WeatherForecast]:
    """
    A real forecast for ONE date, or None when target_date is outside
    Open-Meteo's actual forecast horizon (today .. +16 days) -- a trip
    booked in advance (the normal case for this app) is almost always
    outside that window, and returning nothing is the honest answer,
    not a fabricated one dressed up as a forecast. Callers wanting
    "what's it usually like" for a far-future date should use
    get_historical_average() instead.

    Raises AdapterError for a real request/coordinate failure; returns
    None specifically for "not yet forecastable" so callers can tell
    the two apart if they want to.
    """
    _require_coordinates(resort)
    today = datetime.date.today()
    if target_date < today or (target_date - today).days > MAX_FORECAST_DAYS:
        return None

    key = _cache_key("forecast", resort.name, target_date, target_date)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    data = _fetch_json(FORECAST_URL, {
        "latitude": resort.latitude, "longitude": resort.longitude,
        "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,weather_code",
        "timezone": "auto",
        "start_date": target_date.isoformat(), "end_date": target_date.isoformat(),
    })

    daily = data.get("daily") or {}
    times = daily.get("time") or []
    if not times:
        return None

    forecast = WeatherForecast(
        date=target_date,
        temp_max_c=daily["temperature_2m_max"][0],
        temp_min_c=daily["temperature_2m_min"][0],
        snowfall_cm=daily["snowfall_sum"][0],
        weather_description=_describe_weather_code(daily["weather_code"][0]),
    )
    if use_cache:
        get_cache().set(key, forecast)
    return forecast


def get_historical_average(
    resort: Resort, target_date: datetime.date, years_back: int = 10,
    window_days: int = 3, use_cache: bool = True,
) -> Optional[HistoricalWeatherAverage]:
    """
    Averages real recorded weather from the past `years_back` years
    for the calendar window centered on target_date (+/- window_days),
    e.g. "the week of January 10" across the last 10 winters -- not a
    forecast, a climate baseline: "how good does this trip's timing
    USUALLY look."

    window_days widens the sample beyond one exact date per year
    (10 dates is a thin sample for an average) without smearing across
    genuinely different conditions -- 3 days either side stays within
    the same part of the season.

    Returns None only if EVERY year's request failed (Open-Meteo's
    archive has a few days' processing lag for the very latest data,
    so the most recent year can occasionally be briefly unavailable --
    this degrades to fewer years sampled, reflected honestly in
    years_sampled, not a failure, unless ALL of them come back empty).
    """
    _require_coordinates(resort)

    key = _cache_key("historical", resort.name, target_date, target_date)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    all_temp_max: List[float] = []
    all_temp_min: List[float] = []
    all_snowfall: List[float] = []
    years_sampled = 0

    for years_ago in range(1, years_back + 1):
        try:
            year = target_date.year - years_ago
            center = target_date.replace(year=year)
        except ValueError:
            # Feb 29 in a non-leap year -- skip that one year rather
            # than silently shifting the date.
            continue
        start = center - datetime.timedelta(days=window_days)
        end = center + datetime.timedelta(days=window_days)

        try:
            data = _fetch_json(ARCHIVE_URL, {
                "latitude": resort.latitude, "longitude": resort.longitude,
                "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum",
                "timezone": "auto",
                "start_date": start.isoformat(), "end_date": end.isoformat(),
            })
        except AdapterError:
            continue

        daily = data.get("daily") or {}
        temp_max = [t for t in (daily.get("temperature_2m_max") or []) if t is not None]
        temp_min = [t for t in (daily.get("temperature_2m_min") or []) if t is not None]
        snowfall = [s for s in (daily.get("snowfall_sum") or []) if s is not None]
        if not temp_max:
            continue

        all_temp_max.extend(temp_max)
        all_temp_min.extend(temp_min)
        all_snowfall.extend(snowfall)
        years_sampled += 1

    if years_sampled == 0:
        return None

    window_start = target_date - datetime.timedelta(days=window_days)
    window_end = target_date + datetime.timedelta(days=window_days)
    result = HistoricalWeatherAverage(
        avg_temp_max_c=round(sum(all_temp_max) / len(all_temp_max), 1),
        avg_temp_min_c=round(sum(all_temp_min) / len(all_temp_min), 1),
        avg_snowfall_cm=round(sum(all_snowfall) / len(all_snowfall), 1) if all_snowfall else 0.0,
        years_sampled=years_sampled,
        date_range_label=f"{window_start.strftime('%b %d')} - {window_end.strftime('%b %d')}",
    )
    if use_cache:
        get_cache().set(key, result)
    return result


def clear_cache() -> None:
    """Test/ops helper, matching every other adapter's clear_cache."""
    get_cache().clear()
