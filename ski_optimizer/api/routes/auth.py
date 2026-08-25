"""
Auth routes. Every state-changing endpoint requires the CSRF header
(see security.CSRF_HEADER_NAME) -- enforced in main.py as middleware,
not per-route, so a route can't accidentally be added without it.

TOKEN STRATEGY: bearer tokens in the JSON body, not cookies (changed
this session). access_token and refresh_token are both returned
directly to the client on register/login/refresh/Google callback; the
client holds access_token in memory and sends it as
`Authorization: Bearer <token>` on every request, and persists
refresh_token itself (e.g. localStorage) to call POST /auth/refresh
silently on future visits.

WHY NOT COOKIES (this project already tried it and it broke in
production): the frontend and API are deployed to DIFFERENT
`*.onrender.com` subdomains. `onrender.com` is on the Public Suffix
List (verified directly against publicsuffix.org's data), so those two
subdomains are different SITES to a browser -- and a growing number of
browsers (Safari's ITP for years, others moving the same way) restrict
or drop cookies set/read across a cross-site fetch() regardless of the
SameSite attribute. That's not a config mistake to fix, it's a
structural mismatch between "session lives in a cookie" and "frontend
and API are on different sites" -- a bearer token the client explicitly
attaches sidesteps it entirely, at the cost of the token being
readable by JS (mitigated by the access token's short 15-minute
lifetime; XSS is the real threat model to defend against separately,
not this auth mechanism).
"""
import datetime
import os
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...db.models import User, RefreshToken
from ...adapters import email_adapter
from .. import security
from ..schemas import RegisterRequest, LoginRequest, UserOut, AuthResponse, RefreshRequest, MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> Tuple[str, str]:
    """Returns (access_token, raw_refresh_token). Commits the new refresh token row."""
    access_token = security.create_access_token(user.id)
    raw_refresh = security.generate_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=security.refresh_token_expiry(),
    ))
    db.commit()
    return access_token, raw_refresh


def _bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    return header[len("bearer "):].strip() or None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _bearer_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = security.decode_access_token(token)
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def get_current_user_for_search(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Same as get_current_user, EXCEPT: a request with no valid session is
    let through as anonymous (returns None) rather than raising 401, but
    ONLY if ALLOW_ANONYMOUS_SEARCH is explicitly set to "true". Used
    ONLY by routes/search.py's search endpoints, which never actually
    read the returned User -- it exists purely as an auth gate, so
    swapping it here doesn't touch any search logic.

    AUTH-REQUIRED BY DEFAULT (restored 2026-08-25 -- was briefly
    anonymous-by-default while accounts/Google sign-in weren't wired up
    on the frontend; now that real sign-in exists, search goes back to
    requiring it). Set ALLOW_ANONYMOUS_SEARCH=true explicitly to bypass
    this for local dev/testing without registering an account.
    """
    token = _bearer_token(request)
    if token:
        user_id = security.decode_access_token(token)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user
    if os.environ.get("ALLOW_ANONYMOUS_SEARCH", "false").lower() == "true":
        return None
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        # Same message either way a real attacker would try email
        # enumeration -- but note this DOES still leak via timing/existing
        # accounts in practice; a production system might want a
        # constant-response "check your email" flow instead. Flagged
        # here rather than silently shipping the enumeration risk.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not create account with that email.")

    user = User(
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token, refresh_token = _issue_tokens(db, user)

    # Verification email is fire-and-forget via the console backend in
    # dev (see adapters/email_adapter.py) -- a real link/token generation
    # step belongs here once EMAIL_BACKEND is a real provider; wiring
    # the actual verification-token issuance is left for that point
    # rather than building it against a backend that can't send yet.

    return AuthResponse(user=user, access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Verify against a real dummy hash even when no user is found (see
    # security.DUMMY_PASSWORD_HASH's docstring) -- otherwise "no such
    # user" returns faster than "wrong password" and an attacker can
    # enumerate registered emails by timing alone.
    password_ok = security.verify_password(
        payload.password, user.password_hash if user and user.password_hash else security.DUMMY_PASSWORD_HASH
    )
    if not user or not user.password_hash or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    access_token, refresh_token = _issue_tokens(db, user)
    return AuthResponse(user=user, access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    raw_token = payload.refresh_token
    token_hash = security.hash_refresh_token(raw_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if stored is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token.")

    if stored.revoked_at is not None:
        # REUSE DETECTED: this exact token was already rotated out once
        # before. The only way that happens legitimately is if this
        # refresh call is a replay -- either the user has two tabs
        # racing (rare, and rotation should tolerate a narrow race in a
        # production version) or the token was stolen and both the
        # thief and the real user are using it. Treat it as compromise:
        # revoke every other active token for this user, forcing a
        # fresh login everywhere.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == stored.user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.datetime.utcnow()})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token reuse detected; all sessions revoked.")

    if not stored.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired.")

    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")

    # Rotate: issue a new refresh token, mark this one revoked and
    # linked to its replacement (for audit trail / reuse detection above).
    new_raw = security.generate_refresh_token()
    new_token = RefreshToken(
        user_id=user.id,
        token_hash=security.hash_refresh_token(new_raw),
        expires_at=security.refresh_token_expiry(),
    )
    db.add(new_token)
    db.flush()  # get new_token.id before using it below
    stored.revoked_at = datetime.datetime.utcnow()
    stored.replaced_by_id = new_token.id
    db.commit()

    access_token = security.create_access_token(user.id)
    return AuthResponse(user=user, access_token=access_token, refresh_token=new_raw)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = security.hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.datetime.utcnow()
        db.commit()
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
