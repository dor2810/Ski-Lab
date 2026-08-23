# Auth backend — status

## What this is

A real FastAPI backend for account registration/login: email+password
(Argon2id hashing) and Google OAuth (Authlib), JWT access tokens +
rotating refresh tokens with reuse detection, httpOnly cookie-based
sessions, CSRF header enforcement, CORS locked to an explicit frontend
origin. Not a toy — this is the same pattern (rotating refresh tokens,
hash-at-rest, timing-safe login) you'd find in a production system.

## Honest status: written and reviewed, NOT executed

The sandbox this was built in has **no network access**, so none of
`fastapi`, `sqlalchemy`, `passlib`, `python-jose`, or `authlib` could be
installed, and the code has never actually been run. What was actually
done, so you know exactly how much to trust this:

- ✅ Every file parses as valid Python (`ast.parse`, checked and re-checked
  after every edit)
- ✅ Manually re-read for logic bugs, twice — this genuinely caught 3 real
  ones before you'd have hit them: a `sqlalchemy.orm` import that should've
  been `sqlalchemy.pool` (`StaticPool`), `str | None` syntax that would
  crash on Python <3.10, and a hand-typed fake password hash for the
  timing-attack mitigation that would have raised an exception instead
  of failing cleanly (fixed by generating a real dummy hash at import time)
- ❌ Never run against a real interpreter with the dependencies installed
- ❌ `tests/test_auth.py` has never actually executed — it's written to
  standard FastAPI testing conventions (TestClient + in-memory SQLite
  override) and *should* work, but "should" is doing real work in that
  sentence until proven otherwise

**First real step once you have network access:**

```
pip install -r requirements.txt
python -c "import secrets; print(secrets.token_urlsafe(32))"   # → SECRET_KEY
export SECRET_KEY=<paste that>
pytest tests/test_auth.py -v
```

Expect to fix at least something small — that's normal for code that's
never been executed, not a sign anything here was done carelessly.

## What's real vs. what needs setup outside this codebase

| Piece | Status |
|---|---|
| Register / login / logout / refresh / me | Code complete, needs the above to verify |
| Password hashing, JWT, refresh rotation | Code complete |
| Google OAuth | Code complete, but **inert** without a real Google Cloud OAuth app (Client ID/Secret, registered redirect URI) — that's a Google Cloud Console task, can't be created from code |
| Email verification | `adapters/email_adapter.py`'s console backend actually works (prints instead of sending) — enough to develop the flow locally. A real provider (SendGrid/SES/etc.) is a config change away, not built yet |
| Database | SQLite works out of the box for local dev; Postgres is a `DATABASE_URL` change away |
| HTTPS | Cookies are set `Secure=True` (won't transmit over plain HTTP) — `localhost` gets a browser exception, but any other host needs real HTTPS before login will work at all |

## Security choices worth knowing about (not just "trust me")

- **Argon2id, not bcrypt** — current OWASP recommendation; bcrypt has a
  silent 72-byte input truncation bug that Argon2id doesn't share.
- **12-char minimum, no forced complexity rules** — follows NIST SP
  800-63B; complexity requirements push toward predictable patterns
  more than real entropy.
- **Refresh tokens are opaque + hashed at rest**, not JWTs — a JWT
  can't be revoked without a blocklist anyway, so an opaque token
  backed by a real DB row (with `revoked_at`) is more honest about
  what it actually does.
- **Rotation + reuse detection** — every refresh issues a new token and
  revokes the old one; if a revoked token is ever presented again,
  every active session for that user gets revoked (signal of theft).
- **Timing-safe login** — a nonexistent email still runs a full Argon2
  verify against a real dummy hash, so "no such user" and "wrong
  password" take the same time.
- **httpOnly cookies, not localStorage** — matches the no-localStorage
  rule already governing the frontend, and means an XSS bug can't
  steal the session token via `document.cookie` either.
- **CSRF via required custom header**, not a full double-submit token
  — lighter-weight, sufficient given SameSite=Lax + httpOnly, but
  flagged as a candidate for hardening later, not presented as
  maximal protection.

## What's explicitly NOT done

- No password reset flow yet (verification email path exists; reset
  doesn't) — straightforward to add on the same `EmailVerificationToken`
  pattern, just not built this session.
- No rate limiting on login/register — a real deployment needs this
  (e.g. `slowapi`, or rate limiting at a reverse proxy) before it's
  internet-facing.
- No `alembic` migrations — `init_db()` uses `create_all()`, fine for a
  fresh dev DB, not fine once real user data exists and the schema
  needs to change.
- No saved-trip CRUD yet (`routes/trips.py`'s trip-history/save
  concept from the original architecture plan) — `routes/search.py` is
  live and protected (below), but it's stateless: nothing gets saved.

## POST /trips/search — the first protected route (this session)

Wraps `engine.scoring.rank_trips` exactly as the CLI/frontend prototype
use it — same hard/soft constraint pipeline, no separate scoring logic.
Requires a valid `access_token` cookie (`Depends(get_current_user)`);
no login, no results. Also covered by the CSRF header requirement even
though it doesn't mutate anything — closes off "trigger searches on a
logged-in user's behalf" as an attack surface for negligible cost to a
legitimate client.

Resort data loads once into an in-memory cache at import time, not
per-request. `reload_resorts()` exists for picking up a spreadsheet
edit without a full restart, but isn't wired to any endpoint yet —
deliberately: an under-protected reload endpoint is an easy DoS vector,
so it's a manual/admin-route decision for later, not a default.

`tests/test_search.py` covers: auth required, CSRF required, results
respect the budget filter and sort order, weight validation (unknown
keys rejected, partial/un-normalized weights accepted and normalized),
unknown `target_resort` returns 404, fixed-resort mode returns exactly
one result. Same honesty caveat as everything else in this file:
written and reviewed, never executed.
