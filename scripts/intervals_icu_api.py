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

BASE_URL = "https://intervals.icu/api/v1"
POWER_ZONES = {
    "Z1": (0.00, 0.55), "Z2": (0.55, 0.75), "Z3": (0.75, 0.90),
    "Z4": (0.90, 1.05), "Z5": (1.05, 1.20), "Z6": (1.20, 1.50), "Z7": (1.50, float("inf")),
}

# intervals.icu activity types that produce cycling power data. Used by weekly_summary
# to scope both load aggregation and power-curve fetching to cycling — a high-TSS Run
# would otherwise be picked for power-curve fetch (some watches estimate run power)
# and pollute week_peaks / power_profile with non-cycling watts.
CYCLING_TYPES = ("Ride", "VirtualRide", "EBikeRide", "Handcycle")


def _is_cycling(activity):
    """Treat empty/missing type as cycling (defensive — intervals.icu always sets type)."""
    sport = activity.get("type") or ""
    return not sport or sport in CYCLING_TYPES

# Coggan male power profile table (W/kg thresholds) for rider profiling
POWER_PROFILE = {
    "5s":    {"untrained": 8.0, "fair": 11.0, "moderate": 14.0, "good": 16.5, "very_good": 19.0, "excellent": 22.0, "exceptional": 24.0},
    "1min":  {"untrained": 3.5, "fair": 5.0,  "moderate": 6.5,  "good": 7.5,  "very_good": 8.5,  "excellent": 9.5,  "exceptional": 11.0},
    "5min":  {"untrained": 2.5, "fair": 3.2,  "moderate": 3.8,  "good": 4.3,  "very_good": 4.8,  "excellent": 5.3,  "exceptional": 6.0},
    "20min": {"untrained": 2.0, "fair": 2.8,  "moderate": 3.3,  "good": 3.8,  "very_good": 4.2,  "excellent": 4.6,  "exceptional": 5.2},
}


class IntervalsIcuClient:
    def __init__(self, athlete_id, api_key):
        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = ("API_KEY", api_key)

    def __repr__(self):
        return f"IntervalsIcuClient(athlete_id={self.athlete_id!r})"

    def _get(self, endpoint, params=None):
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(3):
            try:
                r = self.session.get(url, params=params, timeout=15)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < 2:
                    delay = 2 ** (attempt + 1)
                    print(f"WARNING: {type(e).__name__} on {endpoint}, retrying in {delay}s...",
                          file=sys.stderr)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"{type(e).__name__} on {endpoint} after 3 attempts") from e
            if r.status_code == 401:
                raise RuntimeError(f"Authentication failed (401) for {endpoint} — check API key")
            if r.status_code == 404:
                raise RuntimeError(f"Not found (404): {endpoint} — check activity ID")
            if r.status_code in (429, 502, 503, 504):
                if attempt < 2:
                    delay = 2 ** (attempt + 1)
                    print(f"WARNING: HTTP {r.status_code} on {endpoint}, retrying in {delay}s...",
                          file=sys.stderr)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"HTTP {r.status_code} on {endpoint} after 3 attempts")
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                raise RuntimeError(f"Non-JSON response from {endpoint} (HTTP {r.status_code})")

    def get_activity(self, activity_id):
        return self._get(f"/activity/{activity_id}")

    def get_intervals(self, activity_id):
        data = self._get(f"/activity/{activity_id}/intervals")
        # Response is {icu_intervals: [...], icu_groups: [...], ...}
        if isinstance(data, dict):
            return data.get("icu_intervals", [])
        return data

    def get_streams(self, activity_id, types=None):
        if types is None:
            types = ["watts", "heartrate", "cadence"]
        return self._get(f"/activity/{activity_id}/streams.json", {"types": types})

    def get_power_curve(self, activity_id):
        return self._get(f"/activity/{activity_id}/power-curve.json")

    def get_athlete(self):
        return self._get(f"/athlete/{self.athlete_id}")

    def list_activities(self, oldest, newest=None, limit=None):
        params = {"oldest": oldest}
        if newest: params["newest"] = newest
        if limit: params["limit"] = limit
        return self._get(f"/athlete/{self.athlete_id}/activities", params)

    def get_wellness(self, oldest, newest=None):
        """Fetch daily wellness records for date range (YYYY-MM-DD strings)."""
        params = {"oldest": oldest}
        if newest: params["newest"] = newest
        return self._get(f"/athlete/{self.athlete_id}/wellness", params)


# ---------------------------------------------------------------------------
# Metric computation helpers
# ---------------------------------------------------------------------------

def _clean_watts(watts):
    """Replace None/negative power samples with 0 (zero-fill for rolling-window calculations)."""
    return [w if w is not None and w >= 0 else 0 for w in watts]


def compute_np(watts):
    """30s rolling average NP. Assumes 1-second samples (standard for power meters / intervals.icu)."""
    if not watts or len(watts) < 30: return None
    clean = _clean_watts(watts)
    window_sum = sum(clean[:30])
    rolling_fourth = (window_sum / 30) ** 4
    for i in range(1, len(clean) - 29):
        window_sum += clean[i + 29] - clean[i - 1]
        rolling_fourth += (window_sum / 30) ** 4
    n_windows = len(clean) - 29
    return round((rolling_fourth / n_windows) ** 0.25, 1)


