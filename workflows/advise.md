# Workflow: Training Advice, Mid-Week Check-In & Race Peaking

Covers **Training Advice**, **Mid-Week Check-In**, and **Race/Event Peaking**. The SKILL.md → Workflow Dispatch table is the authoritative router.

**Validation gates in this workflow** (Coaching Process Rule 1 — Validate Before Prescribing):

| Sub-workflow | Gate | What gets confirmed |
|--------------|------|---------------------|
| Training Advice | **Step 2 Validation Gate** | Present athlete assessment (FTP, block phase, recent load, fatigue signals); confirm zone confidence (Rule 2); wait for athlete confirmation before prescribing. |
| Mid-Week Check-In | (read-only) | Reports plan status + readiness verdict + ceiling. No plan edits — Rule 1 is satisfied by the assessment-then-ceiling presentation. If the athlete asks to *swap* a session, the gate engages: re-confirm before the session table is edited. |
| Race / Event Peaking | **Step 5 → Step 6 Validation Gate** | Taper schedule is presented in Step 5; athlete confirms before Step 6 generates `.zwo` files and updates `plans/active_plan.md`. |

---

## Training Advice

**Step 1:** Assess context before responding:
- Current FTP, weight, training age (check `plans/active_plan.md` → Athlete Profile; if no active plan, ask the athlete or check intervals.icu profile via `--use-athlete-profile`)
- Current block and phase (check `plans/active_plan.md` → Plan Overview + Current Week Schedule)
- Recent session load: count hard sessions in last 7 days, check for back-to-back intensity
- Fatigue signals: RPE trends, HR:Power drift, missed targets in recent sessions
- Schedule constraints: available days/hours this week

**Step 2:** Present your athlete situation assessment and confirm before prescribing (Coaching Process Rule 1). Verify zone confidence — if zones are unvalidated, flag uncertainty before using power targets (Rule 2).

**Step 3:** Reference zones from `references/training_zones.md` and block templates / progressions from `references/block_templates.md`.

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
1. Run `python scripts/intervals_icu_api.py --readiness-check` — its verdict + ceiling is the primary gate (pulls RHR, sleep, HRV band, Recovery, respiration, SpO2 in one call). If wellness data is unavailable (script `error` field), fall back to asking: RHR vs baseline, sleep last 2 nights
2. Ask about what the data can't see: life stress, motivation, soreness
3. Prescribe based on fatigue level using the Recovery Prescription table below
4. **Rule of thumb**: Modified workout > forced workout > skipped workout

**Recovery Prescription table (fatigue → action):**

> HRV framing uses **Plews/Buchheit 7-day rolling band** (μ ± 0.5σ) — the operational rule shipped in `--readiness-check`. Single-day below band = yellow; 2 consecutive days below band = red (de-load trigger). The legacy "% drop" framing is deprecated.

> **Signal-mode scope:** the Recovery-score band cells (Recovery ≥67, 34–66, <34) apply in **`full` signal mode only** — when WHOOP Recovery is present. In `reduced` or `minimal` mode there is no Recovery score; use the RHR, sleep, and HRV signals in each row instead. Full mode→bands contract: `references/cli_reference.md` → Readiness Check → Signal-mode contract.

| Fatigue signal | Action | Session adjustment |
|---|---|---|
| Mild (RPE +1 vs typical, sleep ok, Recovery ≥67, HRV in/above 7-day band) | Train as planned, monitor first 15 min | None — abort if RPE doesn't settle |
| Moderate-high (Recovery 50–66 with no other flags — engine YELLOW-HIGH) | Proceed with caution | Threshold/SS as planned; VO2max marginal — proceed only if motivated, abort if HR/RPE elevated |
| Moderate-low (RHR +5 bpm OR poor sleep 1 night OR HRV below 7-day band (single day) OR Recovery 34–49 OR respiration +1/min vs baseline — engine YELLOW-LOW) | Modify down; ceiling = Sweet Spot 88–94% FTP | SS → proceed; threshold → SS; VO2max → SS or Z2; cut duration 20% |
| High (RHR ≥+10 bpm OR poor sleep 2+ nights, OR HRV below 7-day band 2 consecutive days, OR Recovery <34, OR respiration +2/min vs baseline, OR SpO2 <90%, OR TSB <−30, OR motivation absent) | Replace with active recovery | 30–45 min Z1, no intervals |
| Severe ((RHR +10 bpm AND illness symptoms) OR (Recovery <34 with red signals across HRV/RHR/respiration)) | Full rest | No bike. Reassess next day. |
| Sick (above-neck only) | Z1–Z2 only, ~50% volume, 3–5 days; resume structure when symptoms resolve | Per `references/weekly_adaptation.md` → Illness/Injury rules (Severity 1) |
| Sick (below-neck or systemic) | Full rest until 48h symptom-free | Per `references/weekly_adaptation.md` → Illness/Injury rules |

