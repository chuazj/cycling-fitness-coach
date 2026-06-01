"""Single-activity analysis and weekly training summary."""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from .metrics import (
    _is_cycling, analyze_power_profile, compute_drift, compute_np, compute_tss,
    compute_peaks, compute_zones, detect_ftp_test, detect_indoor, fmt_time,
    interval_stats, parse_power_curve, parse_streams,
)


# ---------------------------------------------------------------------------
# Single-responsibility helpers (module-private)
# ---------------------------------------------------------------------------

def _fetch_activity_data(client, activity_id):
    """Fetch the activity record plus intervals, streams, and power curve concurrently.

    Returns:
        (a, intervals_data, streams, power_curve, fetch_warnings, fetch_errors)
    """
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

    return a, intervals_data, streams, power_curve, fetch_warnings, fetch_errors


def _compute_power_metrics(a, watts, ftp, weight, moving_time, fetch_warnings):
    """Compute NP / IF / TSS / VI / EF / power-to-weight from activity fields and streams.

    Mutates fetch_warnings in place for out-of-range IF cases.
    Returns a dict with only the keys it actually sets.
    """
    m = {}

    # NP: prefer intervals.icu pre-computed, fall back to stream computation
    np_val = a.get("icu_weighted_avg_watts")
    if np_val is None and watts:
        np_val = compute_np(watts)
    m["normalized_power"] = np_val

    avg_w = a.get("icu_average_watts")

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

    # TSS: prefer pre-computed, else model from NP/FTP/duration
    tss_val = a.get("icu_training_load")
    if tss_val is not None:
        m["tss"] = round(tss_val, 1)
    else:
        modeled_tss = compute_tss(np_val, ftp, moving_time)
        if modeled_tss is not None:
            m["tss"] = modeled_tss

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

    return m


def _compute_stream_metrics(watts, hr, power_curve, has_power_stream, has_hr_stream, ftp,
                            fetch_warnings):
    """Compute peak_powers / zone_seconds / zone_percent / cardiac_drift from streams.

    Mutates fetch_warnings in place for power-curve fallback cases.
    Returns a dict with only the keys it actually sets.
    """
    m = {}

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

    return m


def _build_lap_list(intervals_data):
    """Build the lap/interval list from raw intervals API data.

    Returns a list of dicts, one per valid interval entry.
    """
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
    return lap_list


def _build_activity_block(a, moving_time, avg_w, max_watts, avg_hr, has_power, trainer,
                           is_indoor, activity_id):
    """Build the ``"activity"`` sub-dict of the analyze return value.

    Returns that dict.
    """
    return {
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
    }


# ---------------------------------------------------------------------------
# Main analysis (thin orchestrator)
# ---------------------------------------------------------------------------

def analyze(client, activity_id, ftp=200, weight=70.0):
    # Fetch all data; collect fetch_warnings and fetch_errors
    a, intervals_data, streams, power_curve, fetch_warnings, fetch_errors = \
        _fetch_activity_data(client, activity_id)

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
        # S2: emit "too short" only for a genuinely short power stream.
        # A fully absent power stream (watts == []) is already reflected by
        # has_power_stream=False → zone_seconds=None + the peak-powers
        # "unavailable" warning; a second (misleading) message is wrong.
        if watts and len(watts) < 30:
            fetch_warnings.append("streams_too_short: Power stream present but too short for zone/drift analysis")
    data_completeness = "complete" if not missing_components else f"partial (missing: {', '.join(missing_components)})"

    avg_w = a.get("icu_average_watts")
    moving_time = a.get("moving_time") or 0
    avg_hr = a.get("average_heartrate")

    # --- Metrics ---
    m = {}
    m.update(_compute_power_metrics(a, watts, ftp, weight, moving_time, fetch_warnings))
    m.update(_compute_stream_metrics(watts, hr, power_curve, has_power_stream, has_hr_stream,
                                     ftp, fetch_warnings))

    # --- Intervals/laps ---
    lap_list = _build_lap_list(intervals_data)
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
    data_warnings = list(fetch_warnings)
    if not has_power:
        data_warnings.append("estimated_power: No power meter detected — power metrics may be inaccurate")
    if not has_power and not is_indoor:
        data_warnings.append("outdoor_no_power: Outdoor ride without power meter — power data is estimated")

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
        "activity": _build_activity_block(a, moving_time, avg_w, max_watts, avg_hr,
                                          has_power, trainer, is_indoor, activity_id),
        "data_completeness": data_completeness,
        "data_warnings": data_warnings,
        "fetch_errors": fetch_errors,  # {} when all 3 concurrent fetches succeeded
        "laps": lap_list,
        "metrics": m,
        "streams_available": bool(watts or hr),
        "ftp_reference": ftp,
        "source": "intervals.icu",
    }


