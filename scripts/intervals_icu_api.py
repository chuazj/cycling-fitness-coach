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


def readiness_check(client, lookback_days=14):
    """Point-in-time pre-ride readiness verdict.

    Aggregates today's WHOOP-synced wellness against a 14-day baseline and emits a
    single GREEN / YELLOW-HIGH / YELLOW-LOW / RED verdict with a session-type ceiling.
    Intended as a one-shot replacement for manual sleep/recovery/TSB gate-checking.

    Signals combined (worst-of-severity wins):
      - Sleep hours (≥7h pass, 6-7h tiebroken by WHOOP sleep score, <6h fail)
      - WHOOP recovery (green ≥67, yellow-high 50-66, yellow-low 34-49, red <34)
      - HRV vs 7-day rolling band (μ ± 0.5σ, Plews/Buchheit): today below = yellow,
        2 consecutive days below = red de-load trigger (escalation, not duplicate)
      - HRV CV-trend (14-day split-window): last-7d CV ≥ prior-7d CV + 2.0pp = yellow
        informational flag, early autonomic-strain signal
      - RHR vs 14-day baseline (≥5bpm = yellow, ≥10bpm = red)
      - Respiration vs 14-day baseline (+1.0/min = yellow, +2.0/min = red illness gate)
      - SpO2 vs 14-day baseline (≥2pp below = yellow) + absolute <90% red floor;
        relative yellow needs a mature baseline (≥7 days), red floor always fires
      - 3-day recovery slope (drop ≥10pt over 3 days = yellow trend flag)
      - Progression signal (HRV ≥3 days above μ+0.5σ AND CTL rising → +5-10% TSS;
        informational, surfaced separately from gating flags)
      - TSB context (informational, not gating)
      - Subjective wellness staleness check (all = 1 across 3+ fields = noisy data warning)

    Returns dict with `verdict`, `ceiling`, per-signal breakdown, and `verdict_text`
    (human-readable rendering for stdout).
    """
    summary = wellness_summary(client, days=lookback_days)
    if summary.get("error"):
        return {"error": summary["error"], "lookback_days": lookback_days}

    latest = summary.get("latest") or {}
    baseline = summary.get("baseline") or {}
    sample_sizes = summary.get("baseline_sample_sizes") or {}
    flags = list(summary.get("flags") or [])
    today_recovery = latest.get("readiness")

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Training load + 3-day slope are now sourced from wellness_summary (R6).
    # No extra API call needed; no recomputation here.
    tl = summary.get("training_load") or {}
    ctl, atl, tsb = tl.get("ctl"), tl.get("atl"), tl.get("tsb")

    # Pass the full slope dict through so format_readiness_check can render
    # positive trends ("Recovery improving") too — not just alarms. The dict
    # carries `alarm: bool` so downstream rendering can style accordingly.
    slope_alarm = summary.get("recovery_slope_3day")

    # Subdivide recovery band
    band = None
    if today_recovery is not None:
        if today_recovery >= 67:
            band = "green"
        elif today_recovery >= 50:
            band = "yellow-high"
        elif today_recovery >= 34:
            band = "yellow-low"
        else:
            band = "red"

    # Sleep with score tiebreaker (borderline 6-7h)
    sleep_h = latest.get("sleep_hours")
    sleep_score = latest.get("sleep_score")
    sleep_status = "green"
    sleep_note = None
    if sleep_h is None:
        sleep_status = "missing"
    elif sleep_h < 6:
        sleep_status = "red"
    elif sleep_h < 7:
        if sleep_score is not None and sleep_score >= 85:
            sleep_status = "yellow"
            sleep_note = f"borderline ({sleep_h}h) but score {sleep_score} keeps yellow (would have been red)"
        elif sleep_score is not None and sleep_score < 70:
            sleep_status = "red"
            sleep_note = f"borderline ({sleep_h}h) and score {sleep_score} downgrades to red"
        else:
            sleep_status = "yellow"
    # ≥7h = green by default

    # Verdict: worst-of(sleep, recovery band, slope, RHR/HRV flags).
    # Exclude the legacy "recovery" flag from the yellow/red check — the new `band`
    # variable supersedes it (band has finer granularity: yellow-high vs yellow-low).
    # Otherwise the 34-66 flag from wellness_summary would force every yellow-high
    # day into yellow-low.
    gating_flags = [f for f in flags if f.get("signal") != "recovery"]
    has_red_flag = any(f["severity"] == "red" for f in gating_flags)
    has_yellow_flag = any(f["severity"] == "yellow" for f in gating_flags)

    if sleep_status == "red" or band == "red" or has_red_flag:
        verdict_band = "RED"
        verdict = "RED — recovery/Z2 only. Skip planned hard session."
        ceiling = "Z1-Z2 endurance, 60min max, no intervals"
    elif band == "yellow-low" or sleep_status == "yellow" or has_yellow_flag:
        verdict_band = "YELLOW-LOW"
        verdict = "YELLOW-LOW — Sweet Spot OK; downgrade Threshold to SS, swap VO2max to SS or Z2."
        ceiling = "Sweet Spot 88-94% FTP max"
    elif band == "yellow-high":
        verdict_band = "YELLOW-HIGH"
        verdict = "YELLOW-HIGH — Threshold/SS OK; VO2max marginal (proceed if motivated, abort if HR/RPE elevated)."
        ceiling = "Threshold 97-101% FTP max; VO2max with abort triggers armed"
    elif band == "green":
        verdict_band = "GREEN"
        verdict = "GREEN — all session types clear."
        ceiling = "No restrictions"
    else:
        verdict_band = "INSUFFICIENT-DATA"
        verdict = "INSUFFICIENT DATA — log a wellness entry or wait for WHOOP sync."
        ceiling = "—"

    # Subjective stale-data + subjective values: lifted from wellness_summary (R6).
    subj_keys = ["fatigue", "soreness", "stress", "mood"]
    subj_vals = {k: latest.get(k) for k in subj_keys}
    subj_stale = bool(summary.get("subjective_stale_warning"))

    age_days = summary.get("latest_date_age_days")

    result = {
        "date": today_str,
        "lookback_days": lookback_days,
        "verdict_band": verdict_band,
        "verdict": verdict,
        "ceiling": ceiling,
        "data_age_days": age_days,
        "baseline_maturity": summary.get("baseline_maturity"),
        "baseline_note": summary.get("baseline_note"),
        "sleep": {"hours": sleep_h, "score": sleep_score, "status": sleep_status, "note": sleep_note},
        "recovery": {"score": today_recovery, "band": band, "slope_3day": slope_alarm},
        "hrv": {"today": latest.get("hrv"), "baseline": baseline.get("hrv_avg"),
                "cv_pct": baseline.get("hrv_cv_pct"),
                "cv_trend": baseline.get("hrv_cv_trend"),
                "band_mean_7d": baseline.get("hrv_7d_mean"),
                "band_sd_7d": baseline.get("hrv_7d_sd"),
                "sample_size": sample_sizes.get("hrv", 0)},
        "resting_hr": {"today": latest.get("resting_hr"), "baseline": baseline.get("resting_hr_avg"),
                       "sample_size": sample_sizes.get("resting_hr", 0)},
        "respiration": {"today": latest.get("respiration"),
                        "baseline": baseline.get("respiration_avg"),
                        "sample_size": sample_sizes.get("respiration", 0)},
        "spo2": {"today": latest.get("spo2"),
                 "baseline": baseline.get("spo2_avg"),
                 "sample_size": sample_sizes.get("spo2", 0)},
        "tsb": {"ctl": ctl, "atl": atl, "tsb": tsb},
        "progression_signal": summary.get("progression_signal"),
        "subjective": {**subj_vals, "stale_warning": subj_stale,
                       "stale_note": ("All values = 1 (best/default) — verify athlete is updating these manually"
                                      if subj_stale else None)},
        "flags": flags,
        "overall_status": summary.get("overall_status"),
    }
    result["verdict_text"] = format_readiness_check(result)
    return result


