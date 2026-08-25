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
    assert body["query_resort_count"] == 30
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


def test_search_flight_link_includes_dates_when_outbound_date_is_given(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "ski_days": 5,
        "target_resort": "Livigno", "outbound_date": "2027-01-10",
    }, headers=CSRF_HEADERS)
    body = resp.json()
    result = body["results"][0]
    assert "on 2027-01-10 through 2027-01-16" in result["flight_search_url"].replace("%20", " ")


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


def test_list_resort_names_returns_thirty(authed_client):
    resp = authed_client.get("/trips/resorts")
    assert resp.status_code == 200
    names = resp.json()
    assert len(names) == 30
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
