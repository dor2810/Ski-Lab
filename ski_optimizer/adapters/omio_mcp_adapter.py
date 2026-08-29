"""
Scheduled ground transport (coach / train / ferry) via Omio's hosted
MCP server -- the CHEAP alternative to Alps2Alps' private minivans.

WHY: Alps2Alps' public API sells only private vehicles. Measured
2026-08-29, Geneva Airport -> Val Thorens on the same date for two
people: private minivan EUR423.50 PER PERSON, scheduled coach EUR57.62
per person, with nine departures available. The owner's verdict on the
private-only status quo was blunt and correct -- "i am not satisfied
with the alps2alps" -- and this is the missing cheap option.

HOW THIS PROVIDER WAS FOUND (worth recording, because the obvious
reading was wrong): mcpmarket.com lists Omio as a *WebMCP* -- tools a
site exposes to an agent running inside a BROWSER via
`navigator.modelContext`, with no callable endpoint. That looked
un-integrable for a Python backend, and it was reported as such.
The owner pushed back -- "can't we write some python code that
searches the browser and then uses the mcp?" -- which was right: a
headless browser with an injected agent-side shim proved the tools are
real, and intercepting the page's network showed those tools are thin
proxies for a PLAIN HOSTED MCP SERVER at llm-apps.omio.ai/mcp.
So no browser is needed in production at all. The lesson is recorded
rather than tidied away: "the listing says browser-only" was an
assumption, and testing it cost one afternoon and saved a 7x price
error on every transfer we quote.

ACCESS: keyless, no signup, no account. Server self-identifies as
"discovery-mcp" 1.0.2. Same JSON-RPC-over-HTTP-with-SSE transport as
adapters/kiwi_mcp_adapter.py, and for the same reason -- the official
`mcp` Python SDK's httpx/h11 stack chokes on this framing, while
`requests`/urllib3 tolerates it.

WHAT THIS IS NOT: a door-to-door quote. These are STATION-TO-STATION
scheduled services (airport coach bay to resort bus station), so they
carry timetable constraints a private transfer does not -- which is
exactly why both are shown rather than one silently replacing the
other. Prices arrive in CENTS for the WHOLE PARTY.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from .base import AdapterError
from .response_cache import get_cache

logger = logging.getLogger(__name__)

OMIO_MCP_URL = "https://llm-apps.omio.ai/mcp"
PROTOCOL_VERSION = "2025-03-26"
_TIMEOUT_S = 45

#: Modes worth quoting for an airport->resort leg. "flight" is
#: excluded deliberately: the trip already HAS a flight, and a second
#: one between the arrival airport and the resort is never the transfer
#: a skier means.
_GROUND_MODES = ("bus", "train", "ferry")


@dataclass(frozen=True)
class GroundQuote:
    """Cheapest scheduled service for one route/date, per person."""
    price_eur_per_person: float
    mode: str            # "bus" | "train" | "ferry"
    options_count: int   # how many departures the provider had


def _parse_sse_json(body: str) -> dict:
    """Last data: payload of an SSE-framed JSON-RPC response."""
    payloads = [line[len("data:"):].strip()
                for line in body.splitlines() if line.startswith("data:")]
    if not payloads:
        raise AdapterError(f"Omio MCP: no data frame in response: {body[:120]!r}")
    return json.loads(payloads[-1])


def _call_tool(tool: str, arguments: dict) -> dict:
    """One MCP round trip: initialize, notify, call. Module-level so
    tests stub the transport in exactly one place (house style, see
    kiwi_mcp_adapter._call_search_tool)."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })

    def rpc(method, params=None, notification=False, msg_id=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notification:
            msg["id"] = msg_id
        resp = session.post(OMIO_MCP_URL, data=json.dumps(msg), timeout=_TIMEOUT_S)
        resp.raise_for_status()
        if notification:
            return None
        data = (_parse_sse_json(resp.text)
                if "text/event-stream" in resp.headers.get("content-type", "")
                else resp.json())
        if "error" in data:
            raise AdapterError(f"Omio MCP {method}: {data['error']}")
        return data["result"]

    rpc("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "ski-lab", "version": "1.0"},
    }, msg_id=1)
    rpc("notifications/initialized", notification=True)
    result = rpc("tools/call", {"name": tool, "arguments": arguments}, msg_id=2)

    for item in result.get("content", []):
        if item.get("type") == "text":
            return json.loads(item["text"])
    raise AdapterError(f"Omio MCP: {tool} returned no text content")


