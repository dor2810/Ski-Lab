# Next Steps — saved 2026-08-29

The agreed backlog, in the order recommended. Kept out of
PROJECT_STATE.md deliberately: that file records what IS, this one
records what's NEXT and why it hasn't happened yet.

## 1. Postgres cutover — BLOCKED ON OWNER (5 minutes)
The last big structural item. Litestream (`run.sh`, `litestream.yml`,
Dockerfile stanza) has held up fine — accounts survive deploys — but it
forces `--max-instances=1` because SQLite has one writer, and it is a
stopgap by design.

**Owner action:** create a free project at https://neon.tech (or
Supabase) and hand over the connection string.

**Then (all ready on this side):** set `DATABASE_URL` on the Cloud Run
service; `db/database.py` already reads it and switches engine +
connect_args automatically. Delete `run.sh`, `litestream.yml`, the
Dockerfile's litestream layer, and drop `--max-instances=1`. Keep the
GCS bucket until a real Postgres backup has been verified.

## 2. Restrict or rotate the Google Maps API key — OWNER, 1 minute
`GOOGLE_MAPS_API_KEY` was pasted into chat on 2026-08-29. It lives only
in the gitignored `.env` and was used for 71 one-off Directions calls
(the frozen drive-time dataset), so there is no recurring exposure —
but Console → Credentials → the key → **Restrict key → Directions API
only**, or reset it and tell Claude to update `.env`.

Same standing note for `GOOGLE_CLIENT_SECRET` (already rotated once)
and `SERPAPI_API_KEY`.

## 3. Split `api/routes/search.py` — no owner action needed
1,486 lines, flagged by the 2026-08-28 code review. Suggested split:
response models → `api/schemas_out.py`; the `_*_search_url` /
`_*_options_out` helpers → `api/routes/_result_builders.py`. Pure
refactor, no behaviour change; the 577-test suite is the safety net.
`tests/test_search.py` (1,260 lines) can follow the same seams.

## 4. Monitors for things that change on their own
- **January fares appearing** for LJU / TLS / ZAG — service exists,
  fares were not yet published when probed 2026-08-28. Self-heals; a
  weekly check would confirm and could flip those resorts to live.
- **Ski-pass tariffs** — Chamonix's page is still ambiguous, and the
  five dynamic-pricing resorts (Grandvalira, Vallnord, Formigal,
  Pamporovo, Astun) may publish fixed 6-day products in a future
  season. Worth a seasonal re-check, not a manual re-research.
- Both are candidates for a scheduled agent rather than hand-running
  the research again.

## 5. Ski school lesson costs — the last blueprint data gap
Only 6 of 39 resorts researched. Suggested approach: seed a
`data/ski_school_links.py` first (every resort's official ski-school
page), then price a standard product (6 half-days, group, adult) the
same way `ski_pass_prices.py` was built — with an explicit
UNPRICED_RESORTS dict recording exactly why any resort has no figure.

## Smaller / opportunistic
- `assemble_coverage_first` truncation ordering artifact when
  `top_n` < resort count (LOW, documented in the code review).
- TripAdvisor MCP: connects and lists tools but `search_hotels`
  returns "Internal error" for every location — re-test occasionally;
  `hotel_details` would add photos and amenities.
- stayingapi.com — unified cross-OTA hotel API, free tier, needs an
  owner-created key.
- Krvavec is the one resort with no frozen lift coordinates (Overpass
  rate-limited mid-run). Re-run `scripts/build_lift_locations.py`.