# ---------------------------------------------------------------------------
# Weekly summary helpers (module-private)
# ---------------------------------------------------------------------------

def _aggregate_week(activities):
    """Accumulate per-activity totals across all cycling activities in the list.

    Skips non-cycling activities and activities with moving_time <= 0.

    Returns:
        dict with keys: total_tss, total_kj, total_moving_time, activity_count,
        training_dates, if_duration_pairs, zone_duration
    """
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

    return {
        "total_tss": total_tss,
        "total_kj": total_kj,
        "total_moving_time": total_moving_time,
        "activity_count": activity_count,
        "training_dates": training_dates,
        "if_duration_pairs": if_duration_pairs,
        "zone_duration": zone_duration,
    }


def _fetch_week_peaks(client, activities):
    """Fetch power curves from the top-3 TSS cycling activities and accumulate peak powers.

    FE-3: Reduces N API calls to 3 by limiting to top-3 TSS activities.
    Captures per-activity fetch errors in power_curve_errors so the caller
    can distinguish "no peaks because no top-3 activities" from fetch failures.

    Returns:
        (week_peaks, power_curve_errors, max_20min_peak)
        week_peaks: dict[duration -> peak_watts] for profile_durations
        power_curve_errors: dict[aid -> error_msg]; {} when all fetches succeeded
        max_20min_peak: float or None
    """
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
    max_20min_peak = None
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

    return week_peaks, power_curve_errors, max_20min_peak


def _ftp_update_suggestion(max_20min_peak, ftp):
    """Compute FTP-update suggestion fragment from the week's 20-min peak power.

    Returns a dict fragment to be merged into the weekly_summary result:
    - None peak: {"ftp_update_suggested": False}
    - Peak present, threshold not crossed: {"max_20min_peak": ..., "ftp_update_suggested": False}
    - Peak present, threshold crossed: {"max_20min_peak": ..., "ftp_update_suggested": True,
                                         "suggested_ftp": ..., "ftp_change_pct": ...,
                                         "requires_confirming_test": True, "note": <retest caveat>}
      suggested_ftp is a RETEST FLAG, not an apply-able FTP: it is derived from an
      unpaced training peak (×0.95), so it always carries requires_confirming_test.
    """
    # FE-3: Auto-FTP detection
    if max_20min_peak is not None:
        frag = {"max_20min_peak": round(max_20min_peak, 1)}
        suggested_ftp = round(max_20min_peak * 0.95)
        if suggested_ftp > ftp * 1.03:
            change_pct = round((suggested_ftp - ftp) / ftp * 100, 1)
            frag["ftp_update_suggested"] = True
            frag["suggested_ftp"] = suggested_ftp
            frag["ftp_change_pct"] = change_pct
            # An unpaced training 20-min peak is NOT a paced FTP test: flag it
            # retest-only, never apply-able (aligns with weekly_adaptation.md →
            # "do NOT derive a new FTP from the training peak").
            frag["requires_confirming_test"] = True
            frag["note"] = ("unpaced training peak — schedule a dedicated FTP test "
                            "before changing FTP; do not apply this estimate directly")
        else:
            frag["ftp_update_suggested"] = False
        return frag
    else:
        return {"ftp_update_suggested": False}


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

    agg = _aggregate_week(activities)
    total_tss = agg["total_tss"]
    total_kj = agg["total_kj"]
    total_moving_time = agg["total_moving_time"]
    activity_count = agg["activity_count"]
    training_dates = agg["training_dates"]
    if_duration_pairs = agg["if_duration_pairs"]
    zone_duration = agg["zone_duration"]

    week_peaks, power_curve_errors, max_20min_peak = _fetch_week_peaks(client, activities)

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
    rest_days = max(0, days - training_days)

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

    # FE-3: Auto-FTP detection — merge suggestion fragment
    result.update(_ftp_update_suggestion(max_20min_peak, ftp))

    # Power profile across the week (best of top-3 sessions per duration)
    if week_peaks:
        result["week_peaks"] = {dur: round(v, 1) for dur, v in week_peaks.items()}
        if weight and weight > 0:
            result["power_profile"] = analyze_power_profile(week_peaks, ftp, weight)

    return result
