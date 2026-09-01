"""
Date-range search: "give me the best ski trip for EUR X, sometime in February."

This is the SECOND of the two query modes (see date-range-search-design.md).
The rest of the engine answers "fixed dates, which resort?"; this answers
"fixed budget and duration, which resort AND which dates?".

THE ORGANISING INSIGHT -- which costs move with dates:

  Tier 1, continuous:  flight, accommodation      <- the search axes
  Tier 2, season band: ski pass, accommodation    <- coarse steps
  Tier 3, fixed/resort: transfer, equipment, food <- cancel out across dates

Tier 3 costs are IDENTICAL across every candidate date for one resort, so
they cannot change which date wins. That is the whole reason a month-wide
search is tractable. Crucially this is NOT because they are small or
uniform: researched round-trip transfers range EUR22 (Obergurgl by bus) to
EUR220 (Zermatt's mandatory rail leg). Each resort's own figure is always
used; no global constant is ever assumed.

THREE-STAGE FUNNEL (naive search is 30 resorts x 25 dates = 750 flight
lookups, which is unaffordable):

  Stage 1  Prune resorts on date-independent criteria. Free, no API calls.
           Includes a feasibility floor: if Tier 2 + Tier 3 alone already
           bust the budget, no flight price can rescue that resort.
  Stage 2  Search flights across dates for the shortlist only.
  Stage 3  Price accommodation for surviving (resort, date) pairs only.

Stages 1 and 2 are implemented here and work against STATIC flight
estimates, so the funnel logic is fully testable offline with no API key.
Live pricing plugs into _flight_cost_for_date without touching the funnel.
"""
import datetime
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace as dc_replace
from typing import Callable, List, Optional

from ..models import Resort, UserPreferences, CostBreakdown
from .cost_calculator import (
    airport_codes_for,
    compute_trip_cost, flight_cost_eur, transfer_cost_eur_per_person,
    ski_pass_cost, food_cost_eur, season_band, EQUIPMENT_EUR_PER_DAY,
    apply_live_flight_price, apply_live_accommodation_price,
)
from .scoring import rank_trips, _normalize, _ski_quality_score, narrow_resort_pool, score_resort

# Live pricing is network I/O, not CPU, so threads overlap cleanly.
# Kept modest rather than unbounded: these are scrapes against Google,
# and hammering them concurrently is the fastest way to get rate-limited
# (adapters/google_flights_adapter.py's own docstring warns about
# exactly that), which would cost far more than the latency it saves.
_LIVE_PRICING_WORKERS = 8

# Seconds of jittered delay before each live lookup starts.
#
# Eight threads firing the instant the pool opens is a burst that looks
# exactly like automation, and the provider throttles accordingly --
# measured, with most routes returning nothing while a single route
# succeeded. A small random stagger costs almost nothing in wall-clock
# time (the work still overlaps; only the start times spread) and makes
# the traffic pattern far less machine-like.
_REQUEST_STAGGER_S = 0.25


def _staggered(fn):
    """Wraps a live-pricing call with a short random delay before it runs."""
    def _call(*args, **kwargs):
        time.sleep(random.random() * _REQUEST_STAGGER_S * _LIVE_PRICING_WORKERS)
        return fn(*args, **kwargs)
    return _call


@dataclass
class DatedTripOption:
    """A candidate trip: a resort AND a specific start date."""
    resort: Resort
    start_date: datetime.date
    end_date: datetime.date
    cost: CostBreakdown
    score: float
    score_components: dict
    season: str
    # See models.TripOption.within_budget -- same contract, same reason.
    within_budget: bool = True
    # Other good dates for THIS resort in the searched window, from
    # DIFFERENT calendar weeks than this row -- the per-resort "More
    # dates" expander. Populated only on coverage-first rows (one per
    # resort); empty everywhere else. Tuple, not list: these are
    # attached via dataclasses.replace and never mutated after.
    alternatives: tuple = ()

    @property
    def total_eur(self) -> float:
        return self.cost.total_eur


