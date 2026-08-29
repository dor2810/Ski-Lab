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
class GroundJourney:
    """One scheduled departure on one leg."""
    mode: str                     # "bus" | "train" | "ferry"
    price_eur_per_person: float
    departure: Optional[str] = None      # ISO, provider-local
    arrival: Optional[str] = None
    duration_minutes: Optional[int] = None
    carrier: Optional[str] = None
    booking_url: Optional[str] = None
    leg: str = "outbound"                # "outbound" | "inbound"


@dataclass(frozen=True)
class GroundQuote:
    """Cheapest scheduled service for one route/date, per person."""
    price_eur_per_person: float
    mode: str            # "bus" | "train" | "ferry"
    options_count: int   # how many departures the provider had
    # Omio's OWN signed deep link to this search's results page --
    # taken from the provider, never constructed by us. An earlier
    # hand-built URL (/search-frontend/results/<from>/<to>/<date>)
    # looked plausible and silently loaded Omio's generic landing page
    # with no route at all; the owner caught it in the live app. The
    # signed link carries an X-b2b-expire ~30 days out and is minted
    # fresh on every search, so it is always valid when clicked.
    booking_url: Optional[str] = None
    departure: Optional[str] = None   # ISO, provider's local time
    carrier: Optional[str] = None


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

    text = next((i.get("text") for i in result.get("content", [])
                 if i.get("type") == "text"), None)
    if text is None:
        raise AdapterError(f"Omio MCP: {tool} returned no text content")
    # A tool-level failure comes back as isError with a PLAIN-TEXT body,
    # not JSON. Parsing it blindly raised JSONDecodeError, which the
    # caller swallowed as "no service" -- so a real, diagnosable answer
    # ("DISCOVERY_ROUTE_NOT_FOUND": Omio's discovery index simply does
    # not carry this route) was being reported as an empty timetable.
    # Found while investigating why 23 of 32 resorts looked serviceless.
    if result.get("isError"):
        raise AdapterError(f"Omio MCP {tool}: {text[:200]}")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise AdapterError(f"Omio MCP {tool}: non-JSON reply: {text[:200]}") from exc


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
        # `results`, not `results_summary_cheapest`: the summary tool
        # returns prices per mode but NO link, and a transfer the user
        # cannot open is half a feature. This one call yields the
        # price, the departures, the carrier AND Omio's own signed
        # deep link.
        payload = _call_tool("results", {
            "fromId": from_id, "toId": to_id,
            "outboundDate": outbound_date,
            "adults": adults, "currency": currency, "locale": "en",
        })
    except Exception:
        logger.info("Omio ground quote unavailable for %s->%s on %s",
                    from_id, to_id, outbound_date, exc_info=True)
        return None

    data = (payload or {}).get("data") or {}
    journeys = [j for j in (data.get("outbound") or [])
                if j.get("mode") in _GROUND_MODES
                and (j.get("price") or {}).get("value")]
    if not journeys:
        # No scheduled service on this date. A real answer for an
        # out-of-season Alpine coach route -- never priced as free.
        return None

    cheapest = min(journeys, key=lambda j: j["price"]["value"])
    # Provider prices the WHOLE PARTY; the trip model is per person.
    per_person = round(float(cheapest["price"]["value"]) / adults, 2)
    same_mode = [j for j in journeys if j.get("mode") == cheapest.get("mode")]
    best = GroundQuote(
        price_eur_per_person=per_person,
        mode=cheapest.get("mode"),
        options_count=len(same_mode),
        # Prefer the whole-search link (all departures) over the single
        # journey's -- the user is choosing a time, not confirming one.
        booking_url=data.get("link") or cheapest.get("link"),
        departure=cheapest.get("dep"),
        carrier=(cheapest.get("carrier") or {}).get("name"),
    )

    if use_cache and best is not None:
        get_cache().set(key, best)
    return best


def _parse_minutes(dep: Optional[str], arr: Optional[str]) -> Optional[int]:
    """Journey length from the provider's own timestamps -- timezone
    aware, so a leg crossing an offset is not silently mis-measured."""
    if not dep or not arr:
        return None
    try:
        import datetime as _dt
        start = _dt.datetime.fromisoformat(dep)
        end = _dt.datetime.fromisoformat(arr)
        minutes = int((end - start).total_seconds() // 60)
        return minutes if minutes > 0 else None
    except (TypeError, ValueError):
        return None


def _journeys_from(block, adults: int, leg: str, fallback_link: Optional[str]):
    out = []
    for j in block or []:
        price = (j.get("price") or {}).get("value")
        mode = j.get("mode")
        if not price or mode not in _GROUND_MODES:
            continue
        out.append(GroundJourney(
            mode=mode,
            # Provider prices the WHOLE PARTY; the trip model is per person.
            price_eur_per_person=round(float(price) / adults, 2),
            departure=j.get("dep"), arrival=j.get("arr"),
            duration_minutes=_parse_minutes(j.get("dep"), j.get("arr")),
            carrier=(j.get("carrier") or {}).get("name"),
            booking_url=j.get("link") or fallback_link,
            leg=leg,
        ))
    return out


def search_ground_transport(from_id: int, to_id: int, outbound_date: str,
                            adults: int, inbound_date: Optional[str] = None,
                            currency: str = "EUR", use_cache: bool = True):
    """
    EVERY scheduled coach/train/ferry departure for this route, both
    legs -- {"outbound": [GroundJourney], "inbound": [...],
    "link": <round-trip search link>} -- or None when Omio has no such
    route.

    Round trip in ONE call: passing `inboundDate` returns an `inbound`
    array alongside `outbound` (verified live 2026-08-29, Geneva ->
    Val Thorens: 4 outbound and 7 inbound departures), and the signed
    link then covers the whole journey. Quoting only the outbound --
    which this adapter did at first -- prices half a trip and links to
    half a booking.

    Never raises: an unrouted pair or a provider outage returns None
    and the caller keeps whatever it had, labelled honestly.
    """
    if adults <= 0:
        raise AdapterError(f"adults must be > 0, got {adults}")

    key = f"omio:journeys:{from_id}:{to_id}:{outbound_date}:{inbound_date}:{adults}:{currency}"
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return cached

    args = {"fromId": from_id, "toId": to_id, "outboundDate": outbound_date,
            "adults": adults, "currency": currency, "locale": "en"}
    if inbound_date:
        args["inboundDate"] = inbound_date
    try:
        payload = _call_tool("results", args)
    except Exception as exc:
        # DISCOVERY_ROUTE_NOT_FOUND is the common one and it is a real
        # answer about coverage, not a transport failure -- logged at
        # info so it stays diagnosable without shouting.
        logger.info("Omio has no route %s->%s (%s): %s",
                    from_id, to_id, outbound_date, str(exc)[:160])
        return None

    data = (payload or {}).get("data") or {}
    link = data.get("link")
    result = {
        "outbound": _journeys_from(data.get("outbound"), adults, "outbound", link),
        "inbound": _journeys_from(data.get("inbound"), adults, "inbound", link),
        "link": link,
    }
    if not result["outbound"] and not result["inbound"]:
        return None
    if use_cache:
        get_cache().set(key, result)
    return result
