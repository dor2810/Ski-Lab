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
from ski_optimizer.api import security
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
    yield
    Base.metadata.drop_all(bind=engine)
    del app.dependency_overrides[get_db]


@pytest.fixture
def authed_client():
    """A TestClient that's already registered + logged in (cookies persist across requests)."""
    client = TestClient(app, base_url="https://testserver")
    client.post("/auth/register", json={
        "email": "searcher@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    return client


def test_search_requires_authentication():
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_anonymous_search_allowed_when_dev_flag_set(monkeypatch):
    # Dev-only convenience (ALLOW_ANONYMOUS_SEARCH=true): no cookie, no
    # register/login round-trip, search still works. Default (unset)
    # behavior above must stay exactly as it was -- this is additive.
    monkeypatch.setenv("ALLOW_ANONYMOUS_SEARCH", "true")
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) > 0


def test_anonymous_search_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_ANONYMOUS_SEARCH", raising=False)
    client = TestClient(app, base_url="https://testserver")
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_a_real_session_still_works_when_anonymous_flag_is_set(authed_client, monkeypatch):
    # The flag doesn't break real auth -- a logged-in client still works
    # exactly as before, it's purely an OR, not a replacement.
    monkeypatch.setenv("ALLOW_ANONYMOUS_SEARCH", "true")
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_search_without_csrf_header_is_rejected(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    })  # no CSRF header
    assert resp.status_code == 403


def test_search_returns_ranked_results_within_budget(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5, "group_size": 2,
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


def test_search_with_outbound_date_falls_back_to_static_without_a_serpapi_key(authed_client, monkeypatch):
    # CI/test environment has no SERPAPI_API_KEY (see test_auth.py/test_search.py's
    # setdefault calls -- neither sets it, and .env is never auto-loaded).
    # Passing outbound_date must degrade to the static estimate, not error.
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
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
        "budget_eur_per_person": 10, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    assert all(r["within_budget"] is False for r in results)


def test_search_can_opt_out_of_the_over_budget_fallback(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 10, "trip_nights": 5, "allow_over_budget_fallback": False,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_rejects_invalid_skill_level(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5, "skill_level": "godlike",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_rejects_unknown_weight_key(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "weights": {"apres_ski_quality": 1.0},
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_search_normalizes_weights_not_summing_to_one(authed_client):
    # 200, not 400/422 -- normalization should absorb this, not reject it.
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "weights": {"ski_quality": 5, "price": 5},  # sums to 10, not 1.0
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_search_with_unknown_target_resort_returns_404(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "target_resort": "Definitely Not A Real Resort",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_search_with_valid_target_resort_returns_only_that_one(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 2000, "trip_nights": 5,
        "target_resort": "Livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["resort"]["name"] == "Livigno"


def test_list_resort_names_requires_auth():
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
        "budget_eur_per_person": 2000, "trip_nights": 5,
        "target_resort": "livigno",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["results"][0]["resort"]["name"] == "Livigno"


def test_target_resort_tolerates_whitespace_in_api(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 2000, "trip_nights": 5,
        "target_resort": " Livigno ",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1


def test_search_rejects_negative_trip_nights(authed_client):
    # The domain model rejects this now; the API should surface it as a
    # clean 4xx, never a 500 or a negative-priced "result".
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": -3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code in (400, 422)


def test_search_rejects_zero_group_size(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5, "group_size": 0,
    }, headers=CSRF_HEADERS)
    assert resp.status_code in (400, 422)


def test_include_resorts_restricts_to_exactly_those(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5, "top_n": 10,
        "include_resorts": ["Livigno", "Bansko"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    names = {r["resort"]["name"] for r in resp.json()["results"]}
    assert names <= {"Livigno", "Bansko"}


def test_exclude_resorts_removes_just_that_one(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5, "top_n": 30,
        "exclude_resorts": ["Val Thorens"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    names = {r["resort"]["name"] for r in resp.json()["results"]}
    assert "Val Thorens" not in names


def test_unknown_include_resort_404s(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "include_resorts": ["Not A Real Resort"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 404


def test_min_budget_filters_out_cheaper_results(authed_client):
    baseline = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5, "top_n": 30,
    }, headers=CSRF_HEADERS).json()["results"]
    assert baseline  # sanity: something exists below the floor we're about to set
    cheapest = min(r["cost"]["total_eur"] for r in baseline)
    floor = cheapest + 1

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5, "top_n": 30,
        "min_budget_eur_per_person": floor,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["cost"]["total_eur"] >= floor


def test_max_connections_accepts_valid_values_and_rejects_others(authed_client):
    for value in (0, 1, 2):
        resp = authed_client.post("/trips/search", json={
            "budget_eur_per_person": 1500, "trip_nights": 5, "max_connections": value,
        }, headers=CSRF_HEADERS)
        assert resp.status_code == 200, value

    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5, "max_connections": 3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_top_n_limits_result_count(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5, "top_n": 3,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 3


def test_preferred_transfer_modes_accepts_real_modes(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "preferred_transfer_modes": ["shared_shuttle", "train"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_preferred_transfer_modes_rejects_unknown_mode(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
        "preferred_transfer_modes": ["helicopter"],
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_no_returned_trip_has_a_nonpositive_cost(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        assert result["cost"]["total_eur"] > 0
