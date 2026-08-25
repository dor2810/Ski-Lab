"""
Shared, autouse test setup.

WHY THIS FILE EXISTS: adapters/google_flights_adapter.py needs no API
key (see its own module docstring), unlike the SerpApi adapter it
replaced for live flight pricing. Before that swap, an unset
SERPAPI_API_KEY in the test environment was accidentally the thing
keeping the ENTIRE test suite from making real network calls whenever
a test posted a dated search -- there was no key, so live pricing was
never even attempted. That safety net is gone now that flights don't
need a key at all, so it has to be replaced explicitly, or the full
suite starts scraping Google Flights for real on every run: slow (a
116s run vs. ~8s, measured while building this), flaky (network- and
Google's-anti-bot-mood-dependent), and a real risk of the exact
IP-ban outcome google_flights_adapter.py's own docstring warns about,
now applied to a CI/dev machine hammering it on every test run.

Patched at `fast_flights.get_flights` -- the actual network boundary --
rather than anything in google_flights_adapter.py itself, so tests that
monkeypatch THIS project's own functions (e.g.
test_google_flights_adapter.py patching _search_one_airport directly
to test search_flights' orchestration) are unaffected; they never reach
this patched call at all.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_real_flight_scraping(monkeypatch):
    import fast_flights

    def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "fast_flights.get_flights was called for real during a test run -- "
            "mock the adapter boundary instead (see conftest.py's docstring)."
        )

    monkeypatch.setattr(fast_flights, "get_flights", _blocked)
    yield