def compute_peaks(watts):
    """Fallback peak power computation from stream data."""
    if not watts: return {}
    clean = _clean_watts(watts)
    n = len(clean)
    # Prefix sum: prefix[i] = sum(clean[0:i])
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + clean[i]
    durs = {5: "5s", 15: "15s", 30: "30s", 60: "1min", 120: "2min",
            300: "5min", 600: "10min", 1200: "20min", 1800: "30min", 3600: "1hr"}
    peaks = {}
    for dur, label in durs.items():
        if n < dur: continue
        best = max(prefix[i + dur] - prefix[i] for i in range(n - dur + 1))
        peaks[label] = round(best / dur, 1)
    return peaks


def compute_zones(watts, ftp):
    if not watts or not ftp: return {}, {}
    zs = {z: 0 for z in POWER_ZONES}
    for w in watts:
        if w is None or w < 0: continue
        r = w / ftp
        for z, (lo, hi) in POWER_ZONES.items():
            if lo <= r < hi: zs[z] += 1; break
    t = sum(zs.values())
    return zs, {z: round(s / t * 100, 1) if t else 0 for z, s in zs.items()}


def compute_drift(watts, hr):
    """Cardiac drift as EF decoupling %. Positive = HR drifted up (EF dropped). <5% = good aerobic fitness."""
    if not watts or not hr or len(watts) < 60: return None
    mid = len(watts) // 2
    def ef(ws, hs):
        p = [(w, h) for w, h in zip(ws, hs) if w is not None and w > 0 and h is not None and h > 0]
        if not p: return None
        return (sum(x[0] for x in p) / len(p)) / (sum(x[1] for x in p) / len(p))
    e1, e2 = ef(watts[:mid], hr[:mid]), ef(watts[mid:], hr[mid:])
    if e1 is None or e2 is None or e1 == 0: return None
    return round((e1 - e2) / e1 * 100, 2)


def interval_stats(laps):
    work_laps = [l for l in laps if l.get("average_watts") and l["average_watts"] > 0]
    pows = [l["average_watts"] for l in work_laps]
    if len(pows) < 2: return None
    max_pow = max(pows)
    # Prefer intervals.icu type field (WORK/RECOVERY) for hard/easy split — handles
    # over-under sessions correctly where power-based heuristic misclassifies both as "hard"
    typed = all(l.get("type") for l in work_laps)
    if typed:
        hard = [l["average_watts"] for l in work_laps if l.get("type") == "WORK"]
        easy = [l["average_watts"] for l in work_laps if l.get("type") == "RECOVERY"]
    else:
        # Fall back to 75%-of-max power heuristic
        hard_threshold = max_pow * 0.75
        hard = [p for p in pows if p > hard_threshold]
        easy = [p for p in pows if p <= hard_threshold]
    def _stats(vals):
        if len(vals) < 2: return None
        avg = sum(vals) / len(vals)
        sd = math.sqrt(sum((p - avg) ** 2 for p in vals) / (len(vals) - 1))
        return {"n": len(vals), "powers": vals, "avg": round(avg, 1), "stdev": round(sd, 1),
                "cv": round(sd / avg * 100, 1) if avg else 0,
                "fade": round((vals[0] - vals[-1]) / vals[0] * 100, 1) if vals[0] else 0}
    result = {"all_laps": {"n": len(pows), "powers": pows}}
    if hard:
        result["hard_intervals"] = _stats(hard) or {
            "n": len(hard), "powers": hard, "avg": round(sum(hard) / len(hard), 1),
            "stdev": 0, "cv": 0, "fade": 0}
    if easy:
        result["easy_intervals"] = {"n": len(easy), "powers": easy, "avg": round(sum(easy) / len(easy), 1)}
    return result


FTP_TEST_KEYWORDS = ["ftp test", "ftp_test", "ramp test", "20 min test", "20min test", "8 min test", "8min test", "map test"]

def detect_ftp_test(name, peaks, moving_time, ftp_ref=200):
    name_lower = (name or "").lower()
    by_name = any(kw in name_lower for kw in FTP_TEST_KEYWORDS)
    result = {"likely_ftp_test": False, "detection_methods": []}
    if by_name:
        result["likely_ftp_test"] = True
        result["detection_methods"].append("activity_name")
    p20 = peaks.get("20min")
    # Only flag as FTP test if 20min power is within 80–150% of reference FTP
    min_ftp_test_power = ftp_ref * 0.80
    max_ftp_test_power = ftp_ref * 1.50  # reject anomalous data
    # Skip 20min heuristic for known structured workout types
    WORKOUT_TYPE_KEYWORDS = ["recovery", "sweet spot", "sweetspot", "threshold", "vo2max", "vo2",
                              "endurance", "over-under", "over under", "tempo", "warm", "cool", "opener"]
    is_structured_workout = any(kw in name_lower for kw in WORKOUT_TYPE_KEYWORDS)
    if p20 and min_ftp_test_power <= p20 <= max_ftp_test_power and 1800 <= moving_time <= 5400 and not is_structured_workout:
        result["likely_ftp_test"] = True
        if not by_name:
            result["detection_methods"].append("20min_effort_heuristic")
        result["estimated_ftp_20min"] = round(p20 * 0.95, 1)
        result["estimated_ftp_formula_20min"] = "20min_avg × 0.95"
    if "ramp" in name_lower and 600 <= moving_time <= 1500:
        result["likely_ftp_test"] = True
        result["detection_methods"].append("ramp_test")
        p1 = peaks.get("1min")
        if p1:
            result["estimated_ftp_ramp"] = round(p1 * 0.75, 1)
            result["estimated_ftp_formula_ramp"] = "last_completed_1min × 0.75"
    return result if result["likely_ftp_test"] else None


