"""Wellness aggregation — RHR/HRV/sleep/recovery baselines and flag detection."""
from datetime import datetime, timedelta

from .metrics import _stdev


# ---------------------------------------------------------------------------
# Wellness summary (#6 — readiness/fatigue signal layer)
# ---------------------------------------------------------------------------

def wellness_summary(client, days=14):
    """Aggregate the last N days of intervals.icu wellness data into a readiness summary.

    Pulls daily wellness records (RHR, HRV, sleep, Whoop Recovery/respiration/SpO2,
    subjective fatigue/soreness/stress/mood), computes baselines, and flags deviations
    against the Yellow/Red Flag rules in references/training_zones.md. Deviation-based
    flags (RHR/HRV/respiration) require ≥7 days of per-metric history to fire;
    absolute-threshold flags (Recovery/sleep/subjective) fire regardless. Use 14+
    days for a "stable" baseline.

    Args:
        client: IntervalsIcuClient instance.
        days: lookback window in days (default 14).

    Returns:
        dict with the following keys (or `{"error": ..., "days": N}` if no wellness data):
          - `days`: lookback window (input echo)
          - `days_with_data`: total daily records returned
          - `days_with_whoop_data`: records with ≥1 Whoop-exclusive field populated
            (excludes manual sleep_hours entries)
          - `history_days`: count of records used as baseline (daily minus latest)
          - `partial_baseline`: bool, true only when history is empty (back-compat)
          - `baseline_maturity`: "insufficient" / "preliminary" / "consolidating" / "stable"
            (derived from smallest non-zero per-metric sample size; ≥7 = consolidating,
            ≥14 = stable)
          - `baseline_sample_sizes`: per-metric history counts
            (e.g. `{"resting_hr": 4, "hrv": 4, "respiration": 4, ...}`)
          - `baseline`: per-metric averages (only populated for metrics with history)
          - `baseline_note`: tiered human-readable warning string, None when stable —
            surface verbatim in coaching output
          - `latest`: most recent daily record (snake_case keys, e.g. `spo2`)
          - `latest_date_age_days`: 0 if today's record exists, None if date malformed
          - `flags`: list of yellow/red flag dicts
          - `overall_status`: "green" / "yellow" / "red" rollup over flags
          - `daily`: full list of daily records (oldest first)
          - `recovery_slope_3day`: dict with `today`/`three_days_ago`/`delta`/`alarm`
            (alarm true when delta ≤ -10); None when <4 records or no readiness data
          - `subjective_stale_warning`: true when 3+ subjective fields are filled and
            all equal 1 (athlete probably not updating manually)
          - `training_load`: dict with `ctl`/`atl`/`tsb` from latest raw wellness record
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
    # SpO2 truthiness is safe (0% is physically impossible) but use explicit
    # filter for clarity. SpO2 uses a baseline-relative gate (≥2pp below the
    # personal baseline = yellow) plus an absolute <90% red floor, so it needs
    # both the history values (for the baseline) and the maturity count below.
    spo2s = [d["spo2"] for d in history if d["spo2"] is not None]

    baseline_sample_sizes = {
        "resting_hr": len(rhrs),
        "hrv": len(hrvs),
        "sleep_hours": len(sleeps),
        "readiness": len(readinesses),
        "respiration": len(respirations),
        "spo2": len(spo2s),
    }

    # Baseline maturity tiers — drives both deviation-flag suppression and
    # the human-readable baseline_note. Threshold ≥7 days reflects the noise
    # floor for HRV/RHR daily measurements (single-night swings of ±10-20%
    # are common; require a week of history before treating deltas as signal).
    # ≥14 days = "stable" matches HRV4Training / Marco Altini convention.
    MIN_BASELINE_SIZE = 7
    nonzero_sizes = [n for n in baseline_sample_sizes.values() if n > 0]
    if not nonzero_sizes:
        baseline_maturity = "insufficient"
    elif min(nonzero_sizes) < MIN_BASELINE_SIZE:
        baseline_maturity = "preliminary"
    elif min(nonzero_sizes) < 14:
        baseline_maturity = "consolidating"
    else:
        baseline_maturity = "stable"

    baseline = {}
    if rhrs:
        baseline["resting_hr_avg"] = round(sum(rhrs) / len(rhrs), 1)
    if hrvs:
        baseline["hrv_avg"] = round(sum(hrvs) / len(hrvs), 1)
        # Coefficient of variation (CV) = SD/mean as % — stability signal.
        # Rising CV during chronic load = early autonomic strain even before
        # the mean drops. Plews/Buchheit / HRV4Training convention.
        hrv_sd_full = _stdev(hrvs)
        if hrv_sd_full is not None and baseline["hrv_avg"] > 0:
            baseline["hrv_cv_pct"] = round(hrv_sd_full / baseline["hrv_avg"] * 100, 1)
        # 7-day rolling mean + SD for the band check (Plews/Buchheit method).
        # Window = last 7 days of history (= 7 days before today). Today is
        # compared against this band; yesterday too for the 2-day persistence rule.
        recent7 = hrvs[-7:] if len(hrvs) >= 7 else []
        if recent7:
            baseline["hrv_7d_mean"] = round(sum(recent7) / len(recent7), 1)
            sd7 = _stdev(recent7)
            if sd7 is not None:
                baseline["hrv_7d_sd"] = round(sd7, 1)
        # 14-day CV trend: compare CV of last 7 days vs prior 7 days. Rising
        # CV = widening day-to-day variability = early autonomic strain
        # (Plews/Buchheit). Often precedes the HRV mean dropping below band
        # by several days, so this catches overreaching earlier than the
        # band check alone. Requires ≥14 days of HRV history. Threshold:
        # +2.0 percentage points (≈ 1 SD of typical CV variation; coarse
        # but matches the "meaningful but not noise" line for ZJ's
        # typical CV range of 10-16%).
        if len(hrvs) >= 14:
            prior7 = hrvs[-14:-7]
            recent_mean = sum(recent7) / len(recent7)
            prior_mean = sum(prior7) / len(prior7)
            recent_sd = _stdev(recent7)
            prior_sd = _stdev(prior7)
            if (recent_sd is not None and prior_sd is not None
                    and recent_mean > 0 and prior_mean > 0):
                recent_cv = recent_sd / recent_mean * 100
                prior_cv = prior_sd / prior_mean * 100
                delta_pp = round(recent_cv - prior_cv, 1)
                baseline["hrv_cv_trend"] = {
                    "recent_cv_pct": round(recent_cv, 1),
                    "prior_cv_pct": round(prior_cv, 1),
                    "delta_pp": delta_pp,
                    "rising": delta_pp >= 2.0,
                }
    if sleeps:
        baseline["sleep_hours_avg"] = round(sum(sleeps) / len(sleeps), 1)
    if readinesses:
        baseline["readiness_avg"] = round(sum(readinesses) / len(readinesses), 1)
    if respirations:
        baseline["respiration_avg"] = round(sum(respirations) / len(respirations), 1)
    if spo2s:
        baseline["spo2_avg"] = round(sum(spo2s) / len(spo2s), 1)

    latest = daily[-1] if daily else {}
    flags = []

    # Yellow/Red flag rules from training_zones.md → Fatigue Indicators.
    # Deviation-based flags (RHR, HRV, respiration) are suppressed when the
    # per-metric history is shorter than MIN_BASELINE_SIZE — the comparison
    # is too noisy to be actionable. Recovery and subjective flags use
    # absolute thresholds and fire regardless of baseline depth.
    if (latest.get("resting_hr") and baseline.get("resting_hr_avg")
            and baseline_sample_sizes["resting_hr"] >= MIN_BASELINE_SIZE):
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

    # HRV gating uses Plews/Buchheit 7-day rolling band (μ ± 0.5σ). Replaces
    # the older flat "10% below baseline" rule, which over-flagged athletes
    # with high day-to-day HRV variance and under-flagged athletes with
    # consistently narrow HRV. Requires ≥7 days of HRV history; falls back
    # silently when the 7-day window is incomplete.
    #   - Single-day below band → YELLOW "HRV below band"
    #   - Two consecutive days below band → RED "HRV de-load trigger"
    #     (escalates rather than duplicates; only the red fires in the 2-day case)
    mu7 = baseline.get("hrv_7d_mean")
    sd7 = baseline.get("hrv_7d_sd")
    if (latest.get("hrv") and mu7 is not None and sd7 is not None
            and baseline_sample_sizes["hrv"] >= MIN_BASELINE_SIZE):
        lower_band = round(mu7 - 0.5 * sd7, 1)
        today_below = latest["hrv"] < lower_band
        # Yesterday = daily[-2]; today = daily[-1]. Use the same window for
        # both checks — yesterday's value is included in the window, biasing
        # the band slightly inward, but with n=7 the bias is small and the
        # alternative (re-computing a separate band ending yesterday) needs
        # ≥8 HRV samples and adds complexity for marginal gain.
        yest_hrv = daily[-2].get("hrv") if len(daily) >= 2 else None
        yest_below = yest_hrv is not None and yest_hrv < lower_band
        if today_below and yest_below:
            flags.append({"signal": "HRV", "severity": "red",
                          "value": latest["hrv"], "yesterday": yest_hrv,
                          "band_lower": lower_band, "band_mean": mu7, "band_sd": sd7,
                          "rule": ("HRV below 7-day band (μ-0.5σ = {:.1f}ms) for 2 consecutive days "
                                   "— de-load trigger; downgrade next quality session").format(lower_band)})
        elif today_below:
            flags.append({"signal": "HRV", "severity": "yellow",
                          "value": latest["hrv"], "band_lower": lower_band,
                          "band_mean": mu7, "band_sd": sd7,
                          "rule": ("HRV below 7-day band (μ-0.5σ = {:.1f}ms) today only "
                                   "— watch tomorrow; if still below, de-load").format(lower_band)})

    # HRV CV-trend: widening autonomic variability is an early overreaching
    # signal that often precedes the mean dropping below band. Yellow-only —
    # informational, not gating. If it stacks with a below-band day, the
    # band rule above already escalates appropriately.
    cv_trend = baseline.get("hrv_cv_trend")
    if cv_trend and cv_trend.get("rising"):
        flags.append({"signal": "HRV_CV", "severity": "yellow",
                      "value": cv_trend["recent_cv_pct"],
                      "prior": cv_trend["prior_cv_pct"],
                      "delta_pp": cv_trend["delta_pp"],
                      "rule": ("HRV 7-day CV rose {:+.1f}pp ({}% → {}% over last 14d) "
                               "— early autonomic strain signal; review weekly TSS").format(
                                   cv_trend["delta_pp"], cv_trend["prior_cv_pct"],
                                   cv_trend["recent_cv_pct"])})

    # Respiration two-tier: WHOOP's own published illness-detection data shows
    # +1.0 breath/min vs personal baseline is a reliable 24-48h pre-symptomatic
    # signal; +2.0 typically coincides with active infection or significant
    # stressor (high altitude, severe dehydration). Standalone flag fires
    # before WHOOP folds respiration into Recovery and Recovery turns red.
    if (latest.get("respiration") is not None
            and baseline.get("respiration_avg") is not None
            and baseline_sample_sizes["respiration"] >= MIN_BASELINE_SIZE):
        delta = round(latest["respiration"] - baseline["respiration_avg"], 2)
        if delta > 2.0:
            flags.append({"signal": "respiration", "severity": "red",
                          "value": round(latest["respiration"], 2),
                          "baseline": baseline["respiration_avg"],
                          "delta_per_min": delta,
                          "rule": "Respiration >2/min above baseline (red flag — likely active illness; Z1 30min or full rest)"})
        elif delta > 1.0:
            flags.append({"signal": "respiration", "severity": "yellow",
                          "value": round(latest["respiration"], 2),
                          "baseline": baseline["respiration_avg"],
                          "delta_per_min": delta,
                          "rule": "Respiration >1/min above baseline (yellow flag — early illness onset signal; downgrade tomorrow's quality session)"})

    # SpO2 — baseline-relative gate (replaces the legacy absolute <95/<92 gate).
    # Wrist-PPG SpO2 has higher error than fingertip pulse oximetry, and a stable
    # personal baseline can sit well below 95% (sensor floor / individual
    # variation). An absolute <95% threshold therefore over-flags chronically for
    # such athletes — it fires every night and pins the readiness verdict at
    # yellow-low. Flag relative to the personal 14-day baseline instead, mirroring
    # the RHR / HRV / respiration gates: yellow when ≥2pp below baseline. A hard
    # absolute red floor (<90%) is always retained so a genuine severe
    # desaturation can never be normalised away by a low personal baseline.
    # When the baseline is immature (<MIN_BASELINE_SIZE days) only the red floor
    # fires — the relative yellow stays silent, consistent with HRV/respiration,
    # so the baseline-establishment window doesn't reintroduce the chronic flag.
    spo2_today = latest.get("spo2")
    if spo2_today is not None:
        spo2_base = baseline.get("spo2_avg")
        spo2_mature = (spo2_base is not None
                       and baseline_sample_sizes["spo2"] >= MIN_BASELINE_SIZE)
        spo2_delta = round(spo2_today - spo2_base, 1) if spo2_mature else None
        if spo2_today < 90:
            ctx = f" ({spo2_delta:+.1f}pp vs baseline {spo2_base}%)" if spo2_mature else ""
            flags.append({"signal": "spo2", "severity": "red",
                          "value": spo2_today, "baseline": spo2_base,
                          "delta_pp": spo2_delta,
                          "rule": (f"SpO2 {spo2_today}%{ctx} (<90% absolute floor — red flag: "
                                   "significant desaturation; rest and check for illness / "
                                   "altitude / sleep apnea)")})
        elif spo2_mature and spo2_delta <= -2.0:
            flags.append({"signal": "spo2", "severity": "yellow",
                          "value": spo2_today, "baseline": spo2_base,
                          "delta_pp": spo2_delta,
                          "rule": (f"SpO2 {spo2_today}% ({spo2_delta:+.1f}pp vs baseline "
                                   f"{spo2_base}%) (yellow flag — possible respiratory stress, "
                                   "poor sleep environment, or early illness; pair with "
                                   "respiration check)")})

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

    # Recovery slope (3-day): early-warning trend that often precedes a single-day
    # Recovery dip. Lifted from readiness_check into wellness_summary so the
    # Mid-Week Check-In and Weekly Review workflows get the same signal as
    # --readiness-check without re-implementing the math.
    recovery_slope_3day = None
    latest_recovery = latest.get("readiness")
    if latest_recovery is not None and len(daily) >= 4:
        d3_ago = daily[-4].get("readiness")
        if d3_ago is not None:
            delta = round(latest_recovery - d3_ago, 1)
            recovery_slope_3day = {
                "today": latest_recovery,
                "three_days_ago": d3_ago,
                "delta": delta,
                "alarm": delta <= -10,
            }
            if delta <= -10:
                flags.append({
                    "signal": "recovery_slope", "severity": "yellow",
                    "value": delta,
                    "rule": "Recovery dropped >=10pt over 3 days (early-warning trend)",
                })

    # Subjective-stale heuristic: when 3+ subjective fields are populated and ALL
    # equal 1 ("best" on intervals.icu default scale), the athlete is probably
    # not updating these manually. Surface so coaching templates can downweight.
    subj_keys = ["fatigue", "soreness", "stress", "mood"]
    subj_filled = [latest.get(k) for k in subj_keys if latest.get(k) is not None]
    subjective_stale_warning = len(subj_filled) >= 3 and all(v == 1 for v in subj_filled)

    # Training load context (CTL/ATL/TSB) sourced from the latest raw wellness
    # record. intervals.icu computes these server-side. Pulling here avoids a
    # second API call in readiness_check and lets Mid-Week Check-In correlate
    # readiness with current load without extra plumbing.
    raw_latest = wellness[-1] if wellness else {}
    ctl_raw = raw_latest.get("ctl")
    atl_raw = raw_latest.get("atl")
    training_load = {
        "ctl": round(ctl_raw, 1) if ctl_raw is not None else None,
        "atl": round(atl_raw, 1) if atl_raw is not None else None,
        "tsb": (round(ctl_raw - atl_raw, 1)
                if ctl_raw is not None and atl_raw is not None else None),
    }

    # Progression signal (separate from gating flags — this is "go harder",
    # not "back off"). Fires when HRV is above the 7-day band (μ+0.5σ) for
    # the last 3 days AND CTL is rising over the last 7 days. Indicates the
    # athlete has adapted to current load and can absorb a 5-10% TSS bump.
    # Mostly dormant during maintenance phases; matters during build blocks.
    progression_signal = None
    if (mu7 is not None and sd7 is not None
            and baseline_sample_sizes["hrv"] >= MIN_BASELINE_SIZE):
        upper_band = round(mu7 + 0.5 * sd7, 1)
        last3_hrv = [d.get("hrv") for d in daily[-3:]]
        if all(v is not None and v > upper_band for v in last3_hrv) and len(daily) >= 3:
            # CTL rising check: today's CTL vs 7-days-ago. wellness[-8] = 7 days
            # before wellness[-1] (today). Falls back to "unknown" if <8 records.
            ctl_today = ctl_raw
            ctl_7d_ago = wellness[-8].get("ctl") if len(wellness) >= 8 else None
            ctl_rising = (ctl_today is not None and ctl_7d_ago is not None
                          and ctl_today > ctl_7d_ago)
            if ctl_rising:
                progression_signal = {
                    "rule": ("HRV above band (μ+0.5σ = {:.1f}ms) for 3 days AND CTL rising "
                             "({:.1f} → {:.1f}) — green-light a 5-10% TSS bump on next "
                             "quality session").format(upper_band, ctl_7d_ago, ctl_today),
                    "hrv_last3": last3_hrv,
                    "band_upper": upper_band,
                    "ctl_7d_ago": round(ctl_7d_ago, 1),
                    "ctl_today": round(ctl_today, 1),
                }

    # Days-with-Whoop-data: records where at least one Whoop-exclusive metric
    # is populated. Distinguishes "30 dates returned" from "N dates with actual
    # wearable data" — coaching templates use this to gauge whether baseline
    # numbers are trustworthy. Excludes `sleep_hours` because intervals.icu's
    # UI lets athletes manually enter sleep (a record with only sleepSecs
    # populated is a manual entry, not a Whoop sync). `sleep_score` IS
    # Whoop-exclusive (no manual UI for it). Same for RHR/HRV/readiness/
    # respiration/spO2 — those require a wearable push.
    WHOOP_EXCLUSIVE_FIELDS = ("resting_hr", "hrv", "sleep_score",
                              "readiness", "respiration", "spo2")
    days_with_whoop_data = sum(
        1 for d in daily if any(d.get(f) is not None for f in WHOOP_EXCLUSIVE_FIELDS)
    )

    # Compute overall_status once all flags (including the recovery-slope flag
    # appended above) have been collected. Evaluated here so every flag path
    # is visible before the severity reduction.
    overall = "red" if any(f["severity"] == "red" for f in flags) \
        else "yellow" if any(f["severity"] == "yellow" for f in flags) \
        else "green"

    # Tiered baseline note — replaces the binary partial_baseline message.
    # Drives template-side warnings about how much to trust deviation flags.
    if baseline_maturity == "insufficient":
        baseline_note = (
            "No historical baseline — only the latest day's wellness is available. "
            "RHR / HRV / respiration deviation flags are suppressed; latest-day "
            "flags (sleep <6h, subjective ≥4, Recovery <67) still apply. Log a few "
            "more days to enable full readiness coaching."
        )
    elif baseline_maturity == "preliminary":
        smallest = min(nonzero_sizes)
        baseline_note = (
            f"Baseline is preliminary (smallest metric n={smallest}; need ≥{MIN_BASELINE_SIZE} "
            "for statistical confidence, ≥14 for stable). RHR / HRV / respiration "
            "deviation flags are suppressed below n=7. Recovery + sleep + subjective "
            "flags still apply."
        )
    elif baseline_maturity == "consolidating":
        smallest = min(nonzero_sizes)
        baseline_note = (
            f"Baseline consolidating (n={smallest}, target 14 for stable). "
            "Deviation flags active but treat single-day deltas with caution."
        )
    else:  # stable
        baseline_note = None

    return {
        "days": days,
        "days_with_data": len(daily),
        "days_with_whoop_data": days_with_whoop_data,
        "history_days": len(history),
        "partial_baseline": partial_baseline,
        "baseline_maturity": baseline_maturity,
        "baseline_sample_sizes": baseline_sample_sizes,
        "baseline": baseline,
        "latest": latest,
        "latest_date_age_days": latest_date_age_days,
        "flags": flags,
        "overall_status": overall,
        "daily": daily,
        "baseline_note": baseline_note,
        "recovery_slope_3day": recovery_slope_3day,
        "subjective_stale_warning": subjective_stale_warning,
        "training_load": training_load,
        "progression_signal": progression_signal,
    }
