"""
Regenerates SkiTripOptimizer.jsx's embedded RESORTS data block from the
live seed spreadsheet, via the same resort_repository loader the Python
backend uses -- so the frontend prototype can never drift from what the
real engine sees.

Run from this directory:  python3 regenerate_from_resort_data.py
"""
import json
import re
import sys
from pathlib import Path

# repo root is two levels up from frontend/prototype/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ski_optimizer.data.resort_repository import load_resorts

resorts = load_resorts()
data = []
for r in resorts:
    data.append({
        "name": r.name, "country": r.country, "region": r.region,
        "baseElev": r.base_elevation_m, "summitElev": r.summit_elevation_m, "vertical": r.vertical_drop_m,
        "lifts": r.num_lifts, "pisteKm": r.piste_km,
        "beginner": round(r.terrain_mix.beginner, 3), "intermediate": round(r.terrain_mix.intermediate, 3),
        "advanced": round(r.terrain_mix.advanced, 3), "terrainQuality": r.terrain_data_quality,
        "offPiste": r.off_piste_rating, "snow": r.snow_reliability, "nightlife": r.nightlife_rating,
        "family": r.family_friendliness, "airport": r.nearest_airport, "airportDist": r.airport_distance_km,
        "transferMin": round(r.transfer_time_minutes), "pass6day": r.ski_pass_6day_eur,
        "accomPerNight": r.accommodation_eur_per_night, "needsVerification": r.needs_verification,
    })

RESORTS_JSON = json.dumps(data, separators=(",", ":"))

jsx_path = Path(__file__).parent / "SkiTripOptimizer.jsx"
content = jsx_path.read_text()
new_content = re.sub(
    r"const RESORTS = \[.*?\];",
    lambda _match: f"const RESORTS = {RESORTS_JSON};",  # function repl avoids
    # backslash-escape parsing of \u00e9 etc. inside RESORTS_JSON, which
    # re.sub would otherwise try to interpret as regex group references.
    content, count=1, flags=re.DOTALL,
)
jsx_path.write_text(new_content)
print(f"Regenerated RESORTS block with {len(data)} resorts.")
