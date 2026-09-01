"""
Choosing WHICH property a trip is priced on.

Before this, every trip was priced on the cheapest bed the search
found, whatever it was. The owner's ask, verbatim: "I want people to be
able to choose... if they want three or four or five stars, or... that
the accommodation will cost three hundred dollars for a person... so
it's not, like, the cheapest -- I can actually choose a big number."
"""
import datetime

import pytest

from ski_optimizer.engine import cost_calculator
from ski_optimizer.models import AccommodationFilter, AccommodationOption
from ski_optimizer.data.resort_repository import load_resorts


def _resort():
    return next(r for r in load_resorts() if r.name == "Val Thorens")


def _opts():
    """Shaped like a real Val Thorens response (live 2026-08-30):
    a cheap unclassified bed, two 4-star hotels, one 5-star, and one
    4-star whose class Google simply does not publish."""
    return [
        AccommodationOption(price_eur_per_night=40.0, property_name="Hostel Bunk",
                            star_class=None, rating=3.8, review_count=45),
        AccommodationOption(price_eur_per_night=72.0, property_name="Residence Alpina",
                            star_class=3, rating=4.1, review_count=210),
        AccommodationOption(price_eur_per_night=95.0, property_name="Fahrenheit Seven",
                            star_class=4, rating=4.4, review_count=688,
                            amenities=["SPA", "RESTAURANT"]),
        AccommodationOption(price_eur_per_night=120.0, property_name="Hotel Marielle",
                            star_class=4, rating=4.3, review_count=359),
        AccommodationOption(price_eur_per_night=260.0, property_name="Altapura",
                            star_class=5, rating=4.4, review_count=589,
                            amenities=["SPA", "GYM"]),
    ]


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": _opts()})())
    monkeypatch.setattr(cost_calculator, "_enrich_options",
                        lambda resort, checkin_date, nights, rooms_needed, options: options)


def _pick(filt, nights=6, group_size=2, rooms=1):
    return cost_calculator.select_live_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights, rooms, group_size, filt)


def test_no_filter_still_picks_the_cheapest():
    """The existing behaviour has to survive untouched."""
    chosen, per_person, _ = _pick(None)
    assert chosen.property_name == "Hostel Bunk"
    assert per_person == round(40.0 * 6 / 2, 2)


def test_a_star_floor_picks_the_cheapest_property_that_meets_it():
    """"Four stars" means the cheapest four-star, not the dearest --
    a budget is a ceiling, never a target to spend up to."""
    chosen, per_person, _ = _pick(AccommodationFilter(min_star_class=4))
    assert chosen.property_name == "Fahrenheit Seven"
    assert per_person == round(95.0 * 6 / 2, 2)


def test_a_spend_cap_is_per_person_for_the_whole_stay():
    """EUR300 per person over 6 nights, 2 sharing, allows up to EUR100
    a night for the room -- not EUR300 a night."""
    chosen, _, _ = _pick(AccommodationFilter(max_eur_per_person=300.0, min_star_class=4))
    assert chosen.property_name == "Fahrenheit Seven"
    # POLICY, set by the owner 2026-08-30: the cap is a hard constraint,
    # and within EUR200pp nothing here carries a star class at all (the
    # 4-stars are priced out) -- so this IS the "no option with rate"
    # case, and we offer the cheapest real place inside the budget
    # rather than nothing. Flagged, never passed off as a 4-star.
    chosen_low, _, report_low = _pick(AccommodationFilter(max_eur_per_person=200.0, min_star_class=4))
    assert chosen_low.property_name == "Hostel Bunk"
    assert report_low.fell_back_to_unrated is True


def test_a_property_with_no_star_class_cannot_satisfy_a_star_floor():
    """Google does not classify every property. An unclassified one is
    UNKNOWN, so it must not be counted as meeting "4 stars or better" --
    nor quietly deleted without saying how many were set aside."""
    chosen, _, report = _pick(AccommodationFilter(min_star_class=5))
    assert chosen.property_name == "Altapura"
    assert report.unrated_set_aside == 1, "Hostel Bunk has no class and was not considered"


def test_required_amenities_must_all_be_present():
    chosen, _, _ = _pick(AccommodationFilter(required_amenities=["SPA", "GYM"]))
    assert chosen.property_name == "Altapura"


def test_an_impossible_filter_returns_nothing_rather_than_the_cheapest():
    """The failure mode this guards: silently falling back to the
    cheapest bed would tell the traveller their 5-star filter was met."""
    chosen, per_person, report = _pick(AccommodationFilter(min_star_class=5, max_eur_per_person=100.0))
    assert chosen is None and per_person is None
    assert report.considered == 5 and report.matched == 0


# --- What happens when nothing carries a rating at all ---
#
# Owner's rule: "we can put them at the bottom, and if there is no
# option with rate, put the options you find." Unrated inventory is
# ranked LAST, never preferred -- but a real unclassified property
# beats the alternative, which was falling through to the static
# estimate (engine/scoring.py keeps the estimate when live pricing
# returns None). Verified live 2026-08-30: a Kitzbuehel search returned
# twelve properties and NOT ONE had a star class, so this is the
# common case for that resort, not an edge case.

def _unrated_only():
    return [
        AccommodationOption(price_eur_per_night=60.0, property_name="Chalet Anon", star_class=None),
        AccommodationOption(price_eur_per_night=90.0, property_name="Apartment Anon", star_class=None),
    ]


