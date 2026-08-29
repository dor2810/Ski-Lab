"""
Omio ground-transport pricing via their hosted MCP server.

WHY THIS EXISTS (owner, 2026-08-29): "i am not satisfied with the
alps2alps" -- their public API sells only PRIVATE vehicles, and a
Geneva->Val Thorens minivan quoted EUR423.50 per person while a
scheduled coach on the same route costs EUR57.62 per person. The cheap
option existed; we just had no way to price it.

HOW IT WAS FOUND, because the route matters: the owner asked about
mcpmarket.com/server/omio, which lists a *WebMCP* -- browser-side
tools, not a callable endpoint. Driving a headless browser with an
injected `navigator.modelContext` shim (the owner's own suggestion)
proved the tools were real, and intercepting the network showed those
tools were thin proxies for a PLAIN HOSTED MCP SERVER at
llm-apps.omio.ai/mcp. So no browser is needed at all -- this adapter
speaks JSON-RPC to it exactly as kiwi_mcp_adapter speaks to Kiwi.

Keyless, no signup, server identifies itself as "discovery-mcp".
Tools used: resolve_positions (free text -> stable position ids) and
results_summary_cheapest (cheapest fare per travel mode over a date
range). Prices come back in CENTS for the WHOLE PARTY.
"""
import pytest

from ski_optimizer.adapters import omio_mcp_adapter as omio
from ski_optimizer.adapters.base import AdapterError

SIGNED_LINK = "https://www.omio.com/links/eyJhbGciOiJIUzI1NiJ9.stub.sig"


def _journey(mode, price, dep="2027-01-16T13:15:00+01:00", carrier="Alpine Fleet"):
    return {"mode": mode, "price": {"value": price, "currency": "EUR"},
            "dep": dep, "arr": "2027-01-16T16:30:00+01:00",
            "carrier": {"name": carrier},
            "link": "https://www.omio.com/links/per-journey"}


# Shape of a real `results` response (captured live 2026-08-29).
CHEAPEST_PAYLOAD = {
    "endpoint": "/discovery/results",
    "data": {
        "from": "Genève airport", "to": "Gare Routiere - Val Thorens",
        "link": SIGNED_LINK,
        "outbound": [_journey("bus", 115.24), _journey("bus", 130.0),
                     # A flight between airport and resort is never the
                     # transfer a skier means -- must be ignored even
                     # when it is the cheapest row.
                     _journey("flight", 9.99)],
    },
}


def test_cheapest_ground_option_is_parsed_per_person(monkeypatch):
    monkeypatch.setattr(omio, "_call_tool", lambda *a, **k: CHEAPEST_PAYLOAD)
    quote = omio.cheapest_ground_transport(
        from_id=314520, to_id=440470, outbound_date="2027-01-16", adults=2,
        use_cache=False)
    assert quote is not None
    # 11524 cents for the whole party of 2 -> 57.62 each.
    assert quote.price_eur_per_person == 57.62
    assert quote.mode == "bus"
    assert quote.options_count == 2
    # The link must be the PROVIDER's signed one -- a hand-built URL
    # silently loaded Omio's generic landing page (owner-reported).
    assert quote.booking_url == SIGNED_LINK
    assert quote.carrier == "Alpine Fleet"


def test_a_flight_leg_is_never_offered_as_the_transfer(monkeypatch):
    # The trip already HAS a flight; a second one from the arrival
    # airport is never what "transfer" means -- even at EUR9.99.
    monkeypatch.setattr(omio, "_call_tool", lambda *a, **k: CHEAPEST_PAYLOAD)
    quote = omio.cheapest_ground_transport(
        from_id=1, to_id=2, outbound_date="2027-01-16", adults=2, use_cache=False)
    assert quote.mode == "bus" and quote.price_eur_per_person == 57.62


def test_no_service_at_all_returns_none(monkeypatch):
    # Out-of-season Alpine coach routes genuinely return nothing --
    # verified live (Val Thorens has no service on 2026-12-08 but does
    # on 2027-01-16). Must never be priced as free.
    empty = {"data": {"from": "x", "to": "y", "link": SIGNED_LINK, "outbound": []}}
    monkeypatch.setattr(omio, "_call_tool", lambda *a, **k: empty)
    assert omio.cheapest_ground_transport(
        from_id=1, to_id=2, outbound_date="2027-01-16", adults=2, use_cache=False) is None


def test_provider_failure_degrades_to_none_never_raises(monkeypatch):
    def _boom(*a, **k):
        raise AdapterError("omio unreachable")
    monkeypatch.setattr(omio, "_call_tool", _boom)
    assert omio.cheapest_ground_transport(
        from_id=1, to_id=2, outbound_date="2027-01-16", adults=2, use_cache=False) is None


def test_cheapest_across_modes_wins(monkeypatch):
    payload = {"data": {"link": SIGNED_LINK,
                        "outbound": [_journey("bus", 115.24), _journey("train", 80.0)]}}
    monkeypatch.setattr(omio, "_call_tool", lambda *a, **k: payload)
    quote = omio.cheapest_ground_transport(
        from_id=1, to_id=2, outbound_date="2027-01-16", adults=2, use_cache=False)
    assert quote.mode == "train" and quote.price_eur_per_person == 40.0


def test_adults_must_be_positive():
    with pytest.raises(AdapterError):
        omio.cheapest_ground_transport(
            from_id=1, to_id=2, outbound_date="2027-01-16", adults=0)


def test_sse_framed_response_is_decoded():
    # The server answers text/event-stream, same as Kiwi's -- the
    # transport must read the LAST data: frame, not the raw body.
    body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    assert omio._parse_sse_json(body)["result"] == {"ok": True}


def test_frozen_positions_cover_most_resorts():
    from ski_optimizer.data.omio_positions import OMIO_POSITIONS, UNRESOLVED
    assert len(OMIO_POSITIONS) >= 25
    for name, pos in OMIO_POSITIONS.items():
        assert isinstance(pos["from_id"], int) and pos["from_id"] > 0, name
        assert isinstance(pos["to_id"], int) and pos["to_id"] > 0, name
        assert name not in UNRESOLVED
