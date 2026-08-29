"""
The frozen transfer data: REAL Alps2Alps prices and REAL Google Maps
drive times, and the documented reason for every gap.

Owner's ask, verbatim: "Make it always show real data using the
alps2alps api. If for some resort it doesn't work I want to know
exactly why."
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.data.transfer_drive_times import DRIVE_TIMES, UNMEASURED_ROUTES
from ski_optimizer.data.transfer_quotes import TRANSFER_QUOTES, UNQUOTED_ROUTES
from ski_optimizer.engine.cost_calculator import transfer_source_for


def test_every_resort_is_either_quoted_or_has_a_stated_reason():
    # The honesty contract: no resort may silently lack transfer data.
    names = {r.name for r in load_resorts()}
    accounted = set(TRANSFER_QUOTES) | set(UNQUOTED_ROUTES)
    assert names <= accounted, f"unaccounted for: {sorted(names - accounted)}"


def test_every_gap_reason_is_specific_and_actionable():
    for resort, why in UNQUOTED_ROUTES.items():
        assert len(why) > 40, f"{resort}'s reason is too vague: {why!r}"
        # Must name WHAT was tried and WHY it failed -- an operator, a
        # specific name that wasn't recognised, or an explicit "no
        # vehicle". A bare "failed" is exactly what this forbids.
        assert "Alps2Alps" in why, f"{resort}: {why!r}"
        assert any(marker in why for marker in
                   ("recognises no", "no location matching", "no destination matching",
                    "do not serve", "does not serve", "no vehicle")), (
            f"{resort}'s reason doesn't say what was attempted: {why!r}"
        )


def test_quotes_carry_a_real_price_and_duration():
    assert len(TRANSFER_QUOTES) >= 20, "the frozen dataset lost most of its quotes"
    for resort, quote in TRANSFER_QUOTES.items():
        assert quote["price_eur"] > 0, resort
        assert quote["vehicles_offered"] >= 1, resort


def test_drive_times_cover_every_resort_gateway():
    # Google can measure a road route even where no transfer operator
    # sells one -- which is the point: no resort is left estimated.
    import re
    missing = []
    for resort in load_resorts():
        codes = re.findall(r"\(([A-Z]{3})\)", resort.nearest_airport or "")
        for code in codes:
            if f"{resort.name}|{code}" not in DRIVE_TIMES:
                missing.append(f"{resort.name}|{code}")
    assert not missing, f"unmeasured routes: {missing}"
    assert not UNMEASURED_ROUTES, f"Google could not measure: {UNMEASURED_ROUTES}"


def test_drive_times_are_physically_plausible():
    # REGRESSION: "Les Arcs" first geocoded to the village in Provence,
    # giving 462km from Chambery instead of 128km -- a plausible-looking
    # wrong number, the exact thing this project forbids shipping.
    for key, value in DRIVE_TIMES.items():
        km, minutes = value["km"], value["minutes"]
        assert 0 < km < 700, f"{key}: {km}km is not an airport transfer"
        assert 0 < minutes < 600, f"{key}: {minutes}min is not an airport transfer"
        speed = km / (minutes / 60)
        assert 15 < speed < 130, f"{key}: implies {speed:.0f} km/h"


def test_transfer_source_reports_real_data_or_the_reason():
    # What the API surfaces: either a real Alps2Alps price, or the
    # precise reason there isn't one -- never a silent estimate.
    quoted = next(iter(TRANSFER_QUOTES))
    resort = next(r for r in load_resorts() if r.name == quoted)
    info = transfer_source_for(resort)
    assert info["source"] == "alps2alps"
    assert info["price_eur"] == TRANSFER_QUOTES[quoted]["price_eur"]

    if UNQUOTED_ROUTES:
        gap_name = next(iter(UNQUOTED_ROUTES))
        gap_resort = next(r for r in load_resorts() if r.name == gap_name)
        gap_info = transfer_source_for(gap_resort)
        assert gap_info["source"] in ("estimated", "drive_time_only")
        assert gap_info["unavailable_reason"], "a gap must carry its reason"


# --- Alps2Alps prefilled booking deep links (2026-08-29) ---
# Owner: "i want a link that gets me into the real transfer and not
# some generic search page". Built offline from frozen location codes
# (data/alps2alps_locations.py); the URL SHAPE was verified live --
# quick-checkout without a vehicle id lands in the real funnel with
# the route/date/party loaded.

def test_deeplink_carries_the_route_dates_and_party():
    import datetime
    from urllib.parse import parse_qs, urlparse
    from ski_optimizer.engine.links import alps2alps_deeplink
    from ski_optimizer.data.alps2alps_locations import ALPS2ALPS_LOCATIONS

    name = next(iter(ALPS2ALPS_LOCATIONS))
    url = alps2alps_deeplink(name, datetime.date(2027, 1, 9), "11:00", 3,
                             return_date=datetime.date(2027, 1, 16))
    q = parse_qs(urlparse(url).query)
    assert q["from"][0] == ALPS2ALPS_LOCATIONS[name]["airport_code"]
    assert q["to"][0] == ALPS2ALPS_LOCATIONS[name]["resort_code"]
    assert q["date"][0] == "2027-01-09"
    assert q["return_date"][0] == "2027-01-16"
    assert q["adults"][0] == "3"


def test_deeplink_is_none_without_a_date_or_a_known_resort():
    import datetime
    from ski_optimizer.engine.links import alps2alps_deeplink
    assert alps2alps_deeplink("Val Thorens", None, "11:00", 2) is None
    assert alps2alps_deeplink("Nowhere Ski Resort", datetime.date(2027, 1, 9),
                              "11:00", 2) is None


def test_every_frozen_location_pair_is_well_formed():
    # A malformed code would produce a link that looks real and lands
    # nowhere -- worse than falling back to the generic form.
    from ski_optimizer.data.alps2alps_locations import ALPS2ALPS_LOCATIONS, UNRESOLVED
    assert len(ALPS2ALPS_LOCATIONS) >= 25, "most resorts should have real codes"
    for name, loc in ALPS2ALPS_LOCATIONS.items():
        assert loc["airport_code"].startswith("airport-"), f"{name}: {loc}"
        assert loc["resort_code"].startswith("resort-"), f"{name}: {loc}"
    # Every unresolved resort must say WHY, and never also be resolved.
    for name, reason in UNRESOLVED.items():
        assert "unmatched" in reason, f"{name}: {reason!r}"
        assert name not in ALPS2ALPS_LOCATIONS


def test_search_result_transfer_link_is_the_prefilled_page_not_the_form():
    # The API contract the owner actually sees: a dated result's
    # transfer link must be the prefilled funnel, not /booking/index.
    import datetime
    from ski_optimizer.api.routes.search import _transfer_search_url
    from ski_optimizer.data.alps2alps_locations import ALPS2ALPS_LOCATIONS
    from ski_optimizer.data.resort_repository import load_resorts

    resort = next(r for r in load_resorts() if r.name in ALPS2ALPS_LOCATIONS)
    url = _transfer_search_url(resort, datetime.date(2027, 1, 9), 2, attempt=False,
                               return_date=datetime.date(2027, 1, 16))
    assert "quick-checkout" in url and "booking/index" not in url
