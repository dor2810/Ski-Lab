"""
Tests for POST /trips/search. Same honesty note as test_auth.py: written
to standard conventions, syntax-checked, never actually executed here
(no network access to install dependencies in this sandbox).
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ski_optimizer.api.main import app
from ski_optimizer.api import security, rate_limit
from ski_optimizer.db.database import Base, get_db

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


CSRF_HEADERS = {security.CSRF_HEADER_NAME: security.CSRF_HEADER_VALUE}


@pytest.fixture(autouse=True)
def _fresh_db():
    # See the matching comment in test_auth.py's _fresh_db: this override
    # must be scoped to setup/teardown, not assigned at module-import time,
    # or whichever test file pytest imports last wins the override for the
    # whole session -- including the other file's tests.
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    # rate_limit's limiters are module-level singletons (see its own
    # docstring on why -- same reasoning as response_cache.py). Every
    # TestClient request in this file shares one fixed client identity,
    # so without clearing between tests, the per-IP burst limit (default
    # 6/minute) would trip partway through this file's own test list and
    # fail later tests with an unrelated 429 -- not what any of them
    # are testing for.
    rate_limit.clear_all()
    yield
    Base.metadata.drop_all(bind=engine)
    del app.dependency_overrides[get_db]


@pytest.fixture
def authed_client():
    """A TestClient that's already registered + logged in, with the
    bearer access token set as a persistent per-client header (see
    api/routes/auth.py -- auth is bearer-token, not cookie, so there's
    no ambient credential for TestClient to carry automatically)."""
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/auth/register", json={
        "email": "searcher@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    access_token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {access_token}"
    return client


def test_search_requires_authentication_by_default(monkeypatch):
    # Auth-required is the DEFAULT (restored 2026-08-25 now that real
    # sign-in exists on the frontend -- see
    # routes/auth.get_current_user_for_search's docstring).
    monkeypatch.delenv("ALLOW_ANONYMOUS_SEARCH", raising=False)
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_search_allows_anonymous_when_explicitly_enabled(monkeypatch):
    # ALLOW_ANONYMOUS_SEARCH=true is the local-dev/testing escape hatch.
    monkeypatch.setenv("ALLOW_ANONYMOUS_SEARCH", "true")
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) > 0


def test_a_real_session_works_for_search(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_search_without_csrf_header_is_rejected(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
    })  # no CSRF header
    assert resp.status_code == 403


def test_search_returns_ranked_results_within_budget(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5, "group_size": 2,
        "skill_level": "advanced", "accommodation_tier": "budget",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_resort_count"] == 37
    assert len(body["results"]) > 0
    for result in body["results"]:
        assert result["cost"]["total_eur"] <= 1500
    # sorted descending by score
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_search_results_carry_flight_and_accommodation_links(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert body["results"]
    for result in body["results"]:
        # No outbound_date in this request -> no dated flight link, but
        # the resort/route is still known, so flight_search_url is None
        # or a bare (dateless) query, never a fabricated date.
        assert "flight_search_url" in result
        assert result["accommodation_search_url"].startswith(
            "https://www.google.com/travel/hotels?q="
        )
        # Real, working links for every result, not just the top one --
        # see engine/links.py's equipment_search_url/ski_pass_search_url.
        # Every resort in this project's data has a curated ski-pass URL
        # (data/ski_pass_links.py), so this is never the Google-search
        # fallback in practice -- just a real, non-empty URL.
        assert result["equipment_search_url"]
        assert result["ski_pass_search_url"]


def test_search_flight_link_includes_dates_when_outbound_date_is_given(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    # tfs= is an opaque structured blob now (see engine/links.py's
    # docstring on why the old natural-language "on ... through ..."
    # query was replaced) -- just confirm this is the dated, structured
    # search link, not the dateless natural-language fallback.
    url = result["flight_search_url"]
    assert url.startswith("https://www.google.com/travel/flights/search?tfs=")


def test_search_with_outbound_date_falls_back_to_static_when_live_pricing_is_unavailable(authed_client, monkeypatch):
    # Live flight pricing (adapters/google_flights_adapter.py) needs no
    # API key, so it can't be disabled via env var any more -- mock the
    # adapter call itself to fail instead, matching this test's real
    # intent: passing outbound_date must degrade to the static estimate
    # when a live quote genuinely isn't available, not error. Also keeps
    # this test network-free rather than hitting Google Flights for real.
    from ski_optimizer.adapters import google_flights_adapter
    from ski_optimizer.adapters.base import AdapterError

    def _raise(*_args, **_kwargs):
        raise AdapterError("no network in tests")

    monkeypatch.setattr(google_flights_adapter, "search_flights", _raise)
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "outbound_date": "2027-01-02",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) > 0
    for result in body["results"]:
        assert result["cost"]["flight_price_is_live"] is False


def test_flight_search_url_uses_the_booking_link_when_available(authed_client, monkeypatch):
    # When live pricing succeeds AND a specific-flight booking link can
    # be built (adapters/google_flights_adapter.booking_url()), the API
    # should surface THAT, not the generic route/date search link -- a
    # real improvement, not just "still works."
    from ski_optimizer.adapters import google_flights_adapter
    from ski_optimizer.models import FlightOption, FlightSearchResult

    def fake_search_flights(**_kwargs):
        return FlightSearchResult(options=[
            FlightOption(price_eur=250.0, origin_airport="TLV", destination_airport="BGY",
                        airline="Test Air", total_duration_minutes=200, stops=0,
                        booking_token="fake-token"),
        ])

    monkeypatch.setattr(google_flights_adapter, "search_flights", fake_search_flights)
    monkeypatch.setattr(google_flights_adapter, "booking_url",
                        lambda *a, **k: "https://www.google.com/travel/flights/booking?tfs=FAKE&tfu=FAKE")

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    assert result["cost"]["flight_price_is_live"] is True
    assert result["flight_search_url"] == "https://www.google.com/travel/flights/booking?tfs=FAKE&tfu=FAKE"


def test_flight_search_url_falls_back_to_the_search_link_when_booking_url_is_unavailable(authed_client, monkeypatch):
    # This is the safety net: live pricing succeeding does NOT guarantee
    # a booking link can be built (expired token, round-trip return-leg
    # fetch failing, etc. -- see booking_url()'s own docstring). The
    # result must still carry a real, working link -- the same reliable
    # route/date search link this always fell back to -- never None and
    # never a broken URL.
    from ski_optimizer.adapters import google_flights_adapter
    from ski_optimizer.models import FlightOption, FlightSearchResult

    def fake_search_flights(**_kwargs):
        return FlightSearchResult(options=[
            FlightOption(price_eur=250.0, origin_airport="TLV", destination_airport="BGY",
                        airline="Test Air", total_duration_minutes=200, stops=0,
                        booking_token="fake-token"),
        ])

    monkeypatch.setattr(google_flights_adapter, "search_flights", fake_search_flights)
    monkeypatch.setattr(google_flights_adapter, "booking_url", lambda *a, **k: None)

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    assert result["cost"]["flight_price_is_live"] is True
    assert result["flight_search_url"].startswith("https://www.google.com/travel/flights/search?tfs=")


def test_accommodation_search_url_uses_the_specific_property_link_when_available(authed_client, monkeypatch):
    # Mirrors test_flight_search_url_uses_the_booking_link_when_available
    # for the accommodation side -- see that test's docstring.
    from ski_optimizer.adapters import google_hotels_adapter
    from ski_optimizer.models import AccommodationOption, AccommodationSearchResult

    def fake_search_accommodation(*_args, **_kwargs):
        return AccommodationSearchResult(options=[
            AccommodationOption(price_eur_per_night=100.0, property_name="Test Hotel"),
        ])

    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", fake_search_accommodation)
    monkeypatch.setattr(google_hotels_adapter, "specific_property_url",
                        lambda *a, **k: "https://www.google.com/travel/search?q=FAKE&ts=FAKE&qs=FAKE")

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    assert result["cost"]["accommodation_price_is_live"] is True
    assert result["accommodation_search_url"] == "https://www.google.com/travel/search?q=FAKE&ts=FAKE&qs=FAKE"


def test_accommodation_search_url_falls_back_when_specific_property_url_is_unavailable(authed_client, monkeypatch):
    # The realistic default state (no GOOGLE_KG_API_KEY configured) --
    # must still carry a real, working link, NARROWED to the real
    # scraped property name (not just a bare resort-wide search) since
    # that name is available for free here (same scrape that already
    # priced this result -- see _accommodation_property_name).
    from ski_optimizer.adapters import google_hotels_adapter
    from ski_optimizer.models import AccommodationOption, AccommodationSearchResult

    def fake_search_accommodation(*_args, **_kwargs):
        return AccommodationSearchResult(options=[
            AccommodationOption(price_eur_per_night=100.0, property_name="Test Hotel"),
        ])

    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", fake_search_accommodation)
    monkeypatch.setattr(google_hotels_adapter, "specific_property_url", lambda *a, **k: None)

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    assert result["cost"]["accommodation_price_is_live"] is True
    assert result["accommodation_property_name"] == "Test Hotel"
    assert result["accommodation_search_url"].startswith("https://www.google.com/travel/search?q=")
    from urllib.parse import unquote
    assert "Test Hotel" in unquote(result["accommodation_search_url"])


def test_transfer_search_url_is_populated_only_for_the_top_result(authed_client, monkeypatch):
    # Same amplification concern as flights/hotels: live_transfer_
    # booking_url() makes real, uncached-across-results live requests
    # (location resolution + a price quote) -- must never be attempted
    # for every result in a broad search.
    from ski_optimizer.api.routes import search as search_route

    calls = []
    monkeypatch.setattr(search_route, "live_transfer_booking_url",
                        lambda *a, **k: calls.append(1) or "https://booking.alps2alps.com/fake")
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 5000, "ski_days": 5, "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert len(body["results"]) > 1
    assert len(calls) <= 1
    assert body["results"][0]["transfer_search_url"] == "https://booking.alps2alps.com/fake"
    # Every OTHER result still gets a real, working link -- just the
    # generic Alps2Alps booking form, not a live-quoted one (attempt
    # is gated to the top result only, same as flight/accommodation).
    for result in body["results"][1:]:
        assert result["transfer_search_url"] == "https://booking.alps2alps.com/booking/index"


def test_transfer_search_url_falls_back_to_the_booking_form_when_the_provider_has_nothing(authed_client, monkeypatch):
    # Same "always real, never nothing" contract as flight/
    # accommodation search URLs -- a failed live quote must not leave
    # "View Transfer" with nowhere to go.
    from ski_optimizer.api.routes import search as search_route

    monkeypatch.setattr(search_route, "live_transfer_booking_url", lambda *a, **k: None)
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert body["results"][0]["transfer_search_url"] == "https://booking.alps2alps.com/booking/index"


def test_only_the_top_result_attempts_a_booking_link(authed_client, monkeypatch):
    # REGRESSION (caught in code review): a round-trip booking_url()
    # costs one extra, uncached live request (the "choose return" fetch
    # -- see that function's docstring), and specific_property_url()
    # costs a separate live Knowledge Graph API request. Attempting
    # either for EVERY live-priced result in a response (up to top_n)
    # would silently multiply live requests per API call well beyond
    # live_pricing_allowed()'s one-shot budget spend. Only the single
    # top result should ever attempt one.
    from ski_optimizer.adapters import google_flights_adapter, google_hotels_adapter
    from ski_optimizer.models import (
        FlightOption, FlightSearchResult, AccommodationOption, AccommodationSearchResult,
    )

    def fake_search_flights(**_kwargs):
        return FlightSearchResult(options=[
            FlightOption(price_eur=250.0, origin_airport="TLV", destination_airport="GVA",
                        airline="Test Air", total_duration_minutes=200, stops=0,
                        booking_token="fake-token"),
        ])

    def fake_search_accommodation(*_args, **_kwargs):
        return AccommodationSearchResult(options=[
            AccommodationOption(price_eur_per_night=100.0, property_name="Test Hotel"),
        ])

    flight_booking_calls = []
    accommodation_booking_calls = []

    monkeypatch.setattr(google_flights_adapter, "search_flights", fake_search_flights)
    monkeypatch.setattr(google_flights_adapter, "booking_url",
                        lambda *a, **k: flight_booking_calls.append(1) or "https://fake/flight")
    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", fake_search_accommodation)
    monkeypatch.setattr(google_hotels_adapter, "specific_property_url",
                        lambda *a, **k: accommodation_booking_calls.append(1) or "https://fake/hotel")

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 5000, "ski_days": 5, "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert len(body["results"]) > 1  # a broad search actually returns multiple resorts

    assert len(flight_booking_calls) <= 1
    assert len(accommodation_booking_calls) <= 1
    assert body["results"][0]["flight_search_url"] == "https://fake/flight"
    assert body["results"][0]["accommodation_search_url"] == "https://fake/hotel"
    for result in body["results"][1:]:
        assert result["flight_search_url"] != "https://fake/flight"
        assert result["accommodation_search_url"] != "https://fake/hotel"


def test_weather_carries_a_daily_breakdown_and_an_average(authed_client, monkeypatch):
    from ski_optimizer.api.routes import search as search_route
    from ski_optimizer.models import DailyWeather, TripWeatherSummary
    from datetime import date

    days = [
        DailyWeather(date=date(2027, 1, 10), temp_max_c=-1.0, temp_min_c=-8.0, snowfall_cm=2.0,
                    snow_depth_cm=45.0, is_live_forecast=False, years_sampled=5),
        DailyWeather(date=date(2027, 1, 11), temp_max_c=-3.0, temp_min_c=-10.0, snowfall_cm=4.0,
                    snow_depth_cm=50.0, is_live_forecast=False, years_sampled=5),
    ]
    monkeypatch.setattr(search_route, "get_trip_weather",
                        lambda *a, **k: TripWeatherSummary(days=days, avg_temp_max_c=-2.0,
                                                           avg_temp_min_c=-9.0, avg_snowfall_cm=3.0,
                                                           avg_snow_depth_cm=47.5))
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    weather = body["results"][0]["weather"]
    assert weather is not None
    assert weather["avg_temp_max_c"] == -2.0
    assert weather["avg_temp_min_c"] == -9.0
    assert weather["avg_snowfall_cm"] == 3.0
    assert weather["avg_snow_depth_cm"] == 47.5
    assert len(weather["days"]) == 2
    assert weather["days"][0]["date"] == "2027-01-10"
    assert weather["days"][0]["is_live_forecast"] is False
    assert weather["days"][0]["years_sampled"] == 5
    assert weather["days"][0]["snow_depth_cm"] == 45.0


def test_weather_is_none_when_the_provider_has_nothing(authed_client, monkeypatch):
    from ski_optimizer.api.routes import search as search_route

    monkeypatch.setattr(search_route, "get_trip_weather", lambda *a, **k: None)
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert body["results"][0]["weather"] is None


def test_only_the_top_result_attempts_weather(authed_client, monkeypatch):
    # Mirrors test_only_the_top_result_attempts_a_booking_link -- a
    # historical breakdown costs several real, sequential live requests
    # (one per sampled year), so this must never be attempted for every
    # result in a broad search.
    from ski_optimizer.api.routes import search as search_route
    from ski_optimizer.models import DailyWeather, TripWeatherSummary
    from datetime import date

    calls = []
    day = DailyWeather(date=date(2027, 1, 10), temp_max_c=1.0, temp_min_c=-6.0, snowfall_cm=2.0,
                       snow_depth_cm=30.0, is_live_forecast=False, years_sampled=5)
    monkeypatch.setattr(search_route, "get_trip_weather",
                        lambda *a, **k: calls.append(1) or TripWeatherSummary(
                            days=[day], avg_temp_max_c=1.0, avg_temp_min_c=-6.0, avg_snowfall_cm=2.0,
                            avg_snow_depth_cm=30.0))
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 5000, "ski_days": 5, "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert len(body["results"]) > 1
    assert len(calls) <= 1
    assert body["results"][0]["weather"] is not None
    for result in body["results"][1:]:
        assert result["weather"] is None


def test_search_with_tiny_budget_falls_back_to_cheapest_flagged_over_budget(authed_client):
    # Nothing fits 10 EUR/person -- the API no longer returns an empty
    # list for this (see rank_trips' over-budget-fallback docstring), it
    # returns the cheapest option(s) it found, honestly flagged.
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 10, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    assert all(r["within_budget"] is False for r in results)


def test_search_can_opt_out_of_the_over_budget_fallback(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 10, "ski_days": 5, "allow_over_budget_fallback": False,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_rejects_invalid_skill_level(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5, "skill_level": "godlike",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_rejects_unknown_weight_key(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "weights": {"apres_ski_quality": 1.0},
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_normalizes_weights_not_summing_to_one(authed_client):
    # 200, not 400/422 -- normalization should absorb this, not reject it.
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "weights": {"ski_quality": 5, "price": 5},  # sums to 10, not 1.0
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_search_with_unknown_target_resort_returns_404(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Definitely Not A Real Resort",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_search_with_valid_target_resort_returns_only_that_one(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 2000, "ski_days": 5,
        "target_resort": "Livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["resort"]["name"] == "Livigno"


def test_list_resort_names_requires_authentication_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_ANONYMOUS_SEARCH", raising=False)
    client = TestClient(app, base_url="https://testserver")
    resp = client.get("/trips/resorts")
    assert resp.status_code == 401


def test_list_resort_names_returns_all_resorts(authed_client):
    resp = authed_client.get("/trips/resorts")
    assert resp.status_code == 200
    names = resp.json()
    assert len(names) == 37
    assert names == sorted(names)


def test_target_resort_matching_is_case_insensitive_in_api(authed_client):
    # REGRESSION: the API used an exact, case-SENSITIVE membership test
    # while the engine matched case-insensitively -- so 'livigno' got a
    # 404 here even though the engine would have resolved it fine. Two
    # layers disagreeing about valid resort names is a real bug.
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 2000, "ski_days": 5,
        "target_resort": "livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"][0]["resort"]["name"] == "Livigno"


def test_target_resort_tolerates_whitespace_in_api(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 2000, "ski_days": 5,
        "target_resort": " Livigno ",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1


def test_search_rejects_negative_ski_days(authed_client):
    # The domain model rejects this now; the API should surface it as a
    # clean 4xx, never a 500 or a negative-priced "result".
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": -3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code in (400, 422)


def test_search_rejects_zero_group_size(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5, "group_size": 0,
    }, headers=CSRF_HEADERS)
    assert resp.status_code in (400, 422)


def test_include_resorts_restricts_to_exactly_those(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "top_n": 10,
        "include_resorts": ["Livigno", "Bansko"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    names = {r["resort"]["name"] for r in resp.json()["results"]}
    assert names <= {"Livigno", "Bansko"}


def test_exclude_resorts_removes_just_that_one(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "top_n": 30,
        "exclude_resorts": ["Val Thorens"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    names = {r["resort"]["name"] for r in resp.json()["results"]}
    assert "Val Thorens" not in names


def test_unknown_include_resort_404s(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "include_resorts": ["Not A Real Resort"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_min_budget_filters_out_cheaper_results(authed_client):
    baseline = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "top_n": 30,
    }, headers=CSRF_HEADERS).json()["results"]
    assert baseline  # sanity: something exists below the floor we're about to set
    cheapest = min(r["cost"]["total_eur"] for r in baseline)
    floor = cheapest + 1

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "top_n": 30,
        "min_budget_eur_per_person": floor,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["cost"]["total_eur"] >= floor


def test_max_connections_accepts_valid_values_and_rejects_others(authed_client):
    for value in (0, 1, 2):
        resp = authed_client.post("/trips/search", json={
            "budget_eur_per_person": 1500, "ski_days": 5, "max_connections": value,
        }, headers=CSRF_HEADERS)
        assert resp.status_code == 200, value

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5, "max_connections": 3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_top_n_limits_result_count(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "top_n": 3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 3


def test_preferred_transfer_modes_accepts_real_modes(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "preferred_transfer_modes": ["shared_shuttle", "train"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_preferred_transfer_modes_rejects_unknown_mode(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "preferred_transfer_modes": ["helicopter"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_rate_limit_returns_429_once_exceeded(authed_client):
    from ski_optimizer.api.rate_limit import _PER_IP_LIMIT

    payload = {"budget_eur_per_person": 1500, "ski_days": 5}
    for _ in range(_PER_IP_LIMIT):
        resp = authed_client.post("/trips/search", json=payload, headers=CSRF_HEADERS)
        assert resp.status_code == 200
    resp = authed_client.post("/trips/search", json=payload, headers=CSRF_HEADERS)
    assert resp.status_code == 429


def test_no_returned_trip_has_a_nonpositive_cost(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        assert result["cost"]["total_eur"] > 0


# --- Snow re-ranking (blueprint Milestone 5) ---

def _fake_summary(depth_cm, live):
    from ski_optimizer.models import DailyWeather, TripWeatherSummary
    import datetime as _dt
    days = [DailyWeather(date=_dt.date.today(), temp_max_c=-2.0, temp_min_c=-8.0,
                         snowfall_cm=1.0, snow_depth_cm=depth_cm,
                         is_live_forecast=live, years_sampled=None if live else 5)]
    return TripWeatherSummary(days=days, avg_temp_max_c=-2.0, avg_temp_min_c=-8.0,
                              avg_snowfall_cm=1.0, avg_snow_depth_cm=depth_cm)


def test_far_future_search_spends_no_requests_on_snow_reranking(authed_client, monkeypatch):
    # Beyond the forecast horizon every day is a historical average, so
    # re-ranking provably cannot change the order -- it must not spend
    # the several sequential live requests per resort that it would cost.
    from ski_optimizer.api.routes import search as search_route

    calls = []
    monkeypatch.setattr(search_route, "get_trip_weather",
                        lambda *a, **k: calls.append(1) or _fake_summary(30.0, live=False))
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 5000, "ski_days": 5, "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    # At most the single top-result weather card -- never the re-ranking
    # lookups on top of it.
    assert len(calls) <= 1


def test_near_term_search_does_run_snow_reranking(authed_client, monkeypatch):
    # The other half of the gate: inside the horizon it MUST actually
    # run, otherwise the feature is silently dead and the test above
    # would pass for the wrong reason.
    import datetime as _dt
    from ski_optimizer.api.routes import search as search_route

    calls = []

    def weather_fn(resort, *a, **k):
        calls.append(resort.name)
        return _fake_summary(240.0, live=True)

    monkeypatch.setattr(search_route, "get_trip_weather", weather_fn)
    soon = (_dt.date.today() + _dt.timedelta(days=5)).isoformat()
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 5000, "ski_days": 3, "outbound_date": soon,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(calls) > 1, "re-ranking should have looked up several resorts inside the horizon"
    assert len(calls) <= search_route._SNOW_RERANK_LOOKUPS + 1, "lookups must stay bounded"
