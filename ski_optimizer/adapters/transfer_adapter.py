"""
[PHASE 5/8 — not implemented yet]

Replaces cost_calculator's distance-based transfer formula with real
rate cards from transfer operators (e.g. GoOpti, Alps2Alps, Ski-Lifts,
Alpybus) per resort/airport pair. Per the blueprint's data-architecture
notes, these rarely have public APIs, so this will likely be periodic
manual/scraped rate-table refreshes (see jobs/refresh_static_data.py)
rather than a live per-request API call -- more like a richer version
of today's spreadsheet column than a true "adapter" in the flight/hotel
sense. Kept in adapters/ anyway for interface consistency.

Planned interface:

    def get_transfer_options(
        resort: Resort,
        group_size: int,
    ) -> List[TransferOption]:
        '''
        Returns real transfer options (shared shuttle, private, train,
        bus) with cost and duration for `resort`'s nearest airport. A
        TransferOption dataclass should be added to models.py once this
        is implemented, since real transfer choice (not just cost) is a
        soft preference per the blueprint (Section 2.D).
        '''
        raise NotImplementedError
"""


def get_transfer_options(*args, **kwargs):
    raise NotImplementedError(
        "Real transfer rate cards are planned for Phase 5/8 (see module docstring). "
        "cost_calculator's distance-based formula is the placeholder until then."
    )
