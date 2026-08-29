"""
Removes resorts that are no longer in the seed spreadsheet from the
per-resort data modules that are keyed by resort name.

WHY NOT JUST RE-RUN THE GENERATORS: build_transfer_quotes.py,
build_alps2alps_locations.py and build_omio_positions.py all reach out
to live third-party services. Re-running them to delete ten dictionary
keys would re-scrape every surviving route, cost real requests, and risk
churning quotes that are currently correct. Deleting the dead keys in
place is the smaller, safer change.

The modules this touches carry hand-written rationale in comments and
docstrings, so this deliberately does NOT regenerate them from parsed
data -- that would silently discard the reasoning. It deletes only the
lines belonging to a removed resort and leaves everything else byte for
byte identical.

Entry shapes handled:
    "Resort Name": "https://...",              single line
    'Resort Name': {                           multi-line dict
        "price_eur": 302.5,
    },
    'Resort Name': [                           multi-line list
        (46.29701, 14.53004),
    ],

Both bracket kinds are counted together. Tracking only '{' truncated
ski_lift_locations.py mid-list and left the module unparseable, so the
depth counter deliberately covers '[' as well.

Usage: PYTHONPATH=. python3 scripts/prune_dropped_resorts.py [--dry-run]
"""
import re
import sys

from ski_optimizer.data.resort_repository import load_resorts

TARGETS = [
    "ski_optimizer/data/ski_pass_links.py",
    "ski_optimizer/data/equipment_rental_links.py",
    "ski_optimizer/data/mainstream_resorts.py",
    "ski_optimizer/data/transfer_quotes.py",
    "ski_optimizer/data/alps2alps_locations.py",
    "ski_optimizer/data/omio_positions.py",
    "ski_optimizer/data/ski_lift_locations.py",
    "ski_optimizer/data/ski_pass_prices.py",
]

#: Names dropped by the 2026-08-29 resort/airport review. Explicit rather
#: than "any key the spreadsheet no longer has", because these files also
#: contain NESTED dicts whose inner keys ("price_eur", "airport_code")
#: are not resort names and must never be matched.
DROPPED = {
    "Astún-Candanchú", "Formigal", "Vallnord (Pal-Arinsal)", "Poiana Brasov",
    "Krvavec", "Sella Ronda (Dolomiti)", "Pamporovo", "Obergurgl-Hochgurgl",
    "Méribel", "Avoriaz",
}


def entry_key(line: str):
    """The dict key a line opens, or None if the line isn't an entry."""
    match = re.match(r"""\s+(['"])(.+?)\1\s*:""", line)
    return match.group(2) if match else None


def _depth(line: str) -> int:
    """Net bracket depth a line opens, across all three bracket kinds: a
    value may be a dict '{', a coordinate list '[', or a constructor call
    'SkiPassPrice('."""
    opened = line.count("{") + line.count("[") + line.count("(")
    closed = line.count("}") + line.count("]") + line.count(")")
    return opened - closed


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def prune_file(path: str) -> tuple:
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    kept, removed = [], []
    index = 0
    while index < len(lines):
        line = lines[index]
        if entry_key(line) in DROPPED:
            removed.append(entry_key(line))
            depth = _depth(line)
            key_indent = _indent(line)
            index += 1
            if depth > 0:
                # Bracketed value: consume to its closing bracket, which
                # sits at the SAME indent as the key, so an indent test
                # alone would stop one line early.
                while depth > 0 and index < len(lines):
                    depth += _depth(lines[index])
                    index += 1
            else:
                # Unbracketed value that may continue onto further lines
                # as an implicitly concatenated string. Those
                # continuations are indented deeper than the key.
                while index < len(lines) and _indent(lines[index]) > key_indent:
                    index += 1
            continue
        kept.append(line)
        index += 1

    return kept, removed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    live = {resort.name for resort in load_resorts()}
    print(f"{len(live)} live resorts; pruning {len(DROPPED)} dropped\n")

    still_present = DROPPED & live
    if still_present:
        raise SystemExit(f"these are still in the spreadsheet: {sorted(still_present)}")

    total = 0
    for path in TARGETS:
        kept, removed = prune_file(path)
        if removed:
            if not dry_run:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.writelines(kept)
            print(f"{path}: removed {len(removed)} -> {sorted(set(removed))}")
            total += len(removed)
        else:
            print(f"{path}: nothing to remove")

    print(f"\n{'would remove' if dry_run else 'removed'} {total} entries")


if __name__ == "__main__":
    main()
