"""
Loads Resort objects out of data/ski_resort_database_seed.xlsx.

This is a REPOSITORY: its job is "give the rest of the app Resort
objects", regardless of where they actually live. Right now that's the
human-edited xlsx. When Phase 8 migrates to Postgres (see db/), a
sibling module (e.g. postgres_resort_repository.py) will implement the
exact same load_resorts() -> List[Resort] interface, and nothing in
engine/ or cli/ will need to change.

Column layout (as of the extended-data update): 31 columns --
structured terrain (9-12), five NEW extended-data columns (13-17:
snowfall, glacier access, season, terrain park, Israeli flight access),
then the original ratings/logistics/price columns (18-26), free-text
notes (27-29), and the extended-data quality/note pair (30-31). See
extend_resort_data.py for how columns 13-17 and 30-31 were derived.

Reading the spreadsheet directly (instead of duplicating it into a
JSON file) means this always reflects whatever the human-edited xlsx
currently says, including corrections made during a verification pass.
"""
import re
import warnings
from pathlib import Path
from typing import List

import openpyxl

from ..models import Resort
from ..engine.terrain import TerrainMix, parse_terrain_mix

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ski_resort_database_seed.xlsx"

HEADER_ROW = 4  # matches the spreadsheet's layout
DEFAULT_TRANSFER_MINUTES = 120.0  # only used when parsing genuinely fails; see _parse_transfer_minutes


def parse_transfer_minutes_by_airport(text: str) -> dict:
    """
    Parses "2h30 (GVA) / 1h45 (CMF)" into {"GVA": 150.0, "CMF": 105.0}.

    WHY THIS EXISTS: _parse_transfer_minutes below AVERAGES every time it
    finds, which is meaningless when a resort is served by two airports.
    Val Thorens ("2h30 (GVA) / 1h45 (CMF)") became 127.5 minutes -- not
    the Geneva time, not the Chambery time, a number describing no actual
    journey. Worse, the flight adapter now searches BOTH airports, so the
    engine could pick a Geneva flight while scoring a Geneva/Chambery
    average transfer: the two halves of the same trip disagreeing.

    Returns {} when no airport codes are attached, in which case the
    caller falls back to the averaged figure.
    """
    if not text:
        return {}
    out = {}
    # Match a duration followed by a parenthesised IATA code, e.g.
    # "2h30 (GVA)" or "1h45 (CMF, incl. train)".
    for chunk in str(text).split("/"):
        code_match = re.search(r"\(([A-Z]{3})", chunk)
        if not code_match:
            continue
        minutes = _parse_transfer_minutes(chunk, _warn=False)
        if minutes is not None:
            out[code_match.group(1)] = minutes
    return out


def _parse_transfer_minutes(text: str, _warn: bool = True) -> float:
    """
    Turns strings like '2h-2h30', '1h15-1h30', '3h30-4h', '~1h (est.)',
    and minutes-only forms like '~20min' or '45 minutes' into an average
    number of minutes.

    HISTORY / WHY THE MINUTES CASE MATTERS: this originally only matched
    an `Nh` pattern, so a minutes-only string fell through to the 120.0
    fallback. Krvavec ('~20min' -- the shortest transfer in the whole
    database, and its main selling point) was silently being scored as a
    2-hour transfer, a 6x error that corrupted exactly the dimension the
    resort is best at. The failure was invisible because 120.0 is also a
    perfectly plausible real value.

    Unparseable input now emits a warning rather than failing silently --
    a wrong number that looks reasonable is more dangerous than a loud one.
    """
    if not text or str(text).strip().lower() in ("", "none"):
        if _warn:
            warnings.warn("Empty transfer-time text; falling back to 120 min", stacklevel=2)
        return DEFAULT_TRANSFER_MINUTES

    lowered = str(text).lower()

    # Hours (optionally with minutes): '2h', '1h30', '2h-2h30'
    hour_matches = re.findall(r"(\d+)\s*h\s*(\d+)?", lowered)
    if hour_matches:
        minutes = [int(h) * 60 + (int(m) if m else 0) for h, m in hour_matches]
        return sum(minutes) / len(minutes)

    # Minutes-only: '20min', '45 min', '90 minutes'. Checked only after
    # the hour pattern so '1h30min' can't be misread as 30 minutes.
    minute_matches = re.findall(r"(\d+)\s*min", lowered)
    if minute_matches:
        values = [float(m) for m in minute_matches]
        return sum(values) / len(values)

    if _warn:
        warnings.warn(
            f"Could not parse transfer time {text!r}; falling back to "
            f"{DEFAULT_TRANSFER_MINUTES} min. This silently distorts the "
            "convenience score -- fix the spreadsheet value.",
            stacklevel=2,
        )
    return DEFAULT_TRANSFER_MINUTES


def load_resorts(path: Path = DEFAULT_DATA_PATH) -> List[Resort]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["SkiResorts"]

    resorts = []
    for row in ws.iter_rows(min_row=HEADER_ROW + 1, values_only=True):
        if row[0] is None:
            continue
        (name, country, region, base_elev, summit_elev, vertical, lifts, piste_km,
         beg_pct, inter_pct, adv_pct, terrain_quality,
         snowfall, glacier, season, terrain_park, flight_access,
         off_piste, snow_rel, nightlife, family, airport, dist_km,
         transfer_time_text, pass_price, accom_price, notes, source,
         terrain_note, ext_quality, ext_note) = row[:31]

        if beg_pct is not None and inter_pct is not None and adv_pct is not None:
            terrain_mix = TerrainMix.from_percentages(
                float(beg_pct), float(inter_pct), float(adv_pct),
                quality=str(terrain_quality) if terrain_quality else "estimated",
            )
            quality = str(terrain_quality) if terrain_quality else "estimated"
        else:
            # Fallback path for any future resort added without numeric
            # columns filled in yet -- see engine/terrain.py.
            terrain_mix = parse_terrain_mix(terrain_note)
            quality = "estimated"

        resorts.append(Resort(
            name=name,
            country=country,
            region=region,
            base_elevation_m=int(base_elev),
            summit_elevation_m=int(summit_elev),
            vertical_drop_m=int(vertical),
            num_lifts=int(lifts),
            piste_km=float(piste_km),
            off_piste_rating=int(off_piste),
            snow_reliability=int(snow_rel),
            nightlife_rating=int(nightlife),
            family_friendliness=int(family),
            nearest_airport=airport,
            airport_distance_km=float(dist_km),
            transfer_time_minutes=_parse_transfer_minutes(str(transfer_time_text)),
            transfer_minutes_by_airport=parse_transfer_minutes_by_airport(transfer_time_text),
            ski_pass_6day_eur=float(pass_price),
            accommodation_eur_per_night=float(accom_price),
            needs_verification="flagged for dedicated web verification pass" in str(source),
            terrain_mix=terrain_mix,
            terrain_data_quality=quality,
            avg_annual_snowfall_cm=int(snowfall) if snowfall is not None else None,
            glacier_access=glacier,
            typical_season=season,
            terrain_park=terrain_park,
            israeli_flight_access=flight_access,
            extended_data_quality=str(ext_quality) if ext_quality else "estimated",
        ))
    return resorts
