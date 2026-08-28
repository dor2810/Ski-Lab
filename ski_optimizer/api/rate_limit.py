"""
In-memory rate limiting for the search endpoints.

WHY THIS EXISTS: search is anonymous by default (see
routes/auth.get_current_user_for_search) -- the product deliberately
shows no login, matching the frontend's "no accounts" design (see
frontend/web's brand spec). That means there is NO per-account
accountability standing between a script and hammering live pricing.
Two, deliberately different, limiters cover the two real risks:

  1. PER-CLIENT BURST (enforce_search_rate_limit): a short per-IP
     window, applied to every search request regardless of whether it
     ends up live-priced. Stops one script from spamming the endpoint.

  2. GLOBAL LIVE-PRICING BUDGET (live_pricing_allowed): a single,
     GLOBAL counter -- not per-IP -- because what it protects is itself
     global, shared across every visitor, not a per-visitor resource:
     Google Flights' and Google Hotels' own rate-limit/ban tolerance for
     the scrapers behind live pricing (adapters/google_flights_adapter.py,
     adapters/google_hotels_adapter.py -- unmetered in dollars, no API
     key for either, but not free of limits; see each module's own
     docstring). A single live-eligible request can cost up to ~12-20
     real provider calls (search_date_range live-reprices up to
     live_reprice_n pairs, x2 for flight+accommodation; rank_trips' own
     live_reprice_n defaults higher still) -- so even a SMALL number of
     live SEARCH REQUESTS adds up fast. The default here (8/day) is a
     deliberately conservative safety net; it does NOT precisely track
     actual provider call counts (that would need counting calls inside
     the adapters themselves, not requests here) -- it's a coarse,
     honest budget, not a precise meter. Tune via
     MAX_LIVE_SEARCHES_PER_DAY if real usage shows it's too tight or
     too loose.

When the global live-pricing budget is exhausted, callers must degrade
to the static estimate for the REST of the window -- never block the
search itself. live_pricing_active reports False when the budget is
exhausted (or the request had nothing live-eligible about it, e.g. no
date). It does NOT report False just because a live call happened to
fail for one resort/date -- that's the OTHER degrade path
(flight_price_is_live / accommodation_price_is_live per result; see
engine/date_search.py's flight_cost_fn contract), and conflating the
two used to silently empty the whole result set on any provider hiccup,
not just correctly label one result as estimated.

Bounded, in-memory, single-instance -- same pattern and same reasoning
as adapters/response_cache.py's MemoryResponseCache: Render's free tier
runs one instance, so no cross-instance coordination is needed. Swap
for a Redis-backed limiter if that ever changes.
"""
import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Sliding-window limiter: at most max_requests per key within window_seconds."""

    def __init__(self, max_requests: int, window_seconds: float):
        if max_requests <= 0:
            raise ValueError(f"max_requests must be > 0, got {max_requests}")
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be > 0, got {window_seconds}")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """
        True and records the hit if this key is still under budget;
        False (and does NOT record) if it would exceed it -- a rejected
        attempt doesn't consume budget, so the window empties out purely
        by time passing, not by how hard something hammers it.
        """
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def clear(self) -> None:
        """Test helper."""
        with self._lock:
            self._hits.clear()


def _client_key(request: Request) -> str:
    """
    Prefers the first hop of X-Forwarded-For (Render sits behind a
    proxy, so request.client.host alone would be the proxy's address
    for every visitor, collapsing everyone into one bucket) and falls
    back to request.client.host for direct/local connections.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_PER_IP_LIMIT = int(os.environ.get("SEARCH_RATE_LIMIT_PER_MINUTE", "6"))
_per_ip_limiter = RateLimiter(max_requests=_PER_IP_LIMIT, window_seconds=60)

# Booking-link clicks get their OWN, looser per-IP budget (code review
# 2026-08-28): they shared the 6/min search limiter, so one search plus
# a few Book clicks tripped 429 and silently degraded the deep link to
# the generic search page. A click is one cheap upstream request, not a
# 24-lookup search -- 30/min bounds abuse without punishing real use.
_BOOKING_LINK_LIMIT = int(os.environ.get("BOOKING_LINK_RATE_LIMIT_PER_MINUTE", "30"))
_booking_link_limiter = RateLimiter(max_requests=_BOOKING_LINK_LIMIT, window_seconds=60)

_DAILY_LIVE_LIMIT = int(os.environ.get("MAX_LIVE_SEARCHES_PER_DAY", "8"))
_live_pricing_limiter = RateLimiter(max_requests=_DAILY_LIVE_LIMIT, window_seconds=86400)
_GLOBAL_KEY = "global"


def enforce_search_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429s a client making too many search requests too fast."""
    if not _per_ip_limiter.allow(_client_key(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many search requests -- limit is {_PER_IP_LIMIT} per minute. Try again shortly.",
        )


def enforce_booking_link_rate_limit(request: Request) -> None:
    """Per-IP limit for the flight-booking-link endpoint -- see
    _booking_link_limiter's comment for why it is separate from search."""
    if not _booking_link_limiter.allow(_client_key(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many booking-link requests; try again in a minute.")


def live_pricing_allowed() -> bool:
    """
    Global (not per-client) daily budget gate for LIVE SerpApi pricing.
    Has a side effect (consumes one unit of the daily budget) when it
    returns True -- call it exactly once per request, and only when the
    caller has already confirmed the OTHER conditions for live pricing
    (a date was given, a key is configured), so a request that was
    never going to be live-priced anyway doesn't spend budget checking.
    """
    return _live_pricing_limiter.allow(_GLOBAL_KEY)


def clear_all() -> None:
    """Test helper."""
    _booking_link_limiter.clear()
    _per_ip_limiter.clear()
    _live_pricing_limiter.clear()