#: date.weekday() convention (Monday=0 .. Sunday=6), keyed by lowercase name.
WEEKDAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def candidate_start_dates(earliest: datetime.date, latest: datetime.date,
                          nights: int, step_days: int = 1,
                          start_weekday: Optional[int] = None,
                          start_weekdays: Optional[set] = None) -> List[datetime.date]:
    """
    Every valid start date whose full trip fits inside the window.

    step_days > 1 coarsens the grid. That matters for the bootstrapping
    problem: on day one we have no fare history, so every date costs a
    live API call. Searching every 3rd day first and refining around the
    winner is far cheaper than 25 blind lookups, and gets unnecessary as
    db/fare_history.py accumulates real data.

    start_weekday (0=Monday..6=Sunday, see WEEKDAY_NAMES), when given,
    restricts results to just that weekday -- "only Saturdays in this
    month" -- which is a real, common travel preference (a whole-week
    trip starting mid-week splits a weekend across both ends). This
    REPLACES step_days entirely rather than combining with it: a
    weekly cadence is already implied by "every Saturday", and a second,
    independent step would either be redundant (7 is already a multiple
    of itself) or silently skip weeks in a way nothing here signals.
    """
    if nights <= 0:
        raise ValueError(f"nights must be > 0, got {nights}")
    if step_days <= 0:
        raise ValueError(f"step_days must be > 0, got {step_days}")
    if latest < earliest:
        raise ValueError(f"latest {latest} is before earliest {earliest}")
    if start_weekday is not None and not (0 <= start_weekday <= 6):
        raise ValueError(f"start_weekday must be 0-6 (Monday-Sunday), got {start_weekday}")
    if start_weekdays is not None and not all(isinstance(d, int) and 0 <= d <= 6 for d in start_weekdays):
        raise ValueError(f"start_weekdays must contain 0-6 (Monday-Sunday), got {start_weekdays}")

    # start_weekdays generalizes start_weekday to a SET of allowed
    # days -- added for the "weekend" option (Sat-to-Sat is the classic
    # package changeover, Sunday the established cheaper one, so a
    # weekend search genuinely needs both). A single start_weekday
    # folds into the same mechanism.
    if start_weekdays is None and start_weekday is not None:
        start_weekdays = {start_weekday}

    if start_weekdays:
        out = []
        day = earliest
        while day + datetime.timedelta(days=nights) <= latest:
            if day.weekday() in start_weekdays:
                out.append(day)
            day += datetime.timedelta(days=1)
        return out

    out = []
    day = earliest
    while day + datetime.timedelta(days=nights) <= latest:
        out.append(day)
        day += datetime.timedelta(days=step_days)
    return out


def date_independent_cost(resort: Resort, prefs: UserPreferences) -> float:
    """
    Sum of the Tier 3 costs -- the ones identical across every date.

    Used by the Stage 1 feasibility floor. Deliberately EXCLUDES the ski
    pass, because that is Tier 2 (season-banded) and so does vary by date.
    """
    nights = prefs.nights
    transfer = transfer_cost_eur_per_person(resort, prefs.group_size)
    equipment = EQUIPMENT_EUR_PER_DAY[prefs.equipment_tier] * prefs.ski_days
    food = food_cost_eur(resort, nights, prefs.food_profile)
    return transfer + equipment + food


