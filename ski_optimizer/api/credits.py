"""
Per-user daily SEARCH CREDITS.

WHAT ONE CREDIT BUYS: one candidate start date evaluated. A fixed-date
search ("I'm going on 18 Jan") costs 1. A flexible search over a window
costs one credit per candidate start date it actually has to price and
rank -- a 10-day window for a 7-night trip is 4 candidates, so 4
credits.

WHY THAT UNIT, and not "one credit per search": a search is not a fixed
amount of work. The whole point of the flexible-window mode is that it
prices and ranks every valid start date in the range, so a wide window
is genuinely many searches wearing one button. Charging per search would
make the cheapest thing to do also the most expensive thing to serve.

WHY NOT "one credit per live scrape": that WOULD be the truest measure
of external cost, but it is capped by live_reprice_n regardless of
window width, so a 400-day search and a 1-day search would cost the
same -- which is both surprising to a user and the opposite of the
incentive we want. Candidate dates is the honest, predictable,
explainable proxy: it is exactly the number the API already reports back
as `candidate_dates_per_resort`, so a user can see what they were
charged for.

The cost is computed BEFORE the search runs, so it can be quoted up
front and refused cleanly rather than charged after the fact.
"""
import datetime
import os
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.models import SearchCreditLedger

# Deliberately generous while the project is in development -- the user
# asked for a big allowance now, with the option to sell top-ups later.
# For reference on what "generous" means here: a fixed-date search costs
# 1, and even a full two-season 400-day window costs under 400, so this
# allows roughly one maximal search per day or several hundred ordinary
# ones. A realistic production "taste" tier would be nearer 20-30/day.
DEFAULT_DAILY_CREDITS = int(os.environ.get("DAILY_SEARCH_CREDITS", "500"))

# A single search can never cost more than this, however wide the
# window. Stops one request from consuming an entire day's allowance by
# accident, and pairs with the API's own MAX_SEARCH_WINDOW_DAYS bound.
MAX_CREDITS_PER_SEARCH = int(os.environ.get("MAX_CREDITS_PER_SEARCH", "60"))


@dataclass(frozen=True)
class CreditStatus:
    daily_allowance: int
    used_today: int

    @property
    def remaining(self) -> int:
        return max(0, self.daily_allowance - self.used_today)


def cost_for_candidate_dates(candidate_dates: int) -> int:
    """
    Credits for a search that will evaluate `candidate_dates` start
    dates. Always at least 1 -- a search that found no valid candidate
    date still did the work of looking.
    """
    return max(1, min(MAX_CREDITS_PER_SEARCH, candidate_dates))


def _today() -> datetime.date:
    return datetime.date.today()


def get_status(db: Session, user_id: str) -> CreditStatus:
    """Today's allowance and spend for one user. Never writes."""
    row = (
        db.query(SearchCreditLedger)
        .filter(SearchCreditLedger.user_id == user_id, SearchCreditLedger.day == _today())
        .one_or_none()
    )
    return CreditStatus(
        daily_allowance=DEFAULT_DAILY_CREDITS,
        used_today=row.credits_used if row else 0,
    )


def try_spend(db: Session, user_id: str, cost: int) -> Optional[CreditStatus]:
    """
    Spends `cost` credits if the user has them, and returns the status
    AFTER spending. Returns None -- charging nothing -- when they don't,
    so the caller can refuse the search cleanly.

    Deliberately all-or-nothing: a partially-funded search would either
    have to return partial results (confusing) or do the work anyway
    (pointless), so it is simply refused.

    CONCURRENCY: two searches firing at once (which the landing page
    does routinely -- preview and form submit overlap) both saw "no row
    for today" and both INSERTed, and the unique constraint turned the
    loser into a 500. The constraint was right; the code around it
    wasn't. On collision we roll back and retry against the row the
    winner just created, so the second search is charged correctly
    instead of erroring. Retried rather than pre-locked because the
    conflict window is tiny and SELECT ... FOR UPDATE isn't portable to
    SQLite, which is what production currently runs.
    """
    today = _today()
    for attempt in range(2):
        row = (
            db.query(SearchCreditLedger)
            .filter(SearchCreditLedger.user_id == user_id, SearchCreditLedger.day == today)
            .one_or_none()
        )
        used = row.credits_used if row else 0
        if used + cost > DEFAULT_DAILY_CREDITS:
            return None

        try:
            if row is None:
                db.add(SearchCreditLedger(user_id=user_id, day=today, credits_used=cost))
            else:
                row.credits_used = used + cost
            db.commit()
            return CreditStatus(daily_allowance=DEFAULT_DAILY_CREDITS, used_today=used + cost)
        except IntegrityError:
            # Someone else created today's row between our read and our
            # write. Roll back and go round again -- the second pass
            # takes the UPDATE branch.
            db.rollback()
            if attempt == 1:
                raise
    return None
