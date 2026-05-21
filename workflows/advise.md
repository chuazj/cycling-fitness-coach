# Workflow: Training Advice, Mid-Week Check-In & Race Peaking

Covers **Training Advice**, **Mid-Week Check-In**, and **Race/Event Peaking**. The SKILL.md → Workflow Dispatch table is the authoritative router.

---

## Training Advice

**Step 1:** Assess context before responding:
- Current FTP, weight, training age (check `plans/active_plan.md` → Athlete Profile; if no active plan, ask the athlete or check intervals.icu profile via `--use-athlete-profile`)
- Current block and phase (check `plans/active_plan.md` → Plan Overview + Current Week Schedule)
- Recent session load: count hard sessions in last 7 days, check for back-to-back intensity
- Fatigue signals: RPE trends, HR:Power drift, missed targets in recent sessions
- Schedule constraints: available days/hours this week

**Step 2:** Present your athlete situation assessment and confirm before prescribing (Coaching Process Rule 1). Verify zone confidence — if zones are unvalidated, flag uncertainty before using power targets (Rule 2).

**Step 3:** Reference zones and training blocks from `references/training_zones.md` and `references/periodization.md`.

**Step 4:** Prescribe with power targets as % FTP AND watts. Explain the "why" (Rule 3).

**Step 5:** Include fatigue watch-list for the prescription.

### Common Advice Scenarios

**"Should I lower my FTP?"** — Decision tree:
1. Check recent execution data: Are targets being hit within ±3%?
2. If yes → FTP is correct. Elevated RPE may be fatigue, heat, sleep, not FTP.
3. If no (missing by >5% on 2+ consecutive clean sessions) → consider lowering 3-5%
4. If disrupted sessions (bathroom break, ERG issues, schedule problems) → external cause, not FTP issue. Keep current.
5. **Never lower based on a single bad session.** Look for patterns across 2+ sessions.

**"I'm tired, should I train today?"** — Fatigue assessment:
1. Check resting HR — if +5 bpm above baseline → modify or rest
2. Ask about sleep quality (last 2 nights) and life stress
3. Prescribe based on fatigue level using the Recovery Prescription table below
4. **Rule of thumb**: Modified workout > forced workout > skipped workout

**Recovery Prescription table (fatigue → action):**

> HRV framing uses **Plews/Buchheit 7-day rolling band** (μ ± 0.5σ) — the operational rule shipped in `--readiness-check`. Single-day below band = yellow; 2 consecutive days below band = red (de-load trigger). The legacy "% drop" framing is deprecated.

| Fatigue signal | Action | Session adjustment |
|---|---|---|
| Mild (RPE +1 vs typical, sleep ok, Recovery ≥67, HRV in/above 7-day band) | Train as planned, monitor first 15 min | None — abort if RPE doesn't settle |
| Moderate (RHR +5 bpm OR poor sleep 1 night OR HRV below 7-day band (single day) OR Recovery 34–66 OR HRV CV-trend rising +2pp over 14d OR respiration +1/min vs baseline) | Modify down one tier | SS → endurance Z2; threshold → SS; VO2max → threshold; cut duration 20% |
| High (RHR ≥+10 bpm OR poor sleep 2+ nights, OR HRV below 7-day band 2 consecutive days, OR Recovery <34, OR respiration +2/min vs baseline, OR SpO2 <90%, OR motivation absent) | Replace with active recovery | 30–45 min Z1, no intervals |
| Severe (RHR +10 bpm AND illness symptoms OR TSB <−30 OR Recovery <34 with red signals across HRV/RHR/respiration) | Full rest | No bike. Reassess next day. |
| Sick (above-neck only) | Rest 1–2 days then Z1–Z2 only | Per `references/periodization.md` → Illness/Injury rules |
| Sick (below-neck or systemic) | Full rest until 48h symptom-free | Per `references/periodization.md` → Illness/Injury rules |

**"Can I swap/skip a session?"** — Schedule adaptation:
1. Identify what the session targets (energy system, training stimulus)
2. Check if the stimulus is covered elsewhere this week
3. If swapping: keep hard/easy balance, avoid back-to-back hard days
4. If skipping: assess weekly TSS impact — one skipped session rarely matters; two+ may need week restructuring

**Output template:**

