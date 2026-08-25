"""
Phase 2 demo: given a user's preferences, load the resort database,
compute a real cost breakdown for every resort, filter by hard
constraints, score the survivors, and print the ranked results.

Run with:  python -m ski_optimizer.cli.main

This stays a useful dev/debug entrypoint even after api/ exists later --
it's the fastest way to exercise engine/ without spinning up a server.
"""
import datetime
import os

from ..data.resort_repository import load_resorts
from ..models import UserPreferences
from ..engine.cost_calculator import live_flight_cost_eur, live_accommodation_cost_eur_per_person
from ..engine.scoring import rank_trips
from ..engine.date_search import search_date_range, best_date_per_resort
from ..nlp.explainer import explain


def print_trip(rank: int, trip, skill_level: str = None) -> None:
    r, c = trip.resort, trip.cost
    print(f"\nTrip {rank} — {r.name}, {r.country}  (score {trip.score:.3f})")
    print(f"  Total est. cost per person: €{c.total_eur:,.0f}")
    flight_label = "TLV live" if c.flight_price_is_live else "TLV est."
    print(f"    Flight ({flight_label}):     €{c.flight_eur:,.0f}")
    print(f"    Airport transfer:      €{c.transfer_eur:,.0f}")
    print(f"    Accommodation:         €{c.accommodation_eur:,.0f}")
    print(f"    Ski pass:               €{c.ski_pass_eur:,.0f}")
    print(f"    Equipment rental:       €{c.equipment_eur:,.0f}")
    print(f"    Food:                   €{c.food_eur:,.0f}")
    print(f"    Misc/buffer:            €{c.misc_eur:,.0f}")
    print(f"  Off-piste {r.off_piste_rating}/5 · Snow {r.snow_reliability}/5 · "
          f"Nightlife {r.nightlife_rating}/5 · Transfer ~{r.transfer_time_minutes:.0f}min from {r.nearest_airport}")
    print(f"  {explain(trip, skill_level=skill_level)}")


