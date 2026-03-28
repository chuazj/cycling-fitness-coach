#!/usr/bin/env python3
"""
Batch Zwift Workout (.zwo) Generator for Cycling Fitness Coach.

Takes a JSON array of workout definitions and generates all .zwo files for a training week.
Thin wrapper around generate_zwo.py — reuses workout_from_dict, create_zwo_xml, calculate_workout_stats.

Usage:
    python batch_generate_zwo.py --input week_workouts.json --output-dir plans/workouts/week1/ --ftp 192

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

# Force UTF-8 stdout on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Import from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_zwo import workout_from_dict, create_zwo_xml, calculate_workout_stats


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

    for idx, workout_def in enumerate(workouts_data):
        filename = workout_def.get("filename")
        if not filename:
            errors.append({"index": idx, "error": "missing required 'filename' field"})
            continue

        try:
            workout = workout_from_dict(workout_def)
            xml_content = create_zwo_xml(workout)
            stats = calculate_workout_stats(workout, ftp)

            filepath = os.path.join(output_dir, filename)
            if not dry_run:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(xml_content)

            total_duration += stats["total_duration_min"]
            total_tss += stats["estimated_tss"]

            results.append({
                "filename": filename,
                "name": workout.name,
                "duration_min": stats["total_duration_min"],
                "estimated_tss": stats["estimated_tss"],
                "estimated_if": stats["estimated_avg_intensity"],
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


def main():
    p = argparse.ArgumentParser(
        description="Batch generate Zwift workout files from JSON array"
    )
    p.add_argument("--input", "-i", required=True,
                   help="JSON file with array of workout definitions")
    p.add_argument("--output-dir", "-d", required=True,
                   help="Output directory for .zwo files")
    p.add_argument("--ftp", type=int, default=200,
                   help="FTP for stats calculation (default: 200)")
    p.add_argument("-o", "--output", help="Write summary JSON to file (default: stdout)")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate and compute stats without writing .zwo files")

    args = p.parse_args()

    if not (50 <= args.ftp <= 500):
        p.error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")

    with open(args.input, "r", encoding="utf-8") as f:
        workouts_data = json.load(f)

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
    print(f"\nGenerated {result['workouts_generated']} workout files in {args.output_dir}", file=sys.stderr)
    for w in result["workouts"]:
        print(f"  {w['filename']:40s} {w['duration_min']:>5.0f}min  TSS ~{w['estimated_tss']}", file=sys.stderr)
    print(f"  {'Total':40s} {result['total_duration_min']:>5.0f}min  TSS ~{result['total_estimated_tss']}", file=sys.stderr)

    if result.get("errors"):
        print(f"  FAILED: {result['workouts_failed']} workout(s) had errors:", file=sys.stderr)
        for err in result["errors"]:
            print(f"    #{err['index']}: {err.get('filename', 'unknown')} — {err['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
