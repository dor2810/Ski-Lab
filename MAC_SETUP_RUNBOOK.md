# Mac Setup Runbook — Ski Lab

*The goal of this session: convert the unverified pile into verified-or-fixed. Budget ~1 hour.*

---

## What's actually unverified right now

| Component | Status |
|---|---|
| Engine, scoring, terrain, validation, transfers, date search | ✅ 163 tests running and passing |
| Auth backend (register/login/JWT/Google OAuth) | ❌ **never executed** |
| Search API route | ❌ **never executed** |
| Fare-history persistence | ❌ 8 tests skipped (needs sqlalchemy) |
| Live SerpApi calls | ❌ request params never verified against the real API |

Everything in the top row is genuinely tested. Everything below it is code that has been written and reviewed but has **never run**. Expect breakage — that's the point of the session, not a sign something went wrong.

---

## Step 1 — Get the code onto the Mac (~5 min)

Unzip `ski-trip-optimizer.zip`, then:

```bash
cd ski-trip-optimizer
git init
git add -A
git commit -m "Ski Lab: engine, adapters, transfers, date search, auth backend"
```

**Before the first push anywhere**, confirm `.gitignore` covers `.env` and `*.db`. Leaked keys in git history are painful to purge properly.

---

## Step 2 — Environment (~5 min)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Paste that into `SECRET_KEY=` in `.env`. The auth backend refuses to start without it — deliberately, rather than silently signing tokens with a blank key.

---

## Step 3 — Confirm what already works (~2 min)

```bash
pytest tests/ -v
```

**Expected:** the 163 currently-passing tests still pass, the 8 fare-history tests now RUN (sqlalchemy is installed), and `test_auth.py` / `test_search.py` run for the first time.

If anything in the previously-passing 163 breaks here, that's environment-related (Python version, openpyxl version) rather than logic — tell me the traceback.

---

## Step 4 — The auth and search tests (~20 min, expect failures)

This is the real work. These have never executed. Likely failure classes, in rough order of probability:

1. **Import/name errors** — trivial, fast to fix.
2. **Pydantic v2 API drift** — `field_validator` and `from_attributes` are v2 syntax; if the installed version differs, decorators need adjusting.
3. **FastAPI `TestClient` cookie handling** — the refresh-rotation tests manipulate cookies directly, and TestClient's cookie jar behaviour varies by version. This is the test I'd most expect to need work.
4. **`Secure=True` cookies over HTTP** — cookies are set Secure, so they won't transmit over plain HTTP. Browsers grant localhost an exception; `TestClient` may not. If auth tests fail with "no cookie received", this is why.
5. **SQLAlchemy 2.x** — `declarative_base` moved; if it errors on import, that's the cause.

**Send me any traceback and I'll fix it.** Don't spend long debugging solo — I wrote it, I know what it was meant to do.

---

## Step 5 — First real SerpApi call (~10 min)

Get a key at serpapi.com, add `SERPAPI_API_KEY=` to `.env`, then:

```python
from datetime import date
from ski_optimizer.adapters import flight_adapter

result = flight_adapter.search_flights(
    "TLV", ["GVA", "INN"], date(2027, 1, 16), date(2027, 1, 22)
)
print(len(result.options), "options")
for o in result.options[:5]:
    print(f"  {o.airline:20} {o.destination_airport}  EUR{o.price_eur:.0f}  {o.stops} stops")
print("insight:", result.insight)
```

**What this verifies that tests couldn't:** that the request params are the ones SerpApi actually expects, that multi-airport search works as documented (both GVA and INN in one call), and that real responses match the fixture shape.

**The parsing is well-tested** (28 tests against a fixture built from their published schema), so if anything breaks it'll most likely be param names or auth, not the parser.

---

## Step 6 — Sanity-check the estimates against reality (~10 min)

The one thing no amount of code can verify. Take the CLI's top result:

```bash
python -m ski_optimizer.cli.main
```

Then manually check that route on Google Flights and a hotel site for the same dates. **Is the total in the right ballpark?** This is the question the whole project rests on, and it's never actually been asked against real prices.

If the estimates are wildly off, that's far more important than any code bug.

---

## Step 7 — Optional: Claude Code + git

If you want the phone→Mac workflow: install Claude Code, run it in the repo, pair with the mobile app. Then you can delegate from your phone and it executes locally.

---

## Known gaps you may notice (already documented, not bugs to report)

- **Transfer airport consistency.** With no airport specified, transfer cost resolves to the cheapest airport for that resort (Val Thorens → Lyon €85, not Geneva €100). Fixing it properly needs the flight search to report which airport it chose. Documented in `transfer_cost_eur_per_person`'s docstring and covered by a test that makes the behaviour explicit.
- **20 of 46 transfer pairs unresearched** — they fall back to the distance formula, visibly.
- **13 of 30 resorts have estimated terrain data.**
- **Default flight function is date-blind** — date-range search can only rank on season bands until live pricing is injected via `flight_cost_fn`.
- **Affiliate/booking URLs absent** — never verified that transfer operators run affiliate programs.

---

## If you only have 20 minutes

Steps 1–3 and the first half of 4. Getting `pytest` to run at all, and seeing which auth tests fail, is 80% of the value. The SerpApi call can wait.
