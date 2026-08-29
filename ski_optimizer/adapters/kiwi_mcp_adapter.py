"""
Flight search via Kiwi.com's official hosted MCP server -- the FREE
fallback behind the Google Flights scraper.

WHY: the Google adapter is a scraper of an undocumented payload, and
2026-08-28 measured both of its failure modes in production
(fare-stripped pages for our egress IP; routes whose January fares
simply aren't published on Google). Kiwi's MCP server
(https://mcp.kiwi.com -- no auth, no key, their own published
integration channel) is a SUPPORTED search API whose virtual-interline
inventory often prices routes Google can't. The engine calls this when
the scraper finds nothing, BEFORE the paid SerpApi fallback -- free
beats metered.

PROVENANCE: grown from poc/kiwi_mcp_client.py, verified live the same
day (kiwicom-flight-search 1.28.1; 15 real TLV->GVA itineraries,
EUR280-336, each with per-segment carriers, flight numbers, and a
working kiwi.com booking deep link). tests/fixtures/kiwi_tlv_gva.json
is one of those live responses, captured as the offline parsing
fixture.

TRANSPORT NOTE, learned the hard way: the official `mcp` Python SDK's
httpx/h11 stack rejects this server's chunked encoding ("illegal chunk
header") and hangs. The protocol underneath is JSON-RPC POSTed over
HTTP with SSE-framed responses, so this module speaks it directly via
`requests` (urllib3 tolerates the chunking). Stateless server --
verified no session header is issued -- so each search is
initialize + call in one short-lived requests.Session.

Same boundary contract as every flight adapter: FlightOption /
FlightSearchResult out, AdapterError on total failure, one bad
itinerary dropped rather than fatal, response-cached.
"""
import datetime
import json
import logging
from typing import List, Optional

import requests

from ..models import FlightOption, FlightSearchResult
from .base import AdapterError
from .response_cache import get_cache

logger = logging.getLogger(__name__)

KIWI_MCP_URL = "https://mcp.kiwi.com"
PROTOCOL_VERSION = "2025-03-26"
_TIMEOUT_S = 45
_SEARCH_TOOL = "search-flight"


def _parse_sse_json(body: str) -> dict:
    """Last data: payload of an SSE-framed JSON-RPC response."""
    payloads = [line[len("data:"):].strip()
                for line in body.splitlines() if line.startswith("data:")]
    if not payloads:
        raise AdapterError(f"Kiwi MCP: no data frame in response: {body[:120]!r}")
    return json.loads(payloads[-1])


def _call_search_tool(arguments: dict) -> dict:
    """One MCP round trip: initialize, notify, call search-flight.
    Returns the tool's decoded JSON payload. Module-level so tests (and
    the engine's own tests) can stub the transport in one place."""
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
        resp = session.post(KIWI_MCP_URL, data=json.dumps(msg), timeout=_TIMEOUT_S)
        resp.raise_for_status()
        if notification:
            return None
        data = (_parse_sse_json(resp.text)
                if "text/event-stream" in resp.headers.get("content-type", "")
                else resp.json())
        if "error" in data:
            raise AdapterError(f"Kiwi MCP {method}: {data['error']}")
        return data["result"]

    rpc("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "ski-lab", "version": "1.0"},
    }, msg_id=1)
    rpc("notifications/initialized", notification=True)
    result = rpc("tools/call", {"name": _SEARCH_TOOL, "arguments": arguments}, msg_id=2)

    for item in result.get("content", []):
        if item.get("type") == "text":
            return json.loads(item["text"])
    raise AdapterError("Kiwi MCP: tool result carried no text content")


def _format_flight_number(segment: dict) -> Optional[str]:
    """Kiwi writes 'LX253'; the whole project (and every departure
    board) writes 'LX 253'. Normalized so the frontend and the
    booking-link matcher see one format."""
    raw = segment.get("flightNumber") or ""
    carrier = segment.get("carrier") or ""
    if raw.startswith(carrier) and carrier and len(raw) > len(carrier):
        return f"{carrier} {raw[len(carrier):]}"
    return raw or None


