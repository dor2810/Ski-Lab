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
    # Auth endpoints are rate limited (security review 2026-08-28) and
    # every test in this file shares one client identity -- clear
    # between tests exactly as test_search.py does.
    from ski_optimizer.api import rate_limit as _rl
    _rl.clear_all()
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


def test_google_callback_redirects_cleanly_when_the_user_cancels_consent(client, monkeypatch):
    # REGRESSION: per Google's own OAuth docs, an app "must gracefully
    # handle situations where some permissions are denied" -- the most
    # common real case is the user clicking "Cancel" on Google's consent
    # screen, which Authlib surfaces as an OAuthError from
    # authorize_access_token. Before this was caught, that crashed with
    # an unhandled 500 instead of sending the user back to the app.
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    from authlib.integrations.base_client.errors import OAuthError
    from ski_optimizer.api.routes import google_oauth

    async def _raise(*_args, **_kwargs):
        raise OAuthError(error="access_denied")

    monkeypatch.setattr(google_oauth.oauth.google, "authorize_access_token", _raise)

    resp = client.get("/auth/google/callback", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "auth_error=google_oauth_failed" in resp.headers["location"]


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


# --- security review 2026-08-28: auth hardening ---

def test_auth_endpoints_are_rate_limited(client):
    # HIGH finding: /auth/* had NO rate limiting -- credential stuffing
    # and mass account creation ran at full speed while /trips/search
    # was carefully throttled. Argon2's cost is incidental, not a
    # control. 10/min per IP; the 11th call in a minute is refused.
    for _ in range(10):
        r = client.post("/auth/login", json={
            "email": "nobody@example.com", "password": "wrong-password",
        }, headers=CSRF_HEADERS)
        assert r.status_code == 401
    r = client.post("/auth/login", json={
        "email": "nobody@example.com", "password": "wrong-password",
    }, headers=CSRF_HEADERS)
    assert r.status_code == 429


def test_google_login_refuses_to_link_an_unverified_password_account():
    # CRITICAL finding (dormant until OAuth credentials exist):
    # register victim@x.com with the ATTACKER's password (registration
    # never verifies email ownership), wait for the real victim to
    # "Sign in with Google" -- the old code silently linked the
    # victim's Google identity onto the attacker-controlled row,
    # whose password the attacker still knows. Linking by bare email
    # match must be refused when that account never proved it owns
    # the address.
    import pytest as _pytest
    from ski_optimizer.api.routes.google_oauth import (
        UnverifiedAccountCollision, _resolve_google_user)
    from ski_optimizer.db.models import User

    db = TestingSessionLocal()
    try:
        attacker_row = User(email="victim@example.com",
                            password_hash="$argon2-fake", is_email_verified=False)
        db.add(attacker_row); db.commit()

        with _pytest.raises(UnverifiedAccountCollision):
            _resolve_google_user(db, google_sub="g-123",
                                 email="victim@example.com", display_name="Victim")
        db.refresh(attacker_row)
        assert attacker_row.google_sub is None, "the Google identity must NOT be linked"
    finally:
        db.close()


def test_google_login_still_links_a_verified_account_and_creates_new_ones():
    # The two legitimate paths must keep working: linking onto an
    # account that DID prove email ownership, and first-time signup.
    from ski_optimizer.api.routes.google_oauth import _resolve_google_user
    from ski_optimizer.db.models import User

    db = TestingSessionLocal()
    try:
        verified = User(email="proved@example.com",
                        password_hash="$argon2-fake", is_email_verified=True)
        db.add(verified); db.commit()

        linked = _resolve_google_user(db, google_sub="g-1", email="proved@example.com",
                                      display_name="P")
        assert linked.id == verified.id and linked.google_sub == "g-1"

        fresh = _resolve_google_user(db, google_sub="g-2", email="new@example.com",
                                     display_name="N")
        assert fresh.google_sub == "g-2" and fresh.is_email_verified is True
    finally:
        db.close()


def test_refresh_rotation_revocation_is_atomic():
    # MEDIUM finding: rotation was ORM read-then-write, so two refreshes
    # racing with the SAME still-valid token could both win -- a token
    # thief racing the real user minted a session the reuse detector
    # never saw. The revoke step is now a conditional UPDATE; the loser
    # observes 0 rows and is treated as reuse.
    from ski_optimizer.api.routes.auth import _revoke_if_active
    from ski_optimizer.db.models import RefreshToken, User
    from ski_optimizer.api import security as sec

    db = TestingSessionLocal()
    try:
        u = User(email="r@example.com", password_hash="x", is_email_verified=False)
        db.add(u); db.commit()
        t = RefreshToken(user_id=u.id, token_hash=sec.hash_refresh_token("raw"),
                         expires_at=sec.refresh_token_expiry())
        db.add(t); db.commit()

        assert _revoke_if_active(db, t.id, replaced_by_id=None) is True, "first revoke wins"
        assert _revoke_if_active(db, t.id, replaced_by_id=None) is False, "second observes the loss"
    finally:
        db.close()
