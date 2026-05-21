#!/usr/bin/env python3
"""
intervals.icu API Client for Cycling Fitness Coach.
Fetches activity data, intervals, streams, power curves. Computes NP, IF, TSS, VI, zones.
Also provides weekly summary aggregation, power profile analysis, and auto-FTP detection.

Usage:
    python intervals_icu_api.py --activity i126468486 --ftp 200 --weight 70
    python intervals_icu_api.py --list-recent 10
    python intervals_icu_api.py --activity i126468486 --use-athlete-profile
    python intervals_icu_api.py --weekly-summary 7 --use-athlete-profile
    python intervals_icu_api.py --wellness 14
"""

import argparse
import json
import math
import os
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Force UTF-8 on Windows (default cp1252 cannot encode CJK activity names or em-dashes
# in warning messages). Both streams need reconfiguring — stdout for JSON output, stderr
# for the WARNING: ... messages this script emits which contain Unicode punctuation.
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("ERROR: pip install requests", file=sys.stderr)
    sys.exit(1)

from intervals_icu.api_client import IntervalsIcuClient, load_env
from intervals_icu.metrics import (
    _clean_watts, compute_np, compute_peaks, compute_zones, compute_drift,
    interval_stats, detect_ftp_test, detect_indoor, fmt_time, extract_id,
    parse_power_curve, parse_streams, analyze_power_profile,
    POWER_ZONES, POWER_PROFILE,
)
from intervals_icu.metrics import _is_cycling, _stdev
from intervals_icu.activity import analyze, weekly_summary
from intervals_icu.wellness import wellness_summary
from intervals_icu.readiness import readiness_check, format_readiness_check


def apply_compact(result):
    """Remove rarely-used fields for token-efficient output.

    MUTATES `result` in place and returns it for chaining. Fields removed:
    metrics.{variability_index, efficiency_factor, zone_seconds} and per-lap
    {distance, max_watts, intensity}.
    """
    m = result.get("metrics", {})
    for key in ("variability_index", "efficiency_factor", "zone_seconds"):
        m.pop(key, None)
    for lap in result.get("laps", []):
        for key in ("distance", "max_watts", "intensity"):
            lap.pop(key, None)
    return result


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(description="intervals.icu activity analysis")
    p.add_argument("--athlete-id", help="intervals.icu athlete ID (default: from .env)")
    p.add_argument("--api-key", help="intervals.icu API key (default: from .env)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--activity", help="Activity ID or intervals.icu URL")
    mode.add_argument("--latest", action="store_true", help="Fetch and analyze the most recent activity")
    mode.add_argument("--list-recent", type=int, help="List N most recent activities")
    mode.add_argument("--weekly-summary", type=int, nargs="?", const=7,
                       help="Weekly training summary for last N days (default: 7)")
    mode.add_argument("--wellness", type=int, nargs="?", const=14,
                       help="Wellness/readiness summary for last N days (default: 14). "
                            "Pulls RHR, HRV, sleep, and subjective fatigue/soreness/stress; "
                            "flags deviations vs baseline against Yellow/Red Flag rules.")
    mode.add_argument("--readiness-check", action="store_true",
                       help="One-shot pre-ride verdict. Combines today's sleep/HRV/RHR/recovery/TSB/"
                            "3-day slope/subjective into GREEN/YELLOW-HIGH/YELLOW-LOW/RED with session ceiling. "
                            "Use --output for JSON; default is human-readable text.")
    p.add_argument("--ftp", type=int, default=None,
                   help="FTP in watts. Prefer --use-athlete-profile to auto-fetch from intervals.icu. "
                        "If neither flag is given a neutral 200W default is used with a stderr warning.")
    p.add_argument("--weight", type=float, default=None,
                   help="Body weight in kg. Prefer --use-athlete-profile to auto-fetch from intervals.icu. "
                        "If neither flag is given a neutral 70kg default is used with a stderr warning.")
    p.add_argument("--use-athlete-profile", action="store_true",
                   help="Auto-fetch FTP/weight from intervals.icu athlete profile")
    p.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p.add_argument("--compact", action="store_true",
                   help="Omit rarely-used fields (VI, EF, zone_seconds, per-interval distance/max_watts/intensity)")
    return p


if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()

    # Load .env
    load_env()

    athlete_id = args.athlete_id or os.environ.get("INTERVALS_ICU_ATHLETE_ID")
    api_key = args.api_key or os.environ.get("INTERVALS_ICU_API_KEY")

    if not athlete_id or not api_key:
        p.error("Provide --athlete-id and --api-key, or set INTERVALS_ICU_ATHLETE_ID and "
                "INTERVALS_ICU_API_KEY in .env or environment")

    client = IntervalsIcuClient(athlete_id, api_key)

    if args.use_athlete_profile:
        profile_error = None
        try:
            profile = client.get_athlete()
            # FTP: try top-level icu_ftp first (legacy/some accounts), then walk
            # sportSettings to find the bike entry. intervals.icu stores per-sport
            # FTPs under sportSettings[i]['ftp'] where types includes Ride/VirtualRide.
            if args.ftp is None:
                ftp_value = profile.get("icu_ftp")
                ftp_source = "icu_ftp"
                if not ftp_value:
                    for s in profile.get("sportSettings") or []:
                        types = s.get("types") or []
                        if any(t in types for t in ("Ride", "VirtualRide", "Cyclocross")):
                            ftp_value = s.get("ftp")
                            ftp_source = f"sportSettings[{','.join(types)}].ftp"
                            break
                if ftp_value:
                    args.ftp = ftp_value
                    print(f"Using FTP from athlete profile: {args.ftp}W (source: {ftp_source})", file=sys.stderr)
            if profile.get("icu_weight") and args.weight is None:
                args.weight = profile["icu_weight"]
                print(f"Using weight from athlete profile: {args.weight}kg", file=sys.stderr)
        except Exception as e:
            profile_error = e
            print(f"WARNING: Could not fetch athlete profile: {e}", file=sys.stderr)

        # If --use-athlete-profile was requested but didn't yield an FTP, prompt
        # interactively rather than silently defaulting to 200W. Hard-error if
        # stdin isn't a TTY (e.g., piped/CI) — caller must pass --ftp explicitly.
        if args.ftp is None:
            reason = ("profile fetch failed" if profile_error is not None
                      else "no FTP in intervals.icu profile (check sportSettings → bike → ftp)")
            if not sys.stdin.isatty():
                p.error(f"--use-athlete-profile: {reason}, and stdin is not a TTY for prompt. "
                        f"Pass --ftp <watts> explicitly.")
            print(f"FTP unavailable: {reason}.", file=sys.stderr)
            while True:
                try:
                    raw = input("Enter your FTP in watts (50-500): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.", file=sys.stderr)
                    sys.exit(1)
                try:
                    ftp_val = int(raw)
                except ValueError:
                    print(f"  invalid number: {raw!r}", file=sys.stderr)
                    continue
                if not (50 <= ftp_val <= 500):
                    print(f"  FTP must be between 50 and 500W (got {ftp_val})", file=sys.stderr)
                    continue
                args.ftp = ftp_val
                print(f"Using user-provided FTP: {args.ftp}W", file=sys.stderr)
                break

        # Same hardening for weight: prompt rather than silently default to 70kg.
        if args.weight is None:
            reason = ("profile fetch failed" if profile_error is not None
                      else "no weight in intervals.icu profile (icu_weight is unset)")
            if not sys.stdin.isatty():
                p.error(f"--use-athlete-profile: {reason}, and stdin is not a TTY for prompt. "
                        f"Pass --weight <kg> explicitly.")
            print(f"Weight unavailable: {reason}.", file=sys.stderr)
            while True:
                try:
                    raw = input("Enter your weight in kg (30-200): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.", file=sys.stderr)
                    sys.exit(1)
                try:
                    weight_val = float(raw)
                except ValueError:
                    print(f"  invalid number: {raw!r}", file=sys.stderr)
                    continue
                if not (30 <= weight_val <= 200):
                    print(f"  weight must be between 30 and 200 kg (got {weight_val})", file=sys.stderr)
                    continue
                args.weight = weight_val
                print(f"Using user-provided weight: {args.weight}kg", file=sys.stderr)
                break

    # Final fallbacks after profile logic — neutral generic defaults, warn loudly.
    # Modes that don't use FTP/weight (--list-recent, --wellness, --readiness-check)
    # should NOT see this warning since the defaults are never read by them.
    needs_ftp_weight = not (args.list_recent or args.wellness is not None or args.readiness_check)
    used_fallback = []
    if args.ftp is None:
        args.ftp = 200
        used_fallback.append("FTP=200W")
    if args.weight is None:
        args.weight = 70.0
        used_fallback.append("weight=70kg")
    if used_fallback and needs_ftp_weight:
        print(
            f"WARNING: using neutral default {' / '.join(used_fallback)} — "
            "power/zone/TSS analysis will be inaccurate. "
            "Pass --use-athlete-profile (recommended) or explicit --ftp/--weight.",
            file=sys.stderr,
        )

    # Validate bounds
    if not (50 <= args.ftp <= 500):
        p.error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")
    if not (30 <= args.weight <= 200):
        p.error(f"--weight must be between 30 and 200 kg (got {args.weight})")

    def _apply_compact(result):
        """Apply compact filtering if --compact flag is set."""
        if not args.compact:
            return result
        return apply_compact(result)

    if args.latest:
        newest = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        oldest = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S")
        activities = client.list_activities(oldest=oldest, newest=newest, limit=1)
        if not activities:
            print("No recent activities found.", file=sys.stderr)
            sys.exit(1)
        aid = activities[0]["id"]
        print(f"Latest activity: {activities[0].get('name', '')} ({aid})", file=sys.stderr)
        result = _apply_compact(analyze(client, aid, args.ftp, args.weight))
        out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(out)
    elif args.list_recent:
        newest = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        oldest = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S")
        activities = client.list_activities(oldest=oldest, newest=newest, limit=args.list_recent)
        for i, a in enumerate(activities, 1):
            w = a.get("icu_weighted_avg_watts") or a.get("icu_average_watts")
            dist = (a.get("distance") or 0) / 1000
            name = (a.get("name") or "")[:30]
            date = (a.get("start_date_local") or "")[:16]
            print(f"{i:>3}. {date}  {name:<30}  {dist:.1f}km  {f'{w:.0f}W' if w else '-':>5}")
    elif args.weekly_summary is not None:
        result = weekly_summary(client, days=args.weekly_summary, ftp=args.ftp, weight=args.weight)
        out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(out)
    elif args.wellness is not None:
        result = wellness_summary(client, days=args.wellness)
        out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(out)
    elif args.readiness_check:
        result = readiness_check(client, lookback_days=14)
        if args.output:
            out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            # Default: human-readable text. Strip the redundant verdict_text key
            # since we're printing it directly.
            print(result.get("verdict_text") or json.dumps(result, indent=2, default=str, ensure_ascii=False))
    elif args.activity:
        aid = extract_id(args.activity)
        result = _apply_compact(analyze(client, aid, args.ftp, args.weight))
        out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(out)
