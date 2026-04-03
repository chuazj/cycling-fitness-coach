#!/usr/bin/env python3
"""
PMC (Performance Management Chart) Calculator for Cycling Fitness Coach.

Computes CTL (Chronic Training Load), ATL (Acute Training Load), TSB (Training Stress Balance)
from intervals.icu activity history. Two modes:

  Bootstrap:  Pull 90-day history, compute current PMC state + peak powers.
  Weekly:     Fetch one week of activities, compare planned vs actual, update PMC.

Usage:
    python pmc_calculator.py --bootstrap --days 90
    python pmc_calculator.py --weekly-update --week 1 --plan-start 2026-03-16 \
        --prev-ctl 42.3 --prev-atl 51.2 --planned-tss '{"Tue":65,"Thu":70,"Sat":80,"Flex":55}'
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

# Force UTF-8 stdout on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Import from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intervals_icu_api import IntervalsIcuClient, load_env, parse_power_curve


# ---------------------------------------------------------------------------
# PMC math
# ---------------------------------------------------------------------------

CTL_DAYS = 42  # Chronic Training Load time constant
ATL_DAYS = 7   # Acute Training Load time constant


def _ewa_constant(days):
    """Exponentially weighted average decay constant: 1/n (standard PMC)."""
    return 1.0 / days


def compute_pmc(daily_tss, initial_ctl=0.0, initial_atl=0.0):
    """Compute CTL, ATL, TSB from daily TSS list.

    Args:
        daily_tss: list of (date_str, tss_value) tuples, sorted by date ascending.
        initial_ctl: starting CTL before first day.
        initial_atl: starting ATL before first day.

    Returns:
        dict with final ctl, atl, tsb and full daily history.
    """
    k_ctl = _ewa_constant(CTL_DAYS)
    k_atl = _ewa_constant(ATL_DAYS)
    ctl = initial_ctl
    atl = initial_atl
    history = []

    for date_str, tss in daily_tss:
        ctl = ctl + k_ctl * (tss - ctl)
        atl = atl + k_atl * (tss - atl)
        tsb = ctl - atl
        acwr = round(atl / ctl, 2) if ctl > 0 else None
        history.append({
            "date": date_str,
            "tss": round(tss, 1),
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
            "acwr": acwr,
        })

    return {
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "tsb": round(ctl - atl, 1),
        "acwr": round(atl / ctl, 2) if ctl > 0 else None,
        "history": history,
    }


def extract_peak_powers(activities, client):
    """Extract best peak powers from recent activities.

    Fetches power curves from top-TSS activities in parallel (up to 8, 4 concurrent).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    powered = [a for a in activities if a.get("icu_training_load") and a.get("icu_training_load") > 0]
    if not powered:
        return {}

    # Sort by TSS descending — best efforts likely in highest-load activities
    powered.sort(key=lambda a: a.get("icu_training_load") or 0, reverse=True)
    max_fetch = min(len(powered), 8)
    best_peaks = {}

    def fetch_peaks(activity):
        aid = activity.get("id")
        if not aid:
            return {}
        try:
            curve = client.get_power_curve(aid)
            return parse_power_curve(curve)
        except Exception as e:
            print(f"WARNING: peak fetch for {aid} failed: {e}", file=sys.stderr)
            return {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_peaks, a): a for a in powered[:max_fetch]}
        for future in as_completed(futures):
            peaks = future.result()
            for label, watts in peaks.items():
                if watts is not None and (label not in best_peaks or watts > best_peaks[label]):
                    best_peaks[label] = watts

    # Return standard durations only
    standard = ["5s", "1min", "5min", "20min"]
    return {k: best_peaks[k] for k in standard if k in best_peaks}


# ---------------------------------------------------------------------------
# Bootstrap mode
# ---------------------------------------------------------------------------

