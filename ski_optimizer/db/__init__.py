"""
[PHASE 8 -- partially started: auth only]

database.py + models.py now hold a real SQLAlchemy setup (SQLite for
local dev, Postgres via DATABASE_URL) -- but ONLY for User,
RefreshToken, and EmailVerificationToken, built to support real account
registration/login. This is NOT the full blueprint schema from Section
6 (SkiResort, Trip, TripOption, Price, Flight, etc.) -- those stay in
the spreadsheet for now; migrating them is a separate, larger decision
that shouldn't ride along with "we needed real user accounts."

migrations/ (alembic) doesn't exist yet -- database.py's init_db() uses
create_all(), which is fine for a fresh SQLite dev DB but has no notion
of altering an existing table. Add alembic before this schema needs its
first real change in a database that already has user data in it.
"""
