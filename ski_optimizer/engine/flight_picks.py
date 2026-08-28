"""
Cheapest / Best / Fastest -- the curated flight picks.

WHY THIS EXISTS: a live search returns a page of itineraries, and the
first attempt at showing them ("cheapest N, plus the fastest") still
made the user read a list and do the comparison themselves. What a
tired person planning a ski trip actually wants is the three answers
every flight product already gives: the cheapest way, the fastest way,
and the sensible middle. Skyscanner's default sort is literally called
"Best" and is defined as the price-vs-convenience trade-off, with
Cheapest and Fastest as the other two sorts; Kayak exposes the same
triad (checked 2026-08-28). We deliberately reuse the convention
travellers already know rather than inventing labels.

NOT called "Luxury": we have no cabin-class data, so that word would
imply knowledge of the seat we don't have. Fastest is a fact.

One itinerary can hold several roles, and when it does it appears ONCE
with all of them -- on real routes the cheapest flight is often also
the fastest, and padding the list with strictly-worse options to make
it look fuller is exactly the kind of filler this module exists to
stop. That means the output is 1-3 picks, never more.

Pure selection maths over FlightOptions: no network, no adapter, fully
testable offline (tests/test_flight_picks.py).
"""
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ..models import FlightOption

ROLE_CHEAPEST = "cheapest"
ROLE_BEST = "best"
ROLE_FASTEST = "fastest"

# Price and journey time weighted equally in the "best" score. Any
# other split would be an invented exchange rate between money and
# hours -- Skyscanner tunes theirs from click data we don't have, and
# 50/50 is the only defensible default until we do.
_BEST_PRICE_WEIGHT = 0.5
_BEST_TIME_WEIGHT = 0.5


@dataclass(frozen=True)
class FlightPick:
    """One shown itinerary and every role it won."""
    option: FlightOption
    roles: Tuple[str, ...]


def _normalized(value: float, lowest: float, highest: float) -> float:
    """0.0 at the best end of the range, 1.0 at the worst; 0.0 when the
    range is a single point (all options equal on this axis)."""
    span = highest - lowest
    if span <= 0:
        return 0.0
    return (value - lowest) / span


def pick_flights(options: Sequence[FlightOption]) -> List[FlightPick]:
    """
    The 1-3 itineraries worth showing, cheapest first, each carrying
    the roles it won (ROLE_CHEAPEST / ROLE_BEST / ROLE_FASTEST).

    Ties break toward the option that is better on the OTHER axis: two
    flights at the same fare are not the same offer -- the one that
    lands sooner is strictly better and must be the one labelled
    cheapest (and vice versa for fastest).
    """
    if not options:
        return []

    cheapest = min(options, key=lambda o: (o.price_eur, o.total_duration_minutes))
    fastest = min(options, key=lambda o: (o.total_duration_minutes, o.price_eur))

    lowest_price = min(o.price_eur for o in options)
    highest_price = max(o.price_eur for o in options)
    shortest = min(o.total_duration_minutes for o in options)
    longest = max(o.total_duration_minutes for o in options)

    def best_score(o: FlightOption) -> float:
        return (_BEST_PRICE_WEIGHT * _normalized(o.price_eur, lowest_price, highest_price)
                + _BEST_TIME_WEIGHT * _normalized(o.total_duration_minutes, shortest, longest))

    best = min(options, key=lambda o: (best_score(o), o.price_eur, o.total_duration_minutes))

    # Merge roles onto shared winners rather than listing one flight
    # twice under two labels. Insertion order of the dict keeps the
    # first-seen option stable; the final sort is by price.
    roles_by_id: dict = {}
    for role, winner in ((ROLE_CHEAPEST, cheapest), (ROLE_BEST, best), (ROLE_FASTEST, fastest)):
        entry = roles_by_id.setdefault(id(winner), (winner, []))
        entry[1].append(role)

    picks = [FlightPick(option=opt, roles=tuple(roles)) for opt, roles in roles_by_id.values()]
    return sorted(picks, key=lambda p: (p.option.price_eur, p.option.total_duration_minutes))
