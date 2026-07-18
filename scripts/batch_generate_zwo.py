#!/usr/bin/env python3
r"""
Batch Zwift Workout (.zwo) Generator for Cycling Fitness Coach.

Takes a JSON array of workout definitions and generates all .zwo files for a training week.
Thin wrapper around generate_zwo.py — reuses workout_from_dict, create_zwo_xml, calculate_workout_stats.

Usage:
    # --output-dir should be the user's Zwift custom workouts folder so files show up in Zwift:
    #   Windows:      %LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\week1\
    #   macOS/Linux:  ~/Documents/Zwift/Workouts/<athlete_id>/week1/
    python batch_generate_zwo.py --input week_workouts.json --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp 200

Input JSON format:
    [
        {
            "filename": "week1_tue_ss.zwo",
            "name": "W1 Tue - Sweet Spot Builder",
            "description": "2x20min Sweet Spot @ 88-94% FTP",
            "tags": ["Sweet Spot", "FTP", "Week 1"],
            "workout": [
                {"type": "Warmup", "duration": 600, "power_low": 0.40, "power_high": 0.75},
                {"type": "SteadyState", "duration": 1200, "power": 0.90, "cadence": 90},
                {"type": "Cooldown", "duration": 300, "power_low": 0.55, "power_high": 0.35}
            ]
        },
        ...
    ]
"""

import argparse
import json
import os
import sys

# Force UTF-8 on Windows (default cp1252 mangles Unicode in stderr summary output).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Import from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_zwo import (
    workout_from_dict,
    create_zwo_xml,
    calculate_workout_stats,
    check_erg_design,
    resolve_ftp_arg,
)


TSS_TOLERANCE = 0.10  # |modeled - planned| / planned above this -> mismatch warning


def check_planned_tss(workout_def, stats):
    """Compare a workout's modeled TSS against an optional ``planned_tss`` target.

    The plan workflow knows each day's target TSS; passing it through lets the
    generator catch a workout whose modeled load drifted from what the block
    intended (a mistyped duration, a wrong power, a dropped rep).

    Returns a dict ``{status, planned_tss, deviation_pct, message}`` where status is:
      - ``not_checked`` — no ``planned_tss`` supplied.
      - ``skipped``     — ``planned_tss`` non-positive/non-numeric, or the modeled
                          TSS is not a faithful basis for comparison: ftptest
                          (``estimated_tss is None``) or FreeRide/MaxEffort
                          placeholder power (``tss_estimated`` True).
      - ``mismatch``    — deviation exceeds ``TSS_TOLERANCE``.
      - ``ok``          — deviation within tolerance.
    """
    planned = workout_def.get("planned_tss")
    if planned is None:
        return {"status": "not_checked", "planned_tss": None,
                "deviation_pct": None, "message": None}
    # bool is a subclass of int — reject it explicitly so `true` isn't treated as 1.
    if isinstance(planned, bool) or not isinstance(planned, (int, float)) or planned <= 0:
        return {"status": "skipped", "planned_tss": planned, "deviation_pct": None,
                "message": f"planned_tss must be a positive number (got {planned!r})"}
    modeled = stats.get("estimated_tss")
    if modeled is None or stats.get("tss_estimated"):
        reason = ("FTP test — TSS unmodeled" if modeled is None
                  else "FreeRide/MaxEffort placeholder power — modeled TSS unreliable")
        return {"status": "skipped", "planned_tss": planned, "deviation_pct": None,
                "message": f"TSS check skipped ({reason})"}
    deviation = abs(modeled - planned) / planned
    dev_pct = round(deviation * 100, 1)
    if deviation > TSS_TOLERANCE:
        return {
            "status": "mismatch", "planned_tss": planned, "deviation_pct": dev_pct,
            "message": (f"modeled TSS {modeled} vs planned {planned} "
                        f"({dev_pct}% off, > {round(TSS_TOLERANCE * 100)}% tolerance)"),
        }
    return {"status": "ok", "planned_tss": planned,
            "deviation_pct": dev_pct, "message": None}


