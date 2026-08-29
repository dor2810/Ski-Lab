"""
ONE ranked list of real airport-to-resort options, priced per person.

WHY THIS EXISTS (owner, 2026-08-29): "improve the UI of the transfer
results. to be like flight options... i want it to be as stable as the
flights", and, on the previous attempt, "you didnt update the transfer
price, you just added a tag that says there is a cheeper option."

Both criticisms have the same root cause: transfers were modelled as
ONE private quote plus a footnote, while flights were modelled as a
ranked LIST the user picks from. This module gives transfers the same
shape -- private hire (adapters/transfer_adapter, Alps2Alps) and
scheduled coach/train (adapters/omio_mcp_adapter) merged, compared on
one axis, and ranked -- so the cheapest can actually drive the cost
line instead of merely being mentioned.

COMPARABILITY IS THE WHOLE POINT: Alps2Alps prices a VEHICLE, Omio
prices SEATS. Every option here is already divided down to euros per
person by its adapter, which is the only basis on which a EUR423.50
minivan and a EUR57.62 coach seat can honestly sit in the same list.

Roles reuse the flight vocabulary (engine/flight_picks.py) on purpose:
travellers already read Cheapest/Fastest, and one option holding both
is shown ONCE with both badges rather than listed twice.

Pure ranking maths over plain dataclasses -- no network, no adapter
imports, fully testable offline.
"""
from dataclasses import dataclass, field, replace
from typing import List, Optional, Sequence

ROLE_CHEAPEST = "cheapest"
ROLE_FASTEST = "fastest"

#: How many rows are worth showing. Beyond this the list stops being a
#: choice and becomes a timetable dump -- Omio alone can return a dozen
#: near-identical departures for one coach route.
MAX_OPTIONS = 6


@dataclass(frozen=True)
class TransferOption:
    """
    One way of getting from the arrival airport to the resort.

    kind: "private" (a whole vehicle, your own schedule) or "scheduled"
    (a seat on a timetabled service). This is the trade-off the user is
    actually making, so it is a first-class field rather than something
    inferred from the mode string.
    """
    kind: str
    mode: str                       # minivan | bus | train | ferry
    price_eur_per_person: float
    duration_minutes: Optional[int] = None
    carrier: Optional[str] = None
    departure: Optional[str] = None       # ISO, provider-local
    booking_url: Optional[str] = None
    # True when the price covers BOTH legs (airport->resort and back).
    # Private quotes are round-trip; a scheduled seat usually is not,
    # and saying so is the difference between an honest comparison and
    # a flattering one.
    is_round_trip: bool = False
    roles: tuple = field(default_factory=tuple)
    # Which resort this option was fetched FOR. Carried so the caller
    # can prove an option belongs to the row it is about to be shown
    # on: production served Zermatt's SBB train (EUR118.12) on Val
    # Thorens rows, which has only buses. Root cause not yet isolated
    # -- it does not reproduce locally -- so this makes the failure
    # mode impossible to DISPLAY rather than merely unlikely, which is
    # this project's rule about wrong numbers.
    resort_name: Optional[str] = None
    # INDICATIVE options (Rome2Rio) are a price RANGE for the journey
    # with no date attached -- route discovery, not a quote. They exist
    # because they are the only thing that covers every resort, and
    # they must never be mistaken for the dated, bookable quotes.
    is_indicative: bool = False
    price_high_eur_per_person: Optional[float] = None


def _dedupe_key(option: TransferOption):
    """
    Same operator, same product, same price -- ONE row.

    Neither departure time nor DURATION is part of the key. Measured in
    production: Zermatt returned four SBB trains all at EUR118.12,
    lasting 240, 242, 262 and 468 minutes. They are one offer with
    several departures, and the 7h48 routing is strictly worse than the
    4h one -- listing all four turns a choice into a timetable dump.
    The representative kept is the FASTEST (see _better_of), because at
    an identical fare nobody wants the slower train.
    """
    return (option.kind, option.mode, round(option.price_eur_per_person, 2),
            option.carrier)


def _is_better(candidate: TransferOption, current: TransferOption) -> bool:
    """Among same-priced offers from one operator: shorter journey
    first, then earlier departure."""
    cand = (candidate.duration_minutes if candidate.duration_minutes is not None else 10**6,
            candidate.departure or "~")
    cur = (current.duration_minutes if current.duration_minutes is not None else 10**6,
           current.departure or "~")
    return cand < cur


def rank_transfer_options(options: Sequence[TransferOption]) -> List[TransferOption]:
    """
    Cheapest first, deduplicated, capped, with Cheapest/Fastest tagged.

    Ties break toward the shorter journey, matching flight_picks: two
    offers at the same fare are not the same offer, and the one that
    arrives sooner is strictly better.
    """
    if not options:
        return []

    seen = {}
    for option in options:
        key = _dedupe_key(option)
        # At an identical fare from the same operator, the FASTEST
        # journey represents the offer; ties fall back to the earliest
        # departure, the useful one for someone landing that morning.
        existing = seen.get(key)
        if existing is None or _is_better(option, existing):
            seen[key] = option
    unique = list(seen.values())

    # A bookable quote outranks an indicative range at equal price:
    # the range is the low end of a guess, and letting it take the
    # Cheapest badge would advertise a number nobody can actually pay.
    cheapest = min(unique, key=lambda o: (o.price_eur_per_person, o.is_indicative,
                                          o.duration_minutes or 10**6))
    timed = [o for o in unique if o.duration_minutes is not None]
    fastest = (min(timed, key=lambda o: (o.duration_minutes, o.price_eur_per_person))
               if timed else None)

    ranked = sorted(unique, key=lambda o: (o.price_eur_per_person,
                                           o.duration_minutes or 10**6))[:MAX_OPTIONS]
    # Make sure the fastest survives the cap -- it is one of the two
    # answers we promise to show.
    if fastest is not None and fastest not in ranked:
        ranked = ranked[:MAX_OPTIONS - 1] + [fastest]

    out = []
    for option in ranked:
        roles = []
        if option is cheapest:
            roles.append(ROLE_CHEAPEST)
        if fastest is not None and option is fastest:
            roles.append(ROLE_FASTEST)
        out.append(replace(option, roles=tuple(roles)))
    return out


def cheapest_price_eur_per_person(options: Sequence[TransferOption]) -> Optional[float]:
    """
    What the transfer line should SAY -- the cheapest real option we
    found, per person. None when we found nothing, so the caller keeps
    its estimate rather than inventing a free transfer.
    """
    if not options:
        return None
    return min(o.price_eur_per_person for o in options)
