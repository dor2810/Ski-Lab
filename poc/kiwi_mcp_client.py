"""
POC: Ski Lab as an MCP CLIENT, pulling flight data from Kiwi.com's
official hosted MCP server -- no scraping, no API key.

WHY THIS MATTERS TO THIS PROJECT: every live flight price today comes
from scraping Google Flights, which throttles our Cloud Run egress IP
under load (measured 2026-08-28: fare-stripped pages, null payloads)
and forced a SerpApi fallback. Kiwi's MCP server (https://mcp.kiwi.com,
no auth -- their own published integration channel) is a SUPPORTED way
to search flights programmatically. If this POC holds up, a
kiwi_mcp_adapter can join google_flights_adapter behind the same
FlightOption boundary type, and the scraper stops being a single point
of failure.

Booking.com ships the same idea for hotels
(https://demandapi-mcp.booking.com/v1/mcp/:affiliateId) but requires a
Demand API affiliate ID + OAuth -- the exact partner approval
adapters/accommodation_adapter.py has been waiting on -- so it is
documented here and testable the day that approval lands.

IMPLEMENTATION NOTE, learned the hard way: the official `mcp` Python
SDK's httpx/h11 transport rejects Kiwi's chunked encoding ("illegal
chunk header") and hangs. The protocol underneath is just JSON-RPC
POSTed over HTTP with SSE-framed responses, so this client speaks it
directly via `requests` (urllib3 tolerates the server's chunking).
Verified against the live server: initialize -> kiwicom-flight-search
1.28.1, tool `search-flight`.

Run: python3 poc/kiwi_mcp_client.py
"""
import json
import sys

import requests

KIWI_MCP_URL = "https://mcp.kiwi.com"
PROTOCOL_VERSION = "2025-03-26"
TIMEOUT_S = 60


def _parse_sse_json(body: str):
    """The last data: payload of an SSE-framed JSON-RPC response."""
    payloads = [line[len("data:"):].strip()
                for line in body.splitlines() if line.startswith("data:")]
    if not payloads:
        raise ValueError(f"no data: lines in response: {body[:200]!r}")
    return json.loads(payloads[-1])


class KiwiMcpClient:
    """Minimal streamable-HTTP MCP client -- enough protocol to
    initialize, list tools, and call one. Stateless server, so no
    session header handling is needed (verified: none is returned)."""

    def __init__(self, url: str = KIWI_MCP_URL):
        self.url = url
        self._id = 0
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })

    def _rpc(self, method: str, params: dict | None = None, notification: bool = False):
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notification:
            self._id += 1
            msg["id"] = self._id
        resp = self.session.post(self.url, data=json.dumps(msg), timeout=TIMEOUT_S)
        resp.raise_for_status()
        if notification or not resp.text.strip():
            return None
        data = _parse_sse_json(resp.text) if "text/event-stream" in resp.headers.get(
            "content-type", "") else resp.json()
        if "error" in data:
            raise RuntimeError(f"{method} -> {data['error']}")
        return data["result"]

    def initialize(self):
        result = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "ski-lab-poc", "version": "0.1"},
        })
        self._rpc("notifications/initialized", notification=True)
        return result

    def list_tools(self):
        return self._rpc("tools/list")["tools"]

    def call_tool(self, name: str, arguments: dict):
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


def main() -> int:
    client = KiwiMcpClient()

    info = client.initialize()
    server = info["serverInfo"]
    print(f"connected: {server['name']} {server['version']}")

    tools = client.list_tools()
    for t in tools:
        print(f"tool: {t['name']} -- {t.get('description', '').splitlines()[0][:90]}")

    search = next(t for t in tools if "search" in t["name"])
    props = search.get("inputSchema", {}).get("properties", {})
    print(f"\nsearch-flight parameters: {sorted(props)}\n")

    # Built after reading the ACTUAL declared schema (printed above) --
    # adjust here if the server evolves.
    args = {
        "flyFrom": "TLV", "flyTo": "GVA",
        "departureDate": "2027-01-09", "returnDate": "2027-01-15",
        "adults": 1, "currency": "EUR",
    }
    # Keep only what the schema actually declares, mapping common
    # variants so a rename doesn't silently drop a parameter.
    variants = {
        "flyFrom": ["flyFrom", "origin", "from", "source", "departure_airport"],
        "flyTo": ["flyTo", "destination", "to", "arrival_airport"],
        "departureDate": ["departureDate", "outbound_date", "date_from", "departure_date", "dateFrom"],
        "returnDate": ["returnDate", "inbound_date", "date_to", "return_date", "dateTo"],
        "adults": ["adults", "passengers", "adult_count"],
        "currency": ["currency", "curr"],
    }
    mapped = {}
    for value_key, names in variants.items():
        for name in names:
            if name in props:
                mapped[name] = args[value_key]
                break
    print(f"calling {search['name']} with {json.dumps(mapped)}")

    result = client.call_tool(search["name"], mapped)
    for item in result.get("content", [])[:3]:
        if item.get("type") == "text":
            print(item["text"][:3000])
            if len(item["text"]) > 3000:
                print("...[truncated]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