def batch_generate(workouts_data, output_dir, ftp, dry_run=False):
    """Generate .zwo files for all workouts in the batch.

    Args:
        workouts_data: list of workout definition dicts (each must include 'filename').
        output_dir: directory to write .zwo files into.
        ftp: FTP for stats calculation.
        dry_run: if True, validate and compute stats without writing files.

    Returns:
        dict with per-workout stats and summary.
    """
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    results = []
    errors = []
    total_duration = 0
    total_tss = 0
    seen_filenames = set()

    for idx, workout_def in enumerate(workouts_data):
        filename = workout_def.get("filename")
        if not filename:
            errors.append({"index": idx, "error": "missing required 'filename' field"})
            continue

        # Reject path traversal / absolute paths — filename must be a bare
        # basename. ':' catches Windows drive-relative paths ("D:evil.zwo",
        # which os.path.isabs misses and os.path.join silently re-roots) and
        # NTFS alternate data streams ("w1.zwo:x").
        if (os.sep in filename or "/" in filename or ":" in filename
                or filename.startswith("..") or os.path.isabs(filename)):
            errors.append({
                "index": idx, "filename": filename,
                "error": "filename must be a bare filename (no path separators, ':' or '..')",
            })
            continue

        # Reject duplicates — second-and-later writes would silently clobber the first
        if filename in seen_filenames:
            errors.append({
                "index": idx, "filename": filename,
                "error": "duplicate filename in batch (would clobber an earlier entry)",
            })
            continue
        seen_filenames.add(filename)

        try:
            workout = workout_from_dict(workout_def)
            xml_content = create_zwo_xml(workout)
            stats = calculate_workout_stats(workout, ftp)

            filepath = os.path.join(output_dir, filename)
            if not dry_run:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(xml_content)

            total_duration += stats["total_duration_min"]
            total_tss += stats["estimated_tss"] or 0  # None for ftptest workouts

            results.append({
                "filename": filename,
                "name": workout.name,
                "duration_min": stats["total_duration_min"],
                "estimated_tss": stats["estimated_tss"],
                "estimated_if": stats["estimated_if"],
                "erg_warnings": check_erg_design(workout),
                "tss_check": check_planned_tss(workout_def, stats),
                "path": filepath,
            })
        except Exception as e:
            errors.append({"index": idx, "filename": filename, "error": str(e)})

    return {
        "workouts_generated": len(results),
        "workouts_failed": len(errors),
        "output_dir": output_dir,
        "ftp": ftp,
        "dry_run": dry_run,
        "total_duration_min": round(total_duration, 1),
        "total_estimated_tss": round(total_tss),
        "workouts": results,
        "errors": errors,
    }


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(
        description="Batch generate Zwift workout files from JSON array"
    )
    p.add_argument("--input", "-i", required=True,
                   help="JSON file with array of workout definitions")
    p.add_argument("--output-dir", "-d", required=True,
                   help="Output directory for .zwo files")
    p.add_argument("--ftp", type=int, default=None,
                   help="FTP in watts for stats calculation (50-500). If omitted, "
                        "defaults to 200 with a warning — pass the athlete's real FTP "
                        "or the whole week's TSS/intensity estimates will be wrong.")
    p.add_argument("-o", "--output", help="Write summary JSON to file (default: stdout)")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate and compute stats without writing .zwo files")
    return p


def main():
    p = build_parser()
    args = p.parse_args()

    args.ftp = resolve_ftp_arg(
        args.ftp, p,
        "WARNING: --ftp not supplied — using 200W for batch stats. The whole "
        "week's TSS/IF estimates will be wrong unless 200W is the athlete's actual "
        "FTP. Re-run with --ftp <actual> for accurate numbers.",
    )

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            workouts_data = json.load(f)
    except FileNotFoundError:
        p.error(f"Input file not found: {args.input}")
    except json.JSONDecodeError as e:
        p.error(f"Invalid JSON in {args.input}: {e}")

    if not isinstance(workouts_data, list):
        p.error("Input JSON must be an array of workout definitions")

    if not all(isinstance(w, dict) for w in workouts_data):
        p.error("Each item in JSON array must be a JSON object")

    result = batch_generate(workouts_data, args.output_dir, args.ftp, dry_run=args.dry_run)

    out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Summary written to {args.output}", file=sys.stderr)
    else:
        print(out)

    # Also print human-readable summary to stderr
    if args.dry_run:
        print(f"\nDRY RUN: would generate {result['workouts_generated']} workout files in {args.output_dir} (no files written)", file=sys.stderr)
    else:
        print(f"\nGenerated {result['workouts_generated']} workout files in {args.output_dir}", file=sys.stderr)
    for w in result["workouts"]:
        tss_disp = w["estimated_tss"] if w["estimated_tss"] is not None else "n/a"
        print(f"  {w['filename']:40s} {w['duration_min']:>5.0f}min  TSS ~{tss_disp}", file=sys.stderr)
    print(f"  {'Total':40s} {result['total_duration_min']:>5.0f}min  TSS ~{result['total_estimated_tss']}", file=sys.stderr)

    # Surface ERG-design warnings per workout (parity with generate_zwo.main).
    for w in result["workouts"]:
        for erg_warning in w.get("erg_warnings", []):
            print(f"  ERG-design warning ({w['filename']}): {erg_warning}", file=sys.stderr)

    # Surface planned-vs-modeled TSS mismatches per workout (P2-3).
    for w in result["workouts"]:
        chk = w.get("tss_check") or {}
        if chk.get("status") == "mismatch":
            print(f"  TSS mismatch ({w['filename']}): {chk['message']}", file=sys.stderr)

    if result.get("errors"):
        print(f"  FAILED: {result['workouts_failed']} workout(s) had errors:", file=sys.stderr)
        for err in result["errors"]:
            print(f"    #{err['index']}: {err.get('filename', 'unknown')} — {err['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
