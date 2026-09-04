# ops — production monitoring

## What is watching Ski Lab

| Thing | Where | Notes |
|---|---|---|
| Uptime check `ski-lab-api-health` | GCP Monitoring | GETs `https://ski-lab-api-…/health` every 5 min from several regions, HTTPS, 2xx required |
| Alert policy `Ski Lab API is down or degraded` | `alert_api_down.json` | Fires when the check fails from more than one region for 5 minutes; emails the owner; auto-closes after 30 min |
| `/health` itself | `ski_optimizer/api/main.py` | Runs `SELECT 1` against Postgres and answers **503** when that fails |

## Why /health is not a constant

It used to `return {"status": "ok"}` unconditionally. On 2026-09-01
registration was returning 500 because the pooled Postgres connection
was dead (Neon suspends idle compute) and this endpoint reported "ok"
throughout — an alarm wired to it would have been theatre. It now
checks the dependency that broke.

## Two traps found while setting this up — check both if you rebuild it

1. **`gcloud monitoring uptime create` does not use SSL by default.**
   The first check ran plain HTTP against port 443 and failed every
   time (`passed=0 failed=66`) while the endpoint was perfectly
   healthy. `--protocol=https` is not accepted by this gcloud version;
   patch the config instead:

   ```
   curl -X PATCH ".../uptimeCheckConfigs/<id>?updateMask=httpCheck.useSsl,httpCheck.validateSsl" \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -d '{"httpCheck":{"useSsl":true,"validateSsl":true}}'
   ```

2. **An alarm nobody has watched fire is not an alarm.** Verify by
   creating a temporary uptime check against a path that 404s, plus a
   copy of the policy pointing at it, and confirming the email lands.
   Delete both afterwards. That is exactly how trap 1 was found.

## Still missing

A daily synthetic SEARCH. `/health` proves the service and database are
up; it would not have caught the calendar quoting prices no card
showed, or the paid single-date lookup silently doing nothing. Both
were found by a human. A signed-in search run once a day, asserting a
few invariants (results non-empty, every card's date present in
`date_prices`, totals agreeing), would have caught both.
