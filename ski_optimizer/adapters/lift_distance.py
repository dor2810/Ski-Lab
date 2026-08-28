"""
How far a hotel is from the nearest ski lift -- computed, not guessed.

WHY THIS EXISTS, in the project owner's words: "One of the most
important info I want about the accommodation is distance from ski
lifts. This is a ski vacation at the end of the day." Correct: on a ski
trip the walk to the lift is a daily tax paid twice a day in boots.
AccommodationOption has carried a distance_to_lifts_km field since the
first design and it has never once been populated, because no provider
gives it.

SO WE COMPUTE IT. Two free, honest inputs:
  1. Hotel coordinates -- adapters/stays_adapter.py returns real
     lat/lng per property.
  2. Lift coordinates -- OpenStreetMap, which maps Alpine lifts in
     extraordinary detail under the `aerialway` tag (154 lift features
     around Val Thorens alone). Queried through the public Overpass
     API: free, no key, no account.

Then it is just haversine. Verified live 2026-08-28 against Val
Thorens, whose hotels really are ski-in/ski-out: Club Med 45m from the
Cairn lift, Hotel Marielle 69m, Fahrenheit Seven 143m from Pionniers.

WHAT THIS IS NOT: walking distance. It is straight-line distance to
the nearest lift structure, which in a compact purpose-built resort is
close to the truth and in a spread-out valley village understates the
walk. Labelled as such wherever it surfaces -- never dressed up as
"3 minutes to the piste".

COST DISCIPLINE: lift geography does not change between searches, so
lift points are fetched ONCE PER RESORT and cached for the process
lifetime; every hotel in that resort is then measured locally with no
further network calls. A failed or slow Overpass call degrades to
None -- a missing distance, never a wrong one, and never a broken
search.
"""
import logging
import math
from typing import List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_TIMEOUT_S = 45
# Lifts further out than this from the resort centre belong to a
# different village; 6km comfortably covers even sprawling domains.
_SEARCH_RADIUS_M = 6000
_USER_AGENT = "SkiLab/1.0 (+https://ski-lab-app.web.app)"

# resort name -> [(lat, lon, name)], fetched once per process.
_LIFT_CACHE: dict = {}

#: Lift types worth measuring to. Deliberately EXCLUDES drag lifts
#: (t-bar/platter/rope-tow) and magic carpets: they are usually
#: beginner-area or connector lifts scattered through a resort, and
#: including them would flatter every hotel with a nursery slope
#: outside it into looking lift-side.
_LIFT_KINDS = "^(gondola|chair_lift|cable_car|mixed_lift|funicular)$"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def _overpass_query(lat: float, lon: float) -> str:
    return (
        f"[out:json][timeout:40];"
        f"(node(around:{_SEARCH_RADIUS_M},{lat},{lon})[aerialway=station];"
        f" way(around:{_SEARCH_RADIUS_M},{lat},{lon})[aerialway~\"{_LIFT_KINDS}\"];);"
        f"out center 300;"
    )


def fetch_lift_points(lat: float, lon: float) -> List[Tuple[float, float, Optional[str]]]:
    """Lift stations and lift lines near a coordinate, from OSM.
    Returns [] on any failure -- see the module docstring's degradation
    rule. `way` elements come back with a `center`, which for a lift
    line is its midpoint; the station nodes are the precise boarding
    points and dominate the nearest-neighbour result in practice."""
    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": _overpass_query(lat, lon)},
            timeout=_TIMEOUT_S,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except Exception:
        logger.warning("Overpass lift lookup failed near (%s, %s)", lat, lon, exc_info=True)
        return []

    points: List[Tuple[float, float, Optional[str]]] = []
    for element in elements:
        point_lat = element.get("lat") or (element.get("center") or {}).get("lat")
        point_lon = element.get("lon") or (element.get("center") or {}).get("lon")
        if point_lat is None or point_lon is None:
            continue
        points.append((point_lat, point_lon, (element.get("tags") or {}).get("name")))
    return points


def lift_points_for_resort(resort) -> List[Tuple[float, float, Optional[str]]]:
    """
    This resort's lift coordinates -- from the FROZEN dataset
    (data/ski_lift_locations.py), with no network call at all.

    WHY FROZEN: the first version queried Overpass at runtime and
    worked perfectly in development, then returned 504 Gateway Timeout
    from Cloud Run's IP on the very first production search (measured
    2026-08-28) -- the public instance throttles cloud ranges. Lift
    geography is static, so the honest fix was to fetch it once and
    ship it: instant, free, offline, unfailing. Regenerate with
    scripts/build_lift_locations.py when resorts change.

    Falls back to a live fetch only for a resort missing from the
    dataset, so a newly added resort still works (just slower, and
    only until the generator is re-run).
    """
    from ..data.ski_lift_locations import SKI_LIFT_COORDS

    frozen = SKI_LIFT_COORDS.get(resort.name)
    if frozen:
        return [(lat, lon, None) for lat, lon in frozen]

    if resort.latitude is None or resort.longitude is None:
        return []
    cached = _LIFT_CACHE.get(resort.name)
    if cached is not None:
        return cached
    points = fetch_lift_points(resort.latitude, resort.longitude)
    _LIFT_CACHE[resort.name] = points
    return points


def nearest_lift_km(lat: Optional[float], lon: Optional[float], lift_points) -> Optional[float]:
    """Straight-line km from a property to the nearest lift, or None
    when either side is unknown. Rounded to 2dp -- 10m precision is
    already beyond what a straight-line proxy can honestly claim."""
    if lat is None or lon is None or not lift_points:
        return None
    best = min(haversine_km(lat, lon, p[0], p[1]) for p in lift_points)
    return round(best, 2)


def clear_cache() -> None:
    """Test helper."""
    _LIFT_CACHE.clear()
