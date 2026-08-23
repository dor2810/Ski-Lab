"""
Append-only persistence of observed flight fares.

WHY THIS EXISTS AT ALL -- the strategic point, not just a technical one:
SerpApi is a scraper. If Google changes its markup or SerpApi's terms
shift, our live search breaks with no recourse. Every search we make
returns price data; if we discard it after an hour, the differentiator
("is this fare actually good? should you shift your dates?") stays
rented from a provider forever. If we KEEP it, then after one season we
hold Israeli-market ski-route fare history that nobody else has, and
that survives any provider going away.

It costs nothing extra -- we're already making the call.

DESIGN NOTES:
  - APPEND-ONLY. Observations are facts about what a price was at a
    moment. They are never updated or corrected, only added to.
  - Two record types, deliberately kept distinct:
      * FareObservation  -- a price WE saw, from an actual search we ran.
      * FareHistoryPoint -- a point from the provider's own reported
        history, which we did not observe ourselves.
    Conflating them would let unverified provider data masquerade as our
    own measurements. Same honesty rule the resort spreadsheet follows
    with sourced vs. estimated.
  - Deduplicated per (route, dates, source, observed_at) so re-running
    the same search, or replaying a provider's history series, doesn't
    inflate the record.
"""
import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, Index, UniqueConstraint,
)

from .database import Base


class FareObservation(Base):
    """A fare WE observed, from a search we actually ran."""
    __tablename__ = "fare_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_airport = Column(String, nullable=False)
    destination_airport = Column(String, nullable=False)
    outbound_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)      # NULL = one-way
    price_eur = Column(Float, nullable=False)
    airline = Column(String, nullable=True)
    stops = Column(Integer, nullable=True)
    provider = Column(String, nullable=False, default="serpapi")
    observed_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        # The query this table exists to serve: "what has this route
        # cost over time for these dates?"
        Index("ix_fare_route_dates", "origin_airport", "destination_airport",
              "outbound_date", "return_date"),
        Index("ix_fare_observed_at", "observed_at"),
    )


class FareHistoryPoint(Base):
    """
    A point from the PROVIDER's reported price history -- data we did
    not observe ourselves. Kept separate from FareObservation on
    purpose; see the module docstring.
    """
    __tablename__ = "fare_history_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_airport = Column(String, nullable=False)
    destination_airport = Column(String, nullable=False)
    outbound_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    price_eur = Column(Float, nullable=False)
    point_timestamp = Column(DateTime, nullable=False)  # when the price applied
    provider = Column(String, nullable=False, default="serpapi")
    recorded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        # Replaying the same provider series must not duplicate rows.
        UniqueConstraint(
            "origin_airport", "destination_airport", "outbound_date",
            "return_date", "point_timestamp", "provider",
            name="uq_fare_history_point",
        ),
        Index("ix_fare_history_route", "origin_airport", "destination_airport"),
    )


def record_search_result(db, origin_airport, outbound_date, return_date,
                         result, provider="serpapi") -> int:
    """
    Persists everything worth keeping from one search. Returns the
    number of rows written.

    Takes an explicit db Session so the caller controls the transaction
    (and so this is trivially testable against an in-memory SQLite).

    Never raises on a persistence problem the caller can't act on --
    failing to record history should never break a user's search. The
    caller sees the row count; 0 means nothing was stored.
    """
    rows = 0

    for option in getattr(result, "options", []) or []:
        db.add(FareObservation(
            origin_airport=origin_airport,
            destination_airport=option.destination_airport,
            outbound_date=outbound_date,
            return_date=return_date,
            price_eur=option.price_eur,
            airline=option.airline,
            stops=option.stops,
            provider=provider,
        ))
        rows += 1

    insight = getattr(result, "insight", None)
    if insight is not None and insight.price_history:
        # The provider's history isn't tied to a single destination when
        # the search covered several airports, so attribute it to the
        # cheapest option's destination -- and only when unambiguous.
        destinations = {o.destination_airport for o in (result.options or [])}
        destination = destinations.pop() if len(destinations) == 1 else None
        if destination is not None:
            for point in insight.price_history:
                try:
                    ts, price = point[0], float(point[1])
                except (TypeError, ValueError, IndexError):
                    continue
                try:
                    point_dt = datetime.datetime.utcfromtimestamp(ts)
                except (TypeError, ValueError, OSError, OverflowError):
                    continue
                db.add(FareHistoryPoint(
                    origin_airport=origin_airport,
                    destination_airport=destination,
                    outbound_date=outbound_date,
                    return_date=return_date,
                    price_eur=price,
                    point_timestamp=point_dt,
                    provider=provider,
                ))
                rows += 1

    return rows


def cheapest_observed(db, origin_airport, destination_airport,
                      outbound_date, return_date=None) -> Optional[float]:
    """Lowest fare we've ever recorded for this exact route and dates."""
    q = (db.query(FareObservation)
           .filter(FareObservation.origin_airport == origin_airport,
                   FareObservation.destination_airport == destination_airport,
                   FareObservation.outbound_date == outbound_date,
                   FareObservation.return_date == return_date)
           .order_by(FareObservation.price_eur.asc()))
    row = q.first()
    return row.price_eur if row else None


def observations_for_route(db, origin_airport, destination_airport,
                           limit: int = 500) -> List[FareObservation]:
    """Our own observations for a route, newest first."""
    return (db.query(FareObservation)
              .filter(FareObservation.origin_airport == origin_airport,
                      FareObservation.destination_airport == destination_airport)
              .order_by(FareObservation.observed_at.desc())
              .limit(limit)
              .all())
