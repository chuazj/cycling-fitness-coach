"""Pre-ride readiness verdict and its human-readable rendering."""
from datetime import datetime

from .wellness import wellness_summary


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
