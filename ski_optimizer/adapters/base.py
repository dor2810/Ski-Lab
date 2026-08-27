"""
Shared conventions for every adapter in this package. Kept deliberately
thin -- fill in real retry/caching/rate-limit logic when the FIRST real
adapter (flight_adapter, Phase 4) actually needs it, rather than
guessing at requirements now.

Every adapter module should:
  1. Read its API key/credentials from environment variables (see
     .env.example at the repo root), never hardcode them.
  2. Raise a clear, specific exception on failure -- never silently
     fall back to a fabricated number. If live data is unavailable,
     the caller (engine/) decides what to do (e.g. fall back to the
     static estimate with a visible "estimated" flag), not the adapter.
  3. Cache short-TTL (per the blueprint's architecture: Redis in
     production, in-memory dict is fine for local dev) since flight/
     hotel search APIs are commonly rate-limited and/or billed per call.
"""


class AdapterError(Exception):
    """Base class for all adapter-level failures (auth, rate limit, no results, etc.)."""


class ProviderBlockedError(AdapterError):
    """
    The provider served an anti-bot challenge instead of data.

    Distinct from a generic AdapterError on purpose. This module's
    live pricing is a SCRAPER, and Google answers suspected automation
    with a CAPTCHA page rather than an error status: HTTP 200, ~1.8MB of
    HTML, the expected script tag present, but no flight payload behind
    it. fast_flights then fails deep inside with "'NoneType' object is
    not subscriptable", which is indistinguishable from a parser bug or
    a genuinely empty route.

    That ambiguity was the real cost. Every blocked lookup silently
    became a static estimate, so a user saw "EST." with no way to tell
    whether we had failed to fetch a price or there was genuinely no
    flight -- and this project's rule is to degrade VISIBLY. Naming the
    condition lets callers report it honestly and lets a fallback
    provider be tried instead of retrying a challenge that will never
    pass.
    """