def detect_indoor(trainer, sport_type):
    """Determine if activity is indoor. intervals.icu returns trainer=null for VirtualRide."""
    return bool(trainer) or sport_type in ("VirtualRide", "VirtualRun")


def fmt_time(sec):
    h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


# ---------------------------------------------------------------------------
# intervals.icu specific helpers
# ---------------------------------------------------------------------------

def extract_id(url_or_id):
    """Extract activity ID from intervals.icu URL or raw ID string."""
    s = str(url_or_id).strip()
    # Already an intervals.icu ID like "i126468486" or plain numeric "17478304236"
    if re.match(r"^i\d+$", s):
        return s
    if re.match(r"^\d+$", s):
        return s
    # URL pattern: intervals.icu/activities/i123456 or intervals.icu/activities/123456
    m = re.search(r"intervals\.icu/activities/(i?\d+)", s)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract intervals.icu activity ID from: {url_or_id}")


def parse_power_curve(curve_data):
    """Parse intervals.icu power curve into standard peak powers dict."""
    if not curve_data: return {}
    target_durations = {5: "5s", 15: "15s", 30: "30s", 60: "1min", 120: "2min",
                        300: "5min", 600: "10min", 1200: "20min", 1800: "30min", 3600: "1hr"}
    peaks = {}

    if isinstance(curve_data, dict) and "secs" in curve_data:
        secs_list = curve_data.get("secs", [])
        watts_list = curve_data.get("watts", [])
        if secs_list and watts_list:
            lookup = dict(zip(secs_list, watts_list))
            for dur, label in target_durations.items():
                if dur in lookup and lookup[dur] is not None:
                    peaks[label] = round(lookup[dur], 1)
    elif curve_data:
        # Non-empty but unexpected format — warn so silent data loss is visible
        warnings.warn(
            f"Unexpected power curve format: {type(curve_data).__name__}, "
            f"expected dict with 'secs'/'watts' keys"
        )

    return peaks


