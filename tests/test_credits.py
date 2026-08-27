"""
Tests for per-user daily search credits (api/credits.py).

The unit is one CANDIDATE START DATE evaluated, so a wide flexible
window genuinely costs more than a fixed date -- see credits.py's
docstring for why that unit and not "one credit per search".
"""
import datetime
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ski_optimizer.api.main import app
from ski_optimizer.api import security, rate_limit, credits as credits_module
from ski_optimizer.db.database import Base, get_db

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


CSRF = {security.CSRF_HEADER_NAME: security.CSRF_HEADER_VALUE}


@pytest.fixture(autouse=True)
def _fresh_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    rate_limit.clear_all()
    yield
    Base.metadata.drop_all(bind=engine)
    del app.dependency_overrides[get_db]


@pytest.fixture
def client():
    c = TestClient(app, base_url="https://testserver")
    resp = c.post("/auth/register", json={
        "email": "credituser@example.com", "password": "correcthorsebattery",
    }, headers=CSRF)
    c.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return c


def _window(days_wide):
    start = datetime.date.today() + datetime.timedelta(days=30)
    return start.isoformat(), (start + datetime.timedelta(days=days_wide)).isoformat()


# --- the cost function itself ---

def test_a_search_always_costs_at_least_one_credit():
    # Even a search that finds no valid candidate date still did the
    # work of looking.
    assert credits_module.cost_for_candidate_dates(0) == 1


def test_cost_tracks_candidate_dates():
    assert credits_module.cost_for_candidate_dates(1) == 1
    assert credits_module.cost_for_candidate_dates(7) == 7


def test_one_search_can_never_drain_the_whole_allowance():
    huge = credits_module.cost_for_candidate_dates(100_000)
    assert huge == credits_module.MAX_CREDITS_PER_SEARCH
    assert huge < credits_module.DEFAULT_DAILY_CREDITS


# --- charging through the API ---

def test_a_fixed_date_search_costs_exactly_one_credit(client):
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon,
    }, headers=CSRF)
    assert resp.status_code == 200
    c = resp.json()["credits"]
    assert c["cost"] == 1
    assert c["remaining"] == c["daily_allowance"] - 1


def test_a_wider_window_costs_more_than_a_narrow_one(client):
    # The whole point of the unit: a flexible search is many searches
    # wearing one button, and should be priced like it.
    narrow_start, narrow_end = _window(8)
    wide_start, wide_end = _window(30)

    r1 = client.post("/trips/search-dates", json={
        "budget_eur_per_person": 3000, "ski_days": 5,
        "earliest_date": narrow_start, "latest_date": narrow_end,
    }, headers=CSRF)
    r2 = client.post("/trips/search-dates", json={
        "budget_eur_per_person": 3000, "ski_days": 5,
        "earliest_date": wide_start, "latest_date": wide_end,
    }, headers=CSRF)
    assert r1.status_code == r2.status_code == 200
    assert r2.json()["credits"]["cost"] > r1.json()["credits"]["cost"]


def test_charged_cost_matches_the_candidate_count_reported_back(client):
    # A user must be able to see what they were charged for.
    start, end = _window(12)
    resp = client.post("/trips/search-dates", json={
        "budget_eur_per_person": 3000, "ski_days": 5,
        "earliest_date": start, "latest_date": end,
    }, headers=CSRF)
    body = resp.json()
    assert body["credits"]["cost"] == body["candidate_dates_per_resort"]


