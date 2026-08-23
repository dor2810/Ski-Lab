"""
Security primitives. Every function here wraps a well-established
library -- nothing here is hand-rolled cryptography, on purpose.
Auth is one of the few areas where "clever" is a bug, not a feature.

Requires: passlib[argon2], python-jose[cryptography]. Not installed in
this sandbox (no network access here) -- see the repo README for the
honest status of what's been run vs. only syntax-checked.
"""
import datetime
import os
import secrets
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

# --- password hashing ---
#
# Argon2id over bcrypt: it's the current OWASP-recommended default
# (bcrypt has a silent 72-byte input truncation footgun that Argon2
# doesn't have, and Argon2 is memory-hard, which matters more against
# GPU-based cracking than bcrypt's cost factor alone). deprecated="auto"
# means if this list ever gains a second scheme, passlib will
# transparently re-hash old hashes into the new scheme on next login.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


# A real, validly-formatted Argon2 hash of an arbitrary fixed value --
# used ONLY as a comparison target when a login attempt targets an
# email that doesn't exist (see routes/auth.py), so that "no such
# user" and "wrong password" take the same amount of time and can't be
# told apart by an attacker measuring response latency. Computed once
# at import time rather than hardcoded as a string: a hand-typed fake
# hash is easy to get subtly wrong (wrong length, bad encoding) in a
# way that makes passlib raise instead of returning False, which would
# leak "no such user" via a 500 instead of via timing -- a different
# bug, not a fix.
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-timing-safety")


# --- JWT access tokens ---
#
# Short-lived on purpose (default 15 min): if one leaks (XSS, a logged
# request, a browser extension), the exposure window is small. The
# refresh token (below) is what actually keeps someone logged in.
SECRET_KEY = os.environ.get("SECRET_KEY")  # MUST be set in production; see .env.example
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def _require_secret_key() -> str:
    if not SECRET_KEY:
        # Fail loudly rather than silently signing tokens with a blank/
        # guessable key -- that would be a much worse failure mode than
        # a crashed dev server.
        raise RuntimeError(
            "SECRET_KEY is not set. Generate one (e.g. `python -c "
            "\"import secrets; print(secrets.token_urlsafe(32))\"`) and "
            "set it in your environment before starting the server."
        )
    return SECRET_KEY


def create_access_token(user_id: str) -> str:
    key = _require_secret_key()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the user_id if the token is valid and unexpired, else None."""
    key = _require_secret_key()
    try:
        payload = jwt.decode(token, key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload.get("sub")


# --- refresh tokens ---
#
# Deliberately NOT a JWT: a refresh token needs to be revocable
# (logout, rotation, reuse detection), and a self-contained signed JWT
# can't be un-issued short of maintaining a blocklist anyway -- so it's
# simpler and more honest to make it a random opaque string backed by a
# DB row from the start (see db/models.py RefreshToken). Only its HASH
# is ever stored; the raw value lives in the httpOnly cookie and
# briefly in memory.
REFRESH_TOKEN_BYTES = 32
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    # A refresh token is already 256 bits of secure randomness (unlike a
    # user-chosen password), so a fast hash is fine here -- Argon2's
    # deliberate slowness is solving a different problem (defending a
    # low-entropy, guessable password) that doesn't apply to this value.
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expiry() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


# --- lightweight CSRF mitigation ---
#
# Because auth tokens live in httpOnly cookies (not a header the JS
# sets explicitly), the browser attaches them automatically to ANY
# request to this origin -- including one triggered by a malicious
# third-party page. Requiring a custom header on state-changing
# requests defeats that: a cross-site <form> POST can't set custom
# headers, only simple ones. This is a lighter-weight alternative to a
# double-submit CSRF token; upgrading to that later is straightforward
# if this project needs stricter guarantees.
CSRF_HEADER_NAME = "X-Requested-With"
CSRF_HEADER_VALUE = "SkiLab"