def parse_streams(stream_data):
    """Parse intervals.icu streams response into {type: [values]} dict."""
    if not stream_data: return {}
    # intervals.icu streams: list of dicts with "type" and "data", or dict keyed by type
    if isinstance(stream_data, dict):
        return {k: v for k, v in stream_data.items() if isinstance(v, list)}
    if isinstance(stream_data, list):
        result = {}
        for item in stream_data:
            if isinstance(item, dict) and "type" in item and "data" in item:
                result[item["type"]] = item["data"]
        return result
    return {}


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze(client, activity_id, ftp=200, weight=70.0):
    a = client.get_activity(activity_id)
    fetch_warnings = []
    fetch_errors = {}  # component -> error message; empty when all fetches succeeded

    # Fetch intervals, streams, and power curve concurrently (independent API calls)
    intervals_data, streams, power_curve = [], {}, {}

    def _fetch_intervals():
        return client.get_intervals(activity_id)

    def _fetch_streams():
        return parse_streams(client.get_streams(activity_id))

    def _fetch_power_curve():
        return parse_power_curve(client.get_power_curve(activity_id))

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_intervals = pool.submit(_fetch_intervals)
        fut_streams = pool.submit(_fetch_streams)
        fut_curve = pool.submit(_fetch_power_curve)

        try:
            intervals_data = fut_intervals.result(timeout=60)
        except Exception as e:
            fetch_warnings.append(f"intervals_fetch_failed: {e}")
            fetch_errors["intervals"] = str(e)

        try:
            streams = fut_streams.result(timeout=60)
        except Exception as e:
            fetch_warnings.append(f"streams_fetch_failed: {e}")
            fetch_errors["streams"] = str(e)

        try:
            power_curve = fut_curve.result(timeout=60)
        except Exception as e:
            fetch_warnings.append(f"power_curve_fetch_failed: {e}")
            fetch_errors["power_curve"] = str(e)

    watts = streams.get("watts", streams.get("power", []))
    hr = streams.get("heartrate", streams.get("heart_rate", []))

    # --- Stream availability ---
    has_power_stream = bool(watts and len(watts) >= 30)
    has_hr_stream = bool(hr and len(hr) >= 30)

    # --- Data completeness ---
    missing_components = []
    for warn in fetch_warnings:
        if "intervals_fetch_failed" in warn:
            missing_components.append("intervals")
        if "streams_fetch_failed" in warn:
            missing_components.append("streams")
        if "power_curve_fetch_failed" in warn:
            missing_components.append("power_curve")
    if not has_power_stream and "streams" not in missing_components:
        if watts is not None and len(watts) <= 30:
            fetch_warnings.append("streams_too_short: Power stream available but too short for zone/drift analysis")
    data_completeness = "complete" if not missing_components else f"partial (missing: {', '.join(missing_components)})"

    # --- Metrics ---
    m = {}

    # NP: prefer intervals.icu pre-computed, fall back to stream computation
    np_val = a.get("icu_weighted_avg_watts")
    if np_val is None and watts:
        np_val = compute_np(watts)
    m["normalized_power"] = np_val

    avg_w = a.get("icu_average_watts")
    moving_time = a.get("moving_time") or 0

    # IF: prefer pre-computed (icu_intensity is always a percentage, e.g. 89.13 = 0.8913 IF)
    if_val = a.get("icu_intensity")
    if if_val is not None:
        computed_if = if_val / 100
        if 0.3 <= computed_if <= 2.0:
            m["intensity_factor"] = round(computed_if, 3)
        elif np_val and ftp:
            print(f"WARNING: stored icu_intensity={if_val} (IF={computed_if:.3f}) out of plausible range "
                  f"[0.3, 2.0] — recomputing from NP/FTP", file=sys.stderr)
            fetch_warnings.append(f"if_out_of_range: stored IF={computed_if:.3f} dropped, recomputed from NP/FTP")
            m["intensity_factor"] = round(np_val / ftp, 3)
        else:
            print(f"WARNING: stored icu_intensity={if_val} (IF={computed_if:.3f}) out of plausible range "
                  f"[0.3, 2.0] — no NP/FTP fallback available", file=sys.stderr)
            fetch_warnings.append(f"if_out_of_range: stored IF={computed_if:.3f} dropped, no fallback")
    elif np_val and ftp:
        m["intensity_factor"] = round(np_val / ftp, 3)

    # TSS: prefer pre-computed
    tss_val = a.get("icu_training_load")
    if tss_val is not None:
        m["tss"] = round(tss_val, 1)
    elif np_val and ftp and moving_time:
        # TSS = (duration_s × IF² / 3600) × 100, where IF = NP / FTP
        intensity_factor = np_val / ftp
        m["tss"] = round((moving_time * intensity_factor ** 2) / 3600 * 100, 1)

    # Variability Index
    if np_val and avg_w and avg_w > 0:
        m["variability_index"] = round(np_val / avg_w, 3)

    # Efficiency Factor
    avg_hr = a.get("average_heartrate")
    if np_val is not None and avg_hr is not None and avg_hr > 0:
        m["efficiency_factor"] = round(np_val / avg_hr, 3)

    # Power to Weight
    if avg_w is not None and weight:
        m["power_to_weight"] = round(avg_w / weight, 2)

    # Peak Powers: prefer power curve API, fall back to stream computation
    if power_curve:
        m["peak_powers"] = power_curve
    elif has_power_stream:
        m["peak_powers"] = compute_peaks(watts)
        fetch_warnings.append("Power curve data could not be parsed - peak powers computed from streams instead")
    else:
        m["peak_powers"] = {}
        fetch_warnings.append("Power curve data unavailable - peak powers could not be determined")

    # Zone distribution from streams
    if has_power_stream:
        zs, zp = compute_zones(watts, ftp)
        m["zone_seconds"] = zs
        m["zone_percent"] = zp
    else:
        m["zone_seconds"] = None
        m["zone_percent"] = None

    # Cardiac drift
    if has_power_stream and has_hr_stream:
        m["cardiac_drift"] = compute_drift(watts, hr)
    else:
        m["cardiac_drift"] = None

    # --- Intervals/laps ---
    lap_list = []
    for idx, iv in enumerate(intervals_data):
        if not isinstance(iv, dict):
            continue
        lap_list.append({
            "name": iv.get("label") or iv.get("type", ""),
            "lap_index": idx,
            "type": iv.get("type", ""),
            "elapsed_time": iv.get("elapsed_time") or 0,
            "moving_time": iv.get("moving_time") or 0,
            "distance": iv.get("distance") or 0,
            "average_watts": iv.get("average_watts"),
            "normalized_power": iv.get("weighted_average_watts"),
            "average_heartrate": iv.get("average_heartrate"),
            "max_heartrate": iv.get("max_heartrate"),
            "average_cadence": iv.get("average_cadence"),
            "max_watts": iv.get("max_watts"),
            "intensity": iv.get("intensity"),
        })

    m["interval_consistency"] = interval_stats(lap_list)

    # FTP test detection
    ftp_test = detect_ftp_test(a.get("name", ""), m.get("peak_powers", {}), moving_time, ftp_ref=ftp)
    if ftp_test:
        m["ftp_test"] = ftp_test

    # --- Data quality warnings ---
    has_power = bool(a.get("device_watts", False))
    trainer = a.get("trainer", False)
    sport_type = a.get("type", "")
    is_indoor = detect_indoor(trainer, sport_type)
    warnings = list(fetch_warnings)
    if not has_power:
        warnings.append("estimated_power: No power meter detected — power metrics may be inaccurate")
    if not has_power and not is_indoor:
        warnings.append("outdoor_no_power: Outdoor ride without power meter — power data is estimated")

    # Max watts: from power curve if available, else from intervals
    max_watts = None
    if power_curve:
        # Shortest duration peak is effectively max power
        for label in ["5s", "1min"]:
            if label in (m.get("peak_powers") or {}):
                if max_watts is None or m["peak_powers"][label] > max_watts:
                    max_watts = m["peak_powers"][label]
    if max_watts is None:
        max_watts = a.get("p_max")

    return {
        "activity": {
            "id": a.get("id", activity_id),
            "name": a.get("name", ""),
            "sport_type": a.get("type", ""),
            "start_date_local": a.get("start_date_local", ""),
            "distance_km": round((a.get("distance") or 0) / 1000, 2),
            "moving_time": moving_time,
            "moving_time_fmt": fmt_time(moving_time),
            "elapsed_time": a.get("elapsed_time") or 0,
            "elevation_gain": a.get("total_elevation_gain") or 0,
            "average_watts": avg_w,
            "max_watts": max_watts,
            "average_heartrate": avg_hr,
            "max_heartrate": a.get("max_heartrate"),
            "average_cadence": a.get("average_cadence"),
            "kilojoules": round(a.get("icu_joules") / 1000, 1) if a.get("icu_joules") is not None else None,
            "has_power": has_power,
            "trainer": trainer,
            "power_data_quality": "measured" if has_power else "estimated",
            "context": "indoor" if is_indoor else "outdoor",
        },
        "data_completeness": data_completeness,
        "data_warnings": warnings,
        "fetch_errors": fetch_errors,  # {} when all 3 concurrent fetches succeeded
        "laps": lap_list,
        "metrics": m,
        "streams_available": bool(watts or hr),
        "ftp_reference": ftp,
        "source": "intervals.icu",
    }


