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
    # In-season, always: the API floors any off-season start to Dec 1
    # of the coming season (the owner's "season starts December 1st"
    # rule), so a today+30 window in August would be silently reshaped
    # and the wide/narrow comparison would collapse.
    start = max(datetime.date.today() + datetime.timedelta(days=30),
                datetime.date(datetime.date.today().year, 12, 10)
                if datetime.date.today().month >= 5
                else datetime.date.today() + datetime.timedelta(days=30))
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


def test_concurrent_spends_never_lose_a_charge(tmp_path):
    """
    Real concurrency, against a realistic database configuration.

    TWO earlier versions of this test were flaky, and both were flaky
    for the same reason -- they shared ONE SQLite connection across
    threads (StaticPool + :memory:, which the rest of this file uses
    deliberately so the API tests see a single database). Driving
    concurrent transactions down one sqlite3 connection is API misuse,
    and it surfaced as `InterfaceError: bad parameter or other API
    misuse` and `DatabaseError: another row available` -- driver errors,
    not defects in try_spend. A test that reports the harness's
    limitations as product bugs is worse than no test.

    So this one builds its own FILE-backed engine with SQLAlchemy's
    normal pooling, where each thread gets its own connection. That is
    how the code actually runs in production (and how Postgres behaves
    when this moves off SQLite), so a failure here would be real.

    What it guards: every successful spend lands in the ledger, and no
    spend is wrongly REFUSED while the user still has credits -- being
    denied a credit you have is a bug, not a limit.
    """
    import threading

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from ski_optimizer.db.models import User

    db_path = tmp_path / "credits_concurrency.db"
    concurrent_engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    ConcurrentSession = sessionmaker(bind=concurrent_engine)
    Base.metadata.create_all(bind=concurrent_engine)

    setup = ConcurrentSession()
    user = User(email="concurrent@example.com", password_hash="x")
    setup.add(user)
    setup.commit()
    user_id = user.id
    setup.close()

    outcomes: list = []

    def spend():
        db = ConcurrentSession()
        try:
            outcomes.append(credits_module.try_spend(db, user_id, 1))
        except Exception as exc:  # recorded, not swallowed -- see assert below
            outcomes.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=spend) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    errors = [o for o in outcomes if isinstance(o, Exception)]
    assert not errors, f"concurrent spends raised: {errors!r}"
    assert all(o is not None for o in outcomes), (
        "no spend should have been refused -- the daily allowance is far higher than 8"
    )

    db = ConcurrentSession()
    try:
        assert credits_module.get_status(db, user_id).used_today == len(threads), (
            "every successful spend must be recorded; a lost write is a free search"
        )
    finally:
        db.close()
        concurrent_engine.dispose()


def test_a_row_appearing_mid_spend_is_retried_not_refused():
    """
    Forces the exact interleaving that a concurrent first-spend produces,
    deterministically.

    The window: our atomic UPDATE runs while today's ledger row does not
    yet exist, so it matches nothing; a competing request INSERTs the row
    a moment later; we then look and DO find a row. An earlier version
    treated "UPDATE matched nothing AND a row exists" as "out of
    credits" and refused a user who had 500 -- which a concurrency test
    caught as spends being refused rather than lost.

    Simulated by making the FIRST atomic update a no-op while the row
    really is present, which is indistinguishable from losing that race.
    """
    from ski_optimizer.db.models import SearchCreditLedger, User

    db = TestingSessionLocal()
    try:
        user = User(email="racer@example.com", password_hash="x")
        db.add(user)
        db.commit()

        db.add(SearchCreditLedger(user_id=user.id, day=datetime.date.today(), credits_used=3))
        db.commit()

        real_query = db.query
        calls = {"update": 0}

        class _FirstUpdateMisses:
            def __init__(self, inner):
                self._inner = inner

            def filter(self, *a, **k):
                return _FirstUpdateMisses(self._inner.filter(*a, **k))

            def one_or_none(self):
                return self._inner.one_or_none()

            def update(self, *a, **k):
                calls["update"] += 1
                if calls["update"] == 1:
                    return 0  # lost the race: nothing to update yet
                return self._inner.update(*a, **k)

        db.query = lambda model: (
            _FirstUpdateMisses(real_query(model))
            if model is SearchCreditLedger else real_query(model)
        )
        after = credits_module.try_spend(db, user.id, 2)
        db.query = real_query

        assert calls["update"] >= 2, "the retry path must actually have run"
        assert after is not None, "losing the insert race must not look like being out of credits"
        assert after.used_today == 5, "the retry must add to the existing row, not overwrite it"
    finally:
        db.close()


def test_a_genuinely_exhausted_allowance_is_still_refused(monkeypatch):
    # The other side of that distinction: when the row really is maxed
    # out, refuse -- don't spin through the retries and then charge.
    from ski_optimizer.db.models import SearchCreditLedger, User

    monkeypatch.setattr(credits_module, "DEFAULT_DAILY_CREDITS", 5)
    db = TestingSessionLocal()
    try:
        user = User(email="broke@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.add(SearchCreditLedger(user_id=user.id, day=datetime.date.today(), credits_used=5))
        db.commit()

        assert credits_module.try_spend(db, user.id, 1) is None
        assert credits_module.get_status(db, user.id).used_today == 5, "a refusal must charge nothing"
    finally:
        db.close()
