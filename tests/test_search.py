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


app.dependency_overrides[get_db] = override_get_db

CSRF_HEADERS = {security.CSRF_HEADER_NAME: security.CSRF_HEADER_VALUE}


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def authed_client():
    """A TestClient that's already registered + logged in (cookies persist across requests)."""
    client = TestClient(app)
    client.post("/auth/register", json={
        "email": "searcher@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    return client


def test_search_requires_authentication():
    client = TestClient(app)
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 1500, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


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


def test_search_with_tiny_budget_returns_empty_results(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 10, "trip_nights": 5,
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
    client = TestClient(app)
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


def test_no_returned_trip_has_a_nonpositive_cost(authed_client):
    resp = authed_client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "trip_nights": 5,
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        assert result["cost"]["total_eur"] > 0