```
## Training Recommendation
**Context**: [Current FTP, available time, recent load/TSB]
**Assessment**: [Athlete's current state — fatigue, fitness, readiness]
**This Week's Plan**:
| Day | Session | Duration | Key Interval | Fuel |
|-----|---------|----------|--------------|------|
| ... | ...     | ...      | ...          | {one-line cue from fueling.md → Quick-Reference} |
**Key Focus**: [Target adaptation and why this matters now]
**Watch For**: [Fatigue signals that would trigger plan adjustment]
**Fueling**: see `references/fueling.md` → Quick-Reference for per-session cues; full detail in the rest of that doc. For any Threshold or VO2max session, keep the pre-ride meal low-fiber within ~2h — fiber raises gut-distress risk at high intensity (`references/fueling.md` → Pre-Ride Nutrition → Key Rules).
```

---

## Mid-Week Check-In

When user asks about plan status ("check my plan", "what's next", "plan status"):

**Step 1:** Read `plans/active_plan.md`. If the file does not exist, inform user that no active plan is found and suggest creating one via the Create Plan workflow.

**Step 2 (optional but recommended):** Pull readiness verdict:
```bash
python scripts/intervals_icu_api.py --readiness-check -o readiness.json
```
Returns a single GREEN / YELLOW-HIGH / YELLOW-LOW / RED verdict + session-type ceiling, plus all underlying signals:

