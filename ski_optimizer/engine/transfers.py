"""
Airport-to-resort transfer selection.

Replaces the old distance formula in cost_calculator, which divided a
distance-based figure by group_size ** 0.3 -- a fudge matching no real
pricing structure. Reality splits cleanly in two:

  per_person  (shared shuttle, train, bus): total scales with headcount
  per_vehicle (private transfer, taxi, car): total is flat; per-person
                                             cost falls with group size

Which one wins is ROUTE-DEPENDENT, not a general rule. Measured against
the researched data: on Geneva->Val Thorens the shared shuttle stays
cheapest all the way to 8 people (EUR50pp vs EUR52.50pp private),
because Geneva's shuttle market is competitive. On Innsbruck->Obergurgl
private wins from 6 people (EUR37pp vs EUR39pp). A formula cannot know
that; only data can. Hence this module reads a curated table.

DESIGN DECISIONS (all confirmed with the project owner):
  - Multi-vehicle: a group larger than one vehicle books ceil(n/cap)
    vehicles rather than being refused. Ski groups of 8-12 are common.
  - Round trips: operator quotes are stored EXACTLY as published, with
    an is_round_trip flag. One-way prices are never doubled to fake a
    return, because return legs are frequently discounted -- Ben's Bus
    Val Thorens is GBP49 one-way but GBP94 return, not GBP98. Doubling
    would systematically overstate.
  - Transfer mode is a user preference (see UserPreferences.
    preferred_transfer_modes): some people will not share a shuttle,
    some will not drive abroad in winter.
  - Availability is modelled, not assumed. Four routes in the researched
    data run weekends- or Saturdays-only. That was a footnote for
    fixed-date search; for date-range search, which compares dozens of
    candidate start dates, pricing a Tuesday against a shuttle that does
    not run that day is simply wrong.
"""
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import openpyxl

DEFAULT_TRANSFER_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "transfer_options.xlsx"
)
HEADER_ROW = 4

# Python's date.weekday(): Monday=0 ... Sunday=6
_DAY_CODES = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

PER_PERSON = "per_person"
PER_VEHICLE = "per_vehicle"


@dataclass
class TransferOption:
    airport_iata: str
    resort_name: str
    mode: str
    cost_eur: float
    cost_basis: str            # per_person | per_vehicle
    vehicle_capacity: Optional[int]
    duration_minutes: float
    is_round_trip: bool
    is_mandatory: bool         # true where no alternative exists (Zermatt rail)
    runs_on_days: str          # "daily" or e.g. "SA,SU"
    operator: str
    data_quality: str          # sourced | sourced_conflicting | estimated
    source_note: str

    def runs_on(self, travel_date) -> bool:
        """Whether this service operates on a given date."""
        if not self.runs_on_days or self.runs_on_days.strip().lower() == "daily":
            return True
        if travel_date is None:
            return True  # no date supplied -> don't filter
        allowed = {
            _DAY_CODES[code.strip().upper()]
            for code in self.runs_on_days.split(",")
            if code.strip().upper() in _DAY_CODES
        }
        return not allowed or travel_date.weekday() in allowed

    def vehicles_needed(self, group_size: int) -> int:
        if self.cost_basis != PER_VEHICLE:
            return 1
        capacity = self.vehicle_capacity or group_size
        return max(1, math.ceil(group_size / capacity))

    def cost_per_person(self, group_size: int) -> float:
        """
        Per-person cost for this group size.

        NOTE: returns the cost AS QUOTED -- if is_round_trip is False
        this is a one-way figure. Callers wanting a round trip must use
        round_trip_cost_per_person, which is explicit about the
        assumption it makes.
        """
        if group_size <= 0:
            raise ValueError(f"group_size must be > 0, got {group_size}")
        if self.cost_basis == PER_PERSON:
            return self.cost_eur
        return self.cost_eur * self.vehicles_needed(group_size) / group_size

    def round_trip_cost_per_person(self, group_size: int) -> float:
        """
        Round-trip per-person cost.

        When the stored quote is already a round trip, it is used as-is.
        When it is one-way, it is doubled -- and that IS an approximation:
        real return fares are often discounted (Ben's Bus Val Thorens:
        GBP49 one-way, GBP94 return, not GBP98). Doubling therefore tends
        to OVERSTATE slightly. Preferred to understating, and the fix is
        to research round-trip quotes rather than to guess a discount.
        """
        one_way = self.cost_per_person(group_size)
        return one_way if self.is_round_trip else one_way * 2


