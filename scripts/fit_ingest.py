#!/usr/bin/env python3
"""Analyze a local .fit activity file — the intervals.icu fallback.

For a ride that exists only on Strava/Garmin/Zwift and has not synced to
intervals.icu, this parses the local .fit and emits the same analysis JSON
as scripts/intervals_icu_api.py --activity (source: "fit_file").

Two layers:
  parse_fit(path)    — thin fitparse adapter → (records, metadata)
  analyze_local(...) — pure; reuses intervals_icu.metrics → analysis dict

Requires `pip install fitparse` for the parse layer only; analyze_local has
no third-party dependency.
"""

import argparse
import json
import os
import sys

# Force UTF-8 on Windows (default cp1252 cannot encode Unicode in report output).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intervals_icu.metrics import (
    analyze_power_profile, compute_drift, compute_np, compute_peaks,
    compute_tss, compute_zones, detect_ftp_test, fmt_time, interval_stats,
)


def _import_fitparse():
    """Import fitparse lazily; raise a clear install hint when it is absent."""
    try:
        import fitparse
        return fitparse
    except ImportError:
        raise RuntimeError(
            "fit ingest needs the 'fitparse' package — install it with: "
            "pip install fitparse"
        )


def _build_metadata(session, records, laps, name):
    """Assemble the metadata dict from the optional session message + records."""
    has_power = any(r["watts"] is not None for r in records)
    sport_type, sub_sport = "", ""
    distance_m, elevation = 0, 0
    start = ""
    elapsed_s = len(records)
    timer_s = len(records)
    if session is not None:
        sport_type = session.get_value("sport") or ""
        sub_sport = session.get_value("sub_sport") or ""
        distance_m = session.get_value("total_distance") or 0
        elevation = session.get_value("total_ascent") or 0
        elapsed_s = session.get_value("total_elapsed_time") or len(records)
        timer_s = session.get_value("total_timer_time") or elapsed_s
        st = session.get_value("start_time")
        start = st.isoformat() if hasattr(st, "isoformat") else (str(st) if st else "")
    return {
        "name": name,
        "sport_type": sport_type or "Ride",
        "start_date_local": start,
        "distance_m": distance_m,
        "moving_time_s": int(timer_s) if timer_s else len(records),
        "elapsed_time_s": int(elapsed_s) if elapsed_s else len(records),
        "total_elevation_gain": elevation,
        "device_watts": has_power,
        "trainer": sub_sport in ("virtual_activity", "indoor_cycling"),
        "laps": laps,
    }


def _extract(fitfile, name):
    """Map a fitparse FitFile (or any object with get_messages) → (records, metadata).

    Pure with respect to fitparse internals — only message.get_value(...) is
    used — so it is tested with a fake FitFile, no .fit bytes required.
    """
    records = []
    for i, m in enumerate(fitfile.get_messages("record")):
        records.append({
            "seconds": i,
            "watts": m.get_value("power"),
            "heartrate": m.get_value("heart_rate"),
            "cadence": m.get_value("cadence"),
        })
    laps = []
    for idx, m in enumerate(fitfile.get_messages("lap")):
        laps.append({
            "name": f"Lap {idx + 1}",
            "lap_index": idx,
            "type": "",  # .fit laps carry no WORK/RECOVERY tag → heuristic path
            "elapsed_time": m.get_value("total_elapsed_time") or 0,
            "moving_time": (m.get_value("total_timer_time")
                            or m.get_value("total_elapsed_time") or 0),
            "distance": m.get_value("total_distance") or 0,
            "average_watts": m.get_value("avg_power"),
            "normalized_power": m.get_value("normalized_power"),
            "average_heartrate": m.get_value("avg_heart_rate"),
            "max_heartrate": m.get_value("max_heart_rate"),
            "average_cadence": m.get_value("avg_cadence"),
            "max_watts": m.get_value("max_power"),
            "intensity": m.get_value("intensity"),
        })
    session = next(iter(fitfile.get_messages("session")), None)
    return records, _build_metadata(session, records, laps, name)


def parse_fit(path):
    """Parse a .fit file → (records, metadata). Raises RuntimeError on any failure."""
    fitparse = _import_fitparse()
    try:
        fitfile = fitparse.FitFile(str(path))
    except Exception as e:
        raise RuntimeError(f"Failed to read .fit file '{path}': {e}") from e
    name = os.path.splitext(os.path.basename(str(path)))[0]
    try:
        return _extract(fitfile, name)
    except Exception as e:
        raise RuntimeError(f"Failed to parse .fit file '{path}': {e}") from e