# ---------------------------------------------------------------------------
# Power profile analysis (FE-2)
# ---------------------------------------------------------------------------

def analyze_power_profile(peaks, ftp, weight):
    """Analyze peak powers against Coggan's power profile categories.

    Args:
        peaks: dict of peak powers, e.g. {"5s": 750, "1min": 350, "5min": 250, "20min": 200}
        ftp: functional threshold power in watts
        weight: body weight in kg

    Returns:
        dict with profile_type, w_per_kg, categories, strengths, weaknesses
    """
    if not peaks or not weight or weight <= 0:
        return {"profile_type": "unknown", "w_per_kg": {}, "categories": {},
                "strengths": [], "weaknesses": []}

    # Compute W/kg for each duration present in both peaks and POWER_PROFILE
    w_per_kg = {}
    categories = {}
    category_order = ["untrained", "fair", "moderate", "good", "very_good",
                      "excellent", "exceptional"]

    for duration in POWER_PROFILE:
        if duration not in peaks or peaks[duration] is None:
            continue
        wpk = round(peaks[duration] / weight, 2)
        w_per_kg[duration] = wpk

        # Find highest threshold the athlete exceeds
        thresholds = POWER_PROFILE[duration]
        cat = "untrained"
        for level in category_order:
            if wpk >= thresholds[level]:
                cat = level
            else:
                break
        categories[duration] = cat

    if not categories:
        return {"profile_type": "unknown", "w_per_kg": w_per_kg, "categories": categories,
                "strengths": [], "weaknesses": []}

    # Find strengths (highest category) and weaknesses (lowest category)
    cat_ranks = {c: i for i, c in enumerate(category_order)}
    ranked = [(dur, cat_ranks.get(cat, 0)) for dur, cat in categories.items()]
    max_rank = max(r for _, r in ranked)
    min_rank = min(r for _, r in ranked)
    strengths = [dur for dur, r in ranked if r == max_rank]
    weaknesses = [dur for dur, r in ranked if r == min_rank and min_rank < max_rank]

    # Determine rider type based on relative strengths
    def _cat_rank(duration):
        return cat_ranks.get(categories.get(duration, "untrained"), 0)

    short_rank = max(_cat_rank("5s"), _cat_rank("1min"))
    long_rank = max(_cat_rank("5min"), _cat_rank("20min"))
    five_min_rank = _cat_rank("5min")
    twenty_min_rank = _cat_rank("20min")

    if short_rank > long_rank:
        profile_type = "sprinter"
    elif twenty_min_rank > short_rank:
        profile_type = "time_trialist"
    elif five_min_rank >= short_rank and five_min_rank >= twenty_min_rank and five_min_rank > 0:
        profile_type = "pursuiter"
    else:
        profile_type = "all_rounder"

    return {
        "profile_type": profile_type,
        "w_per_kg": w_per_kg,
        "categories": categories,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


# ---------------------------------------------------------------------------
# Weekly summary with auto-FTP detection (FE-1 + FE-3)
# ---------------------------------------------------------------------------

def weekly_summary(client, days=7, ftp=200, weight=70.0):
    """Aggregate the last N days of activities into a weekly training summary.

    Args:
        client: IntervalsIcuClient instance
        days: number of days to look back (default 7)
        ftp: functional threshold power in watts
        weight: body weight in kg

    Returns:
        dict with aggregated metrics, zone distribution, and optional FTP update suggestion
    """
    newest = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    activities = client.list_activities(oldest=oldest, newest=newest)
    if not activities:
        return {"error": "No activities found in the last {} days".format(days),
                "activity_count": 0}

    # Aggregate metrics
    total_tss = 0.0
    total_kj = 0.0
    total_moving_time = 0  # seconds
    activity_count = 0
    training_dates = set()

    # For duration-weighted IF average
    if_duration_pairs = []  # (IF, duration_seconds)

    # For IF-based zone distribution (weighted by duration)
    zone_duration = {"Z1": 0, "Z2": 0, "Z3": 0, "Z4": 0, "Z5+": 0}

    # Track max 20-min peak power for FTP detection (FE-3)
    max_20min_peak = None

    for a in activities:
        # Skip non-cycling activities (e.g., logged runs) — weekly summary is for cycling load
        if not _is_cycling(a):
            continue
        moving_time = a.get("moving_time") or 0
        if moving_time <= 0:
            continue

        activity_count += 1
        total_moving_time += moving_time

        # Track unique training dates
        date_str = (a.get("start_date_local") or "")[:10]
        if date_str:
            training_dates.add(date_str)

        # TSS: use pre-computed value
        tss = a.get("icu_training_load")
        if tss is not None:
            total_tss += tss

        # kJ: use pre-computed value
        kj = a.get("icu_joules")
        if kj is not None:
            total_kj += kj / 1000  # joules -> kJ

        # IF for zone heuristic and weighted average
        if_val = a.get("icu_intensity")
        if if_val is not None:
            computed_if = if_val / 100
            if 0.3 <= computed_if <= 2.0:
                if_duration_pairs.append((computed_if, moving_time))

                # Classify entire activity by IF into approximate zone
                if computed_if < 0.55:
                    zone_duration["Z1"] += moving_time
                elif computed_if < 0.75:
                    zone_duration["Z2"] += moving_time
                elif computed_if < 0.90:
                    zone_duration["Z3"] += moving_time
                elif computed_if < 1.05:
                    zone_duration["Z4"] += moving_time
                else:
                    zone_duration["Z5+"] += moving_time

    # FE-3: Fetch power curves only from top-3 TSS activities (reduces N API calls to 3).
    # Pull all key durations in one fetch per activity, then take the max across the
    # top-3 for each duration — gives a usable "best 7 days" power profile for free.
    # Filter to cycling here too — a high-TSS Run would otherwise consume a top-3 slot
    # and contribute garbage (or empty) power-curve data to week_peaks.
    tss_sorted = sorted(
        [a for a in activities if a.get("icu_training_load") and _is_cycling(a)],
        key=lambda a: a.get("icu_training_load", 0),
        reverse=True,
    )[:3]
    profile_durations = ("5s", "1min", "5min", "20min")

    # Capture per-activity power-curve fetch errors so the caller can distinguish
    # "no peaks because no top-3 activities" from "no peaks because the fetch failed".
    # dict[aid] = error_msg; safe under ThreadPoolExecutor because CPython dict
    # __setitem__ is atomic under the GIL and each worker writes a distinct key.
    power_curve_errors = {}

    def _fetch_curve(activity):
        aid = activity.get("id")
        try:
            return parse_power_curve(client.get_power_curve(aid))
        except Exception as e:
            msg = str(e)
            power_curve_errors[aid] = msg
            print(f"WARNING: power curve fetch for {aid} failed: {msg}", file=sys.stderr)
            return {}

    week_peaks = {}
    if tss_sorted:
        with ThreadPoolExecutor(max_workers=3) as executor:
            curves = list(executor.map(_fetch_curve, tss_sorted))
        for curve in curves:
            for dur in profile_durations:
                v = curve.get(dur)
                if v is None:
                    continue
                if dur not in week_peaks or v > week_peaks[dur]:
                    week_peaks[dur] = v
        max_20min_peak = week_peaks.get("20min")

    # Compute duration-weighted average IF
    avg_if = None
    if if_duration_pairs:
        total_weight = sum(d for _, d in if_duration_pairs)
        if total_weight > 0:
            avg_if = round(sum(if_val * d for if_val, d in if_duration_pairs) / total_weight, 3)

    # Zone distribution as percentages
    total_zone_time = sum(zone_duration.values())
    zone_pct = {}
    if total_zone_time > 0:
        zone_pct = {z: round(secs / total_zone_time * 100, 1) for z, secs in zone_duration.items()}

    # Training vs rest days
    training_days = len(training_dates)
    rest_days = days - training_days

    result = {
        "period_days": days,
        "activity_count": activity_count,
        "training_days": training_days,
        "rest_days": rest_days,
        "total_tss": round(total_tss, 1),
        "total_kj": round(total_kj, 1),
        "total_moving_time_s": total_moving_time,
        "total_moving_time_fmt": fmt_time(total_moving_time),
        "avg_if_weighted": avg_if,
        "zone_distribution_pct": zone_pct,
        "zone_distribution_seconds": zone_duration,
        "ftp_reference": ftp,
        "power_curve_errors": power_curve_errors,  # {aid: msg}; {} when all fetches succeeded
    }

    # FE-3: Auto-FTP detection
    if max_20min_peak is not None:
        result["max_20min_peak"] = round(max_20min_peak, 1)
        suggested_ftp = round(max_20min_peak * 0.95)
        if suggested_ftp > ftp * 1.03:
            change_pct = round((suggested_ftp - ftp) / ftp * 100, 1)
            result["ftp_update_suggested"] = True
            result["suggested_ftp"] = suggested_ftp
            result["ftp_change_pct"] = change_pct
        else:
            result["ftp_update_suggested"] = False
    else:
        result["ftp_update_suggested"] = False

    # Power profile across the week (best of top-3 sessions per duration)
    if week_peaks:
        result["week_peaks"] = {dur: round(v, 1) for dur, v in week_peaks.items()}
        if weight and weight > 0:
            result["power_profile"] = analyze_power_profile(week_peaks, ftp, weight)

    return result


# ---------------------------------------------------------------------------
# Wellness summary (#6 — readiness/fatigue signal layer)
# ---------------------------------------------------------------------------

def wellness_summary(client, days=14):
    """Aggregate the last N days of intervals.icu wellness data into a readiness summary.

    Pulls daily wellness records (RHR, HRV, sleep, subjective fatigue/soreness/stress/mood),
    computes a baseline average, and flags deviations against the Yellow/Red Flag rules in
    references/training_zones.md. Use 14+ days for a stable baseline.

    Args:
        client: IntervalsIcuClient instance.
        days: lookback window in days (default 14).

    Returns:
        dict with `daily` records, `baseline` averages, `latest` day, `flags` list,
        and `overall_status` ("green", "yellow", "red"). Returns `{"error": ..., "days": N}`
        if no wellness data is available.
    """
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        wellness = client.get_wellness(oldest, newest)
    except Exception as e:
        return {"error": f"Failed to fetch wellness: {e}", "days": days}

    if not wellness:
        return {
            "error": f"No wellness data found in last {days} days. "
                     "Log wellness in intervals.icu (or sync from Garmin/Oura/etc.) to enable readiness coaching.",
            "days": days,
            "days_with_data": 0,
        }

    # Sort by date ascending; intervals.icu uses "id" = "YYYY-MM-DD"
    wellness = sorted(wellness, key=lambda w: w.get("id", ""))

    daily = []
    for w in wellness:
        sleep_secs = w.get("sleepSecs")
        sleep_hours = round(sleep_secs / 3600, 1) if sleep_secs else None
        daily.append({
            "date": w.get("id"),
            "resting_hr": w.get("restingHR"),
            "hrv": w.get("hrv"),
            "sleep_hours": sleep_hours,
            "sleep_quality": w.get("sleepQuality"),
            "sleep_score": w.get("sleepScore"),
            "fatigue": w.get("fatigue"),
            "soreness": w.get("soreness"),
            "stress": w.get("stress"),
            "mood": w.get("mood"),
            "weight": w.get("weight"),
            "readiness": w.get("readiness"),
            "respiration": w.get("respiration"),
            "spo2": w.get("spO2"),
        })

    # Baseline = mean of available values across the window (excluding the latest day,
    # so today's values are compared against rolling history, not against themselves).
    # When there is only one daily record, history is empty — comparing a value against
    # itself would produce zero deltas and no flag could ever fire. In that case we
    # surface partial_baseline: True so callers know the deviation flags are suppressed
    # (the latest-day-only flags — sleep <6h and subjective ≥4 — still apply).
    history = daily[:-1] if len(daily) > 1 else []
    partial_baseline = len(history) == 0

    rhrs = [d["resting_hr"] for d in history if d["resting_hr"]]
    hrvs = [d["hrv"] for d in history if d["hrv"]]
    sleeps = [d["sleep_hours"] for d in history if d["sleep_hours"]]
    # Readiness uses `is not None` (not truthiness) because Recovery=0 is a valid
    # Whoop value (total wreck); RHR/HRV/sleep=0 are physically impossible.
    readinesses = [d["readiness"] for d in history if d["readiness"] is not None]
    respirations = [d["respiration"] for d in history if d["respiration"] is not None]

    baseline = {}
    if rhrs:
        baseline["resting_hr_avg"] = round(sum(rhrs) / len(rhrs), 1)
    if hrvs:
        baseline["hrv_avg"] = round(sum(hrvs) / len(hrvs), 1)
    if sleeps:
        baseline["sleep_hours_avg"] = round(sum(sleeps) / len(sleeps), 1)
    if readinesses:
        baseline["readiness_avg"] = round(sum(readinesses) / len(readinesses), 1)
    if respirations:
        baseline["respiration_avg"] = round(sum(respirations) / len(respirations), 1)

    latest = daily[-1] if daily else {}
    flags = []

    # Yellow/Red flag rules from training_zones.md → Fatigue Indicators
    if latest.get("resting_hr") and baseline.get("resting_hr_avg"):
        delta = round(latest["resting_hr"] - baseline["resting_hr_avg"], 1)
        if delta >= 10:
            flags.append({"signal": "RHR", "severity": "red",
                          "value": latest["resting_hr"], "baseline": baseline["resting_hr_avg"],
                          "delta_bpm": delta,
                          "rule": "RHR elevated >10 bpm above baseline (red flag)"})
        elif delta >= 5:
            flags.append({"signal": "RHR", "severity": "yellow",
                          "value": latest["resting_hr"], "baseline": baseline["resting_hr_avg"],
                          "delta_bpm": delta,
                          "rule": "RHR elevated >5 bpm above baseline (yellow flag)"})

    if latest.get("hrv") and baseline.get("hrv_avg") and baseline["hrv_avg"] > 0:
        delta_pct = round((latest["hrv"] - baseline["hrv_avg"]) / baseline["hrv_avg"] * 100, 1)
        if delta_pct <= -10:
            flags.append({"signal": "HRV", "severity": "yellow",
                          "value": latest["hrv"], "baseline": baseline["hrv_avg"],
                          "delta_pct": delta_pct,
                          "rule": "HRV depressed >10% below baseline (yellow flag)"})

    if latest.get("sleep_hours") is not None and latest["sleep_hours"] < 6:
        flags.append({"signal": "sleep", "severity": "yellow",
                      "value": latest["sleep_hours"],
                      "rule": "Sleep <6h last night (yellow flag — modify next session)"})

    # Recovery score (0–100) — sourced from intervals.icu `readiness` field, which Whoop
    # populates with its Recovery score (HRV + RHR + sleep + respiration roll-up).
    # Whoop's standard bands are absolute (already baseline-calibrated by Whoop), so no
    # deviation-from-baseline rule needed here.
    recovery = latest.get("readiness")
    if recovery is not None:
        if recovery < 34:
            flags.append({"signal": "recovery", "severity": "red",
                          "value": recovery,
                          "rule": "Recovery <34 (red flag — significantly modify or skip session)"})
        elif recovery < 67:
            flags.append({"signal": "recovery", "severity": "yellow",
                          "value": recovery,
                          "rule": "Recovery 34–66 (yellow flag — moderate session, listen to body)"})

    # Subjective scales (intervals.icu uses 1=best, 4=worst by default; some users invert).
    # Flag elevated subjective stress/fatigue/soreness only when ≥4 (worst tier).
    for key, label in (("fatigue", "fatigue"), ("soreness", "soreness"), ("stress", "stress")):
        v = latest.get(key)
        if v is not None and v >= 4:
            flags.append({"signal": key, "severity": "yellow",
                          "value": v,
                          "rule": f"Subjective {label} elevated ({v}/4 — yellow flag, watch for compounding)"})

    overall = "red" if any(f["severity"] == "red" for f in flags) \
        else "yellow" if any(f["severity"] == "yellow" for f in flags) \
        else "green"

    # Age of the most recent wellness record. 0 = logged today, 1 = yesterday, etc.
    # If the athlete missed logging for a day or two, `latest` is *not* today's
    # reading — coaching templates should surface the age when > 0 so the
    # athlete doesn't act on stale numbers. None when the date is missing/malformed.
    latest_date_age_days = None
    if latest.get("date"):
        try:
            latest_dt = datetime.strptime(latest["date"], "%Y-%m-%d").date()
            latest_date_age_days = (datetime.now().date() - latest_dt).days
        except ValueError:
            pass

    return {
        "days": days,
        "days_with_data": len(daily),
        "history_days": len(history),
        "partial_baseline": partial_baseline,
        "baseline": baseline,
        "latest": latest,
        "latest_date_age_days": latest_date_age_days,
        "flags": flags,
        "overall_status": overall,
        "daily": daily,
        "baseline_note": (
            "Only one daily wellness record available — no historical baseline to "
            "compare against. RHR / HRV deviation flags are suppressed; latest-day "
            "flags (sleep <6h, subjective ≥4, Recovery <67) still apply. Log a few "
            "more days to enable full readiness coaching."
        ) if partial_baseline else None,
    }


def load_env(env_path=None):
    """Load .env file from script dir or project root."""
    if env_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, ".env"),
            os.path.join(os.path.dirname(script_dir), ".env"),
        ]
    else:
        candidates = [env_path]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    val = val.strip()
                    # Strip matching quotes (single or double)
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                    else:
                        # Strip inline comments only if # is preceded by whitespace
                        # (avoids truncating values that legitimately contain #)
                        val = re.split(r'\s+#', val, maxsplit=1)[0]
                    os.environ.setdefault(key.strip(), val)
            return


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

    # Final fallbacks after profile logic — neutral generic defaults, warn loudly
    used_fallback = []
    if args.ftp is None:
        args.ftp = 200
        used_fallback.append("FTP=200W")
    if args.weight is None:
        args.weight = 70.0
        used_fallback.append("weight=70kg")
    if used_fallback:
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
