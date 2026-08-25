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

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
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

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        # An account with this email might already exist from password
        # signup -- link them by email rather than creating a duplicate,
        # but only because Google has already verified this email above.
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_sub = google_sub
        else:
            user = User(
                email=email, google_sub=google_sub,
                display_name=claims.get("name"), is_email_verified=True,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

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
