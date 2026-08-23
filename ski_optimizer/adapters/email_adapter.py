"""
Sends account-related emails (verification, password reset).

Unlike the flight/accommodation/weather adapters (which are pure
NotImplementedError stubs because there's genuinely nothing useful to
do without a real API key), this one CAN be made real today in a
limited way: a "console" backend that prints the email instead of
sending it, which is enough to actually develop and test the
verification flow locally. The real-provider path (SendGrid, SES,
Postgres-backed outbox, whatever) is the part that's stubbed, and it's
a config change away once a provider is chosen -- nothing in
api/routes/auth.py needs to change, it just calls send_verification_email().
"""
import os


class EmailAdapterError(Exception):
    pass


def _backend() -> str:
    return os.environ.get("EMAIL_BACKEND", "console")


def send_verification_email(to_email: str, verification_link: str) -> None:
    backend = _backend()
    if backend == "console":
        print(f"\n[EMAIL/console] To: {to_email}\n"
              f"Subject: Verify your Ski Lab account\n"
              f"Click to verify: {verification_link}\n")
        return
    raise EmailAdapterError(
        f"EMAIL_BACKEND={backend!r} is not implemented yet. Only 'console' "
        "works today (prints instead of sending -- fine for local dev). "
        "Wire up a real provider (SendGrid, AWS SES, Postgres, etc.) here "
        "when the app has a real domain to send from."
    )


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    backend = _backend()
    if backend == "console":
        print(f"\n[EMAIL/console] To: {to_email}\n"
              f"Subject: Reset your Ski Lab password\n"
              f"Click to reset: {reset_link}\n")
        return
    raise EmailAdapterError(
        f"EMAIL_BACKEND={backend!r} is not implemented yet. See "
        "send_verification_email's docstring."
    )
