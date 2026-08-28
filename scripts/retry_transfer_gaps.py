"""
Second pass over the resorts scripts/build_transfer_quotes.py could not
quote, retrying with adapters/transfer_adapter.name_variants().

Most first-pass gaps were NAME MISMATCHES rather than missing coverage
(our "Milan Malpensa" vs their "Malpensa"), so this converts documented
gaps into real quotes. Updates the same progress file, then rewrites
the frozen module. Paced for the measured ~14-calls-then-10-minutes
limit; resumable.
"""
import datetime
import json
import time

from ski_optimizer.adapters import transfer_adapter as ta
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.data.resort_repository import load_resorts
from scripts.build_transfer_quotes import (PROGRESS, _QUOTE_DATE, _SPACING_S,
                                           _COOLDOWN_S, load_progress,
                                           save_progress, write_module)


def retry(resort, adults: int) -> dict:
    """Re-quote through the real (now variant-aware) adapter path."""
    result = ta.search_transfer_options(resort, _QUOTE_DATE, "10:00", adults=adults,
                                        use_cache=False)
    if not result.options:
        return {"status": "no_vehicles",
                "why": f"Alps2Alps resolved the route but offered no vehicle for "
                       f"{adults} passengers"}
    cheapest = min(result.options, key=lambda q: q.price_eur)
    return {"status": "ok", "price_eur": round(cheapest.price_eur, 2),
            "duration_minutes": getattr(cheapest, "duration_minutes", None),
            "vehicle": getattr(cheapest, "vehicle_type", None),
            "vehicles_offered": len(result.options)}


def main() -> None:
    adults = 2
    progress = load_progress()
    gaps = [r for r in load_resorts()
            if progress.get(f"{adults}:{r.name}", {}).get("status") not in ("ok", None)]
    print(f"retrying {len(gaps)} gaps with name variants\n")
    for resort in gaps:
        while True:
            try:
                entry = retry(resort, adults)
                break
            except AdapterError as exc:
                if "rate limit" not in str(exc).lower():
                    entry = {"status": "adapter_error", "why": str(exc)[:200]}
                    break
                print(f"  rate limited -- sleeping {_COOLDOWN_S}s", flush=True)
                time.sleep(_COOLDOWN_S)
            except Exception as exc:  # noqa: BLE001
                entry = {"status": type(exc).__name__, "why": str(exc)[:200]}
                break
        progress[f"{adults}:{resort.name}"] = entry
        save_progress(progress)
        detail = entry.get("price_eur") or entry.get("matched_via") or entry.get("why", "")
        print(f'  {entry["status"]:<18} {resort.name[:26]:<28} {str(detail)[:52]}', flush=True)
        time.sleep(_SPACING_S)
    write_module(progress, adults)


if __name__ == "__main__":
    main()