> **TSB persistence rules live in `references/weekly_adaptation.md`** (TSB <−30 → insert recovery day; <−40 → replace hard sessions with Z1–Z2 until TSB >−25). The High-row `TSB <−30` cell is the same rule's same-day rendering — an active-recovery spin, not forced full rest.

> **HRV CV-trend is informational, not a same-day downgrade.** A rising 7-day CV (≥ prior-7d + 2.0pp over the 14-day split-window) is an early autonomic-strain signal — it prompts a **weekly-TSS review**, not a session cut. `--readiness-check` surfaces it as an Active flag but does **not** gate the verdict on it (consistent with the Gating? table below + `references/training_zones.md` → Fatigue Indicators). Cut today's session only if an acute signal in the table above also fires.

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
Returns a single GREEN / YELLOW-HIGH / YELLOW-LOW / RED verdict + session-type ceiling, plus all underlying signals (band scale varies by mode — see `references/cli_reference.md` → Readiness Check → Signal-mode contract):

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

**If the script/API fails** (timeout / 5xx / auth): the client retries 3× with backoff; on persistent failure, proceed on `plans/active_plan.md` alone and suggest retrying later (see `workflows/analyze.md` → Error Handling) rather than blocking the check-in.

**Subjective override (within YELLOW-HIGH only):** the verdict above is driven by Recovery/HRV/sleep/SpO2; the intervals.icu subjective fields (fatigue/soreness/stress/mood, 1=best…4=worst) are otherwise only a data-quality check. When the verdict lands **YELLOW-HIGH** and the athlete logs subjective fields, apply this tiebreaker: if **soreness ≥3 OR fatigue ≥3 OR mood ≥3**, step the session ceiling down to **YELLOW-LOW** (Sweet Spot, not Threshold/VO2max). The athlete logs all six fields daily — genuine signal, not noise — so let it subdivide the borderline band. Does not apply to GREEN (subjective alone doesn't veto a clear day) or to YELLOW-LOW/RED (already conservative).

**Wearable dependency — signal-mode contract.** The full mode→bands table lives in `references/cli_reference.md` → Readiness Check → Signal-mode contract. Key fact for this workflow: **the subjective override above applies in `full` mode only** — `reduced`/`minimal` have no YELLOW-HIGH band to subdivide.

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

Render the per-metric body (Recovery / Sleep / HRV / RHR / Respiration / SpO2 / TSB / Subjective / Active flags / Progression signal) using `references/readiness_template.md` — map `--readiness-check` field paths (`recovery.score`, `hrv.today`, `resting_hr.today`, `respiration.today`, `spo2.today`, `tsb.tsb`, etc.) to the canonical line skeletons. The shared interpretation footnotes (Recovery lag, Reading priority, Baseline-maturity caveat, Data freshness) also live there.

**Mid-Week-specific addendum:** if verdict is YELLOW-LOW or RED, apply the verdict's ceiling to the planned session before showing it. The Recovery Prescription table (Training Advice section above) maps sessions *under* that ceiling — the ceiling always wins: keep downgrading until the session fits (YELLOW-LOW caps at Sweet Spot 88–94% FTP, RED at Z1–Z2).

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

**Step 2:** Read `references/race_taper.md` (taper protocols + TSB projection).

**Step 3:** If `plans/active_plan.md` exists, read current PMC snapshot (CTL, ATL, TSB).
Otherwise, bootstrap PMC:
```bash
python scripts/pmc_calculator.py --bootstrap --days 90
```

**Step 4:** Calculate taper timing:
- Determine current TSB and target TSB (+5 to +15, per `references/race_taper.md`)
- Select protocol per `references/race_taper.md`: 2-week (A-priority) or 1-week mini-taper (B-priority); priority wins over CTL on conflicts; event <7 days → final-week structure only
- Project TSB forward to confirm the taper duration achieves target freshness

**Step 5:** Present taper plan:
```
## Race Peaking: {Event Name} — {Date}
**Current**: CTL {X} | ATL {X} | TSB {X}
**Target race-day TSB**: +5 to +15
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
