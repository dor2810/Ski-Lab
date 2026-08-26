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
    assert forecast.weather_description == "Moderate snow"


def test_get_forecast_caches_identical_queries(monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(url, params):
        call_count["n"] += 1
        return {
            "daily": {
                "time": ["x"], "temperature_2m_max": [1.0], "temperature_2m_min": [-1.0],
                "snowfall_sum": [0.0], "weather_code": [0],
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
