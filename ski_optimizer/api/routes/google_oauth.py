"""
Google OAuth via Authlib -- the standard, well-maintained OAuth client
for Python (not a hand-rolled OAuth implementation).

Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (see .env.example),
which come from a Google Cloud OAuth consent screen + credentials that
DON'T EXIST YET -- this code is correct but inert without them, and the
redirect URI registered in Google Cloud must exactly match
GOOGLE_REDIRECT_URI below (including scheme -- Google requires https
except for localhost). None of that can be set up from this sandbox;
it's a Google Cloud Console task for whoever owns the project.
"""
import os

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Depends, HTTPException, status
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...db.models import User
from .. import security
from .auth import _issue_tokens

router = APIRouter(prefix="/auth/google", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

_FRONTEND_URL_RAW = os.environ.get("FRONTEND_URL", "http://localhost:3000")
# FRONTEND_URL is comma-separated (see api/main.py's CORS setup, which
# allow-lists every entry) -- a browser redirect can only ever go to
# ONE URL, so this takes the first as the primary deploy target.
FRONTEND_URL = _FRONTEND_URL_RAW.split(",")[0].strip()
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


def _require_google_configured():
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Google sign-in isn't configured yet -- GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET "
            "are unset. This needs a real Google Cloud OAuth app, set up outside this codebase.",
        )


@router.get("/login")
async def google_login(request: Request):
    _require_google_configured()
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


class UnverifiedAccountCollision(Exception):
    """A Google sign-in's email matches an existing account that never
    proved it owns that address -- linking is refused."""


def _resolve_google_user(db: Session, google_sub: str, email: str, display_name):
    """
    Find or create the User for a verified Google identity.

    SECURITY (review 2026-08-28, CRITICAL, fixed before OAuth was ever
    enabled): the old inline version linked by bare email match. But
    password registration never verifies email ownership -- so an
    attacker could pre-register victim@x.com with a password only THEY
    know, wait for the victim to "Sign in with Google", and the
    victim's real Google identity would be silently attached to the
    attacker-controlled row. Linking is now allowed ONLY onto accounts
    that already proved email ownership (is_email_verified); an
    unverified collision raises and the user is told to sign in with
    the password flow instead.
    """
    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user:
        return user
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        if not existing.is_email_verified:
            raise UnverifiedAccountCollision(email)
        existing.google_sub = google_sub
        db.commit()
        db.refresh(existing)
        return existing
    user = User(email=email, google_sub=google_sub,
                display_name=display_name, is_email_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    _require_google_configured()
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        # Per Google's own OAuth docs: an app "must gracefully handle
        # situations where some permissions are denied" -- the most
        # common real cause here is the user clicking "Cancel" on
        # Google's consent screen, which Google reports back as an
        # error redirect (access_denied) rather than an authorization
        # code. A stale/expired session cookie failing Authlib's CSRF
        # state check lands here too. Either way: redirect back to the
        # app with a clean signal, don't crash with an unhandled 500.
        return RedirectResponse(url=f"{FRONTEND_URL}#auth_error=google_oauth_failed")
    # parse_id_token verifies the JWT signature/audience/issuer against
    # Google's published keys -- this is the actual identity proof, not
    # just "we got redirected back so it must be fine."
    claims = await oauth.google.parse_id_token(request, token)

    google_sub = claims["sub"]
    email = claims.get("email")
    if not email or not claims.get("email_verified"):
        # Don't trust an unverified email from the provider as proof of
        # ownership -- Google marks this explicitly for a reason.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google account has no verified email.")
    # Normalize identically to schemas.py's Register/LoginRequest. This
    # path bypasses those Pydantic schemas entirely (the email comes from
    # Google's token, not a request body), so without this a Google
    # sign-in with 'Dor@x.com' would fail to link to an existing
    # password account registered as 'dor@x.com' and would create a
    # duplicate instead.
    email = email.strip().lower()

    try:
        user = _resolve_google_user(db, google_sub=google_sub, email=email,
                                    display_name=claims.get("name"))
    except UnverifiedAccountCollision:
        # Refuse the silent merge and say why, without leaking more.
        return RedirectResponse(
            f"{FRONTEND_URL}/sign-in#error=account_exists_use_password")

    access_token, refresh_token = _issue_tokens(db, user)
    # Tokens travel in the URL FRAGMENT (#...), not a query string or a
    # cookie: a fragment is never sent to any server (including this
    # one, on the next request) and doesn't appear in server access
    # logs, but the frontend's own JS can read it via
    # window.location.hash immediately after this redirect lands. See
    # auth.py's module docstring for why this whole flow avoids cookies
    # in the first place. The frontend is responsible for reading these
    # once, storing them, and stripping the fragment from the URL.
    redirect_url = f"{FRONTEND_URL}#access_token={access_token}&refresh_token={refresh_token}"
    return RedirectResponse(url=redirect_url)
