"""Pure metric computation and parsing — no I/O, stdlib only.

NP/IF/TSS, peak powers, zone distribution, cardiac drift, interval stats,
FTP-test detection, intervals.icu response parsing, and Coggan power profiling.
"""
import math
import re
import warnings

POWER_ZONES = {
    "Z1": (0.00, 0.55), "Z2": (0.55, 0.75), "Z3": (0.75, 0.90),
    "Z4": (0.90, 1.05), "Z5": (1.05, 1.20), "Z6": (1.20, 1.50), "Z7": (1.50, float("inf")),
}

# intervals.icu activity types that produce cycling power data. Used by weekly_summary
# to scope both load aggregation and power-curve fetching to cycling — a high-TSS Run
# would otherwise be picked for power-curve fetch (some watches estimate run power)
# and pollute week_peaks / power_profile with non-cycling watts.
CYCLING_TYPES = ("Ride", "VirtualRide", "EBikeRide", "Handcycle")

# Coggan male power profile table (W/kg thresholds) for rider profiling
POWER_PROFILE = {
    "5s":    {"untrained": 8.0, "fair": 11.0, "moderate": 14.0, "good": 16.5, "very_good": 19.0, "excellent": 22.0, "exceptional": 24.0},
    "1min":  {"untrained": 3.5, "fair": 5.0,  "moderate": 6.5,  "good": 7.5,  "very_good": 8.5,  "excellent": 9.5,  "exceptional": 11.0},
    "5min":  {"untrained": 2.5, "fair": 3.2,  "moderate": 3.8,  "good": 4.3,  "very_good": 4.8,  "excellent": 5.3,  "exceptional": 6.0},
    "20min": {"untrained": 2.0, "fair": 2.8,  "moderate": 3.3,  "good": 3.8,  "very_good": 4.2,  "excellent": 4.6,  "exceptional": 5.2},
}


# ---------------------------------------------------------------------------
# Metric computation helpers
# ---------------------------------------------------------------------------

def _is_cycling(activity):
    """Treat empty/missing type as cycling (defensive — intervals.icu always sets type)."""
    sport = activity.get("type") or ""
    return not sport or sport in CYCLING_TYPES


def _stdev(values):
    """Sample standard deviation. Returns None for n<2 (math undefined).
    Plain stdlib math, no numpy. Used for HRV 7-day rolling band per Plews/Buchheit."""
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(var)


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


def compute_tss(np_watts, ftp, duration_s):
    """Training Stress Score from Normalized Power.

    TSS = duration_s × IF² / 3600 × 100, where IF = NP / FTP.
    Returns None when any input is missing or non-positive (no TSS is
    better than a misleading zero).
    """
    if np_watts is None or ftp is None or duration_s is None:
        return None
    if np_watts <= 0 or ftp <= 0 or duration_s <= 0:
        return None
    intensity_factor = np_watts / ftp
    return round((duration_s * intensity_factor ** 2) / 3600 * 100, 1)


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