def format_readiness_check(result):
    """Render readiness_check result as human-readable text for stdout."""
    if result.get("error"):
        return f"ERROR: {result['error']}"

    lines = [f"Date: {result['date']}"]
    age = result.get("data_age_days")
    if age is not None and age > 0:
        lines.append(f"  ⚠ Latest wellness record is {age} day(s) old — today's WHOOP may not have synced yet")
    lines.append("")

    s = result["sleep"]
    sleep_h = f"{s['hours']}h" if s["hours"] is not None else "—"
    sleep_sc = f"score {s['score']}" if s["score"] is not None else "score —"
    sleep_tag = {"green": "OK", "yellow": "WARN", "red": "FAIL", "missing": "?"}.get(s["status"], "?")
    line = f"Sleep:        {sleep_h:<8} | {sleep_sc:<10} [{sleep_tag}]"
    if s.get("note"):
        line += f"  ({s['note']})"
    lines.append(line)

    h = result["hrv"]
    if h["today"] is not None:
        hrv_disp = round(h["today"], 1)
        n = h.get("sample_size") or 0
        if h["baseline"] is not None and n > 0:
            d = round(h["today"] - h["baseline"], 1)
            line = f"HRV:          {hrv_disp}ms{'':<3} | {d:+}ms vs {n}d baseline {h['baseline']}ms"
            # Add 7-day band context when available (Plews/Buchheit reference).
            if h.get("band_mean_7d") is not None and h.get("band_sd_7d") is not None:
                mu, sd = h["band_mean_7d"], h["band_sd_7d"]
                line += f" | 7d band μ{mu}±{sd*0.5:.1f}"
            if h.get("cv_pct") is not None:
                line += f" | CV {h['cv_pct']}%"
            lines.append(line)
            # CV trend (14d split-window). Render only when rising — stable
            # CV doesn't warrant a line of its own; the absolute CV above
            # already shows the level.
            ct = h.get("cv_trend") or {}
            if ct.get("rising"):
                lines.append(f"  └─ ⚠ CV trend: {ct['prior_cv_pct']}% → "
                             f"{ct['recent_cv_pct']}% ({ct['delta_pp']:+}pp over 14d) "
                             f"— widening variability")
        else:
            lines.append(f"HRV:          {hrv_disp}ms{'':<3} | (no baseline yet)")

    r = result["resting_hr"]
    if r["today"] is not None:
        n = r.get("sample_size") or 0
        if r["baseline"] is not None and n > 0:
            d = round(r["today"] - r["baseline"], 1)
            lines.append(f"RHR:          {r['today']}bpm{'':<4} | {d:+}bpm vs {n}d baseline {r['baseline']}bpm")
        else:
            lines.append(f"RHR:          {r['today']}bpm{'':<4} | (no baseline yet)")

    rr = result.get("respiration") or {}
    if rr.get("today") is not None:
        n = rr.get("sample_size") or 0
        if rr.get("baseline") is not None and n > 0:
            d = round(rr["today"] - rr["baseline"], 2)
            lines.append(f"Resp rate:    {rr['today']:.1f}/min  | {d:+}/min vs {n}d baseline {rr['baseline']:.1f}/min")
        else:
            lines.append(f"Resp rate:    {rr['today']:.1f}/min  | (no baseline yet)")

    sp = result.get("spo2") or {}
    if sp.get("today") is not None:
        n = sp.get("sample_size") or 0
        today_sp = sp["today"]
        base_sp = sp.get("baseline")
        # Mirrors the wellness_summary SpO2 gate: baseline-relative when mature
        # (≥7 days, = MIN_BASELINE_SIZE), absolute <90% red floor always.
        sp_mature = base_sp is not None and n >= 7
        if today_sp < 90:
            tag = "FAIL"
        elif sp_mature and round(today_sp - base_sp, 1) <= -2.0:
            tag = "WARN"
        else:
            tag = "OK"
        if sp_mature:
            d = round(today_sp - base_sp, 1)
            baseline_str = f"{d:+.1f}pp vs {n}d baseline {base_sp}%"
        elif n > 0:
            baseline_str = f"baseline maturing (n={n})"
        else:
            baseline_str = "(no baseline yet)"
        lines.append(f"SpO2:         {today_sp}%{'':<5} | {baseline_str} [{tag}]")

    rc = result["recovery"]
    if rc["score"] is not None:
        band_disp = {"green": "GREEN", "yellow-high": "YELLOW-HIGH",
                     "yellow-low": "YELLOW-LOW", "red": "RED"}.get(rc["band"], "—")
        lines.append(f"Recovery:     {rc['score']}{'':<7} | {band_disp}")
        sl = rc.get("slope_3day")
        if sl and abs(sl.get("delta") or 0) >= 5:
            # Render meaningful trends (≥5pt change over 3 days). Alarms get
            # the ⚠ marker; positive trends get a neutral confirmation.
            label = "⚠ trend alarm" if sl.get("alarm") else "trending up" if sl["delta"] > 0 else "trending down"
            lines.append(f"  └─ 3-day slope: {sl['three_days_ago']} → {sl['today']} ({sl['delta']:+}pt) {label}")

    t = result["tsb"]
    if t["tsb"] is not None:
        state = ("fresh" if t["tsb"] >= 5 else "neutral" if t["tsb"] >= -10 else
                 "productive" if t["tsb"] >= -30 else "overreached")
        lines.append(f"TSB:          {t['tsb']:+}{'':<7} | CTL {t['ctl']} / ATL {t['atl']} ({state})")

    sj = result["subjective"]
    filled = [(k, sj[k]) for k in ("fatigue", "soreness", "stress", "mood") if sj.get(k) is not None]
    if filled:
        lines.append(f"Subjective:   " + ", ".join(f"{k}={v}" for k, v in filled))
        if sj.get("stale_warning"):
            lines.append(f"  └─ ⚠ {sj['stale_note']}")

    lines += ["", "─" * 70,
              f"VERDICT:  {result['verdict']}",
              f"CEILING:  {result['ceiling']}",
              "─" * 70]

    yellow_red_flags = [f for f in (result.get("flags") or []) if f["severity"] in ("yellow", "red")]
    if yellow_red_flags:
        lines.append("")
        lines.append("Active flags:")
        for f in yellow_red_flags:
            lines.append(f"  [{f['severity'].upper()}] {f['rule']}")

    prog = result.get("progression_signal")
    if prog:
        lines.append("")
        lines.append("Progression signal:")
        lines.append(f"  [GREEN-LIGHT] {prog['rule']}")

    return "\n".join(lines)


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
