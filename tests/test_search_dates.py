"""
Tests for POST /trips/search-dates -- the "give me a window, find me the
best week(s) in it" endpoint. Same fixtures/conventions as test_search.py
on purpose: this wraps engine/date_search.search_date_range exactly as
test_search.py's target wraps engine/scoring.rank_trips, so the test
harness should look identical.
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
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    # See test_search.py's matching comment: rate_limit's limiters are
    # module-level singletons shared across every test in the process.
    rate_limit.clear_all()
    yield
    Base.metadata.drop_all(bind=engine)
    del app.dependency_overrides[get_db]


@pytest.fixture
def authed_client():
    # Bearer-token auth (see api/routes/auth.py) -- set as a persistent
    # per-client header rather than relying on TestClient's automatic
    # cookie jar, since there's no cookie in this flow at all.
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/auth/register", json={
        "email": "dateseeker@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    access_token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {access_token}"
    return client


BASE_PAYLOAD = {
    "budget_eur_per_person": 2000,
    "ski_days": 6,  # -> 7 nights away (see UserPreferences.nights)
    "earliest_date": "2027-01-10",
    "latest_date": "2027-01-20",  # 10-day window, 7-night trip -> 4 candidate starts
}


def test_search_dates_requires_authentication_by_default(monkeypatch):
    # See routes/auth.get_current_user_for_search's docstring.
    monkeypatch.delenv("ALLOW_ANONYMOUS_SEARCH", raising=False)
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_search_dates_allows_anonymous_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_ANONYMOUS_SEARCH", "true")
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_search_dates_without_csrf_header_is_rejected(authed_client):
    resp = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD)  # no CSRF header
    assert resp.status_code == 403


def test_10_day_window_7_night_trip_yields_four_candidate_dates(authed_client):
    # The exact scenario from the product ask: a 10-day range for a
    # 6-ski-day trip (7 nights away, see BASE_PAYLOAD) should search day
    # 1/2/3/4 as valid start dates (day 4 + 7 nights = day 11, still
    # inside the 10-day window which runs Jan 10 through Jan 20
    # inclusive of checkout).
    resp = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_dates_per_resort"] == 4


def test_search_dates_returns_results_within_budget(authed_client):
    resp = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) > 0
    for result in body["results"]:
        assert result["cost"]["total_eur"] <= BASE_PAYLOAD["budget_eur_per_person"]
        assert result["start_date"] < result["end_date"]
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_search_dates_results_carry_dated_flight_and_accommodation_links(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "target_resort": "Livigno",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    assert body["results"]
    for result in body["results"]:
        # Both links now delegate to their adapter's own structured,
        # dated search_url() (see engine/links.py's docstring) rather
        # than building a natural-language query with the dates spelled
        # out in it -- so "dated" is verified by URL shape, not by a
        # human-readable date substring.
        assert result["flight_search_url"].startswith(
            "https://www.google.com/travel/flights/search?tfs="
        )
        assert result["accommodation_search_url"].startswith(
            "https://www.google.com/travel/search?q="
        )
        assert "&ts=" in result["accommodation_search_url"]


def test_search_dates_degrades_to_static_per_result_when_the_provider_fails(authed_client, monkeypatch):
    # See test_search.py's matching test for why this mocks the adapter
    # instead of unsetting SERPAPI_API_KEY: live flight pricing
    # (adapters/google_flights_adapter.py) needs no key any more, so
    # live_pricing_active now means "live pricing was eligible and
    # attempted" (budget + a date), not "every result got a real live
    # price" -- it correctly stays True here even though the provider
    # fails on every attempt; results.flight_price_is_live is the
    # honest per-result signal, and (per the date_search.py fix this
    # test guards) a failed attempt must still return results, just
    # statically priced, not an empty list.
    from ski_optimizer.adapters import google_flights_adapter
    from ski_optimizer.adapters.base import AdapterError

    def _raise(*_args, **_kwargs):
        raise AdapterError("no network in tests")

    monkeypatch.setattr(google_flights_adapter, "search_flights", _raise)
    resp = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["live_pricing_active"] is True
    assert body["results"]
    for result in body["results"]:
        assert result["cost"]["flight_price_is_live"] is False


def test_search_dates_rejects_window_shorter_than_the_trip(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "ski_days": 29, "earliest_date": "2027-01-10", "latest_date": "2027-01-12",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_dates_rejects_latest_before_earliest(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "earliest_date": "2027-01-20", "latest_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 400


def test_search_dates_with_unknown_target_resort_returns_404(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "target_resort": "Definitely Not A Real Resort",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_search_dates_with_valid_target_resort_returns_only_that_one(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "target_resort": "Livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    # query_resort_count reports the full dataset size, matching
    # /trips/search's convention -- the narrowing itself is proven by
    # the results, not this count (see engine.scoring.narrow_resort_pool).
    assert body["query_resort_count"] == 37
    for result in body["results"]:
        assert result["resort"]["name"] == "Livigno"


def test_search_dates_target_resort_matching_is_case_insensitive(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "target_resort": "livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"]
    assert all(r["resort"]["name"] == "Livigno" for r in body["results"])


def test_search_dates_with_tiny_budget_falls_back_to_cheapest_flagged(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "budget_eur_per_person": 10,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    assert all(r["within_budget"] is False for r in results)


def test_search_dates_can_opt_out_of_the_over_budget_fallback(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "budget_eur_per_person": 10, "allow_over_budget_fallback": False,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_dates_rejects_invalid_skill_level(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "skill_level": "godlike",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_dates_rejects_unknown_weight_key(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "weights": {"apres_ski_quality": 1.0},
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_dates_include_resorts_restricts_to_exactly_those(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "include_resorts": ["Livigno", "Bansko"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"]
    names = {r["resort"]["name"] for r in body["results"]}
    assert names <= {"Livigno", "Bansko"}


def test_search_dates_exclude_resorts_removes_just_that_one(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "budget_eur_per_person": 3000, "exclude_resorts": ["Val Thorens"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    names = {r["resort"]["name"] for r in resp.json()["results"]}
    assert "Val Thorens" not in names


def test_search_dates_unknown_include_resort_404s(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "include_resorts": ["Definitely Not A Real Resort"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_search_dates_unknown_exclude_resort_404s(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "exclude_resorts": ["Definitely Not A Real Resort"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_search_dates_start_weekday_restricts_results_to_that_day(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        "budget_eur_per_person": 3000, "ski_days": 6,
        "earliest_date": "2027-01-04", "latest_date": "2027-02-01",
        "start_weekday": "saturday", "include_resorts": ["Livigno"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"]
    import datetime as _dt
    for r in body["results"]:
        d = _dt.date.fromisoformat(r["start_date"])
        assert d.weekday() == 5  # Saturday


def test_search_dates_invalid_start_weekday_rejected(authed_client):
    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "start_weekday": "funday",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_dates_min_budget_filters_out_cheaper_results(authed_client):
    baseline = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS).json()["results"]
    assert baseline
    cheapest = min(r["cost"]["total_eur"] for r in baseline)
    floor = cheapest + 1

    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "min_budget_eur_per_person": floor,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["cost"]["total_eur"] >= floor


def test_search_dates_max_connections_accepts_valid_values_and_rejects_others(authed_client):
    for value in (0, 1, 2):
        resp = authed_client.post("/trips/search-dates", json={
            **BASE_PAYLOAD, "max_connections": value,
        }, headers=CSRF_HEADERS)
        assert resp.status_code == 200, value

    resp = authed_client.post("/trips/search-dates", json={
        **BASE_PAYLOAD, "max_connections": 3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_dates_each_result_carries_season_and_explanation(authed_client):
    resp = authed_client.post("/trips/search-dates", json=BASE_PAYLOAD, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    for result in results:
        assert result["season"] in ("peak", "high", "shoulder")
        assert isinstance(result["explanation"], str) and result["explanation"]


def test_a_two_resort_pool_is_not_padded_with_the_cheapest_resort(authed_client):
    # THE USER'S OWN COMPLAINT, reproduced live 2026-08-28: the popular
    # shortlist at a EUR1500 budget left two affordable resorts and the
    # response was Bansko NINE times out of twelve. The engine's
    # pad_with_duplicates=False must actually be wired into THIS
    # endpoint -- the engine test alone stays green if the route stops
    # passing the flag.
    from collections import Counter

    resp = authed_client.post("/trips/search-dates", json={
        "budget_eur_per_person": 1500, "ski_days": 5, "group_size": 2,
        "earliest_date": "2027-01-05", "latest_date": "2027-02-05",
        "top_n": 12, "include_resorts": ["Bansko", "Pamporovo"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    counts = Counter(r["resort"]["name"] for r in resp.json()["results"])
    assert max(counts.values()) <= 3, f"duplicate padding is back: {dict(counts)}"
    assert len(counts) >= 2, f"expected both resorts represented: {dict(counts)}"
