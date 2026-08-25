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
