"""
[PHASE 6 — not implemented yet]

Turns free text ("I'm intermediate/advanced, 5 nights, max €1500, care
more about off-piste than luxury...") into a structured UserPreferences
object. This is the other LLM-touching file alongside explainer.py --
same rule applies: the LLM's job is producing a UserPreferences object
(constraints + weights), never a price or a score. Once parsed, the
rest of the pipeline (engine/) works exactly as it does today when
UserPreferences is built by hand.

Planned interface:

    def parse_preferences(text: str) -> UserPreferences:
        '''
        Calls an LLM with a prompt that maps free text to the
        UserPreferences schema (budget, nights, group_size, skill_level,
        accommodation_tier, food_profile, weights dict). Should validate
        the result against the dataclass's own constraints (e.g. weights
        summing to 1.0) before returning -- reject/retry on a malformed
        response rather than silently coercing it.
        '''
        raise NotImplementedError
"""
from ..models import UserPreferences


def parse_preferences(text: str) -> UserPreferences:
    raise NotImplementedError(
        "Natural-language preference parsing is planned for Phase 6 (see module docstring). "
        "Build UserPreferences directly until then (see cli/main.py for examples)."
    )
