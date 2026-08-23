"""
[PHASE 7 — not implemented yet]

Candidate providers: Open-Meteo (free) or Meteoblue. Only matters for
near-term trips -- for dates months out, use snow_adapter's historical
reliability data instead, not a forecast that far ahead (see
engine/reranker.py's docstring).

Planned interface:

    def get_forecast(resort: Resort, target_date: date) -> WeatherForecast:
        raise NotImplementedError
"""


def get_forecast(*args, **kwargs):
    raise NotImplementedError("Live weather forecast is planned for Phase 7 (see module docstring).")
