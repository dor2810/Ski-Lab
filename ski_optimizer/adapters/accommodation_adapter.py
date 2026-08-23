"""
[PHASE 5 — not implemented yet]

Replaces the static accommodation_eur_per_night column in the seed
spreadsheet with real, live inventory/pricing. Candidate providers:
Booking.com Affiliate/Demand API, Expedia Rapid API, Hotelbeds.

Planned interface:

    def search_accommodation(
        resort: Resort,
        checkin_date: date,
        nights: int,
        rooms_needed: int,
    ) -> List[AccommodationOption]:
        '''
        Returns real accommodation options near `resort` for the given
        dates. Raises adapters.base.AdapterError on failure. An
        AccommodationOption dataclass (price/night, rating, distance to
        lifts, cancellation policy) should be added to models.py once
        this is implemented.
        '''
        raise NotImplementedError
"""


def search_accommodation(*args, **kwargs):
    raise NotImplementedError(
        "Live accommodation search is planned for Phase 5 (see module docstring). "
        "The seed spreadsheet's researched rate-card estimate is the placeholder until then."
    )
