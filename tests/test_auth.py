"""
Auth API tests. Uses FastAPI's TestClient + an in-memory SQLite DB
override, which is the standard pattern for testing FastAPI apps
without hitting a real database.

Bearer-token model (see api/routes/auth.py's module docstring): every
authenticated request needs `Authorization: Bearer <access_token>` set
explicitly, and refresh/logout take refresh_token in the JSON body --
there's no ambient cookie carrying it for TestClient to persist
automatically, unlike the old cookie-based version of this file.
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


@pytest.fixture(autouse=True)
def _fresh_db():
    # Scoped to setup/teardown, not module import: test_search.py defines its
    # own get_db override on the same shared `app` singleton, and pytest
    # imports every test module before running any test. Assigning this at
    # import time meant whichever file was imported last silently won the
    # override for the ENTIRE session, including this file's tests -- which
    # is how every test here ended up querying test_search.py's (tableless,
    # from this file's perspective) engine instead of its own.
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    del app.dependency_overrides[get_db]


CSRF_HEADERS = {security.CSRF_HEADER_NAME: security.CSRF_HEADER_VALUE}


@pytest.fixture
def client():
    return TestClient(app, base_url="https://testserver")


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email="skier@example.com", password="correcthorsebattery"):
    return client.post("/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADERS)


def test_register_returns_user_and_bearer_tokens(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "skier@example.com"
    assert body["access_token"]
    assert body["refresh_token"]


def test_register_rejects_short_password(client):
    resp = _register(client, email="skier2@example.com", password="short")
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
    _register(client, email="login@example.com")
    resp = client.post("/auth/login", json={
        "email": "login@example.com", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_fails(client):
    _register(client, email="login2@example.com")
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


def test_me_rejects_a_garbage_bearer_token(client):
    resp = client.get("/auth/me", headers=_bearer("not-a-real-token"))
    assert resp.status_code == 401


def test_me_returns_current_user_given_a_valid_access_token(client):
    access_token = _register(client, email="me@example.com").json()["access_token"]
    resp = client.get("/auth/me", headers=_bearer(access_token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_refresh_rotates_token_and_old_one_becomes_invalid(client):
    old_refresh = _register(client, email="rotate@example.com").json()["refresh_token"]

    r1 = client.post("/auth/refresh", json={"refresh_token": old_refresh}, headers=CSRF_HEADERS)
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Replay the OLD token -- should be rejected AND should revoke the
    # new one too (reuse-detection: see routes/auth.py's comment).
    r2 = client.post("/auth/refresh", json={"refresh_token": old_refresh}, headers=CSRF_HEADERS)
    assert r2.status_code == 401

    r3 = client.post("/auth/refresh", json={"refresh_token": new_refresh}, headers=CSRF_HEADERS)
    assert r3.status_code == 401  # revoked by the reuse-detection above


def test_refresh_with_unknown_token_is_rejected(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "made-up-token"}, headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client):
    refresh_token = _register(client, email="logout@example.com").json()["refresh_token"]
    resp = client.post("/auth/logout", json={"refresh_token": refresh_token}, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    refresh_after_logout = client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}, headers=CSRF_HEADERS
    )
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
    assert resp.json()["user"]["email"] == "mixedcase@example.com"


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
    resp = client.post("/auth/login", json={
        "email": "Casing@Example.COM", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 200


def test_email_surrounding_whitespace_is_stripped(client):
    resp = client.post("/auth/register", json={
        "email": "  spaced@example.com  ", "password": "correcthorsebattery",
    }, headers=CSRF_HEADERS)
    assert resp.status_code == 201
    assert resp.json()["user"]["email"] == "spaced@example.com"
