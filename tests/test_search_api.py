

def test_a_fixed_date_search_echoes_the_dates_it_priced_for():
    """
    REGRESSION, found in production 2026-09-01. The fixed-date response
    carried no start_date, so a caller that asked "price this resort on
    this day" got a valid trip back with no way to tell which day it
    belonged to. The calendar's "price this day properly" action spent
    the traveller's credit, could not match the answer to the cell, and
    silently dropped it.
    """
    from ski_optimizer.api.routes.search import TripResultOut
    fields = TripResultOut.model_fields
    assert "start_date" in fields and "end_date" in fields
