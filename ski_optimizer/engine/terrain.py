"""
Structured terrain data for scoring: beginner/intermediate/advanced
fractions, plus a fallback parser for free-text terrain descriptions.

AS OF THE TERRAIN DATA MIGRATION, the primary construction path is
TerrainMix.from_percentages(), reading real numbers straight out of the
spreadsheet's Beginner %/Intermediate %/Advanced % columns (see
data/resort_repository.py). Every resort in the seed database has a
value there now -- either a genuinely sourced breakdown or a clearly
flagged estimate (see terrain_data_quality on Resort).

parse_terrain_mix() below is kept as a FALLBACK ONLY, for any future
resort added with prose-only terrain data before someone gets round to
sourcing real numbers for it (see migrate_terrain_columns.py for how
the original 30 were converted). It has the same honesty policy as
before: when the text carries no usable numbers, it returns None rather
than guessing -- callers must handle that, not assume a default.
"""
import re
from dataclasses import dataclass
from typing import Optional

# Difficulty vocabulary -> which bucket(s) a label contributes to.
# Piste-colour conventions: green = true beginner, blue = easy (beginner
# -leaning), red = intermediate, black = advanced. European grading is
# not standardized across countries, so this is approximate by nature.
_LABEL_TO_BUCKETS = {
    "beg": ("beginner",),
    "green": ("beginner",),
    "easy": ("beginner",),
    "blue": ("beginner",),
    "int": ("intermediate",),
    "red": ("intermediate",),
    "adv": ("advanced",),
    "exp": ("advanced",),
    "black": ("advanced",),
}


@dataclass
class TerrainMix:
    """Fractions summing to ~1.0. Source is kept for transparency/debugging."""
    beginner: float
    intermediate: float
    advanced: float
    source: str  # 'sourced' | 'sourced_conflicting' | 'estimated' | 'percentages' | 'run_counts'

    @classmethod
    def from_percentages(cls, beginner_pct: float, intermediate_pct: float,
                         advanced_pct: float, quality: str) -> "TerrainMix":
        """
        Builds directly from the spreadsheet's numeric Beginner %/Intermediate
        %/Advanced % columns (see data/resort_repository.py). This is the
        normal construction path today -- every resort has real numbers now,
        whether sourced or a flagged estimate (quality tells you which).
        """
        total = beginner_pct + intermediate_pct + advanced_pct
        return cls(
            beginner=beginner_pct / total,
            intermediate=intermediate_pct / total,
            advanced=advanced_pct / total,
            source=quality,
        )

    def fraction_for_skill(self, skill_level: str) -> float:
        """
        How much of this resort's terrain suits the given skier.

        A skier is served by terrain at their level AND below it (an
        advanced skier can happily ski a red run; a beginner cannot ski
        a black one). So this is cumulative downward, not just the
        single matching band -- otherwise a resort that's 90%
        intermediate would score terribly for an advanced skier, which
        is plainly wrong.
        """
        if skill_level == "beginner":
            return self.beginner
        if skill_level == "intermediate":
            return self.beginner + self.intermediate
        # advanced / expert
        return self.beginner + self.intermediate + self.advanced

    def challenge_for_skill(self, skill_level: str) -> float:
        """
        How much terrain will actually *challenge* this skier -- i.e.
        terrain at or above their level. This is the counterweight to
        fraction_for_skill(): an advanced skier is technically 'served'
        by 100% of a beginner hill, but would be bored senseless.
        """
        if skill_level == "beginner":
            return self.beginner + self.intermediate + self.advanced
        if skill_level == "intermediate":
            return self.intermediate + self.advanced
        return self.advanced


def _normalize(beginner: float, intermediate: float, advanced: float,
               source: str) -> Optional[TerrainMix]:
    total = beginner + intermediate + advanced
    if total <= 0:
        return None
    return TerrainMix(
        beginner=beginner / total,
        intermediate=intermediate / total,
        advanced=advanced / total,
        source=source,
    )


def _distribute(value: float, labels_found: list, buckets: dict) -> None:
    """Splits `value` evenly across every bucket the matched labels map to."""
    targets = []
    for label in labels_found:
        targets.extend(_LABEL_TO_BUCKETS[label])
    if not targets:
        return
    share = value / len(targets)
    for target in targets:
        buckets[target] += share


def _find_labels(segment: str) -> list:
    """
    Returns every difficulty label in a segment, in order, de-duplicated.
    'Beg-Int' -> ['beg', 'int']; 'Adv (black)' -> ['adv'] (not double-counted).
    """
    found = []
    for label in _LABEL_TO_BUCKETS:
        if re.search(rf"\b{label}", segment):
            if label not in found:
                found.append(label)
    # 'adv' and 'black' (or 'beg'/'green') in one segment mean the same
    # band stated twice -- collapse to a single bucket set to avoid
    # splitting the value across what is really one category.
    collapsed = []
    seen_buckets = set()
    for label in found:
        buckets = _LABEL_TO_BUCKETS[label]
        if buckets[0] in seen_buckets:
            continue
        seen_buckets.add(buckets[0])
        collapsed.append(label)
    return collapsed


def parse_terrain_mix(text: str) -> Optional[TerrainMix]:
    """
    Returns a TerrainMix, or None when the text carries no usable numbers.
    None is a legitimate, expected result -- do not treat it as an error.
    """
    if not text:
        return None
    lowered = str(text).lower()

    buckets = {"beginner": 0.0, "intermediate": 0.0, "advanced": 0.0}

    # --- Attempt 1: explicit percentages, e.g. '40% Beg, 20% Adv-Exp' ---
    # Split on commas so each 'NN% label' pair is scoped to its own segment.
    pct_pairs = re.findall(r"(\d+)\s*%\s*([^,;]*)", lowered)
    if pct_pairs:
        for value_str, segment in pct_pairs:
            labels = _find_labels(segment)
            if labels:
                _distribute(float(value_str), labels, buckets)
        result = _normalize(buckets["beginner"], buckets["intermediate"],
                            buckets["advanced"], "percentages")
        if result:
            return result

    # --- Attempt 2: run counts, e.g. '8 green, 36 blue, 23 red, 9 black' ---
    # Only counts as a match if we find at least two colour/level pairs,
    # so a stray number elsewhere in the prose can't trigger this path.
    buckets = {"beginner": 0.0, "intermediate": 0.0, "advanced": 0.0}
    count_pairs = re.findall(r"(\d+)\s+(green|blue|red|black)", lowered)
    if len(count_pairs) >= 2:
        for value_str, colour in count_pairs:
            _distribute(float(value_str), [colour], buckets)
        result = _normalize(buckets["beginner"], buckets["intermediate"],
                            buckets["advanced"], "run_counts")
        if result:
            return result

    # --- No usable numbers: say so honestly rather than guessing. ---
    return None