def _parse_bool(value) -> bool:
    return str(value).strip().lower() in ("yes", "true", "1")


def load_transfer_options(path: Path = DEFAULT_TRANSFER_PATH) -> List[TransferOption]:
    """Loads the curated transfer table. Returns [] if the file is absent."""
    if not Path(path).exists():
        return []
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["TransferOptions"]

    options = []
    for row in ws.iter_rows(min_row=HEADER_ROW + 1, values_only=True):
        if not row or row[0] is None:
            continue
        (airport, resort, mode, cost, basis, capacity, duration,
         round_trip, mandatory, runs_on, operator, quality, note) = row[:13]
        options.append(TransferOption(
            airport_iata=str(airport).strip().upper(),
            resort_name=str(resort).strip(),
            mode=str(mode).strip(),
            cost_eur=float(cost),
            cost_basis=str(basis).strip(),
            vehicle_capacity=int(capacity) if capacity is not None else None,
            duration_minutes=float(duration),
            is_round_trip=_parse_bool(round_trip),
            is_mandatory=_parse_bool(mandatory),
            runs_on_days=str(runs_on).strip() if runs_on else "daily",
            operator=str(operator or "").strip(),
            data_quality=str(quality or "estimated").strip(),
            source_note=str(note or "").strip(),
        ))
    return options


def options_for(options: List[TransferOption], resort_name: str,
                airport_iata: Optional[str] = None) -> List[TransferOption]:
    """All options for a resort, optionally restricted to one airport."""
    target = resort_name.strip().lower()
    out = [o for o in options if o.resort_name.strip().lower() == target]
    if airport_iata:
        code = airport_iata.strip().upper()
        out = [o for o in out if o.airport_iata == code]
    return out


def select_transfer(
    options: List[TransferOption],
    resort_name: str,
    group_size: int,
    airport_iata: Optional[str] = None,
    travel_date=None,
    preferred_modes: Optional[List[str]] = None,
    optimize_for: str = "cost",     # "cost" | "time"
) -> Optional[TransferOption]:
    """
    Picks the best transfer, or None when nothing viable exists.

    Filter order matters:
      1. Mandatory options override everything. Zermatt is car-free --
         road access ends at Tasch and the final leg MUST be rail. A
         "private transfer to Zermatt" actually terminates at Tasch and
         does not remove the train leg, so offering it as an alternative
         would mislead.
      2. Availability. A service that does not run on the travel date is
         not an option, however cheap.
      3. User mode preferences, applied only if they leave something --
         better to return a viable transfer the user mildly dislikes
         than to return nothing at all.
    """
    candidates = options_for(options, resort_name, airport_iata)
    if not candidates:
        return None

    mandatory = [o for o in candidates if o.is_mandatory]
    if mandatory:
        candidates = mandatory

    available = [o for o in candidates if o.runs_on(travel_date)]
    if available:
        candidates = available
    # If nothing runs that day we deliberately fall through rather than
    # returning None: the caller still needs a cost estimate, and
    # transfer_availability_warning() reports the problem separately.

    if preferred_modes:
        preferred = [o for o in candidates if o.mode in preferred_modes]
        if preferred:
            candidates = preferred

    if optimize_for == "time":
        return min(candidates, key=lambda o: (o.duration_minutes,
                                              o.round_trip_cost_per_person(group_size)))
    return min(candidates, key=lambda o: (o.round_trip_cost_per_person(group_size),
                                          o.duration_minutes))


