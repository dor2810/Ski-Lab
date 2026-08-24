"""
Auth routes. Every state-changing endpoint requires the CSRF header
(see security.CSRF_HEADER_NAME) -- enforced in main.py as middleware,
not per-route, so a route can't accidentally be added without it.

Cookie strategy: access_token and refresh_token are both httpOnly,
Secure, SameSite=None cookies -- never returned in a JSON body, never
touchable by JS. Secure=True means these cookies won't be sent at all
over plain HTTP; the dev server needs to run over https (or a
localhost exception, which browsers grant automatically) for cookies
to work at all. That's intentional friction, not an oversight.

WHY SameSite=None, NOT Lax (changed this session, deploying to Render):
the frontend and API are deployed to DIFFERENT `*.onrender.com`
subdomains. `onrender.com` is on the Public Suffix List (verified
directly against publicsuffix.org's data, not assumed), which means
those two subdomains are different SITES to a browser, not just
different origins -- SameSite=Lax cookies are never sent on cross-site
fetch()/XHR (Lax only permits top-level navigations), so login would
silently appear to work (the Set-Cookie response is fine) while every
following "authenticated" request came back 401, no matter how correct
the CORS config was. None is the standard fix for a legitimate
cross-site cookie-auth setup and requires Secure=True, which was
already set. Locally (frontend and API both on `localhost`, different
ports only) this is a no-op -- same-site cross-port requests were never
restricted by SameSite in the first place.
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...db.models import User, RefreshToken
from ...adapters import email_adapter
from .. import security
from ..schemas import RegisterRequest, LoginRequest, UserOut, MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE, access_token, httponly=True, secure=True, samesite="none",
        max_age=security.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, httponly=True, secure=True, samesite="none",
        max_age=security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, path="/auth",
        # scoped to /auth, not /: the refresh token has no business being
        # sent on every API call, only on the refresh/logout requests.
    )


def _issue_session(db: Session, user: User, response: Response) -> None:
    access_token = security.create_access_token(user.id)
    raw_refresh = security.generate_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=security.refresh_token_expiry(),
    ))
    db.commit()
    _set_auth_cookies(response, access_token, raw_refresh)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = security.decode_access_token(token)
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
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

    _issue_session(db, user, response)

    # Verification email is fire-and-forget via the console backend in
    # dev (see adapters/email_adapter.py) -- a real link/token generation
    # step belongs here once EMAIL_BACKEND is a real provider; wiring
    # the actual verification-token issuance is left for that point
    # rather than building it against a backend that can't send yet.

    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
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

    _issue_session(db, user, response)
    return user


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token provided.")

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
    _set_auth_cookies(response, access_token, new_raw)
    return user


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if raw_token:
        token_hash = security.hash_refresh_token(raw_token)
        stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.datetime.utcnow()
            db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
