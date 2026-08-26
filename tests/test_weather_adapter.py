"""
Tests for adapters/weather_adapter.py.

Same philosophy as the other keyless adapters in this package: parsing/
orchestration is tested offline by mocking _fetch_json (this module's
own network boundary), never the real requests.get call (blocked
globally anyway -- see tests/conftest.py).

What these do NOT prove: that Open-Meteo's real response shape still
matches what's hardcoded here. That was verified live, by hand, while
building this adapter (see the module's own docstring) -- not something
an offline test can keep proving on every run.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import weather_adapter as wa
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.models import Resort


@pytest.fixture(autouse=True)
def _fresh_cache():
    response_cache.get_cache().clear()
    yield
    response_cache.get_cache().clear()


def _resort(**overrides):
    kw = dict(
        name="Val Thorens", country="France", region="Savoy",
        base_elevation_m=1850, summit_elevation_m=3230, vertical_drop_m=1380,
        num_lifts=31, piste_km=150.0, off_piste_rating=4, snow_reliability=5,
        nightlife_rating=5, family_friendliness=3, nearest_airport="Geneva (GVA)",
        airport_distance_km=147.0, transfer_time_minutes=150.0,
        ski_pass_6day_eur=340.0, accommodation_eur_per_night=140.0,
        latitude=45.2978, longitude=6.5838,
    )
    kw.update(overrides)
    return Resort(**kw)


# --- _describe_weather_code ---

def test_describe_weather_code_maps_known_codes():
    assert wa._describe_weather_code(0) == "Clear sky"
    assert wa._describe_weather_code(75) == "Heavy snow"


def test_describe_weather_code_falls_back_for_unknown_codes():
    assert wa._describe_weather_code(12345) == "WMO code 12345"


def test_describe_weather_code_handles_none():
    assert wa._describe_weather_code(None) == "Unknown"


# --- get_forecast ---

def test_get_forecast_requires_coordinates():
    resort = _resort(latitude=None, longitude=None)
    with pytest.raises(AdapterError):
        wa.get_forecast(resort, date.today() + timedelta(days=3))


def test_get_forecast_returns_none_beyond_the_forecast_horizon():
    resort = _resort()
    far_future = date.today() + timedelta(days=wa.MAX_FORECAST_DAYS + 30)
    assert wa.get_forecast(resort, far_future) is None


def test_get_forecast_returns_none_for_a_past_date():
    resort = _resort()
    assert wa.get_forecast(resort, date.today() - timedelta(days=1)) is None


def test_get_forecast_parses_a_real_shaped_response(monkeypatch):
    def fake_fetch(url, params):
        return {
            "daily": {
                "time": ["2027-01-10"],
                "temperature_2m_max": [-2.5],
                "temperature_2m_min": [-10.1],
                "snowfall_sum": [4.2],
                "snow_depth_max": [0.85],  # meters -- converted to cm
                "weather_code": [73],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    target = date.today() + timedelta(days=5)
    forecast = wa.get_forecast(resort, target, use_cache=False)
    assert forecast is not None
    assert forecast.temp_max_c == -2.5
    assert forecast.temp_min_c == -10.1
    assert forecast.snowfall_cm == 4.2
    assert forecast.snow_depth_cm == 85.0
    assert forecast.weather_description == "Moderate snow"


def test_get_forecast_caches_identical_queries(monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(url, params):
        call_count["n"] += 1
        return {
            "daily": {
                "time": ["x"], "temperature_2m_max": [1.0], "temperature_2m_min": [-1.0],
                "snowfall_sum": [0.0], "snow_depth_max": [0.1], "weather_code": [0],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    target = date.today() + timedelta(days=2)
    wa.get_forecast(resort, target, use_cache=True)
    wa.get_forecast(resort, target, use_cache=True)
    assert call_count["n"] == 1


# --- get_historical_average ---

def test_get_historical_average_requires_coordinates():
    resort = _resort(latitude=None, longitude=None)
    with pytest.raises(AdapterError):
        wa.get_historical_average(resort, date(2027, 1, 10))


def test_get_historical_average_computes_a_real_mean(monkeypatch):
    def fake_fetch(url, params):
        return {
            "daily": {
                "temperature_2m_max": [-1.0, -3.0, -5.0],
                "temperature_2m_min": [-8.0, -10.0, -12.0],
                "snowfall_sum": [0.0, 2.0, 4.0],
                "snow_depth_max": [0.3, 0.4, 0.5],  # meters
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    result = wa.get_historical_average(resort, date(2027, 1, 10), years_back=3, use_cache=False)
    assert result is not None
    assert result.years_sampled == 3
    # each fake year contributes the SAME 3 values -> mean == that value
    assert result.avg_temp_max_c == -3.0
    assert result.avg_temp_min_c == -10.0
    assert result.avg_snowfall_cm == 2.0
    assert result.avg_snow_depth_cm == 40.0  # mean of 0.3/0.4/0.5m -> 0.4m -> 40cm
    assert result.date_range_label == "Jan 07 - Jan 13"


def test_get_historical_average_degrades_gracefully_when_some_years_fail(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, params):
        calls["n"] += 1
        if calls["n"] == 1:
            raise AdapterError("simulated provider hiccup for the most recent year")
        return {
            "daily": {
                "temperature_2m_max": [0.0], "temperature_2m_min": [-5.0], "snowfall_sum": [1.0],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    result = wa.get_historical_average(resort, date(2027, 1, 10), years_back=3, use_cache=False)
    assert result is not None
    assert result.years_sampled == 2  # one year's request failed, two succeeded


def test_get_historical_average_is_none_when_every_year_fails(monkeypatch):
    def fake_fetch(url, params):
        raise AdapterError("provider down")

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    assert wa.get_historical_average(resort, date(2027, 1, 10), years_back=3, use_cache=False) is None


# --- get_forecast_range ---

def test_get_forecast_range_clips_to_the_horizon(monkeypatch):
    calls = []

    def fake_fetch(url, params):
        calls.append((params["start_date"], params["end_date"]))
        return {"daily": {"time": [], "temperature_2m_max": [], "temperature_2m_min": [],
                          "snowfall_sum": [], "weather_code": []}}

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    far_future_end = date.today() + timedelta(days=wa.MAX_FORECAST_DAYS + 30)
    wa.get_forecast_range(resort, date.today(), far_future_end, use_cache=False)
    start, end = calls[0]
    assert end == (date.today() + timedelta(days=wa.MAX_FORECAST_DAYS)).isoformat()


def test_get_forecast_range_is_empty_when_the_whole_range_is_beyond_the_horizon():
    resort = _resort()
    far_start = date.today() + timedelta(days=wa.MAX_FORECAST_DAYS + 10)
    far_end = far_start + timedelta(days=3)
    assert wa.get_forecast_range(resort, far_start, far_end, use_cache=False) == []


def test_get_forecast_range_parses_a_multi_day_response(monkeypatch):
    def fake_fetch(url, params):
        return {
            "daily": {
                "time": ["2026-08-28", "2026-08-29"],
                "temperature_2m_max": [15.0, 16.0],
                "temperature_2m_min": [5.0, 6.0],
                "snowfall_sum": [0.0, 0.0],
                "snow_depth_max": [0.0, 0.0],
                "weather_code": [0, 3],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    days = wa.get_forecast_range(resort, date.today() + timedelta(days=2),
                                 date.today() + timedelta(days=3), use_cache=False)
    assert len(days) == 2
    assert days[0].is_live_forecast is True
    assert days[0].description == "Clear sky"
    assert days[1].description == "Overcast"
    assert days[0].snow_depth_cm == 0.0


# --- get_historical_daily_breakdown ---

def test_get_historical_daily_breakdown_averages_per_calendar_day(monkeypatch):
    # Each fetched "year" returns the SAME two-day series, so each
    # trip day's average should equal that constant value exactly --
    # and each day must keep its OWN sample, not get pooled together.
    def fake_fetch(url, params):
        return {
            "daily": {
                "time": [params["start_date"], params["end_date"]],
                "temperature_2m_max": [-1.0, -5.0],
                "temperature_2m_min": [-8.0, -12.0],
                "snowfall_sum": [1.0, 3.0],
                "snow_depth_max": [0.2, 0.6],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    days = wa.get_historical_daily_breakdown(resort, date(2027, 1, 10), date(2027, 1, 11),
                                              years_back=3, use_cache=False)
    assert len(days) == 2
    assert days[0].date == date(2027, 1, 10)
    assert days[0].temp_max_c == -1.0
    assert days[0].years_sampled == 3
    assert days[0].snow_depth_cm == 20.0
    assert days[1].date == date(2027, 1, 11)
    assert days[1].temp_max_c == -5.0
    assert days[1].snow_depth_cm == 60.0


def test_get_historical_daily_breakdown_makes_one_request_per_year_not_per_day(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, params):
        calls["n"] += 1
        return {"daily": {"temperature_2m_max": [1.0] * 7, "temperature_2m_min": [-1.0] * 7,
                          "snowfall_sum": [0.0] * 7}}

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    wa.get_historical_daily_breakdown(resort, date(2027, 1, 10), date(2027, 1, 16),
                                      years_back=4, use_cache=False)
    assert calls["n"] == 4  # years_back requests, NOT years_back * 7 days


def test_get_historical_daily_breakdown_skips_a_day_with_no_samples(monkeypatch):
    monkeypatch.setattr(wa, "_fetch_json", lambda url, params: {"daily": {
        "temperature_2m_max": [], "temperature_2m_min": [], "snowfall_sum": [],
    }})
    resort = _resort()
    days = wa.get_historical_daily_breakdown(resort, date(2027, 1, 10), date(2027, 1, 10),
                                              years_back=2, use_cache=False)
    assert days == []


# --- get_trip_weather ---

def test_get_trip_weather_combines_forecast_and_historical_days(monkeypatch):
    forecast_day = wa.DailyWeather(date=date.today() + timedelta(days=2), temp_max_c=10.0,
                                   temp_min_c=2.0, snowfall_cm=0.0, snow_depth_cm=0.0,
                                   is_live_forecast=True, description="Clear sky")
    historical_day = wa.DailyWeather(date=date.today() + timedelta(days=3), temp_max_c=-2.0,
                                     temp_min_c=-8.0, snowfall_cm=1.0, snow_depth_cm=25.0,
                                     is_live_forecast=False, years_sampled=5)

    monkeypatch.setattr(wa, "get_forecast_range", lambda *a, **k: [forecast_day])
    monkeypatch.setattr(wa, "get_historical_daily_breakdown", lambda *a, **k: [historical_day])
    resort = _resort()
    summary = wa.get_trip_weather(resort, date.today() + timedelta(days=2), date.today() + timedelta(days=3))
    assert summary is not None
    assert len(summary.days) == 2
    assert summary.days[0].is_live_forecast is True
    assert summary.days[1].is_live_forecast is False
    assert summary.avg_temp_max_c == 4.0  # (10.0 + -2.0) / 2
    assert summary.avg_snow_depth_cm == 12.5  # (0.0 + 25.0) / 2


def test_get_trip_weather_falls_back_to_historical_for_the_whole_trip_when_forecast_fails(monkeypatch):
    # REGRESSION: a forecast-leg failure used to silently drop the
    # would-have-been-forecastable days entirely instead of falling
    # back to historical for them too.
    def raise_adapter_error(*a, **k):
        raise AdapterError("simulated forecast outage")

    historical_day = wa.DailyWeather(date=date.today() + timedelta(days=2), temp_max_c=1.0,
                                     temp_min_c=-3.0, snowfall_cm=0.5, snow_depth_cm=10.0,
                                     is_live_forecast=False, years_sampled=5)
    calls = []

    def fake_historical(resort, start, end, **kwargs):
        calls.append((start, end))
        return [historical_day]

    monkeypatch.setattr(wa, "get_forecast_range", raise_adapter_error)
    monkeypatch.setattr(wa, "get_historical_daily_breakdown", fake_historical)
    resort = _resort()
    target_start = date.today() + timedelta(days=2)
    summary = wa.get_trip_weather(resort, target_start, target_start)
    assert summary is not None
    assert len(summary.days) == 1
    # historical was asked to cover from the TRIP START, not from
    # after some horizon boundary -- the forecast leg produced nothing.
    assert calls[0][0] == target_start


def test_get_trip_weather_is_none_when_nothing_is_available(monkeypatch):
    monkeypatch.setattr(wa, "get_forecast_range", lambda *a, **k: [])
    monkeypatch.setattr(wa, "get_historical_daily_breakdown", lambda *a, **k: [])
    resort = _resort()
    assert wa.get_trip_weather(resort, date(2027, 1, 10), date(2027, 1, 16)) is None


def test_get_historical_average_skips_feb_29_years_cleanly(monkeypatch):
    # target_date.replace(year=...) raises ValueError for Feb 29 in a
    # non-leap year -- must skip that one year, not crash the whole call.
    def fake_fetch(url, params):
        return {
            "daily": {
                "temperature_2m_max": [1.0], "temperature_2m_min": [-2.0], "snowfall_sum": [0.5],
            }
        }

    monkeypatch.setattr(wa, "_fetch_json", fake_fetch)
    resort = _resort()
    result = wa.get_historical_average(resort, date(2028, 2, 29), years_back=4, use_cache=False)
    assert result is not None
    assert result.years_sampled <= 4