def test_falls_back_to_unrated_when_nothing_carries_a_class(monkeypatch):
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": _unrated_only()})())
    chosen, per_person, report = _pick(AccommodationFilter(min_star_class=4))
    assert chosen.property_name == "Chalet Anon", "cheapest of what we could find"
    assert per_person == round(60.0 * 6 / 2, 2)
    assert report.fell_back_to_unrated is True, "the UI has to be able to say so"


def test_the_fallback_never_beats_a_property_that_actually_qualifies():
    """A 4-star exists, so an unrated one must not be chosen even
    though it is cheaper -- that is the whole point of the filter."""
    chosen, _, report = _pick(AccommodationFilter(min_star_class=4))
    assert chosen.property_name == "Fahrenheit Seven"
    assert report.fell_back_to_unrated is False


def test_the_fallback_still_respects_the_spend_cap(monkeypatch):
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": _unrated_only()})())
    chosen, _, _ = _pick(AccommodationFilter(min_star_class=4, max_eur_per_person=100.0))
    assert chosen is None, "EUR180pp and EUR270pp both bust a EUR100pp cap"


def test_a_below_floor_property_is_the_LAST_resort_and_is_labelled_as_such(monkeypatch):
    """Unknown is a gap in our data; 3 stars when you asked for 5 is a
    known answer -- so unrated is preferred over below-floor. But
    below-floor still beats returning nothing, because nothing sends
    the ranker back to a static estimate and replaces a real price with
    a guess (the regression this policy exists to avoid)."""
    only_three_star = [AccommodationOption(price_eur_per_night=72.0,
                                           property_name="Residence Alpina", star_class=3)]
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": only_three_star})())
    chosen, per_person, report = _pick(AccommodationFilter(min_star_class=5))
    assert chosen.property_name == "Residence Alpina"
    assert per_person == round(72.0 * 6 / 2, 2)
    assert report.fell_back_below_floor is True
    assert report.fell_back_to_unrated is False, "it IS rated -- just not highly enough"


def test_unrated_is_preferred_over_a_property_known_to_be_below_the_floor(monkeypatch):
    """Order of the two fallbacks, stated as a test: an unclassified
    place might be what you asked for; a 2-star demonstrably is not."""
    mixed = [AccommodationOption(price_eur_per_night=50.0, property_name="Two Star Inn", star_class=2),
             AccommodationOption(price_eur_per_night=90.0, property_name="Unknown Chalet", star_class=None)]
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": mixed})())
    chosen, _, report = _pick(AccommodationFilter(min_star_class=5))
    assert chosen.property_name == "Unknown Chalet", "even though it costs more"
    assert report.fell_back_to_unrated is True
    assert report.fell_back_below_floor is False


def test_the_shown_list_puts_unrated_places_last_when_a_floor_is_set(monkeypatch):
    """Second half of the owner's rule: unrated inventory is ranked
    LAST, not deleted. Without a floor the list stays in pure price
    order, because then there is nothing to rank against."""
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": _opts()})())
    unfiltered = cost_calculator.live_accommodation_options(
        _resort(), datetime.date(2027, 1, 9), nights=6, rooms_needed=1, limit=5)
    assert [o.property_name for o in unfiltered][0] == "Hostel Bunk", "cheapest first, as before"

    filtered = cost_calculator.live_accommodation_options(
        _resort(), datetime.date(2027, 1, 9), nights=6, rooms_needed=1, limit=5,
        accommodation_filter=AccommodationFilter(min_star_class=4))
    names = [o.property_name for o in filtered]
    # The rule is specifically about UNRATED places, so everything that
    # carries a class keeps its price order -- a 3-star is a known
    # answer and stays where its price puts it. Only the unclassified
    # one moves.
    assert names[-1] == "Hostel Bunk", "unrated sinks to the bottom, but is still offered"
    assert names[0] == "Residence Alpina", "rated places keep plain price order"
    assert names.index("Fahrenheit Seven") < names.index("Hostel Bunk")


def test_provider_vetted_beats_plain_unknown_and_is_reported_as_such(monkeypatch):
    """Measured 2026-08-30: ask Google for hotel_class=[4,5] in
    Kitzbuehel and it returns a genuinely different twelve properties
    -- but publishes no class for any of them. Those are NOT the same
    as a property nobody filtered: Google vetted them, we just cannot
    re-check its work. They rank above plain unknowns, and the report
    says "vetted", not "fell back to unrated", so the card can explain
    the difference instead of implying we found nothing."""
    mixed = [
        AccommodationOption(price_eur_per_night=90.0, property_name="Unvetted Chalet",
                            star_class=None, star_class_source=None),
        AccommodationOption(price_eur_per_night=147.0, property_name="Hotel Aurach",
                            star_class=None, star_class_source="provider_filter"),
    ]
    monkeypatch.setattr(cost_calculator, "_live_accommodation_search",
                        lambda *a, **k: type("R", (), {"options": mixed})())
    chosen, _, report = _pick(AccommodationFilter(min_star_class=4))
    assert chosen.property_name == "Hotel Aurach", "vetted wins even though it costs more"
    assert report.provider_vetted == 1
    assert report.fell_back_to_unrated is False, "Google did filter these -- say so accurately"
