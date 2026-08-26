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

Both of the above answer for ONE date. get_forecast_range(),
get_historical_daily_breakdown(), and get_trip_weather() are the same
two ideas extended across a WHOLE trip (check-in..check-out), one
DailyWeather per day -- forecast where possible, historical average per
calendar day otherwise, mixed within the same trip when its dates
straddle the forecast horizon. get_trip_weather() is the one callers
actually want; the other two are its building blocks (fetched
efficiently -- one bulk request per data source, not one per day).

Needs Resort.latitude/longitude (see that field's own docstring in
models.py for how they were sourced) -- Open-Meteo takes coordinates,
not place names.

SNOW CONDITIONS, not just weather: every function here also returns
snow_depth_cm (ground/base depth) alongside snowfall_cm (NEW snow that
fell/will fall). Same provider, same two endpoints, same forecast-vs-
historical split -- Open-Meteo's `snow_depth_max` daily variable
(meters, converted to cm here) needed no new adapter, no new API key,
just one more field on the existing request. Live-tested (2026-08-26)
against Chamonix's coordinates: winter dates (mid-January) returned a
real, plausible ~0.5m base depth; summer dates correctly returned 0.
This is the actual "is there snow on the ground" answer a forecast
temperature can't give on its own -- a mild, dry week can still have a
great base from earlier storms, and a cold, snowy-looking forecast
means little if the base is already thin.

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
from typing import Dict, List, Optional, Tuple

from ..models import DailyWeather, HistoricalWeatherAverage, Resort, TripWeatherSummary, WeatherForecast
from .base import AdapterError
from .response_cache import get_cache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo's real forecast horizon, empirically confirmed live: a
# request for end_date=today+16 returned "Parameter 'end_date' is out
# of allowed range" with the actual allowed upper bound at today+15 --
# NOT +16 as originally assumed from the docs' "up to 16 days" phrasing
# (off-by-one between "16 days of data" and "16 days from today").
# get_trip_weather() also treats a forecast-range failure defensively
# (falls through to historical for those days) rather than trusting
# this constant to be perfectly exact forever -- Open-Meteo's own
# model-refresh timing could plausibly shift the real boundary by a day
# in either direction.
MAX_FORECAST_DAYS = 15

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


def _m_to_cm(value: Optional[float]) -> float:
    # Open-Meteo reports snow_depth in meters (unlike snowfall_sum,
    # which is already cm) -- converted here so every DailyWeather/
    # WeatherForecast field in this module is in the same unit.
    return round(value * 100, 1) if value is not None else 0.0


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
        "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,snow_depth_max,weather_code",
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
        snow_depth_cm=_m_to_cm(daily["snow_depth_max"][0]),
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
    all_snow_depth: List[float] = []
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
                "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,snow_depth_max",
                "timezone": "auto",
                "start_date": start.isoformat(), "end_date": end.isoformat(),
            })
        except AdapterError:
            continue

        daily = data.get("daily") or {}
        temp_max = [t for t in (daily.get("temperature_2m_max") or []) if t is not None]
        temp_min = [t for t in (daily.get("temperature_2m_min") or []) if t is not None]
        snowfall = [s for s in (daily.get("snowfall_sum") or []) if s is not None]
        snow_depth = [d for d in (daily.get("snow_depth_max") or []) if d is not None]
        if not temp_max:
            continue

        all_temp_max.extend(temp_max)
        all_temp_min.extend(temp_min)
        all_snowfall.extend(snowfall)
        all_snow_depth.extend(snow_depth)
        years_sampled += 1

    if years_sampled == 0:
        return None

    window_start = target_date - datetime.timedelta(days=window_days)
    window_end = target_date + datetime.timedelta(days=window_days)
    result = HistoricalWeatherAverage(
        avg_temp_max_c=round(sum(all_temp_max) / len(all_temp_max), 1),
        avg_temp_min_c=round(sum(all_temp_min) / len(all_temp_min), 1),
        avg_snowfall_cm=round(sum(all_snowfall) / len(all_snowfall), 1) if all_snowfall else 0.0,
        avg_snow_depth_cm=_m_to_cm(sum(all_snow_depth) / len(all_snow_depth)) if all_snow_depth else 0.0,
        years_sampled=years_sampled,
        date_range_label=f"{window_start.strftime('%b %d')} - {window_end.strftime('%b %d')}",
    )
    if use_cache:
        get_cache().set(key, result)
    return result


