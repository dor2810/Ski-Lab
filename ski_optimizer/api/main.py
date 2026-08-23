"""
FastAPI app entrypoint.

Run locally (once dependencies are actually installed -- see repo
README for this sandbox's honesty note about that):

    uvicorn ski_optimizer.api.main:app --reload

CORS is intentionally an explicit allow-list (FRONTEND_URL), never "*"
-- a wildcard origin combined with allow_credentials=True is rejected
by browsers anyway (and rightly so: it would let any website read
authenticated responses), so this isn't just caution, it's required for
cookie-based auth to work at all.
"""
import os

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from ..db.database import init_db
from . import security
from .routes import auth, google_oauth, search

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
SESSION_SECRET = os.environ.get("SECRET_KEY", "")  # required for Authlib's OAuth state; see security.py

app = FastAPI(title="Ski Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,  # required so the browser sends the httpOnly cookies cross-origin (dev: 3000 -> 8000)
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authlib's Starlette integration stores OAuth flow state (the "state"
# param, PKCE verifier) in a server-side session cookie during the
# redirect round-trip to Google -- this is separate from our own
# access/refresh token cookies and only lives for the duration of login.
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


@app.middleware("http")
async def enforce_csrf_header(request: Request, call_next):
    """
    Requires the custom header (see security.CSRF_HEADER_NAME) on every
    state-changing request to /auth/* or /trips/*, EXCEPT the Google
    OAuth redirect routes -- those are browser navigations (the user
    clicking a link/being redirected), not fetch() calls, so they can't
    carry a custom header, and they don't rely on ambient cookie auth
    the same way (the callback is proving identity via Google's signed
    token, not via a cookie an attacker's page could trigger).

    /trips/search is a POST but doesn't mutate anything -- it's a
    search, not a write. It's covered anyway, on purpose: it's a
    cookie-authenticated endpoint that does real (if modest) work per
    request, and requiring the header costs nothing for a legitimate
    client while closing off "trigger searches on a logged-in user's
    behalf" as an attack surface, however low-value that attack is today.
    """
    is_state_changing = request.method in ("POST", "PUT", "PATCH", "DELETE")
    is_oauth_route = request.url.path.startswith("/auth/google")
    is_protected_prefix = request.url.path.startswith("/auth") or request.url.path.startswith("/trips")
    if is_state_changing and is_protected_prefix and not is_oauth_route:
        if request.headers.get(security.CSRF_HEADER_NAME) != security.CSRF_HEADER_VALUE:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing required header.")
    return await call_next(request)


app.include_router(auth.router)
app.include_router(google_oauth.router)
app.include_router(search.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
