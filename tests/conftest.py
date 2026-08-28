"""
Shared, autouse test setup.

WHY THIS FILE EXISTS: neither adapters/google_flights_adapter.py nor
adapters/google_hotels_adapter.py needs an API key (see each module's
own docstring), unlike the SerpApi adapters they replaced. Before those
swaps, an unset SERPAPI_API_KEY in the test environment was
accidentally the thing keeping the ENTIRE test suite from making real
network calls whenever a test posted a dated search -- there was no
key, so live pricing was never even attempted. That safety net is gone
now that neither leg needs a key at all, so it has to be replaced
explicitly, or the full suite starts scraping Google for real on every
run: slow (measured 116-127s vs. ~8-12s blocked, while building each
swap), flaky (network- and Google's-anti-bot-mood-dependent), and a
real risk of the exact IP-ban outcome both adapters' own docstrings
warn about, now applied to a CI/dev machine hammering it on every test
run.

Patched at each adapter's actual THIRD-PARTY network boundary --
`fast_flights.get_flights`, `fast_flights.fetcher.fetch_flights_html`,
and `primp.Client.get` -- rather than anything in this project's own
adapter modules, so tests that monkeypatch THIS project's own functions
(e.g. test_google_flights_adapter.py patching _search_one_airport,
test_google_hotels_adapter.py patching _fetch_html, to test each
adapter's own orchestration) are unaffected; they never reach these
patched calls at all.

fetch_flights_html is patched IN ADDITION TO get_flights: google_flights_
adapter.booking_url()'s round-trip path (see that module's own docstring)
needs the raw JSON payload get_flights() itself discards, so
_search_one_airport calls fetch_flights_html directly rather than going
through get_flights() -- get_flights() alone no longer covers every real
network path this adapter can take.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_real_flight_scraping(monkeypatch):
    import fast_flights
    import fast_flights.fetcher

    def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "fast_flights made a real network call during a test run -- "
            "mock the adapter boundary instead (see conftest.py's docstring)."
        )

    monkeypatch.setattr(fast_flights, "get_flights", _blocked)
    monkeypatch.setattr(fast_flights.fetcher, "fetch_flights_html", _blocked)
    yield


@pytest.fixture(autouse=True)
def _no_real_hotel_scraping(monkeypatch):
    import primp

    def _blocked(self, *_args, **_kwargs):
        raise RuntimeError(
            "primp.Client.get was called for real during a test run -- "
            "mock adapters.google_hotels_adapter._fetch_html instead (see conftest.py's docstring)."
        )

    monkeypatch.setattr(primp.Client, "get", _blocked)
    yield


@pytest.fixture(autouse=True)
def _no_real_weather_requests(monkeypatch):
    # adapters/weather_adapter.py (Open-Meteo) needs no API key either --
    # same hazard as the two above, at requests.get instead of
    # fast_flights/primp. Other adapters (flight_adapter.py,
    # serpapi_hotel_adapter.py, accommodation_adapter.py) also use
    # requests, but those are unswapped SerpApi/Booking fallbacks gated
    # behind an API key that's never set in the test environment, so
    # they never reach this call for real regardless -- blocking it here
    # is still correct for them, just redundant.
    import requests

    def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "requests.get was called for real during a test run -- "
            "mock adapters.weather_adapter._fetch_json instead (see conftest.py's docstring)."
        )

    monkeypatch.setattr(requests, "get", _blocked)
    yield


@pytest.fixture(autouse=True)
def _no_retry_backoff_in_tests(monkeypatch):
    """
    The flight adapter retries a failed scrape once with a short
    randomised pause -- correct against a real, rate-limitable provider,
    but pure dead time in a test suite where every failure is a mock.
    Without this, the tests that deliberately make a fetch fail each
    slept ~1s and the suite time roughly doubled.

    The retry itself still runs; only the sleep is removed, so the
    retry BEHAVIOUR stays under test.
    """
    from ski_optimizer.adapters import google_flights_adapter

    monkeypatch.setattr(google_flights_adapter, "_RETRY_BASE_DELAY_S", 0.0)

    # Same reasoning for the live-pricing request stagger: it exists to
    # make real traffic look less like a burst of automation, and is
    # pure dead time against mocks.
    from ski_optimizer.engine import date_search

    monkeypatch.setattr(date_search, "_REQUEST_STAGGER_S", 0.0)


@pytest.fixture(autouse=True)
def _no_real_kiwi_mcp(monkeypatch):
    """
    Keep the suite OFFLINE: with Kiwi wired in as the scraper's
    fallback (cost_calculator._kiwi_flight_fallback), every pre-existing
    test that mocks Google Flights to fail/return-empty would otherwise
    fall through to a REAL network call against mcp.kiwi.com -- turning
    a 10-second suite into minutes of live traffic. The transport is
    stubbed to raise; tests that want Kiwi behavior mock
    kiwi_mcp_adapter.search_flights directly (mock.patch inside the
    test body overrides this setup-time stub).
    """
    from ski_optimizer.adapters import kiwi_mcp_adapter
    from ski_optimizer.adapters.base import AdapterError

    def _offline(_args):
        raise AdapterError("network disabled in tests (see conftest._no_real_kiwi_mcp)")

    monkeypatch.setattr(kiwi_mcp_adapter, "_call_search_tool", _offline)