def _trip_dates(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    n = (end_date - start_date).days
    return [start_date + datetime.timedelta(days=i) for i in range(n + 1)]


def get_forecast_range(
    resort: Resort, start_date: datetime.date, end_date: datetime.date, use_cache: bool = True,
) -> List[DailyWeather]:
    """
    Real forecasts for every date in [start_date, end_date] that falls
    within Open-Meteo's actual forecast horizon (today..+MAX_FORECAST_
    DAYS) -- ONE bulk request covers the whole span (Open-Meteo's
    forecast API natively takes a start_date/end_date range), not one
    request per day. Dates outside the horizon are simply absent from
    the result -- see get_historical_daily_breakdown() for how those
    get covered instead, and get_trip_weather() for how the two are
    combined into one trip.
    """
    _require_coordinates(resort)
    today = datetime.date.today()
    horizon_end = today + datetime.timedelta(days=MAX_FORECAST_DAYS)
    clipped_start = max(start_date, today)
    clipped_end = min(end_date, horizon_end)
    if clipped_start > clipped_end:
        return []

    key = _cache_key("forecast_range", resort.name, clipped_start, clipped_end)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    data = _fetch_json(FORECAST_URL, {
        "latitude": resort.latitude, "longitude": resort.longitude,
        "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,snow_depth_max,weather_code",
        "timezone": "auto",
        "start_date": clipped_start.isoformat(), "end_date": clipped_end.isoformat(),
    })
    daily = data.get("daily") or {}
    times = daily.get("time") or []
    days = []
    for i, t in enumerate(times):
        try:
            days.append(DailyWeather(
                date=datetime.date.fromisoformat(t),
                temp_max_c=daily["temperature_2m_max"][i],
                temp_min_c=daily["temperature_2m_min"][i],
                snowfall_cm=daily["snowfall_sum"][i],
                snow_depth_cm=_m_to_cm(daily["snow_depth_max"][i]),
                is_live_forecast=True,
                description=_describe_weather_code(daily["weather_code"][i]),
            ))
        except (IndexError, KeyError, TypeError, ValueError):
            continue  # one malformed day shouldn't sink the rest of the range
    if use_cache:
        get_cache().set(key, days)
    return days


def get_historical_daily_breakdown(
    resort: Resort, start_date: datetime.date, end_date: datetime.date,
    years_back: int = 5, use_cache: bool = True,
) -> List[DailyWeather]:
    """
    One real historical average PER CALENDAR DAY in [start_date,
    end_date], each averaged across years_back past years' real
    recorded weather for that SAME calendar day -- e.g. this trip's
    "Jan 10" is averaged against the last 5 January 10ths, "Jan 11"
    against the last 5 January 11ths, and so on. Unlike
    get_historical_average()'s single blended window, no +/-window_days
    smoothing is needed here: each day already gets years_back real
    samples of its own.

    EFFICIENT ON PURPOSE: fetches ONE request PER YEAR spanning the
    WHOLE date range (not one request per day per year, which would be
    years_back x trip_length requests for even a modest week-long
    trip) -- Open-Meteo's archive API already returns a full daily
    series for a date range in one call, so shifting the whole range
    back by each year and making ONE call per year is years_back
    requests total.
    """
    _require_coordinates(resort)

    key = _cache_key("historical_range", resort.name, start_date, end_date)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    trip_dates = _trip_dates(start_date, end_date)
    per_day_samples: Dict[int, List[Tuple[float, float, float, float]]] = {}

    for years_ago in range(1, years_back + 1):
        try:
            shifted_dates = [d.replace(year=d.year - years_ago) for d in trip_dates]
        except ValueError:
            continue  # a Feb 29 in this trip has no match in a non-leap shifted year -- skip that year

        try:
            data = _fetch_json(ARCHIVE_URL, {
                "latitude": resort.latitude, "longitude": resort.longitude,
                "daily": "temperature_2m_max,temperature_2m_min,snowfall_sum,snow_depth_max",
                "timezone": "auto",
                "start_date": shifted_dates[0].isoformat(), "end_date": shifted_dates[-1].isoformat(),
            })
        except AdapterError:
            continue

        daily = data.get("daily") or {}
        times = daily.get("time") or []
        for i in range(min(len(times), len(trip_dates))):
            try:
                tmax = daily["temperature_2m_max"][i]
                tmin = daily["temperature_2m_min"][i]
                snow = daily["snowfall_sum"][i]
                depth = daily["snow_depth_max"][i]
            except (IndexError, KeyError):
                continue
            if tmax is None or tmin is None:
                continue
            per_day_samples.setdefault(i, []).append((tmax, tmin, snow or 0.0, depth or 0.0))

    days = []
    for i, trip_date in enumerate(trip_dates):
        samples = per_day_samples.get(i)
        if not samples:
            continue
        days.append(DailyWeather(
            date=trip_date,
            temp_max_c=round(sum(s[0] for s in samples) / len(samples), 1),
            temp_min_c=round(sum(s[1] for s in samples) / len(samples), 1),
            snowfall_cm=round(sum(s[2] for s in samples) / len(samples), 1),
            snow_depth_cm=_m_to_cm(sum(s[3] for s in samples) / len(samples)),
            is_live_forecast=False,
            years_sampled=len(samples),
        ))

    if use_cache:
        get_cache().set(key, days)
    return days


def get_trip_weather(
    resort: Resort, start_date: datetime.date, end_date: datetime.date,
    historical_years_back: int = 5,
) -> Optional[TripWeatherSummary]:
    """
    Weather for a WHOLE trip (check-in..check-out inclusive), one day
    at a time -- see get_forecast_range()/get_historical_daily_
    breakdown()'s own docstrings. A trip whose dates straddle
    Open-Meteo's forecast horizon gets real forecast days for the near
    part and historical-average days for the rest, not one data source
    forced onto every day.

    Returns None only when NOTHING could be produced for any day in the
    range (e.g. no coordinates, or every request failing) -- a partial
    result (some days missing) is still returned, since a shorter-than-
    requested week is still real information, not nothing.
    """
    try:
        forecast_days = get_forecast_range(resort, start_date, end_date)
        forecast_covered_through = max((d.date for d in forecast_days), default=None)
    except AdapterError:
        # The forecast leg failing (a transient request error, or
        # MAX_FORECAST_DAYS drifting from the provider's real boundary
        # -- see that constant's own comment) shouldn't cost those
        # days entirely -- historical_start below falls back to
        # start_date itself, so the WHOLE trip gets historical coverage
        # instead of the forecast-eligible days silently vanishing.
        forecast_days = []
        forecast_covered_through = None

    historical_start = (
        forecast_covered_through + datetime.timedelta(days=1)
        if forecast_covered_through is not None else start_date
    )
    historical_days: List[DailyWeather] = []
    if historical_start <= end_date:
        historical_days = get_historical_daily_breakdown(
            resort, historical_start, end_date, years_back=historical_years_back)

    all_days = sorted(forecast_days + historical_days, key=lambda d: d.date)
    if not all_days:
        return None

    return TripWeatherSummary(
        days=all_days,
        avg_temp_max_c=round(sum(d.temp_max_c for d in all_days) / len(all_days), 1),
        avg_temp_min_c=round(sum(d.temp_min_c for d in all_days) / len(all_days), 1),
        avg_snowfall_cm=round(sum(d.snowfall_cm for d in all_days) / len(all_days), 1),
        avg_snow_depth_cm=round(sum(d.snow_depth_cm for d in all_days) / len(all_days), 1),
    )


def clear_cache() -> None:
    """Test/ops helper, matching every other adapter's clear_cache."""
    get_cache().clear()