def main():
    resorts = load_resorts()

    # Reproduces the example scenario from the original project spec:
    # Israeli intermediate/advanced skier, 5 ski days, max €1500, cares far
    # more about skiing/off-piste than luxury, ok with a longer transfer
    # to save money, wants nightlife but doesn't care about fine dining.
    prefs = UserPreferences(
        budget_eur_per_person=1500,
        ski_days=5,
        group_size=2,
        skill_level="advanced",
        accommodation_tier="budget",
        food_profile="normal",
        equipment_tier="standard",
        weights={
            "ski_quality": 0.35,
            "price": 0.15,
            "snow": 0.15,
            "nightlife": 0.15,
            "convenience": 0.05,
            "accommodation": 0.15,
        },
    )

    results = rank_trips(resorts, prefs, top_n=5)

    print(f"Loaded {len(resorts)} resorts from the seed database.")
    print(f"Budget: €{prefs.budget_eur_per_person}/person · {prefs.ski_days} ski days ({prefs.nights} nights) · "
          f"group of {prefs.group_size}")
    if not results:
        print("\nNo resorts fit within budget at these settings.")
        return
    print(f"\n{len(results)} trips fit within budget, ranked by weighted score:")
    for i, trip in enumerate(results, start=1):
        print_trip(i, trip, skill_level=prefs.skill_level)

    # --- "Fixed resort" mode demo ---
    # For a user who already knows where they want to go, set target_resort
    # instead of letting the engine pick. IMPORTANT: with today's static,
    # date-independent flight/accommodation estimates, this can only tell
    # you the cost for THIS resort at THESE settings -- it cannot yet tell
    # you which WEEK is cheapest. See engine/date_search.py (Phase 4+).
    print("\n" + "=" * 70)
    print("Fixed-resort mode demo: 'I already want to go to Livigno'")
    fixed_prefs = UserPreferences(
        budget_eur_per_person=1500,
        ski_days=5,
        group_size=2,
        accommodation_tier="budget",
        target_resort="Livigno",
        weights=prefs.weights,
    )
    fixed_results = rank_trips(resorts, fixed_prefs, top_n=1)
    if fixed_results:
        print_trip(1, fixed_results[0], skill_level=fixed_prefs.skill_level)
    print("\n(NOTE: this cost is date-independent right now -- see engine/date_search.py")
    print(" for what's needed to find the actual cheapest/best week, not just one estimate.)")

    # --- Live flight pricing demo ---
    # Same fixed-resort mode, but with outbound_date set and a live
    # flight_cost_fn wired in -- exercises the exact path Part 1 added.
    # No SERPAPI_API_KEY gate any more: live_flight_cost_eur is backed
    # by adapters/google_flights_adapter.py, which needs no key -- see
    # its module docstring.
    print("\n" + "=" * 70)
    print("Live flight pricing demo: Val Thorens, Jan 2-9 2027")
    dated_prefs = UserPreferences(
        budget_eur_per_person=1500,
        ski_days=5,
        group_size=2,
        accommodation_tier="budget",
        target_resort="Val Thorens",
        outbound_date=datetime.date(2027, 1, 2),
        weights=prefs.weights,
    )

    def _live_flight_cost_fn(resort, start_date, end_date, _prefs):
        return live_flight_cost_eur(resort, start_date, end_date, origin_airport="TLV")

    dated_results = rank_trips(resorts, dated_prefs, top_n=1, flight_cost_fn=_live_flight_cost_fn)
    if dated_results:
        print_trip(1, dated_results[0], skill_level=dated_prefs.skill_level)
    else:
        print("No result -- either out of budget once live-priced, or the live call failed.")

    # --- Date-range search demo: "resort + window + trip length -> deals" ---
    # This is the product's second query mode (see engine/date_search.py's
    # module docstring): fixed resort and duration, flexible dates -- exactly
    # "give me a 10-day range for a 7-day vacation, find good deals in it."
    # Same API::POST /trips/search-dates wraps this exact call.
    print("\n" + "=" * 70)
    print("Date-range search demo: Val Thorens, 7 ski days, anytime in a 10-day window")
    window_prefs = UserPreferences(
        budget_eur_per_person=2300,
        ski_days=7,
        group_size=2,
        accommodation_tier="standard",
        target_resort="Val Thorens",
        weights=prefs.weights,
    )
    val_thorens = [r for r in resorts if r.name.strip().lower() == "val thorens"]
    earliest = datetime.date(2027, 1, 10)
    latest = datetime.date(2027, 1, 20)  # 10-day window

    # flight_fn always wired now (no key needed, see the demo above);
    # accom_fn stays gated -- live accommodation still needs SerpApi.
    def flight_fn(resort, start_date, end_date, _prefs):
        return live_flight_cost_eur(resort, start_date, end_date, origin_airport="TLV")

    accom_fn = None
    if os.environ.get("SERPAPI_API_KEY"):
        def accom_fn(resort, start_date, end_date, _prefs):
            return live_accommodation_cost_eur_per_person(
                resort, start_date, nights=window_prefs.nights,
                group_size=window_prefs.group_size, rooms_needed=window_prefs.rooms_needed)

    dated = search_date_range(
        val_thorens, window_prefs, earliest, latest,
        shortlist_size=1, top_n=10, flight_cost_fn=flight_fn, accommodation_cost_fn=accom_fn,
    )
    if not dated:
        print("No date in this window fits the budget (static estimates, or live pricing failed).")
    else:
        print(f"{len(dated)} candidate date(s) fit the budget, best first:")
        for i, opt in enumerate(best_date_per_resort(dated), start=1):
            print(f"\n  #{i}: {opt.start_date} -> {opt.end_date}  (score {opt.score:.3f}, {opt.season} season)")
            print(f"      Total est. cost per person: €{opt.total_eur:,.0f}  "
                  f"(flight €{opt.cost.flight_eur:,.0f}, accommodation €{opt.cost.accommodation_eur:,.0f})")
    if not os.environ.get("SERPAPI_API_KEY"):
        print("\n(Flight prices above are already real/live (no key needed) --")
        print(" set SERPAPI_API_KEY in .env to also see REAL accommodation prices,")
        print(" not just the season-banded static estimate.)")


if __name__ == "__main__":
    main()
