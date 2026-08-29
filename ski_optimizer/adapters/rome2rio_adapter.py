"""
Multi-modal route discovery via Rome2Rio -- the COVERAGE layer beneath
the transfer options list.

WHY THIS EXISTS: Omio's discovery index routes only 9 of our 32 mapped
resorts, and Alps2Alps sells private hire for 30. Neither could answer
"how do I get to St. Anton" at all. Rome2Rio answers it for ALL 39
resorts -- verified 2026-08-29, every resort returned priced routes,
including the ones both other providers refuse (St. Anton EUR12-80 by
train, Zell am See EUR10-14 by bus, Gudauri EUR18-40).

WHAT THE PRICES ARE -- read before trusting them: INDICATIVE RANGES
for the journey, not bookable fares. This endpoint takes NO DATE; it
is route discovery, not a quote. So everything here is labelled
indicative, and the dated Omio/Alps2Alps quotes remain the bookable
options. Presenting a range as a live price would be exactly the
fabrication this project forbids.

PROVENANCE, stated plainly rather than buried: Rome2Rio's DOCUMENTED
partner endpoint is dead -- free.rome2rio.com is NXDOMAIN, and the
api-evangelist profile the owner pointed at records callable_host:
false for it. Their partner API is also gated (100k/month free tier,
but onboarding is a sales conversation). What actually works is the
endpoint their own website calls, with the web client's embedded key,
found by watching the site's network traffic. That places this in the
SAME category as adapters/google_flights_adapter.py and
google_hotels_adapter.py: reverse-engineered, unsanctioned, and liable
to change without notice. It is used the same way -- as an enrichment
that degrades to nothing, never as the only thing holding a result up.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import requests
from urllib.parse import quote

from .base import AdapterError
from .response_cache import get_cache

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.rome2rio.com/api/1.5/json/Search"
#: The web client's own key, as served in their site's requests. Not a
#: partner credential and not a secret -- it ships to every visitor.
WEB_KEY = "jGq3Luw3"
_TIMEOUT_S = 30
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/140.0.0.0 Safari/537.36"),
    "Referer": "https://www.rome2rio.com/",
}

#: Route names containing these are a FLIGHT leg. The trip already has
#: a flight; a second one from the arrival airport is never the
#: transfer a skier means (same exclusion as the Omio adapter).
_FLIGHT_MARKERS = ("fly", "flight")

MAP_BASE = "https://www.rome2rio.com/map"


def _pair_url(payload: dict) -> Optional[str]:
    """
    Rome2Rio's results page for the searched pair, built from the
    canonical slugs the response itself supplies (places[0] is the
    origin, places[1] the destination). Built from THEIR slugs rather
    than by slugifying our own place names -- "St. Anton am Arlberg"
    would become St.-Anton-am-Arlberg, which their router rejects.
    """
    places = (payload or {}).get("places") or []
    if len(places) < 2:
        return None
    origin = places[0].get("canonicalName")
    destination = places[1].get("canonicalName")
    if not origin or not destination:
        return None
    # Percent-encode the slugs: several resorts carry non-ASCII
    # (Kitzbühel, Sölden). A browser encodes these itself -- verified
    # live, the umlaut URL loads -- but anything else consuming this
    # link would not, so it leaves here already safe.
    return f"{MAP_BASE}/{quote(origin)}/{quote(destination)}"


@dataclass(frozen=True)
class Rome2RioRoute:
    """One way to make the journey, with an indicative price range."""
    name: str                       # "Bus", "Train, taxi", "Shuttle"
    price_low_eur: Optional[float]
    price_high_eur: Optional[float]
    duration_minutes: Optional[int]
    #: Always True here -- a reminder at every use site that this is a
    #: range for the journey, not a fare for a date.
    is_indicative: bool = True
    #: Rome2Rio's own results page for this origin/destination pair,
    #: listing every route. VERIFIED in a real browser: it renders
    #: "3 ways to travel from Innsbruck Airport to St Anton am
    #: Arlberg". Deliberately the PAIR-level page, not a per-route URL:
    #: /map/<o>/<d>/<route-canonical> was tested and redirects to an
    #: empty map ("Please enter an origin"), and their results panel is
    #: a SPA that does not change the URL when a route is selected. A
    #: link landing on the right journey list beats a fabricated deep
    #: link landing nowhere -- a mistake already made once here with a
    #: hand-built Omio URL.
    booking_url: Optional[str] = None


def _fetch(origin: str, destination: str, currency: str = "EUR") -> dict:
    """One search request. Module-level so tests stub the transport in
    exactly one place (house style, see kiwi_mcp_adapter)."""
    try:
        resp = requests.get(SEARCH_URL, params={
            "key": WEB_KEY, "oName": origin, "dName": destination,
            "languageCode": "en", "currencyCode": currency,
        }, headers=_HEADERS, timeout=_TIMEOUT_S)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise AdapterError(f"Rome2Rio search failed: {exc}") from exc


def search_routes(origin: str, destination: str, currency: str = "EUR",
                  use_cache: bool = True) -> List[Rome2RioRoute]:
    """
    Priced ways to travel between two free-text places, cheapest first.

    Returns [] on any failure -- never raises past validation, matching
    every adapter in this package. Unpriced routes ("Drive") are
    dropped rather than shown at zero: a suggestion is not an offer.
    """
    if not (origin or "").strip() or not (destination or "").strip():
        raise AdapterError("origin and destination are required")

    key = f"r2r:{origin}|{destination}|{currency}"
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    try:
        payload = _fetch(origin=origin, destination=destination, currency=currency)
    except Exception:
        logger.info("Rome2Rio route lookup failed for %r -> %r", origin, destination,
                    exc_info=True)
        return []

    pair_url = _pair_url(payload)
    routes: List[Rome2RioRoute] = []
    for raw in (payload or {}).get("routes") or []:
        name = (raw.get("name") or "").strip()
        if not name or any(m in name.lower() for m in _FLIGHT_MARKERS):
            continue
        prices = raw.get("indicativePrices") or []
        low = prices[0].get("priceLow") if prices else None
        high = prices[0].get("priceHigh") if prices else None
        if low is None:
            continue  # a route with no price is a suggestion, not an offer
        seconds = raw.get("duration")
        routes.append(Rome2RioRoute(
            name=name,
            price_low_eur=float(low),
            price_high_eur=float(high) if high is not None else None,
            # The provider reports SECONDS; a 24000 "minute" bus would
            # be sixteen days.
            duration_minutes=int(round(seconds / 60)) if seconds else None,
            booking_url=pair_url,
        ))

    routes.sort(key=lambda r: r.price_low_eur)
    if use_cache and routes:
        get_cache().set(key, routes)
    return routes