| Signal | Rule | Gating? |
|---|---|---|
| Sleep | <6h red; 6-7h tiebroken by WHOOP sleep score (≥85 upgrade, <70 downgrade); ≥7h pass | Gating |
| Recovery | Green ≥67 / Yellow-high 50-66 / Yellow-low 34-49 / Red <34 (ZJ's 4-band coaching split of WHOOP's 3-zone) | Gating |
| HRV (rMSSD) | Plews/Buchheit 7-day band μ ± 0.5σ. Today below band = yellow; 2 consecutive days below = red (de-load trigger) | Gating |
| **HRV CV-trend** | Last-7d CV ≥ prior-7d CV + 2.0pp (14-day split-window) = yellow informational flag. Early autonomic-strain signal | Informational (review weekly TSS) |
| RHR | +5 bpm vs 14d baseline = yellow; +10 = red | Gating |
| Respiration | +1.0/min vs 14d baseline = yellow (early illness); +2.0/min = red (active illness) | Gating |
| SpO2 | ≥2pp below 14-day baseline = yellow (needs ≥7d history); <90% = red absolute floor. **Apple Watch cross-check**: 3 spot readings ≥96% clears as wrist-PPG artifact (see [[#SpO2 cross-check]] below) | Gating (after cross-check) |
| 3-day Recovery slope | ≥10pt drop over 3 days = yellow trend flag (even if today's Recovery is green) | Early-warning |
| Progression signal | HRV ≥3 days above μ+0.5σ band AND CTL rising → green-light +5-10% TSS on next quality session | Positive (mostly dormant in maintenance) |
| TSB | CTL/ATL/TSB rendered as fresh/neutral/productive/overreached | Context only (not gating) |
| Subjective | All fatigue/soreness/stress/mood = 1 → stale-warning (athlete may not be updating manually) | Data-quality flag |

Deviation flags (RHR/HRV/respiration/SpO2) are auto-suppressed when per-metric sample size <7 to avoid noise — the SpO2 <90% red floor is the one exception (absolute, fires regardless). CV-trend needs ≥14 days of HRV; below that it's silent. Skip the whole block if athlete doesn't log wellness (script returns `error` field — note in output and proceed without).

**Subjective override (within YELLOW-HIGH only):** the verdict above is driven by Recovery/HRV/sleep/SpO2; the intervals.icu subjective fields (fatigue/soreness/stress/mood, 1=best…4=worst) are otherwise only a data-quality check. When the verdict lands **YELLOW-HIGH** and the athlete logs subjective fields, apply this tiebreaker: if **soreness ≥3 OR fatigue ≥3 OR mood ≥3**, step the session ceiling down to **YELLOW-LOW** (Sweet Spot, not Threshold/VO2max). The athlete logs all six fields daily — genuine signal, not noise — so let it subdivide the borderline band. Does not apply to GREEN (subjective alone doesn't veto a clear day) or to YELLOW-LOW/RED (already conservative).

**Wearable dependency (reuse note):** Recovery, respiration, SpO2 and sleepScore are WHOOP-exclusive fields — a non-WHOOP athlete loses those four signals and the readiness check degrades to HRV + RHR + sleep-hours only. The verdict still works but at lower resolution; recalibrate the Recovery bands if a different wearable's `readiness` field is present (see `references/training_zones.md` → Recovery score notes).

**Step 3:** Present current status:
```
## Plan Status: {Plan Type} — Week {N} ({Phase})

### This Week
| Day | Session | Target TSS | Status |
|-----|---------|------------|--------|
| ... | ...     | ...        | ...    |

### Next Session
**{Day}: {Session Name}**
- Key interval: {description}
- Duration: {X}min | Target TSS: {X}
- Execution notes: {pacing tips, cadence targets}
- ZWO file: {filename}
- **Fuel:** {one-line cue from `references/fueling.md` → Quick-Reference, matched to this session's duration × intensity}

### Readiness (from --readiness-check)
**Verdict:** {verdict_band} — {verdict text}
**Ceiling:** {ceiling}
{If `data_age_days` > 0, lead the section with: **⚠ Latest wellness record is {N} day(s) old — readings below are not today's.** Treat as historical, not current state.}
{If `baseline_maturity` is "preliminary" or "insufficient", surface the `baseline_note` so the athlete understands deviation flags may be suppressed.}

**Recovery lag interpretation:** Whoop Recovery is computed from last night's sleep, which primarily processed *yesterday's* training. A yellow Recovery today usually reflects yesterday's hard session — read it alongside yesterday's training, not today's plan. See `references/training_zones.md` → Recovery Score (Whoop / Wearable) for the full caveat.

- Recovery: {recovery.score} → {recovery.band} {if `recovery.slope_3day.alarm`: ⚠ slope {three_days_ago}→{today} ({delta:+}pt over 3 days)}
- Sleep: {sleep.hours}h, score {sleep.score}/100 → {sleep.status}{if `sleep.note`: ({sleep.note})}
- HRV: {hrv.today}ms vs {hrv.sample_size}d baseline {hrv.baseline}ms ({delta:+}ms){if `hrv.band_mean_7d` and `hrv.band_sd_7d`: | 7d band μ{band_mean_7d}±{band_sd_7d*0.5} (Plews/Buchheit)}{if `hrv.cv_pct`: | CV {cv_pct}%} — *deviation flags inactive if sample_size <7; CV-trend needs ≥14d*
  {If `hrv.cv_trend.rising` is true:} └─ ⚠ CV trend: {cv_trend.prior_cv_pct}% → {cv_trend.recent_cv_pct}% ({delta_pp:+}pp over 14d) — widening variability, early autonomic-strain signal
- RHR: {resting_hr.today}bpm vs {resting_hr.sample_size}d baseline {resting_hr.baseline}bpm ({delta:+}bpm) — *same baseline-maturity guard*
{If `respiration.today` is non-null:}
- Respiration: {respiration.today:.1f}/min vs {respiration.sample_size}d baseline {respiration.baseline:.1f}/min ({delta:+}/min) — *yellow at +1.0, red at +2.0 (illness early-warning)*
{If `spo2.today` is non-null:}
- SpO2: {spo2.today}% {OK/WARN/FAIL tag — WARN if ≥2pp below baseline, FAIL if <90%} — *if WARN/FAIL, apply Apple Watch cross-check (see below) before holding the flag*
- TSB context: {tsb.tsb:+} (CTL {tsb.ctl} / ATL {tsb.atl}) — {fresh/neutral/productive/overreached}
{If at least one of fatigue/soreness/stress/mood is non-null, render:}
- Subjective: {join only non-null fields, e.g. "fatigue=2, mood=3"}{if `subjective.stale_warning`: ⚠ all filled=1, athlete may not be updating manually}
{Otherwise omit the Subjective row entirely.}

**Active flags:** {list flags by severity, or "None — all clear"}

{If `progression_signal` is non-null:}
**Progression signal (positive):** {progression_signal.rule} — green-lights +5-10% TSS on the next quality session if athlete is in build phase. Skip during maintenance unless deliberately ramping back up.

Recovery score (when present) is the single best summary signal — Whoop has baseline-calibrated HRV+RHR+sleep+respiration into it. Use the individual lines below it as drill-down explanations of *why* Recovery is what it is. If Recovery is absent (athlete not on a wearable that pushes it), fall back to HRV+RHR+sleep — but with sample-size confidence in mind.

If verdict is YELLOW-LOW or RED, apply the verdict's ceiling to the planned session (downgrade hard sessions per Recovery Prescription table — Training Advice section above) before showing the session.

### SpO2 cross-check (Apple Watch tiebreaker)

WHOOP wrist-PPG SpO2 runs noisier than fingertip pulse-ox — treat a flagged reading as flag-not-diagnosis. When the readiness check fires a SpO2 yellow/red flag, ask the athlete for 3 Apple Watch spot readings (different optical path, ~5 min apart, still arm), then apply:

| Apple Watch (3 readings) | Action |
|---|---|
| All ≥96% | **Clear** the SpO2 flag as wrist-PPG artifact. Recompute verdict in-conversation by stepping down one band (don't re-run the script). |
| Mixed 94-96% | **Hold** the flag at yellow — no clean tiebreak. |
| Any ≤94% | **Confirm** the WHOOP signal — pair with respiration check for illness assessment. |

This tiebreaker applies to **SpO2 only**. Do NOT use Apple Watch for HRV, RHR, or sleep cross-checks — different reliability profiles.

### PMC Snapshot
CTL: {X} | ATL: {X} | TSB: {X}
Status: {interpretation}
```

If readiness data is unavailable (script returns `error`), skip the Readiness block and note: "Wellness data not logged in intervals.icu — readiness coaching limited to PMC + RPE trends."

---

## Race/Event Peaking

When user mentions a target event ("I have a race on DATE", "peak for event", "taper for race"):

**Step 1:** Confirm event date and priority (A = primary event, B = secondary/fun).

**Step 2:** Read `references/periodization.md` → Race/Event Peaking Protocol.

**Step 3:** If `plans/active_plan.md` exists, read current PMC snapshot (CTL, ATL, TSB).
Otherwise, bootstrap PMC:
```bash
python scripts/pmc_calculator.py --bootstrap --days 90
```

**Step 4:** Calculate taper timing:
- Determine current TSB and target TSB (+5 to +20)
- Select protocol: 2-week taper (A-priority, CTL >50) or 1-week mini-taper (B-priority, CTL <50)
- Project TSB forward to confirm the taper duration achieves target freshness

**Step 5:** Present taper plan:
```
## Race Peaking: {Event Name} — {Date}
**Current**: CTL {X} | ATL {X} | TSB {X}
**Target race-day TSB**: +5 to +20
**Protocol**: {2-week / 1-week} taper starting {date}

### Taper Schedule
| Week | Day | Session | TSS | Fuel |
|------|-----|---------|-----|------|
| ... | ... | ... | ... | {one-line cue from fueling.md → Quick-Reference} |

**Race-day fueling**: rehearse during taper sessions — never try a new product/timing on race day. See `references/fueling.md` → Pre-Ride Nutrition for race-morning timing.
**Projected race-day TSB**: ~{X}
```

**Step 6:** Generate taper week .zwo files and update plan if active.

---

## Menstrual Cycle & Hormonal Contraceptives

For a female athlete, the menstrual cycle — or hormonal-contraceptive status — is a routine input to autoregulation, **not** a plan-restructuring factor. Full protocol: `references/menstrual_cycle_training.md`.

In advice and check-ins:
- **Autoregulate by symptom, not phase.** Treat menstrual symptoms (pain/cramps, fatigue, heavy bleeding, PMS) as a wellness input alongside sleep / HRV / recovery, and adjust by symptom severity (`menstrual_cycle_training.md` §4). Phase-based periodization is not evidence-supported — do not change a plan for cycle phase alone.
- **Read luteal-phase wellness with context.** The luteal phase modestly raises resting HR and core temperature and can lower HRV — do not over-read a luteal-phase dip as fatigue (§3).
- **Red flag — hard gate.** Amenorrhea (no period 3+ months) or oligomenorrhea — or, for a hormonal-contraceptive user, low-energy-availability signs (unexplained performance decline, recurrent illness/injury, stress fractures) — is a possible Relative Energy Deficiency in Sport (RED-S) signal. Refer her to a doctor, hold load at maintenance, never "push through" (`menstrual_cycle_training.md` §7).

**Symptom-severity autoregulation tiers** (`menstrual_cycle_training.md` §4) — adjust the session by symptom severity, not by cycle phase:

| Symptom severity | Action |
|---|---|
| None / mild | Train as planned |
| Moderate — cramps or fatigue affecting focus | Drop intensity one tier (Threshold → Sweet Spot, SS → Z2); trim duration if needed |
| Severe — heavy bleeding or significant pain | Swap to easy Z1-Z2, or rest |
