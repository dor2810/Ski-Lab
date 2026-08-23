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
