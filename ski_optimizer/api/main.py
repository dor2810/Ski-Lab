"""
FastAPI app entrypoint.

Run locally (once dependencies are actually installed -- see repo
README for this sandbox's honesty note about that):

    uvicorn ski_optimizer.api.main:app --reload

CORS is intentionally an explicit allow-list (FRONTEND_URL), never "*"
-- a wildcard origin combined with allow_credentials=True is rejected
by browsers anyway (and rightly so: it would let any website read
authenticated responses). allow_credentials stays on for the OAuth
login/callback navigations (see SessionMiddleware below); it's not
needed for our own bearer-token auth (see routes/auth.py), which the
frontend attaches as an explicit Authorization header, not a cookie.

FRONTEND_URL accepts a comma-separated list, not just one origin --
kept as a list (not simplified back to a single string) so a preview/
staging frontend origin can be added later without another code
change, not because there's more than one production origin today
(there was, briefly, during the Render -> Firebase Hosting + Cloud Run
migration; see git history).
"""
import os

import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from ..db.database import init_db
from . import security
from .routes import auth, google_oauth, search

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
FRONTEND_ORIGINS = [origin.strip() for origin in FRONTEND_URL.split(",") if origin.strip()]
SESSION_SECRET = os.environ.get("SECRET_KEY", "")
# Fail FAST if unset (security review 2026-08-28, MEDIUM): the JWT path
# refuses a missing SECRET_KEY loudly (security._require_secret_key),
# but this silently fell back to signing the OAuth-state session cookie
# with an EMPTY key -- forgeable by anyone. A misconfigured deploy now
# dies at startup instead of degrading quietly.
if not SESSION_SECRET:
    raise RuntimeError("SECRET_KEY must be set (signs both JWTs and the OAuth state cookie)")  # required for Authlib's OAuth state; see security.py

logger = logging.getLogger(__name__)

app = FastAPI(title="Ski Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,  # needed for the Authlib session cookie during the Google OAuth redirect dance
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
            # Raising HTTPException here wouldn't work: this middleware sits
            # outside Starlette's ExceptionMiddleware, which only wraps the
            # router/endpoints, not @app.middleware("http") functions -- a
            # raised HTTPException would propagate as an unhandled error
            # instead of becoming a 403 response.
            return JSONResponse(
                {"detail": "Missing required header."}, status_code=status.HTTP_403_FORBIDDEN,
            )
    return await call_next(request)


app.include_router(auth.router)
app.include_router(google_oauth.router)
app.include_router(search.router)


@app.on_event("startup")
def on_startup():
    init_db()


def _database_ok() -> None:
    """One trivial query. Raises if the database cannot answer."""
    from sqlalchemy import text
    from ..db.database import engine
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@app.get("/health")
def health(response: Response):
    """
    Liveness that can actually fail.

    This used to return {"status": "ok"} unconditionally -- a constant,
    checking nothing. On 2026-09-01 registration was returning 500
    because the pooled Postgres connection was dead, and this endpoint
    reported "ok" throughout; an alarm wired to it would have been
    theatre.

    So it checks the dependency that broke, and the one every real
    request needs. 503 rather than 200-with-a-sad-body, because uptime
    checks watch the STATUS CODE and a monitor that has to parse JSON
    to notice an outage is one nobody wires up correctly.
    """
    checks = {}
    try:
        _database_ok()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 -- the reason is the payload
        logger.exception("health check: database unreachable")
        checks["database"] = f"unavailable: {type(exc).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "checks": checks}
