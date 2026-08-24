"""
Turns a TripOption into a plain-English explanation.

Today this is a simple template (extracted straight out of the old
cli/main.py demo) -- no LLM involved yet. Per the blueprint's own rule
("the LLM should never invent a price"), this file's interface won't
change when an LLM-based version replaces the template in Phase 6: the
signature is always `TripOption -> str`. Everything the explanation
draws on (scores, cost breakdown, resort facts) still comes from
engine/ and models.py, not from the LLM -- an LLM version of this
function would only be asked to phrase already-computed facts more
naturally / conversationally, never to invent new ones.
"""
from ..models import TripOption

_DIM_LABELS = {
    "ski_quality": "strong skiing/off-piste",
    "price": "good value against your budget",
    "snow": "reliable snow",
    "nightlife": "good nightlife",
    "convenience": "short transfer",
    "accommodation": "accommodation matching your comfort level",
}


def _terrain_note(trip: TripOption, skill_level: str) -> str:
    """
    Says something concrete about terrain fit, and is explicit about
    whether that figure is a genuinely sourced number or an estimate --
    both exist in the database (see terrain_data_quality), and treating
    them identically would overstate confidence in the estimated ones.
    """
    tm = trip.resort.terrain_mix
    if tm is None:
        return (" Terrain fit for your level wasn't scored here — this resort's "
                "terrain breakdown isn't in the database yet.")
    pct = {
        "beginner": tm.beginner,
        "intermediate": tm.intermediate,
        "advanced": tm.advanced,
        "expert": tm.advanced,
    }.get(skill_level, tm.intermediate)
    label = {
        "beginner": "beginners",
        "intermediate": "intermediates",
        "advanced": "advanced skiers",
        "expert": "expert skiers",
    }.get(skill_level, "intermediates")
    quality = trip.resort.terrain_data_quality
    if quality == "estimated":
        qualifier = " (estimated, not a published figure)"
    elif quality == "sourced_conflicting":
        qualifier = " (published sources disagree on this — treat as approximate)"
    else:
        qualifier = ""
    return f" Terrain: {pct:.0%} graded for {label}{qualifier}."


def explain(trip: TripOption, top_n: int = 3, skill_level: str = None) -> str:
    top_dims = sorted(trip.score_components.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    bits = [_DIM_LABELS[dim] for dim, _ in top_dims]
    out = f"Why: {', '.join(bits)}."
    if skill_level:
        out += _terrain_note(trip, skill_level)
    if trip.resort.needs_verification:
        out += " (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB)"
    if trip.cost.flight_price_is_live:
        out += " Flight price is live, checked just now."
    if trip.cost.accommodation_price_is_live:
        out += " Accommodation price is live, checked just now."
    if not trip.within_budget:
        out += (" NOTE: this is OVER your stated budget -- it's the cheapest option "
                "found, shown because nothing fit within budget.")
    return out


# --- [PHASE 6] LLM-based version, not implemented yet ---
#
# def explain_conversational(trip: TripOption, user_question: str = None) -> str:
#     '''
#     Same TripOption -> str contract as explain() above, but phrased
#     naturally by an LLM and able to answer a specific follow-up
#     question ("why is this better than Chamonix for me?"). The LLM
#     prompt should be given trip.score_components, trip.cost, and
#     trip.resort as structured context -- it should never be asked to
#     produce or guess at a number that isn't already in those objects.
#     '''
#     raise NotImplementedError
