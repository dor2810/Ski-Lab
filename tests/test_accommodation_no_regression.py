"""
THE REGRESSION THIS FILE EXISTS TO CATCH, in the owner's words:

    "The worst scenario is that we do est accommodation because of the
    change -- that previously we would find but now not."

i.e. a trip that used to carry a LIVE accommodation price now falls
back to the static estimate because selection was rewritten. When
live_accommodation_cost_eur_per_person returns None the ranker keeps
the estimate (engine/scoring.py -- `if live_accom is not None`), so
returning None where the old code returned a number is exactly that
regression, silently.

The old behaviour, in full:

    cheapest = min(options, key=price)      # no filter, no enrichment
    return None if cheapest is None else per_person(cheapest)
"""
import datetime
import random

import pytest

from ski_optimizer.engine import cost_calculator
from ski_optimizer.models import AccommodationFilter, AccommodationOption
from ski_optimizer.data.resort_repository import load_resorts

CHECKIN = datetime.date(2027, 1, 9)
NIGHTS, ROOMS, GROUP = 6, 1, 2


def _resort():
    return next(r for r in load_resorts() if r.name == "Val Thorens")


def _serve(monkeypatch, options, enrich_raises=False):
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": list(options)})())

    def _enrich(resort, checkin_date, nights, rooms_needed, options):
        if enrich_raises:
            raise RuntimeError("stays is down")
        return options
    monkeypatch.setattr(cost_calculator, "_enrich_options", _enrich)


def _old_price(options):
    """Exactly what the pre-change code computed."""
    if not options:
        return None
    cheapest = min(options, key=lambda o: o.price_eur_per_night)
    return round((cheapest.price_eur_per_night * NIGHTS * ROOMS) / GROUP, 2)


def _new_price(**kw):
    return cost_calculator.live_accommodation_cost_eur_per_person(
        _resort(), CHECKIN, nights=NIGHTS, group_size=GROUP, rooms_needed=ROOMS, **kw)


# --- 1. Unfiltered searches must be byte-identical to the old code ---

def test_unfiltered_price_matches_the_old_implementation_exactly(monkeypatch):
    """Randomised over many shapes: prices, missing attributes, ties,
    single entries. Any divergence here is the regression itself."""
    rng = random.Random(20260830)
    for _ in range(300):
        options = [
            AccommodationOption(
                price_eur_per_night=round(rng.uniform(20, 800), 2),
                property_name=f"P{i}",
                star_class=rng.choice([None, 1, 2, 3, 4, 5]),
                rating=rng.choice([None, 2.9, 4.0, 4.6]),
                amenities=rng.choice([None, [], ["SPA"], ["SPA", "GYM"]]),
            )
            for i in range(rng.randint(1, 12))
        ]
        _serve(monkeypatch, options)
        assert _new_price() == _old_price(options)


def test_unfiltered_pricing_never_touches_the_enrichment_provider(monkeypatch):
    """Enrichment is a SECOND network call (adapters/stays_adapter),
    made once per priced row. Pricing an unfiltered trip needs a price
    and nothing else, so it must not be called AT ALL -- counted, not
    merely survived, because a try/except would hide the cost while
    still paying it on every row of every search."""
    calls = {"n": 0}
    options = [AccommodationOption(price_eur_per_night=100.0, property_name="A")]
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": list(options)})())

    def _counting_enrich(resort, checkin_date, nights, rooms_needed, options):
        calls["n"] += 1
        return options
    monkeypatch.setattr(cost_calculator, "_enrich_options", _counting_enrich)

    assert _new_price() == 300.0
    assert calls["n"] == 0, "unfiltered pricing paid for an enrichment call it does not need"

    # ...and with a filter it IS wanted, because that is where the star
    # classes come from.
    assert _new_price(accommodation_filter=AccommodationFilter(min_star_class=4)) == 300.0
    assert calls["n"] == 1


def test_enrichment_outage_on_the_unfiltered_path_cannot_cost_a_live_price(monkeypatch):
    """Belt and braces: even if something reintroduces the call, an
    outage must never downgrade a live price to an estimate."""
    _serve(monkeypatch, [AccommodationOption(price_eur_per_night=100.0, property_name="A")],
           enrich_raises=True)
    assert _new_price() == 300.0


def test_no_options_still_returns_none_as_before(monkeypatch):
    _serve(monkeypatch, [])
    assert _new_price() is None


def test_provider_outage_still_returns_none_as_before(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search", boom)
    assert _new_price() is None


# --- 2. A filter must not create NEW estimate cases beyond its own ---

@pytest.mark.parametrize("filt", [
    AccommodationFilter(min_star_class=4),
    AccommodationFilter(min_star_class=5),
    AccommodationFilter(min_rating=4.5),
    AccommodationFilter(min_star_class=4, min_rating=4.0),
])
def test_a_quality_floor_alone_never_loses_a_live_price(monkeypatch, filt):
    """A floor with no spend cap can always fall back to unrated
    inventory, so a search that could be priced before is still priced.
    Only the CAP may legitimately price nothing out."""
    rng = random.Random(7)
    for _ in range(200):
        options = [
            AccommodationOption(
                price_eur_per_night=round(rng.uniform(20, 800), 2),
                property_name=f"P{i}",
                star_class=rng.choice([None, 1, 2, 3, 4, 5]),
                rating=rng.choice([None, 2.9, 4.0, 4.6]),
            )
            for i in range(rng.randint(1, 10))
        ]
        _serve(monkeypatch, options)
        assert _old_price(options) is not None
        assert _new_price(accommodation_filter=filt) is not None, (
            "a floor turned a live price into an estimate")


def test_a_spend_cap_only_prices_nothing_when_nothing_fits(monkeypatch):
    """The one legitimate way to end up with no live price -- and it
    must be exactly that, not an off-by-one."""
    options = [AccommodationOption(price_eur_per_night=100.0, property_name="A")]  # 300pp
    _serve(monkeypatch, options)
    assert _new_price(accommodation_filter=AccommodationFilter(max_eur_per_person=299.99)) is None
    assert _new_price(accommodation_filter=AccommodationFilter(max_eur_per_person=300.0)) == 300.0
    assert _new_price(accommodation_filter=AccommodationFilter(max_eur_per_person=301.0)) == 300.0


def test_an_empty_filter_object_behaves_as_no_filter(monkeypatch):
    """The API builds a filter from four optional fields; if the
    traveller sets none, the object must not change pricing."""
    options = [AccommodationOption(price_eur_per_night=55.0, property_name="A"),
               AccommodationOption(price_eur_per_night=40.0, property_name="B")]
    _serve(monkeypatch, options)
    assert _new_price(accommodation_filter=AccommodationFilter()) == _old_price(options)


def test_enrichment_outage_under_a_filter_still_prices_from_what_we_have(monkeypatch):
    """With a filter, enrichment IS wanted -- but if it dies, we still
    have real properties, so we price on them rather than estimating."""
    options = [AccommodationOption(price_eur_per_night=100.0, property_name="A")]
    _serve(monkeypatch, options, enrich_raises=True)
    assert _new_price(accommodation_filter=AccommodationFilter(min_star_class=4)) == 300.0