def bootstrap(client, days):
    """Pull activity history and compute current PMC state."""
    newest = datetime.now()
    oldest = newest - timedelta(days=days)

    activities = client.list_activities(
        oldest=oldest.strftime("%Y-%m-%d"),
        newest=newest.strftime("%Y-%m-%d"),
    )

    if not activities:
        return {
            "mode": "bootstrap",
            "date": newest.strftime("%Y-%m-%d"),
            "days_analyzed": days,
            "activities_found": 0,
            "ctl": 0.0,
            "atl": 0.0,
            "tsb": 0.0,
            "weekly_tss_avg_last_4": 0,
            "peak_powers": {},
            "training_day_pattern": [],
            "daily_tss": [],
        }

    # Aggregate to daily TSS
    daily = {}
    for a in activities:
        tss = a.get("icu_training_load")
        if tss is None:
            continue
        date_str = (a.get("start_date_local") or "")[:10]
        if not date_str:
            continue
        daily[date_str] = daily.get(date_str, 0) + tss

    # Fill gaps with zero-TSS days
    all_days = []
    current = oldest.date()
    end = newest.date()
    while current <= end:
        ds = current.strftime("%Y-%m-%d")
        all_days.append((ds, daily.get(ds, 0)))
        current += timedelta(days=1)

    # Compute PMC
    pmc = compute_pmc(all_days)

    # Weekly TSS average (last 4 weeks, or fewer if history is shorter)
    four_weeks_ago = (newest - timedelta(days=28)).strftime("%Y-%m-%d")
    recent_days = [(ds, tss) for ds, tss in all_days if ds >= four_weeks_ago]
    recent_tss = sum(tss for _, tss in recent_days)
    num_weeks = max(1, len(recent_days) / 7)
    weekly_avg = round(recent_tss / num_weeks)

    # Peak powers from best recent activities (last 4 weeks)
    recent_activities = [
        a for a in activities
        if (a.get("start_date_local") or "")[:10] >= four_weeks_ago
    ]
    peaks = extract_peak_powers(recent_activities, client)

    # Training day pattern: count day-of-week frequency from all activities
    from collections import Counter
    day_counter = Counter()
    for a in activities:
        date_str = (a.get("start_date_local") or "")[:10]
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                day_counter[dt.strftime("%a")] += 1
            except ValueError:
                pass
    # Return top 4 most frequent training days
    training_day_pattern = [day for day, _ in day_counter.most_common(4)]

    return {
        "mode": "bootstrap",
        "date": newest.strftime("%Y-%m-%d"),
        "days_analyzed": days,
        "activities_found": len(activities),
        "ctl": pmc["ctl"],
        "atl": pmc["atl"],
        "tsb": pmc["tsb"],
        "acwr": pmc["acwr"],
        "weekly_tss_avg_last_4": weekly_avg,
        "peak_powers": peaks,
        "training_day_pattern": training_day_pattern,
        "daily_tss": [{"date": ds, "tss": round(tss, 1)} for ds, tss in all_days if tss > 0],
    }


# ---------------------------------------------------------------------------
# Weekly update mode
# ---------------------------------------------------------------------------

