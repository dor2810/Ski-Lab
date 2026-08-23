"""
Auth API tests. Uses FastAPI's TestClient + an in-memory SQLite DB
override, which is the standard pattern for testing FastAPI apps
without hitting a real database.

HONESTY NOTE: this file could not be run in the sandbox it was written
in -- there's no network access to `pip install fastapi sqlalchemy ...`
here (see the main repo README). It's been syntax-checked (valid
Python, per `python -m ast`) but never actually executed. Run it for
real -- and expect to fix at least small things -- the first time this
project has network access:

    pip install -r requirements.txt
    pytest tests/test_auth.py -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ski_optimizer.api.main import app
from ski_optimizer.api import security
from ski_optimizer.db.database import Base, get_db

# In-memory SQLite, one connection shared across the test session
# (StaticPool) so :memory: doesn't get wiped between requests --
# each real HTTP request in TestClient can otherwise get a fresh
# in-memory DB and see none of the previous request's data.
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


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


CSRF_HEADERS = {security.CSRF_HEADER_NAME: security.CSRF_HEADER_VALUE}


@pytest.fixture
def client():
    return TestClient(app)


def test_register_creates_user_and_sets_cookies(client):
    resp = client.post("/auth/register", json={
        "email": "skier@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 201
    assert resp.json()["email"] == "skier@example.com"
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={
        "email": "skier2@example.com", "password": "short",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 422


def test_register_without_csrf_header_is_rejected(client):
    resp = client.post("/auth/register", json={
        "email": "skier3@example.com", "password": "correcthorsebattery",
    })  # no CSRF header
    assert resp.status_code == 403


def test_duplicate_email_registration_fails(client):
    payload = {"email": "dup@example.com", "password": "correcthorsebattery"}
    r1 = client.post("/auth/register", json=payload, headers=CSRF_HEADERS)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=payload, headers=CSRF_HEADERS)
    assert r2.status_code == 400


def test_login_with_correct_password_succeeds(client):
    client.post("/auth/register", json={
        "email": "login@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    resp = client.post("/auth/login", json={
        "email": "login@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_login_with_wrong_password_fails(client):
    client.post("/auth/register", json={
        "email": "login2@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    resp = client.post("/auth/login", json={
        "email": "login2@example.com", "password": "totallywrongpassword",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_login_with_nonexistent_email_fails_same_as_wrong_password(client):
    resp = client.post("/auth/login", json={
        "email": "nobody@example.com", "password": "whatever12345",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(client):
    client.post("/auth/register", json={
        "email": "me@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_refresh_rotates_token_and_old_one_becomes_invalid(client):
    client.post("/auth/register", json={
        "email": "rotate@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    old_refresh_cookie = client.cookies.get("refresh_token")

    r1 = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert r1.status_code == 200
    new_refresh_cookie = client.cookies.get("refresh_token")
    assert new_refresh_cookie != old_refresh_cookie

    # Replay the OLD token -- should be rejected AND should revoke the
    # new one too (reuse-detection: see routes/auth.py's comment).
    client.cookies.set("refresh_token", old_refresh_cookie)
    r2 = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert r2.status_code == 401

    client.cookies.set("refresh_token", new_refresh_cookie)
    r3 = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert r3.status_code == 401  # revoked by the reuse-detection above


def test_logout_revokes_refresh_token(client):
    client.post("/auth/register", json={
        "email": "logout@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    resp = client.post("/auth/logout", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    refresh_after_logout = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert refresh_after_logout.status_code == 401


def test_google_login_without_configured_credentials_returns_503(client):
    resp = client.get("/auth/google/login", follow_redirects=False)
    assert resp.status_code == 503


# --- email normalization (regression) ---

def test_email_is_normalized_to_lowercase_on_register(client):
    # REGRESSION: emails were compared with an exact, case-sensitive ==
    # against a case-sensitive DB unique constraint, so 'Dor@x.com' and
    # 'dor@x.com' created two separate accounts.
    resp = client.post("/auth/register", json={
        "email": "MixedCase@Example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 201
    assert resp.json()["email"] == "mixedcase@example.com"


def test_registering_same_email_different_case_is_rejected(client):
    client.post("/auth/register", json={
        "email": "dupe@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    resp = client.post("/auth/register", json={
        "email": "DUPE@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 400, "different-case duplicate should not create a second account"


def test_login_works_with_different_email_casing_than_registration(client):
    # The user-visible half of the same bug: registering as lowercase and
    # logging in with a capital letter previously failed with "incorrect
    # email or password", which is a maddening thing to debug as a user.
    client.post("/auth/register", json={
        "email": "casing@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    client.post("/auth/logout", headers=CSRF_HEADERS)
    resp = client.post("/auth/login", json={
        "email": "Casing@Example.COM", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_email_surrounding_whitespace_is_stripped(client):
    resp = client.post("/auth/register", json={
        "email": "  spaced@example.com  ", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 201
    assert resp.json()["email"] == "spaced@example.com"
