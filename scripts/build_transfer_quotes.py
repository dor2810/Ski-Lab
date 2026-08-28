"""
Freeze REAL Alps2Alps transfer quotes for every resort -- and record
the exact reason for every resort where they can't be had.

WHY FROZEN (measured 2026-08-28, not assumed): Alps2Alps' public API
allows ~14 calls before returning 429, and the cooldown runs well past
TEN MINUTES. A single 12-result search would need ~36 calls, so live
per-search pricing is arithmetically impossible -- which is why the
transfer line has always been a static estimate while every other line
went live. Fetching each route once, offline and slowly, is the only
way to put REAL Alps2Alps numbers in front of a user.

Same approach as scripts/build_lift_locations.py, and for the same
reason: this data is stable (airport-to-resort road transfer pricing
moves seasonally, not per-request).

RESUMABLE: progress is written after every resort, so a run that trips
the limit can be restarted and will skip what it already has.

Usage: PYTHONPATH=. python3 scripts/build_transfer_quotes.py [group_size]
"""
import datetime
import json
import os
import sys
import time

from ski_optimizer.adapters import transfer_adapter as ta
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.data.resort_repository import load_resorts

PROGRESS = "scripts/.transfer_quotes_progress.json"
OUT = "ski_optimizer/data/transfer_quotes.py"

# Measured limit: ~14 calls per window, cooldown >10min. One call every
# 40s never trips it; a 429 still triggers a long, explicit sleep.
_SPACING_S = 40
_COOLDOWN_S = 720
# The reference quote date -- a normal in-season Saturday changeover.
_QUOTE_DATE = datetime.date(2027, 1, 9)


def load_progress() -> dict:
    if os.path.exists(PROGRESS):
        return json.load(open(PROGRESS))
    return {}


def save_progress(data: dict) -> None:
    json.dump(data, open(PROGRESS, "w"), indent=1)


def quote_one(resort, adults: int) -> dict:
    """Real quote, or the precise reason there isn't one."""
    airport_query = ta._airport_city_name(resort.nearest_airport)
    try:
        origin = ta.resolve_location(airport_query, location_type="airport")
        if origin is None:
            return {"status": "no_airport_match",
                    "why": f"Alps2Alps has no location matching the airport {airport_query!r} "
                           f"(from the resort's airport field {resort.nearest_airport!r})"}
        time.sleep(_SPACING_S)
        dest = ta.resolve_location(resort.name, location_type="resort")
        if dest is None:
            return {"status": "no_resort_match",
                    "why": f"Alps2Alps has no destination matching the resort name "
                           f"{resort.name!r} -- they do not serve it, or list it under another name"}
        time.sleep(_SPACING_S)
        result = ta.search_transfer_options(resort, _QUOTE_DATE, "10:00", adults=adults,
                                            use_cache=False)
        if not result.options:
            return {"status": "no_vehicles",
                    "why": f"Alps2Alps resolved both ends ({origin} -> {dest}) but returned no "
                           f"vehicle able to carry {adults} passengers on this route"}
        cheapest = min(result.options, key=lambda o: o.price_eur)
        return {
            "status": "ok",
            "price_eur": round(cheapest.price_eur, 2),
            "duration_minutes": getattr(cheapest, "duration_minutes", None),
            "vehicle": getattr(cheapest, "vehicle_type", None),
            "vehicles_offered": len(result.options),
            "origin_code": origin,
            "dest_code": dest,
        }
    except AdapterError as exc:
        if "rate limit" in str(exc).lower():
            raise
        return {"status": "adapter_error", "why": str(exc)[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"status": type(exc).__name__, "why": str(exc)[:200]}


def main() -> None:
    adults = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    key_prefix = f"{adults}:"
    progress = load_progress()
    resorts = load_resorts()

    for resort in resorts:
        key = key_prefix + resort.name
        if key in progress:
            continue
        while True:
            try:
                entry = quote_one(resort, adults)
                break
            except AdapterError:
                print(f"  rate limited -- sleeping {_COOLDOWN_S}s", flush=True)
                time.sleep(_COOLDOWN_S)
        progress[key] = entry
        save_progress(progress)
        detail = entry.get("price_eur") or entry.get("why", "")
        print(f'  {entry["status"]:<18} {resort.name[:28]:<30} {str(detail)[:60]}', flush=True)
        time.sleep(_SPACING_S)

    write_module(progress, adults)


def write_module(progress: dict, adults: int) -> None:
    rows = {k.split(":", 1)[1]: v for k, v in progress.items() if k.startswith(f"{adults}:")}
    ok = {k: v for k, v in rows.items() if v["status"] == "ok"}
    bad = {k: v for k, v in rows.items() if v["status"] != "ok"}
    lines = [
        '"""',
        "REAL Alps2Alps transfer quotes, frozen per resort.",
        "",
        "GENERATED by scripts/build_transfer_quotes.py -- do not hand-edit.",
        f"Captured for {adults} passengers, pickup {_QUOTE_DATE.isoformat()} 10:00,",
        "cheapest vehicle on each route, EUR, one-way.",
        "",
        "WHY FROZEN: Alps2Alps allows ~14 API calls before a 429 whose",
        "cooldown exceeds ten minutes (measured). A 12-result search would",
        "need ~36 calls, so live per-search quoting is impossible -- this is",
        "how real Alps2Alps numbers reach the user at all.",
        "",
        "UNQUOTED_ROUTES records, per resort, exactly WHY no quote exists.",
        '"""',
        "",
        "TRANSFER_QUOTES: dict[str, dict] = {",
    ]
    for name in sorted(ok):
        v = ok[name]
        lines.append(f"    {name!r}: {{")
        lines.append(f'        "price_eur": {v["price_eur"]},')
        lines.append(f'        "duration_minutes": {v["duration_minutes"]},')
        lines.append(f'        "vehicle": {v["vehicle"]!r},')
        lines.append(f'        "vehicles_offered": {v["vehicles_offered"]},')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("#: resort -> the precise reason Alps2Alps cannot quote it.")
    lines.append("UNQUOTED_ROUTES: dict[str, str] = {")
    for name in sorted(bad):
        lines.append(f"    {name!r}: {bad[name].get('why', bad[name]['status'])!r},")
    lines.append("}")
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote {len(ok)} quotes, {len(bad)} documented gaps -> {OUT}")


if __name__ == "__main__":
    main()
