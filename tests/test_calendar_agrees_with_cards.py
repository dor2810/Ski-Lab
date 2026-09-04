"""
The calendar and the cards must never quote different prices.

FOUND IN PRODUCTION 2026-09-04, reported by the owner: days we had
priced exactly were shown on the calendar as estimates. Measuring the
real response showed something worse than a wrong label -- ALL 24
returned rows disagreed with their own calendar cell, by up to EUR77
(Bansko 12 Dec: EUR970.20 on the card, EUR1,047.29 on the calendar),
and twelve carried price_is_live=False while their cards were fully
live on both flight and accommodation.

Cause: the grid is snapshotted inside search_date_range, but the
displayed rows are repriced again afterwards. The snapshot therefore
held intermediate figures for precisely the days we know best.
"""
import datetime

from ski_optimizer.api.routes.search import _date_prices_out


class _Cost:
    def __init__(self, total, flight_live=False, accom_live=False):
        self.total_eur = total
        self.flight_price_is_live = flight_live
        self.accommodation_price_is_live = accom_live


class _Resort:
    def __init__(self, name):
        self.name, self.country = name, "Bulgaria"


class _Row:
    def __init__(self, name, date, total, flight_live=False, accom_live=False, within=True):
        self.resort = _Resort(name)
        self.start_date = date
        self.cost = _Cost(total, flight_live, accom_live)
        self.within_budget = within


DEC12 = datetime.date(2026, 12, 12)
DEC13 = datetime.date(2026, 12, 13)


def test_a_day_with_a_card_takes_the_card_s_price_and_flags():
    series = [_Row("Bansko", DEC12, 1047.29)]           # stale snapshot
    results = [_Row("Bansko", DEC12, 970.20, True, True)]  # what the card shows
    out = _date_prices_out(series, results, budget=1500)
    assert out[0].total_eur == 970.20, "the calendar was quoting a price no card showed"
    assert out[0].price_is_live is True, "a fully live card must not read as an estimate"


def test_a_day_with_no_card_keeps_the_series_figure():
    """The grid is still the only source for everything off the
    shortlist -- that is the whole reason it exists."""
    series = [_Row("Bansko", DEC13, 1139.69)]
    out = _date_prices_out(series, results=[], budget=1500)
    assert out[0].total_eur == 1139.69
    assert out[0].price_is_live is False


def test_within_budget_follows_the_card_too():
    """The card decides its own budget verdict; recomputing it here
    from a stale total could contradict the badge on the card."""
    series = [_Row("Bansko", DEC12, 1600.0)]
    results = [_Row("Bansko", DEC12, 1400.0, True, True, within=True)]
    assert _date_prices_out(series, results, budget=1500)[0].within_budget is True


def test_a_card_for_a_different_date_does_not_override():
    series = [_Row("Bansko", DEC13, 1139.69)]
    results = [_Row("Bansko", DEC12, 970.20, True, True)]
    assert _date_prices_out(series, results, budget=1500)[0].total_eur == 1139.69