def cheapest_possible_cost(resort: Resort, prefs: UserPreferences) -> float:
    """
    Optimistic lower bound on what this resort could ever cost in the
    window: Tier 3 costs, plus the cheapest season band for the pass and
    accommodation, plus the static flight estimate.

    Deliberately OPTIMISTIC. A resort is only dropped in Stage 1 when even
    its best case busts the budget, so pruning can never discard a trip
    that would actually have been affordable.
    """
    nights = prefs.nights
    # Shoulder band = cheapest, obtained by passing no date.
    pass_cost = ski_pass_cost(resort, prefs.ski_days, None)
    rooms = prefs.rooms_needed or max(1, -(-prefs.group_size // 2))
    accom = (resort.accommodation_eur_per_night * nights * rooms) / prefs.group_size
    subtotal = date_independent_cost(resort, prefs) + pass_cost + accom + flight_cost_eur(resort)
    return subtotal * 1.05  # misc buffer, matching compute_trip_cost


def shortlist_resorts(resorts: List[Resort], prefs: UserPreferences,
                      top_n: int = 8) -> List[Resort]:
    """
    STAGE 1: prune on date-independent criteria. No API calls, no dates.

    Two filters:
      1. Feasibility -- drop resorts whose optimistic best case already
         exceeds the budget.
      2. Fit -- rank the rest on skill/terrain, off-piste, snow, nightlife
         and transfer convenience, and keep the top N.

    Deliberately does NOT score on price: flight prices are unknown at
    this stage, and pre-judging on the static estimate would bias the
    shortlist toward whatever the placeholder happens to say.
    """
    affordable = [r for r in resorts if cheapest_possible_cost(r, prefs) <= prefs.budget_eur_per_person]
    if not affordable:
        return []

    piste_vals = [r.piste_km for r in resorts]
    piste_range = (min(piste_vals), max(piste_vals))
    transfer_vals = [r.transfer_time_minutes for r in resorts]
    transfer_range = (min(transfer_vals), max(transfer_vals))

    weights = prefs.weights
    scored = []
    for r in affordable:
        piste_score = _normalize(r.piste_km, *piste_range)
        components = {
            "ski_quality": _ski_quality_score(r, prefs, piste_score),
            "snow": r.snow_reliability / 5.0,
            "nightlife": r.nightlife_rating / 5.0,
            "convenience": 1.0 - _normalize(r.transfer_time_minutes, *transfer_range),
        }
        # Renormalize over just the date-independent dimensions, so a user
        # who weights price heavily doesn't end up with a near-zero score
        # for every resort at this stage.
        usable = {k: weights.get(k, 0.0) for k in components}
        total_w = sum(usable.values())
        if total_w <= 0:
            fit = sum(components.values()) / len(components)
        else:
            fit = sum(components[k] * (w / total_w) for k, w in usable.items())
        scored.append((fit, r))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [r for _, r in scored[:top_n]]


def _live_reprice_pairs(to_reprice, prefs, flight_cost_fn, accommodation_cost_fn, score_it):
    """
    Concurrently live-price these (resort, date) pairs and return them
    RESCORED, aligned with the input. Extracted verbatim from
    search_date_range's stage 2 so the same machinery can run twice:
    once over the score-selected candidate set, and once (finalize())
    over the rows actually displayed. Every adapter behind the cost
    fns is response-cached, so overlapping pairs between the two
    passes cost no extra network calls.
    """
    # Fetch every live price CONCURRENTLY before applying any of
    # them.
    #
    # WHY THIS MATTERS MORE THAN IT LOOKS: this loop used to be
    # sequential, and each live lookup is a real 1-2s scrape. That
    # made latency scale linearly with how many results got real
    # prices, which is why live_reprice_n had to be small -- and a
    # small cap is exactly why most rows a user saw were labelled
    # "EST." even with live pricing switched on. The work is pure
    # network I/O, so threads genuinely overlap it: the same 24
    # lookups that took ~35s in sequence finish in a few seconds.
    #
    # Ordering is preserved by mapping futures back to their index,
    # never by completion order -- results must stay deterministic.
    live_flights: dict = {}
    live_accoms: dict = {}
    if to_reprice:
        with ThreadPoolExecutor(max_workers=_LIVE_PRICING_WORKERS) as pool:
            # DEDUPLICATE flight lookups. A flight price depends on
            # the route and the dates, NOT on which resort you're
            # heading to afterwards -- and resorts share airports
            # heavily (INN serves 9 of the mainstream resorts, GVA
            # another 9). Submitting one task per (resort, date)
            # meant several threads racing to fetch the IDENTICAL
            # route: the response cache couldn't help, because they
            # all missed it simultaneously and only populated it
            # after the fact. That is wasted latency AND extra load
            # on a provider that rate-limits, which then costs live
            # prices. Measured on a real 24-pair set: 17 distinct
            # routes, so a quarter of the requests were redundant.
            flight_groups: dict = {}
            if flight_cost_fn is not None:
                for i, opt in enumerate(to_reprice):
                    key = (tuple(airport_codes_for(opt.resort)), opt.start_date, opt.end_date)
                    flight_groups.setdefault(key, []).append(i)
            staggered_flight = _staggered(flight_cost_fn) if flight_cost_fn else None
            staggered_accom = _staggered(accommodation_cost_fn) if accommodation_cost_fn else None
            flight_futures = {
                pool.submit(staggered_flight, to_reprice[idxs[0]].resort,
                            to_reprice[idxs[0]].start_date, to_reprice[idxs[0]].end_date, prefs): idxs
                for idxs in flight_groups.values()
            }
            accom_futures = {
                pool.submit(staggered_accom, opt.resort, opt.start_date, opt.end_date, prefs): i
                for i, opt in enumerate(to_reprice)
            } if accommodation_cost_fn is not None else {}

            for future, idxs in flight_futures.items():
                try:
                    value = future.result()
                except Exception:
                    # Same contract as the sequential version: a
                    # failed lookup keeps the static estimate rather
                    # than dropping the date or failing the search.
                    value = None
                # One fetch answers every pair sharing that route.
                for i in idxs:
                    live_flights[i] = value
            for future, i in accom_futures.items():
                try:
                    live_accoms[i] = future.result()
                except Exception:
                    live_accoms[i] = None

    repriced = []
    for i, opt in enumerate(to_reprice):
        cost = opt.cost
        if flight_cost_fn is not None:
            live_flight = live_flights.get(i)
            # None here keeps the static estimate rather than dropping
            # the date -- SAME contract as the accommodation branch
            # below, and for the same reason: a failed live lookup
            # (provider outage, scrape blocked, transient network
            # error -- adapters/google_flights_adapter.py's own
            # docstring warns this provider can get rate-limited/
            # banned, a real and now much more likely failure mode
            # than the old paid API's) is NOT the same fact as "no
            # flight exists for this date," and treating it as one
            # silently emptied the WHOLE result set on any hiccup --
            # discovered exactly that way while building this swap.
            # The static estimate is still honestly labeled
            # (flight_price_is_live stays False), matching this
            # project's degrade-visibly-not-silently rule everywhere
            # else it applies.
            if live_flight is not None and live_flight != cost.flight_eur:
                cost = apply_live_flight_price(cost, live_flight)
        if accommodation_cost_fn is not None:
            live_accom = live_accoms.get(i)
            # None here just keeps the static estimate -- see this
            # function's docstring on why accommodation degrades
            # differently than flight.
            if live_accom is not None and live_accom != cost.accommodation_eur:
                cost = apply_live_accommodation_price(cost, live_accom)
        repriced.append(score_it(opt.resort, opt.start_date, opt.end_date, cost))
    return repriced


def search_date_range(
    resorts: List[Resort],
    prefs: UserPreferences,
    earliest_date: datetime.date,
    latest_date: datetime.date,
    shortlist_size: int = 8,
    step_days: int = 1,
    start_weekday: Optional[int] = None,
    start_weekdays: Optional[set] = None,
    top_n: int = 10,
    flight_cost_fn: Optional[Callable] = None,
    accommodation_cost_fn: Optional[Callable] = None,
    allow_over_budget_fallback: bool = True,
    live_reprice_n: Optional[int] = None,
    max_results_per_resort: int = 3,
    # See cap_per_resort: False = user-facing result lists, where a
    # shorter varied list beats one padded with duplicate resorts.
    pad_with_duplicates: bool = True,
    # OUT-PARAMETER, filled with one compact record per (resort, start
    # date) for EVERY date evaluated -- not just the rows that survive
    # ranking and capping. See the note below on why the calendar needs
    # this. Left as None by callers that do not want it; never read.
    series_out: Optional[list] = None,
) -> List[DatedTripOption]:
    """
    Full funnel: shortlist resorts, then evaluate each across every
    candidate start date, returning the best (resort, date) combinations.

    flight_cost_fn lets a caller inject live pricing with the signature
    (resort, start_date, end_date, prefs) -> float, or None if no live
    price is available for that date -- in which case the static
    estimate is kept (honestly labeled: flight_price_is_live stays
    False), the SAME contract as accommodation_cost_fn below, not a
    dropped date. Defaults to the static estimate, which keeps this
    fully runnable and testable without an API key.

    accommodation_cost_fn is the same idea for accommodation: signature
    (resort, start_date, end_date, prefs) -> Optional[float] (EUR per
    person for the whole stay), or None if no live price is available
    for that date -- in which case the static season-banded estimate is
    kept. Defaults to None, which reproduces the previous
    accommodation-is-always-static behaviour exactly.

    live_reprice_n CAPS how many (resort, date) pairs actually get
    live-priced -- mirrors scoring.rank_trips' own live_reprice_n
    exactly, added for the same reason: this function's search SPACE is
    shortlist_size resorts x every candidate date, which is easily 30-50+
    pairs, and live-pricing ALL of them (this function's original,
    uncapped behaviour) means 30-50+ sequential SerpApi calls PER
    endpoint PER FLIGHT, doubled again for accommodation -- measured at
    over 20 seconds and a large chunk of a 250-call/month quota for ONE
    page interaction once this was actually wired into a live-key
    deployment (see PROJECT_STATE.md). Default None preserves the exact
    prior unbounded behaviour (every existing caller/test assumed every
    pair gets priced); callers wiring in a REAL cost_fn against a live,
    metered API should pass a real cap (the API layer does).

    Mechanically: EVERY (resort, date) pair is still scored with the
    STATIC estimate first (cheap, no network calls) -- exactly like
    rank_trips scores every resort statically before repricing. Only
    the top `live_reprice_n` of those BY STATIC SCORE then get live
    re-priced; the rest keep their static estimate. This is a real
    behavioural difference from the uncapped path (a date that's mediocre
    on the static estimate but would have been great live is not
    reachable when capped -- same accepted tradeoff rank_trips already
    makes), not a free win; it exists specifically to make live pricing
    for this endpoint actually affordable and fast.

    OVER-BUDGET FALLBACK (allow_over_budget_fallback, default True): see
    scoring.rank_trips' docstring for the full rationale -- same contract
    here. If NOTHING in the window fits the stated budget, this returns
    the cheapest (resort, date) combination(s) found instead of an empty
    list, each tagged DatedTripOption.within_budget=False. This also
    overrides Stage 1's affordability pruning (shortlist_resorts): if
    literally nothing passes that optimistic floor, a small fallback
    shortlist (the resorts with the lowest optimistic floor, not
    necessarily the best FIT) is searched instead, so there's still
    something to report as "the cheapest we found" rather than an empty
    result caused by pruning before pricing even ran.

    RESORT SELECTION: prefs.target_resort / include_resorts /
    exclude_resorts (see narrow_resort_pool, shared with rank_trips) let
    a caller pin the search to specific resorts or exclude some, e.g.
    "only these 3" or "everywhere except Val Thorens". When an EXPLICIT
    pin is active (target_resort or include_resorts -- exclude_resorts
    alone still means "search broadly"), Stage 1's affordability/fit
    pruning is skipped entirely: every explicitly chosen resort is
    scored across every date, full stop, relying on the over-budget
    fallback above (not silent pre-filtering) to handle any that don't
    fit -- the user picked these resorts on purpose.
    """
    starts = candidate_start_dates(earliest_date, latest_date, prefs.nights,
                                   step_days, start_weekday, start_weekdays=start_weekdays)
    if not starts:
        return []

    candidate_pool = narrow_resort_pool(resorts, prefs)
    if not candidate_pool:
        return []

    explicit_pin = bool(prefs.target_resort or prefs.include_resorts)
    if explicit_pin:
        shortlist = candidate_pool
    else:
        shortlist = shortlist_resorts(candidate_pool, prefs, top_n=shortlist_size)
        if not shortlist:
            if not allow_over_budget_fallback:
                return []
            # Nothing passed Stage 1's optimistic affordability floor --
            # fall back to the resorts CLOSEST to affordable, so pricing
            # still has something to search rather than reporting empty
            # over a pruning decision made before any real cost was
            # even computed.
            shortlist = sorted(candidate_pool, key=lambda r: cheapest_possible_cost(r, prefs))[:max(3, shortlist_size // 2)]

    # Normalization ranges come from the FULL, UNNARROWED dataset, not
    # the shortlist/candidate_pool, so scores stay comparable with the
    # fixed-date engine's output even when only 1-3 resorts are in play.
    piste_vals = [r.piste_km for r in resorts]
    transfer_vals = [r.transfer_time_minutes for r in resorts]
    accom_vals = [r.accommodation_eur_per_night for r in resorts]
    ranges = {
        "piste": (min(piste_vals), max(piste_vals)),
        "transfer": (min(transfer_vals), max(transfer_vals)),
        "accom": (min(accom_vals), max(accom_vals)),
    }

    def score_it(resort, start, end, cost):
        # Delegates to scoring.score_resort rather than keeping a second
        # copy of the dimension formulas.
        #
        # It DID keep its own copy until 2026-08-27, and that duplication
        # immediately bit: adding the "family" dimension to score_resort
        # left this branch raising KeyError, because the two had silently
        # drifted apart. CLAUDE.md is explicit that the CLI, the API and
        # this engine must never compute scores three different ways --
        # "if the numbers ever look different, that's a bug to find, not
        # an acceptable inconsistency". Verified equivalent before the
        # swap: same inputs, same formulas, same normalization ranges.
        components = score_resort(
            resort, prefs, cost.total_eur,
            ranges["piste"], ranges["transfer"], ranges["accom"],
        )
        score = sum(components[k] * w for k, w in prefs.weights.items())
        return DatedTripOption(
            resort=resort, start_date=start, end_date=end, cost=cost,
            score=round(score, 4),
            score_components={k: round(v, 3) for k, v in components.items()},
            season=season_band(start),
        )

    # STAGE 1: static cost + score for EVERY (resort, date) pair. No
    # network calls, however large the grid -- see live_reprice_n above.
    all_static = []
    for resort in shortlist:
        for start in starts:
            end = start + datetime.timedelta(days=prefs.nights)
            cost = compute_trip_cost(resort, prefs, start_date=start)
            if not (0 < cost.total_eur):
                continue  # nonsensical cost, never a real result
            all_static.append(score_it(resort, start, end, cost))
    # Sort by score -- with a deliberate TIE-BREAK. Within one season
    # band, static totals tie EXACTLY (measured: Dec 1-18 at Val
    # Thorens, all EUR1620.45), and a bare score sort then surfaces
    # whichever date came first -- which is why every December search
    # used to open on Dec 1 with false precision. Among equals, prefer
    # the SATURDAY start (the classic package changeover, per the same
    # research behind the "weekend" start option), then the earlier
    # date. Live pricing, where it covers a pair, differentiates the
    # scores and makes this tie-break moot.
    all_static.sort(key=lambda t: (-t.score, t.start_date.weekday() != 5, t.start_date))

    # STAGE 2: live-reprice only the top `live_reprice_n` (or ALL of
    # them when live_reprice_n is None -- the original, uncapped path).
    live_active = flight_cost_fn is not None or accommodation_cost_fn is not None
    if live_active:
        cutoff = len(all_static) if live_reprice_n is None else live_reprice_n

        # Choose WHICH pairs to live-price using the SAME per-resort cap
        # the final results use.
        #
        # These two features fight each other otherwise, and did: taking
        # the top `cutoff` purely by static score concentrates repricing
        # on a handful of resorts, but the displayed list is then
        # diversified across MANY resorts -- so most rows a user saw
        # came from pairs that were never repriced at all. Measured:
        # 3 of 12 rows live. Repricing the diversified set instead means
        # the pairs we pay to price are the pairs we actually show.
        to_reprice = cap_per_resort(all_static, cutoff, max_results_per_resort)
        reprice_ids = {id(opt) for opt in to_reprice}
        rest = [opt for opt in all_static if id(opt) not in reprice_ids]

        repriced = _live_reprice_pairs(to_reprice, prefs, flight_cost_fn,
                                       accommodation_cost_fn, score_it)
        all_evaluated = repriced + rest
    else:
        all_evaluated = all_static

    def finalize(rows):
        """
        SECOND repricing pass over exactly the rows being RETURNED.

        WHY (the Bansko bug, owner report 2026-08-29): pass 1 prices
        the top pairs by STATIC score, but live prices usually come
        back HIGHER than the static estimates -- so an un-repriced
        row's optimistic estimate outranks its own resort's freshly
        live-priced dates and wins the display slot. The user then
        sees "EST." on the very rows shown, while live pricing worked
        perfectly (measured live: Bardonecchia Dec 12/19 live, Dec 1
        estimated). Pricing what we display, after deciding what to
        display, is the only assignment that cannot drift. Bounded by
        the returned row count (<= top_n); response caching makes
        pairs already tried in pass 1 free to re-check.

        within_budget is recomputed from the LIVE total, both ways.
        Row ORDER is preserved: re-sorting on the new prices would
        re-introduce the drift this pass exists to close.
        """
        if not live_active:
            return rows
        needs = [t for t in rows
                 if (flight_cost_fn is not None and not t.cost.flight_price_is_live)
                 or (accommodation_cost_fn is not None
                     and not t.cost.accommodation_price_is_live)]
        if not needs:
            return rows
        # An explicit cap is a hard cost bound the caller set: this
        # pass may spend at most that many pairs again (display order
        # decides who gets priced first). The frontend's real shape --
        # top_n=12 under a cap of 24 -- never hits this ceiling.
        if live_reprice_n is not None:
            needs = needs[:live_reprice_n]
        fresh = _live_reprice_pairs(needs, prefs, flight_cost_fn,
                                    accommodation_cost_fn, score_it)
        by_pair = {(t.resort.name, t.start_date): t for t in fresh}
        out = []
        for t in rows:
            f = by_pair.get((t.resort.name, t.start_date))
            if f is None:
                out.append(t)
                continue
            out.append(dc_replace(
                t, cost=f.cost, score=f.score,
                score_components=f.score_components,
                within_budget=f.cost.total_eur <= prefs.budget_eur_per_person))

        # Within each resort, re-rank its OWN display slots on the
        # real (post-repricing) scores -- global positions stay frozen
        # (see the docstring), but "deal 1 of N" for a resort must be
        # its genuinely best deal. Without this, static-estimate ties
        # break toward the earlier date BEFORE the real prices land,
        # and the card leads with a date that is pricier AND
        # lower-scoring than its own alternatives (owner's Bansko
        # report, 2026-08-29). Within-budget rows always outrank
        # over-budget ones, whatever their scores.
        slots: dict = {}
        for i, t in enumerate(out):
            slots.setdefault(t.resort.name, []).append(i)
        for idxs in slots.values():
            if len(idxs) < 2:
                continue
            ranked = sorted((out[i] for i in idxs),
                            key=lambda t: (not t.within_budget, -t.score))
            # The "More dates" alternatives ride on a resort's lead
            # row; keep them on whichever row leads after the re-rank.
            alts = next((t.alternatives for t in ranked if t.alternatives), None)
            for slot, row in zip(idxs, ranked):
                cleaned = dc_replace(row, alternatives=[]) if row.alternatives else row
                out[slot] = cleaned
            if alts:
                out[idxs[0]] = dc_replace(out[idxs[0]], alternatives=alts)
        return out

    # THE PRICE-BY-DATE SERIES, and why it exists.
    #
    # This function answers "what are the best trips", and the answer is
    # capped: top_n rows, at most max_results_per_resort each. Measured
    # 2026-08-30 on a whole-December search: 24 candidate start dates
    # were evaluated and priced, and the response carried THREE distinct
    # dates (5, 12, 19 Dec) across 10 rows -- because the best-scoring
    # rows cluster on the best dates.
    #
    # The price calendar asks a different question -- "what does each
    # day cost" -- and was being fed this ranked list, so 21 of 24
    # priced days rendered blank under a note claiming they had no
    # result. They had a result; it was discarded by the cap.
    #
    # Every figure here is already computed, so this is free.
    if series_out is not None:
        best_per_pair: dict = {}
        for t in all_evaluated:
            key = (t.resort.name, t.start_date)
            seen = best_per_pair.get(key)
            if seen is None or t.cost.total_eur < seen.cost.total_eur:
                best_per_pair[key] = t
        series_out.extend(
            sorted(best_per_pair.values(), key=lambda t: (t.start_date, t.resort.name)))

    results = [t for t in all_evaluated if t.cost.total_eur <= prefs.budget_eur_per_person]

    if results or not allow_over_budget_fallback:
        results.sort(key=lambda t: t.score, reverse=True)
        # User-facing multi-resort searches assemble COVERAGE-FIRST --
        # see assemble_coverage_first's docstring for the user quote and
        # the two measured failures that shaped it. Everything else
        # keeps the original score-ranked capped list.
        distinct_evaluated = {t.resort.name for t in all_evaluated}
        if not pad_with_duplicates and len(distinct_evaluated) >= 2:
            return finalize(assemble_coverage_first(
                results, all_evaluated, prefs.budget_eur_per_person,
                top_n, max_results_per_resort, allow_over_budget_fallback))
        return finalize(cap_per_resort(results, top_n, max_results_per_resort,
                                       pad_with_duplicates=pad_with_duplicates))

    if not all_evaluated:
        return []  # genuinely nothing could be priced at all -- not a budget question

    # FALLBACK: real dates were priced, but none fit -- report the
    # cheapest (resort, date) combination(s) found, flagged honestly.
    # Diversify the fallback too -- "nothing fit your budget" is even
    # more useless as twenty rows of the same resort.
    cheapest_first = sorted(all_evaluated, key=lambda t: t.cost.total_eur)
    fallback = cap_per_resort(cheapest_first, max(top_n, 3), max_results_per_resort,
                              pad_with_duplicates=pad_with_duplicates)
    fallback = [DatedTripOption(
        resort=t.resort, start_date=t.start_date, end_date=t.end_date, cost=t.cost,
        score=t.score, score_components=t.score_components, season=t.season,
        within_budget=False,
    ) for t in fallback]
    return finalize(fallback[:top_n])


def spread_alternative_dates(resort_pool: List[DatedTripOption],
                             shown: DatedTripOption,
                             limit: int = 2) -> tuple:
    """
    Up to `limit` other good dates for one resort, each from a
    DIFFERENT calendar week -- both from each other and from the row
    already shown -- returned chronologically.

    WHY WEEKS, in the user's own words: "I gave a big time range, a
    month, and I only got one date for Val Thorens... everything was
    for the beginning." Static totals tie across adjacent dates, so
    score order alone offers Jan 7/8/9 -- three near-identical copies
    of the shown row. One-best-per-ISO-week turns a month window into
    an early/mid/late spread, which is the comparison a person actually
    wants to make.

    Within each week the BEST-SCORING date wins (not the cheapest --
    same ranking currency as the main list); weeks are then kept in
    score order up to `limit` and presented chronologically.
    """
    shown_week = shown.start_date.isocalendar()[:2]
    best_per_week: dict = {}
    for t in resort_pool:
        if t.resort.name != shown.resort.name:
            continue
        week = t.start_date.isocalendar()[:2]
        if week == shown_week:
            continue
        current = best_per_week.get(week)
        if current is None or t.score > current.score:
            best_per_week[week] = t
    picked = sorted(best_per_week.values(), key=lambda t: t.score, reverse=True)[:max(0, limit)]
    return tuple(sorted(picked, key=lambda t: t.start_date))


def assemble_coverage_first(within_budget_sorted: List[DatedTripOption],
                            all_evaluated: List[DatedTripOption],
                            budget_eur: float,
                            top_n: int,
                            max_per_resort: int,
                            allow_over_budget: bool) -> List[DatedTripOption]:
    """
    Result assembly for a user-facing multi-resort search: SECTION 1 is
    one best offer per selected resort -- affordable resorts first in
    score order, then the priced-out ones flagged within_budget=False
    in ascending price order -- and SECTION 2 fills the remaining slots
    with the rest of the best affordable offers, still capped per
    resort.

    Shaped by the user directly, after two narrower fixes missed the
    point: "start giving the best offer for each resort even if it
    exceeds, and then the rest of the best offers... the budget is a
    goal but I am sure it is not the only thing that matters."

    Two measured failures this replaces (both live, 2026-08-28):
      - default EUR1500 budget: 8 of 10 selected resorts cost
        EUR1526-1785 -- just over -- and were entirely invisible;
      - EUR2500 budget: everything affordable, yet depth-before-breadth
        showed only the 4 best-scoring resorts x 3 dates and hid the
        other six.

    Over-budget rows are never smuggled in as affordable: each carries
    within_budget=False, which the UI renders with an explicit warning
    banner. They appear ONCE each -- pointers to a real alternative,
    not a second ranked list.
    """
    best_within: dict = {}
    for t in within_budget_sorted:
        best_within.setdefault(t.resort.name, t)
    section1: List[DatedTripOption] = list(best_within.values())

    if allow_over_budget:
        over_best: dict = {}
        for t in sorted(all_evaluated, key=lambda t: t.cost.total_eur):
            name = t.resort.name
            if name not in best_within and t.cost.total_eur > budget_eur:
                over_best.setdefault(name, t)
        flagged = [DatedTripOption(
            resort=t.resort, start_date=t.start_date, end_date=t.end_date, cost=t.cost,
            score=t.score, score_components=t.score_components, season=t.season,
            within_budget=False,
        ) for t in over_best.values()]
        flagged.sort(key=lambda t: t.cost.total_eur)
        section1 += flagged

    section1 = section1[:top_n]

    shown = {id(t) for t in best_within.values()}
    per_resort = {}
    for t in section1:
        per_resort[t.resort.name] = per_resort.get(t.resort.name, 0) + 1

    out = list(section1)
    for t in within_budget_sorted:
        if len(out) >= top_n:
            break
        if id(t) in shown:
            continue
        if max_per_resort > 0 and per_resort.get(t.resort.name, 0) >= max_per_resort:
            continue
        per_resort[t.resort.name] = per_resort.get(t.resort.name, 0) + 1
        out.append(t)

    # SECTION 3 (owner's ask, 2026-08-29: "Even if it's over the budget
    # you can show some options with the arrows"): slots STILL left
    # after every affordable offer is in means the priced-out resorts'
    # single teaser rows can grow variants -- more dates, cheapest
    # first, every one flagged within_budget=False so the card's
    # warning banner shows on each. Same per-resort cap as everything
    # else; affordable offers always take priority for slots.
    if allow_over_budget and len(out) < top_n:
        shown_pairs = {(t.resort.name, t.start_date) for t in out}
        extra_over = sorted(
            (t for t in all_evaluated
             if t.cost.total_eur > budget_eur
             and (t.resort.name, t.start_date) not in shown_pairs),
            key=lambda t: t.cost.total_eur)
        for t in extra_over:
            if len(out) >= top_n:
                break
            if max_per_resort > 0 and per_resort.get(t.resort.name, 0) >= max_per_resort:
                continue
            per_resort[t.resort.name] = per_resort.get(t.resort.name, 0) + 1
            out.append(DatedTripOption(
                resort=t.resort, start_date=t.start_date, end_date=t.end_date,
                cost=t.cost, score=t.score, score_components=t.score_components,
                season=t.season, within_budget=False,
            ))

    # Attach the "More dates" alternatives to each resort's FIRST row.
    # dataclasses.replace, not mutation: the rows are shared with the
    # caller's own evaluated pool.
    import dataclasses
    first_index_by_resort: dict = {}
    for i, t in enumerate(out):
        first_index_by_resort.setdefault(t.resort.name, i)
    for name, i in first_index_by_resort.items():
        alts = spread_alternative_dates(all_evaluated, out[i], limit=2)
        if alts:
            out[i] = dataclasses.replace(out[i], alternatives=alts)
    return out


def cap_per_resort(options: List[DatedTripOption], top_n: int,
                   max_per_resort: int,
                   pad_with_duplicates: bool = True) -> List[DatedTripOption]:
    """
    Keeps the result list VARIED: at most `max_per_resort` dates from
    any one resort, then fills any remaining slots with the next best
    options regardless of resort.

    THE PROBLEM THIS SOLVES: a raw score sort is monopolised by whichever
    resort happens to be cheapest. Search a 20-day window and Bansko --
    genuinely the cheapest destination in the database -- takes every
    slot, so the answer to "where should I ski?" is twenty flavours of
    the same week in the same place. That is technically the correct
    ranking and a useless one: nobody is choosing between Bansko on the
    11th and Bansko on the 12th, they are choosing between Bansko and
    Val Thorens.

    The two-pass fill matters. A strict cap alone would hurt the
    opposite case: someone who pinned the search to ONE resort
    ("when should I go to Chamonix?") would get 3 results instead of the
    12 they asked for. So pass one enforces variety, pass two backfills
    from what's left in score order -- a single-resort search returns a
    full list of that resort's best dates, exactly as before.

    Input is assumed already sorted best-first; ordering within each
    pass is preserved, so the very best option is always still first.
    """
    if max_per_resort <= 0:
        return options[:top_n]

    per_resort: dict = {}
    picked: List[DatedTripOption] = []
    leftovers: List[DatedTripOption] = []

    for opt in options:
        name = opt.resort.name
        if per_resort.get(name, 0) < max_per_resort:
            per_resort[name] = per_resort.get(name, 0) + 1
            picked.append(opt)
        else:
            leftovers.append(opt)

    # pad_with_duplicates=False suppresses the backfill UNLESS the pool
    # is effectively one resort (the pinned "when should I go to
    # Chamonix?" case, where 12 dates of one place is exactly the
    # question asked). It exists for user-facing result lists:
    # reproduced in production 2026-08-28, a two-resort pool at
    # top_n=12 returned Bansko NINE times -- the cap filled 3+3 and the
    # backfill padded the remaining six slots with more of the cheapest
    # resort, whose statically-estimated duplicate rows even carry
    # identical totals. A shorter varied list beats a padded one.
    #
    # The default stays True because engine-level callers legitimately
    # use a huge top_n to mean "give me the whole pool" (e.g. to
    # reprice or analyse every candidate date) -- silently shrinking
    # their result set broke three of their tests when this was first
    # made unconditional.
    distinct_resorts = len(per_resort)
    if len(picked) < top_n and (pad_with_duplicates or distinct_resorts < 2):
        picked.extend(leftovers[: top_n - len(picked)])
    return picked[:top_n]


def best_date_per_resort(options: List[DatedTripOption]) -> List[DatedTripOption]:
    """
    Collapses to the single best date for each resort.

    Answers "if I specifically want St. Anton, when should I go?" -- and
    stops one resort with a cheap week from monopolising the whole result
    list, which a raw score sort otherwise tends to do.
    """
    best = {}
    for opt in options:
        current = best.get(opt.resort.name)
        if current is None or opt.score > current.score:
            best[opt.resort.name] = opt
    return sorted(best.values(), key=lambda t: t.score, reverse=True)


def price_sensitivity(options: List[DatedTripOption], resort_name: str) -> Optional[dict]:
    """
    How much does timing actually matter for one resort?

    Powers the genuinely differentiating output: "shifting a week saves
    EUR200" vs "timing barely matters here, book whenever suits you".
    Returns None when there aren't at least two dates to compare.
    """
    same = [o for o in options if o.resort.name == resort_name]
    if len(same) < 2:
        return None
    cheapest = min(same, key=lambda o: o.total_eur)
    dearest = max(same, key=lambda o: o.total_eur)
    return {
        "resort": resort_name,
        "cheapest_date": cheapest.start_date,
        "cheapest_eur": round(cheapest.total_eur, 2),
        "most_expensive_date": dearest.start_date,
        "most_expensive_eur": round(dearest.total_eur, 2),
        "spread_eur": round(dearest.total_eur - cheapest.total_eur, 2),
        "dates_compared": len(same),
    }