def transfer_availability_warning(
    options: List[TransferOption], resort_name: str, group_size: int,
    airport_iata: Optional[str] = None, travel_date=None,
    preferred_modes: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Returns a human-readable warning when the chosen date has restricted
    transfer availability, else None.

    Exists because select_transfer falls through rather than failing:
    the user should be TOLD that the cheap shuttle doesn't run on their
    Tuesday, not silently quoted it.
    """
    candidates = options_for(options, resort_name, airport_iata)
    if not candidates or travel_date is None:
        return None
    running = [o for o in candidates if o.runs_on(travel_date)]
    if not running:
        return (f"No researched transfer service runs to {resort_name} on "
                f"{travel_date:%A %d %b}. Costs shown are indicative only.")
    blocked = [o for o in candidates if not o.runs_on(travel_date)]
    if blocked:
        cheapest_blocked = min(blocked, key=lambda o: o.round_trip_cost_per_person(group_size))
        cheapest_running = min(running, key=lambda o: o.round_trip_cost_per_person(group_size))
        if cheapest_blocked.round_trip_cost_per_person(group_size) < \
           cheapest_running.round_trip_cost_per_person(group_size):
            return (f"The cheapest transfer to {resort_name} "
                    f"({cheapest_blocked.mode.replace('_', ' ')}, "
                    f"EUR{cheapest_blocked.round_trip_cost_per_person(group_size):.0f}pp) "
                    f"does not run on {travel_date:%A}s "
                    f"(runs {cheapest_blocked.runs_on_days}).")
    return None


def transfer_cost_per_person(
    options: List[TransferOption], resort_name: str, group_size: int,
    airport_iata: Optional[str] = None, travel_date=None,
    preferred_modes: Optional[List[str]] = None,
    optimize_for: str = "cost",
) -> Optional[float]:
    """Round-trip per-person cost of the best transfer, or None if unknown."""
    chosen = select_transfer(options, resort_name, group_size, airport_iata,
                             travel_date, preferred_modes, optimize_for)
    if chosen is None:
        return None
    return round(chosen.round_trip_cost_per_person(group_size), 2)


def compare_modes(options: List[TransferOption], resort_name: str, group_size: int,
                  airport_iata: Optional[str] = None, travel_date=None) -> List[dict]:
    """
    All viable modes with cost and time, cheapest first.

    Powers the tradeoff line the product should surface -- "private van:
    EUR12 more each, saves 50 minutes" -- which is exactly the kind of
    comparison a group actually wants and which a single number hides.
    """
    candidates = options_for(options, resort_name, airport_iata)
    rows = []
    for o in candidates:
        rows.append({
            "mode": o.mode,
            "airport": o.airport_iata,
            "cost_per_person_eur": round(o.round_trip_cost_per_person(group_size), 2),
            "duration_minutes": o.duration_minutes,
            "vehicles_needed": o.vehicles_needed(group_size),
            "runs_on_days": o.runs_on_days,
            "available_on_date": o.runs_on(travel_date),
            "is_mandatory": o.is_mandatory,
            "data_quality": o.data_quality,
            "operator": o.operator,
        })
    rows.sort(key=lambda r: r["cost_per_person_eur"])
    return rows


# Module-level cache: the trip cost calculator asks for transfer costs
# once per (resort, date) combination, which in a date-range search is
# hundreds of calls. Re-reading the spreadsheet each time would dominate
# runtime. Same reasoning as the resort cache in api/routes/search.py.
_options_cache: Optional[List[TransferOption]] = None


def get_transfer_options(force_reload: bool = False) -> List[TransferOption]:
    global _options_cache
    if _options_cache is None or force_reload:
        _options_cache = load_transfer_options()
    return _options_cache


def clear_options_cache() -> None:
    """Test helper -- lets a test point the loader at a different file."""
    global _options_cache
    _options_cache = None
