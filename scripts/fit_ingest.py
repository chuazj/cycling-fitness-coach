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
    # FIT cycling records are 1Hz — matches intervals_icu.metrics' sampling assumption.
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


def analyze_local(records, metadata, ftp=200, weight=70.0):
    """Analyze parsed .fit records → the same dict shape as activity.analyze().

    Pure (no fitparse). `records` is the list from parse_fit; `metadata` its
    companion dict. `source` is "fit_file"; `fetch_errors` is {} so the dict
    is a drop-in for any analyze() consumer (e.g. workflows/analyze.md).

    Emits an extra `metrics["power_profile"]` key not present in
    activity.analyze()'s per-ride output (analyze() reserves power_profile for
    weekly summaries) — an intentional W7 Task 7 spec choice.
    """
    watts = [r.get("watts") for r in records]
    hr = [r.get("heartrate") for r in records]
    cadence = [r.get("cadence") for r in records]

    watts_present = [w for w in watts if w is not None]
    hr_present = [h for h in hr if h is not None]
    cadence_present = [c for c in cadence if c is not None]

    has_power_stream = len(watts_present) >= 30
    has_hr_stream = len(hr_present) >= 30
    has_power = bool(metadata.get("device_watts")) and bool(watts_present)

    moving_time = metadata.get("moving_time_s") or len(records)

    m = {}
    np_val = compute_np(watts) if watts_present else None
    m["normalized_power"] = np_val
    avg_w = round(sum(watts_present) / len(watts_present), 1) if watts_present else None
    avg_hr = round(sum(hr_present) / len(hr_present), 1) if hr_present else None
    avg_cad = round(sum(cadence_present) / len(cadence_present), 1) if cadence_present else None

    if np_val and ftp:
        m["intensity_factor"] = round(np_val / ftp, 3)
    tss = compute_tss(np_val, ftp, moving_time)
    if tss is not None:
        m["tss"] = tss
    if np_val and avg_w and avg_w > 0:
        m["variability_index"] = round(np_val / avg_w, 3)
    if np_val is not None and avg_hr is not None and avg_hr > 0:
        m["efficiency_factor"] = round(np_val / avg_hr, 3)
    if avg_w is not None and weight:
        m["power_to_weight"] = round(avg_w / weight, 2)

    peaks = compute_peaks(watts) if watts_present else {}
    m["peak_powers"] = peaks
    if has_power_stream:
        zs, zp = compute_zones(watts, ftp)
        m["zone_seconds"], m["zone_percent"] = zs, zp
    else:
        m["zone_seconds"], m["zone_percent"] = None, None
    m["cardiac_drift"] = compute_drift(watts, hr) if (has_power_stream and has_hr_stream) else None

    laps = metadata.get("laps") or []
    m["interval_consistency"] = interval_stats(laps)

    ftp_test = detect_ftp_test(metadata.get("name", ""), peaks, moving_time, ftp_ref=ftp)
    if ftp_test:
        m["ftp_test"] = ftp_test
    if peaks and weight and weight > 0:
        m["power_profile"] = analyze_power_profile(peaks, ftp, weight)

    data_warnings = []
    if not has_power:
        data_warnings.append("estimated_power: No power data in the .fit file — power metrics unavailable or estimated")
    if watts_present and not has_power_stream:
        data_warnings.append("streams_too_short: Power stream present but too short for zone/drift analysis")

    max_watts = max(watts_present) if watts_present else None
    is_indoor = bool(metadata.get("trainer")) or metadata.get("sport_type") in ("VirtualRide", "VirtualRun")
    kj = round(sum(watts_present) / 1000, 1) if watts_present else None

    activity = {
        "id": metadata.get("name", ""),
        "name": metadata.get("name", ""),
        "sport_type": metadata.get("sport_type", ""),
        "start_date_local": metadata.get("start_date_local", ""),
        "distance_km": round((metadata.get("distance_m") or 0) / 1000, 2),
        "moving_time": moving_time,
        "moving_time_fmt": fmt_time(moving_time),
        "elapsed_time": metadata.get("elapsed_time_s") or 0,
        "elevation_gain": metadata.get("total_elevation_gain") or 0,
        "average_watts": avg_w,
        "max_watts": max_watts,
        "average_heartrate": avg_hr,
        "max_heartrate": max(hr_present) if hr_present else None,
        "average_cadence": avg_cad,
        "kilojoules": kj,
        "has_power": has_power,
        "trainer": bool(metadata.get("trainer")),
        "power_data_quality": "measured" if has_power else "estimated",
        "context": "indoor" if is_indoor else "outdoor",
    }

    return {
        "activity": activity,
        "data_completeness": "complete",
        "data_warnings": data_warnings,
        "fetch_errors": {},
        "laps": laps,
        "metrics": m,
        "streams_available": bool(watts_present or hr_present),
        "ftp_reference": ftp,
        "source": "fit_file",
    }


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(
        description="Analyze a local .fit activity file (intervals.icu fallback)")
    p.add_argument("--file", required=True, help="Path to the .fit file")
    p.add_argument("--ftp", type=int, default=None,
                   help="FTP in watts. If omitted, 200W is used with a stderr warning.")
    p.add_argument("--weight", type=float, default=None,
                   help="Body weight in kg. If omitted, 70kg is used with a stderr warning.")
    p.add_argument("-o", "--output", help="Output JSON file path (default: stdout)")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    ftp, weight = args.ftp, args.weight
    fallbacks = []
    if ftp is None:
        ftp = 200
        fallbacks.append("FTP=200W")
    if weight is None:
        weight = 70.0
        fallbacks.append("weight=70kg")
    if fallbacks:
        print(f"WARNING: using neutral default {' / '.join(fallbacks)} — "
              "power/zone/TSS analysis will be inaccurate. Pass --ftp / --weight.",
              file=sys.stderr)

    if not (50 <= ftp <= 500):
        parser.error(f"--ftp must be between 50 and 500 watts (got {ftp})")
    if not (30 <= weight <= 200):
        parser.error(f"--weight must be between 30 and 200 kg (got {weight})")

    try:
        records, metadata = parse_fit(args.file)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    result = analyze_local(records, metadata, ftp=ftp, weight=weight)
    out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