def test_running_out_of_credits_refuses_the_search_cleanly(client, monkeypatch):
    monkeypatch.setattr(credits_module, "DEFAULT_DAILY_CREDITS", 2)
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {"budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon}

    assert client.post("/trips/search", json=body, headers=CSRF).status_code == 200
    assert client.post("/trips/search", json=body, headers=CSRF).status_code == 200
    third = client.post("/trips/search", json=body, headers=CSRF)
    assert third.status_code == 402
    assert "credit" in third.json()["detail"].lower()


def test_a_refused_search_is_not_charged(client, monkeypatch):
    # Being refused must not cost anything, or a user out of credits
    # would sink further every time they retried.
    monkeypatch.setattr(credits_module, "DEFAULT_DAILY_CREDITS", 1)
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {"budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon}

    client.post("/trips/search", json=body, headers=CSRF)
    before = client.get("/trips/credits").json()["remaining"]
    client.post("/trips/search", json=body, headers=CSRF)
    client.post("/trips/search", json=body, headers=CSRF)
    assert client.get("/trips/credits").json()["remaining"] == before


def test_an_invalid_request_is_never_charged(client):
    # Validation failures happen before charging.
    before = client.get("/trips/credits").json()["remaining"]
    resp = client.post("/trips/search", json={
        "budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": "2020-01-01",
    }, headers=CSRF)
    assert resp.status_code == 400
    assert client.get("/trips/credits").json()["remaining"] == before


def test_checking_the_balance_never_spends_one(client):
    first = client.get("/trips/credits").json()
    second = client.get("/trips/credits").json()
    assert first["remaining"] == second["remaining"]
    assert first["cost"] == 0


def test_spend_accumulates_across_searches(client):
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {"budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon}
    start = client.get("/trips/credits").json()["remaining"]
    client.post("/trips/search", json=body, headers=CSRF)
    client.post("/trips/search", json=body, headers=CSRF)
    assert client.get("/trips/credits").json()["remaining"] == start - 2


def test_credits_are_tracked_per_user_not_globally(client):
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {"budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon}
    client.post("/trips/search", json=body, headers=CSRF)

    other = TestClient(app, base_url="https://testserver")
    resp = other.post("/auth/register", json={
        "email": "second@example.com", "password": "correcthorsebattery",
    }, headers=CSRF)
    other.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    st = other.get("/trips/credits").json()
    assert st["remaining"] == st["daily_allowance"], "one user's spend must not bill another"


def test_concurrent_first_searches_do_not_collide(client):
    # REGRESSION (found in a browser test, 2026-08-27): the landing page
    # fires a preview and a form search that can overlap. Both saw "no
    # ledger row for today", both INSERTed, and the unique constraint
    # turned the loser into a 500. The constraint was right; the code
    # around it wasn't.
    import threading

    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {"budget_eur_per_person": 3000, "ski_days": 5, "outbound_date": soon}
    statuses = []

    def fire():
        statuses.append(client.post("/trips/search", json=body, headers=CSRF).status_code)

    threads = [threading.Thread(target=fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(s == 200 for s in statuses), f"expected two clean 200s, got {statuses}"
    # And both were actually charged -- the fix must not silently drop one.
    st = client.get("/trips/credits").json()
    assert st["daily_allowance"] - st["remaining"] == 2


def test_a_stale_read_conflict_is_retried_not_raised():
    """
    Forces the ACTUAL conflict, deterministically.

    An earlier version of this test just pre-inserted a row and called
    try_spend -- but try_spend reads first, found the row, and took the
    UPDATE branch, so it never touched the retry path at all. Breaking
    the `except IntegrityError` on purpose left it green, which is the
    definition of a decorative test. This version makes the first read
    return None WHILE the row really exists, which is exactly the stale
    read a concurrent request produces, so the INSERT genuinely raises.
    """
    from ski_optimizer.db.models import SearchCreditLedger, User

    db = TestingSessionLocal()
    try:
        user = User(email="racer@example.com", password_hash="x")
        db.add(user)
        db.commit()

        # The "winner" has already inserted today's row.
        db.add(SearchCreditLedger(user_id=user.id, day=datetime.date.today(), credits_used=3))
        db.commit()

        real_query = db.query
        calls = {"n": 0}

        class _StaleFirstRead:
            def __init__(self, inner):
                self._inner = inner

            def filter(self, *a, **k):
                return _StaleFirstRead(self._inner.filter(*a, **k))

            def one_or_none(self):
                calls["n"] += 1
                # Only the FIRST read is stale; the retry sees reality.
                return None if calls["n"] == 1 else self._inner.one_or_none()

        def patched_query(model):
            if model is SearchCreditLedger:
                return _StaleFirstRead(real_query(model))
            return real_query(model)

        db.query = patched_query
        after = credits_module.try_spend(db, user.id, 2)
        db.query = real_query

        assert calls["n"] >= 2, "the retry path must actually have run"
        assert after is not None, "a conflict must be retried, not surfaced as an error"
        assert after.used_today == 5, "the retry must add to the winner's row, not overwrite it"
    finally:
        db.close()
