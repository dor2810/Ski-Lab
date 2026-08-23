"""
Phase 2 demo: given a user's preferences, load the resort database,
compute a real cost breakdown for every resort, filter by hard
constraints, score the survivors, and print the ranked results.

Run with:  python -m ski_optimizer.cli.main

This stays a useful dev/debug entrypoint even after api/ exists later --
it's the fastest way to exercise engine/ without spinning up a server.
"""
from ..data.resort_repository import load_resorts
from ..models import UserPreferences
from ..engine.scoring import rank_trips
from ..nlp.explainer import explain


def print_trip(rank: int, trip, skill_level: str = None) -> None:
    r, c = trip.resort, trip.cost
    print(f"\nTrip {rank} — {r.name}, {r.country}  (score {trip.score:.3f})")
    print(f"  Total est. cost per person: €{c.total_eur:,.0f}")
    print(f"    Flight (TLV est.):     €{c.flight_eur:,.0f}")
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
    # Israeli intermediate/advanced skier, 5 nights, max €1500, cares far
    # more about skiing/off-piste than luxury, ok with a longer transfer
    # to save money, wants nightlife but doesn't care about fine dining.
    prefs = UserPreferences(
        budget_eur_per_person=1500,
        trip_nights=5,
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
    print(f"Budget: €{prefs.budget_eur_per_person}/person · {prefs.trip_nights} nights · "
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
        trip_nights=5,
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


if __name__ == "__main__":
    main()