def weekly_update(client, week_num, plan_start, prev_ctl, prev_atl, planned_tss,
                   prev_peaks=None):
    """Fetch week's activities, compare planned vs actual, update PMC."""
    start = datetime.strptime(plan_start, "%Y-%m-%d")
    week_start = start + timedelta(weeks=week_num - 1)
    week_end = week_start + timedelta(days=6)

    activities = client.list_activities(
        oldest=week_start.strftime("%Y-%m-%d"),
        newest=(week_end + timedelta(days=1)).strftime("%Y-%m-%d"),
    )

    # Aggregate actual daily TSS
    daily = {}
    for a in activities:
        tss = a.get("icu_training_load")
        if tss is None:
            continue
        date_str = (a.get("start_date_local") or "")[:10]
        if not date_str:
            continue
        daily[date_str] = daily.get(date_str, 0) + tss

    # Build full week of daily TSS (fill gaps with 0)
    all_days = []
    current = week_start.date()
    end_date = week_end.date()
    while current <= end_date:
        ds = current.strftime("%Y-%m-%d")
        all_days.append((ds, daily.get(ds, 0)))
        current += timedelta(days=1)

    # Compute updated PMC from previous values
    pmc = compute_pmc(all_days, initial_ctl=prev_ctl, initial_atl=prev_atl)

    # Actual TSS breakdown
    actual_tss = {ds: round(tss, 1) for ds, tss in all_days if tss > 0}
    actual_total = round(sum(tss for _, tss in all_days), 1)

    # Planned total
    planned_total = sum(planned_tss.values()) if planned_tss else 0
    completion = round(actual_total / planned_total, 2) if planned_total > 0 else 0

    # Peak powers from this week
    peaks = extract_peak_powers(activities, client)

    # Compute peak power deltas vs previous week
    peak_deltas = {}
    if prev_peaks:
        for label, new_val in peaks.items():
            old_val = prev_peaks.get(label)
            if old_val and old_val > 0:
                delta_pct = (new_val - old_val) / old_val * 100
                sign = "+" if delta_pct >= 0 else ""
                peak_deltas[label] = f"{sign}{delta_pct:.1f}%"

    result = {
        "mode": "weekly_update",
        "week": week_num,
        "date_range": [week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")],
        "planned_tss": {**planned_tss, "total": planned_total},
        "actual_tss": {**actual_tss, "total": actual_total},
        "completion_rate": completion,
        "ctl": pmc["ctl"],
        "atl": pmc["atl"],
        "tsb": pmc["tsb"],
        "acwr": pmc["acwr"],
        "peak_powers": peaks,
        "peak_power_deltas": peak_deltas,
        "daily_pmc": pmc["history"],
    }
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="PMC Calculator — bootstrap from intervals.icu history or update weekly"
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bootstrap", action="store_true",
                      help="Bootstrap PMC from activity history")
    mode.add_argument("--weekly-update", action="store_true",
                      help="Update PMC for a specific training week")

    # Common args
    p.add_argument("--athlete-id", help="intervals.icu athlete ID (default: from .env)")
    p.add_argument("--api-key", help="intervals.icu API key (default: from .env)")
    p.add_argument("-o", "--output", help="Output file path (default: stdout)")

    # Bootstrap args
    p.add_argument("--days", type=int, default=90,
                   help="Number of days of history to analyze (default: 90)")

    # Weekly update args
    p.add_argument("--week", type=int, help="Week number (1-indexed)")
    p.add_argument("--plan-start", help="Plan start date (YYYY-MM-DD)")
    p.add_argument("--prev-ctl", type=float, help="Previous CTL value")
    p.add_argument("--prev-atl", type=float, help="Previous ATL value")
    p.add_argument("--planned-tss", help='Planned TSS as JSON object, e.g. \'{"Tue":65,"Thu":70}\'')
    p.add_argument("--prev-peaks", help='Previous peak powers as JSON, e.g. \'{"5s":450,"1min":280}\'')

    args = p.parse_args()

    # Load credentials
    load_env()
    athlete_id = args.athlete_id or os.environ.get("INTERVALS_ICU_ATHLETE_ID")
    api_key = args.api_key or os.environ.get("INTERVALS_ICU_API_KEY")

    if not athlete_id or not api_key:
        p.error("Provide --athlete-id and --api-key, or set INTERVALS_ICU_ATHLETE_ID and "
                "INTERVALS_ICU_API_KEY in .env or environment")

    client = IntervalsIcuClient(athlete_id, api_key)

    if args.bootstrap:
        result = bootstrap(client, args.days)
    elif args.weekly_update:
        if args.week is None or not args.plan_start or args.prev_ctl is None or args.prev_atl is None:
            p.error("--weekly-update requires --week, --plan-start, --prev-ctl, --prev-atl")

        try:
            datetime.strptime(args.plan_start, "%Y-%m-%d")
        except ValueError:
            p.error(f"--plan-start must be YYYY-MM-DD format, got: {args.plan_start}")

        planned = {}
        if args.planned_tss:
            try:
                planned = json.loads(args.planned_tss)
            except json.JSONDecodeError as e:
                p.error(f"--planned-tss must be valid JSON: {e}")

        prev_peaks = None
        if args.prev_peaks:
            try:
                prev_peaks = json.loads(args.prev_peaks)
            except json.JSONDecodeError as e:
                p.error(f"--prev-peaks must be valid JSON: {e}")

        result = weekly_update(
            client, args.week, args.plan_start,
            args.prev_ctl, args.prev_atl, planned,
            prev_peaks=prev_peaks,
        )

    out = json.dumps(result, indent=2, default=str, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
