"""
Per-request record of whether a live-pricing provider blocked us.

WHY THIS EXISTS: live flight pricing is a scraper, and Google answers
suspected automation with a CAPTCHA page. Every blocked lookup used to
degrade into a static estimate labelled "EST." -- which is technically
true and completely unhelpful, because it looks identical to "we
checked and this is our best guess." The user cannot tell the
difference between "no live price exists" and "we were locked out."

This project's rule is to degrade VISIBLY, not silently. So the fact
gets recorded during a request and reported alongside the results, and
the UI can say "live flight pricing is temporarily blocked" instead of
leaving a wall of unexplained EST. badges.

WHY A CONTEXTVAR, not a global: two requests can be in flight at once
(and repricing itself runs on a thread pool), so a plain module global
would leak one user's blocked state into another user's response.
ContextVar is per-context and, since Python 3.7, is COPIED into threads
started via ThreadPoolExecutor's default context propagation -- which is
exactly the shape of the repricing code that sets it.
"""
from contextvars import ContextVar

_provider_blocked: ContextVar[bool] = ContextVar("provider_blocked", default=False)


def reset_provider_status() -> None:
    """Call at the START of a request, before any live pricing runs."""
    _provider_blocked.set(False)


def note_provider_blocked() -> None:
    """Record that a live-pricing provider served an anti-bot challenge."""
    _provider_blocked.set(True)


def was_provider_blocked() -> bool:
    """Whether any live-pricing lookup in this request hit a block."""
    return _provider_blocked.get()