def resolve_positions(from_term: str, to_term: str, locale: str = "en") -> Optional[dict]:
    """
    Free-text place names -> Omio's own numeric position ids, or None
    when it recognises neither end. Ids are stable (a station does not
    move), which is why scripts/build_omio_positions.py freezes them
    into data/omio_positions.py rather than resolving per search.
    """
    try:
        payload = _call_tool("resolve_positions", {
            "fromTerm": from_term, "toTerm": to_term, "locale": locale})
    except Exception:
        logger.warning("Omio position resolution failed for %r -> %r",
                       from_term, to_term, exc_info=True)
        return None
    suggestion = (payload or {}).get("suggestion") or {}
    try:
        return {"from_id": int(suggestion["fromId"]), "to_id": int(suggestion["toId"])}
    except (KeyError, TypeError, ValueError):
        return None


def cheapest_ground_transport(from_id: int, to_id: int, outbound_date: str,
                              adults: int, currency: str = "EUR",
                              use_cache: bool = True) -> Optional[GroundQuote]:
    """
    Cheapest scheduled coach/train/ferry for this route and date, per
    person -- or None when the provider runs no service (which is a
    real answer for a remote resort, not a failure).

    Never raises: a provider outage degrades to None and the caller
    keeps whatever it had, honestly labelled. Same contract as every
    other adapter here.
    """
    if adults <= 0:
        raise AdapterError(f"adults must be > 0, got {adults}")

    key = f"omio:{from_id}:{to_id}:{outbound_date}:{adults}:{currency}"
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    try:
        payload = _call_tool("results_summary_cheapest", {
            "fromId": from_id, "toId": to_id,
            "outboundDateStart": outbound_date, "outboundDateEnd": outbound_date,
            "adults": adults, "currency": currency, "locale": "en",
        })
    except Exception:
        logger.info("Omio ground quote unavailable for %s->%s on %s",
                    from_id, to_id, outbound_date, exc_info=True)
        return None

    by_date = ((payload or {}).get("data") or {}).get("data") or {}
    day = by_date.get(outbound_date) or {}

    best: Optional[GroundQuote] = None
    for mode in _GROUND_MODES:
        entry = day.get(mode) or {}
        cents = entry.get("priceCents") or 0
        count = entry.get("numberOfResults") or 0
        # priceCents 0 with no results means NO SERVICE, not "free" --
        # pricing that as EUR0 would invent a free transfer, which is
        # exactly the fabrication this project forbids.
        if cents <= 0 or count <= 0:
            continue
        per_person = round(cents / 100 / adults, 2)
        if best is None or per_person < best.price_eur_per_person:
            best = GroundQuote(price_eur_per_person=per_person, mode=mode,
                               options_count=int(count))

    if use_cache and best is not None:
        get_cache().set(key, best)
    return best


def booking_url(from_id: int, to_id: int, outbound_date: str, adults: int) -> str:
    """
    Omio's own dated search page for this route -- a real, working link
    for the journey we priced. Deliberately their normal search URL and
    not the signed partner deep link the MCP returns: those carry an
    embedded partner JWT with an expiry, and a link that dies silently
    is worse than one that always works.
    """
    return (f"https://www.omio.com/search-frontend/results/"
            f"{from_id}/{to_id}/{outbound_date}?adults={adults}")