def _parse_iso_datetime(raw) -> Optional[datetime.datetime]:
    """Kiwi's '2027-01-10T08:30:00' -> datetime, or None for anything
    unparseable. A missing landing time must degrade to 'unknown' (the
    caller then falls back to a documented assumed pickup), never to a
    fabricated one."""
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _parse_itinerary(it: dict) -> Optional[FlightOption]:
    """One itinerary -> FlightOption, or None for anything malformed --
    one bad entry must never sink the whole search (house style, see
    google_flights_adapter._parse_flight_result)."""
    try:
        price = float(it["price"])
        outbound = it["outbound"]
        origin = outbound["from"]
        destination = outbound["to"]
        if price <= 0 or not origin or not destination:
            return None

        # The provider's own end-to-end total -- timezone-correct by
        # construction, the exact trap the Google adapter fell into
        # when it subtracted local clocks (understated every westbound
        # journey by the TLV/CET offset).
        duration_minutes = int(it["totalDurationSeconds"]) // 60

        segments = outbound.get("segments", [])
        carriers = list(dict.fromkeys(
            s.get("carrierName") or s.get("carrier") or "" for s in segments if s))
        carriers = [c for c in carriers if c]
        airline = (carriers[0] if len(carriers) == 1
                   else " + ".join(carriers[:2]) if carriers else "Unknown")

        numbers = [n for n in (_format_flight_number(s) for s in segments) if n]

        return FlightOption(
            price_eur=price,
            origin_airport=origin,
            destination_airport=destination,
            airline=airline,
            total_duration_minutes=duration_minutes,
            stops=int(outbound.get("stops", max(0, len(segments) - 1))),
            is_round_trip="inbound" in it,
            # Kiwi hands over a REAL booking deep link per itinerary --
            # no second fetch, no reverse-engineered protobuf. Stored in
            # the opaque provider slot exactly as FlightOption's
            # docstring prescribes.
            booking_token=it.get("bookingUrl"),
            flight_numbers=numbers,
            # Landing time, local at the destination -- what the airport
            # transfer is actually booked around (see FlightOption.
            # arrival_time). Kiwi gives it directly on the outbound leg;
            # a malformed one degrades to None rather than sinking the
            # whole itinerary, same as every other field here.
            arrival_time=_parse_iso_datetime(outbound.get("arrivalTime")),
            # The return leg's DEPARTURE -- what the homeward transfer
            # has to be built around (see FlightOption).
            return_departure_time=_parse_iso_datetime(
                (it.get("inbound") or {}).get("departureTime")),
            return_duration_minutes=(
                int((it.get("inbound") or {}).get("durationSeconds") or 0) // 60
                or None),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _cache_key(*parts) -> str:
    return "kiwi_mcp:" + "|".join(str(p) for p in parts)


def search_flights(
    origin_airport: str,
    destination_airports,
    outbound_date: datetime.date,
    return_date: Optional[datetime.date] = None,
    adults: int = 1,
    max_connections: Optional[int] = 1,
    currency: str = "EUR",
    use_cache: bool = True,
) -> FlightSearchResult:
    """Same public contract as the other flight adapters (see
    flight_adapter.search_flights). Multi-airport resorts are searched
    in one call -- Kiwi's flyTo accepts a comma-separated list."""
    if isinstance(destination_airports, str):
        destination_airports = [destination_airports]
    destination_airports = [d.strip().upper() for d in destination_airports if d and d.strip()]
    if not destination_airports:
        raise AdapterError("No destination airports supplied")

    key = _cache_key(origin_airport, ",".join(destination_airports), outbound_date,
                     return_date, adults, max_connections, currency)
    if use_cache:
        cached = get_cache().get(key)
        if cached is not None:
            return FlightSearchResult(options=cached.options, from_cache=True)

    args = {
        "flyFrom": origin_airport.strip().upper(),
        "flyTo": ",".join(destination_airports),
        "departureDate": outbound_date.isoformat(),
        "adults": adults,
        "currency": currency,
    }
    if return_date is not None:
        args["returnDate"] = return_date.isoformat()
    if max_connections is not None:
        # Kiwi's own name for exactly our max-connections preference.
        args["max_sector_stopovers"] = max_connections

    try:
        payload = _call_search_tool(args)
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError(f"Kiwi MCP search failed: {exc}") from exc

    options: List[FlightOption] = []
    for it in payload.get("itineraries", []):
        parsed = _parse_itinerary(it)
        if parsed is not None:
            options.append(parsed)

    result = FlightSearchResult(options=options)
    if use_cache:
        get_cache().set(key, result)
    return result


def cheapest_price_eur(result: FlightSearchResult) -> Optional[float]:
    if not result.options:
        return None
    return min(o.price_eur for o in result.options)
