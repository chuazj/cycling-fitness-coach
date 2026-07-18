# Weekly Adaptation Decision Trees

Reference for Claude-as-coach: IF/THEN rules applied after each weekly review to decide load, intensity, and progression adjustments for the next week.

**Scope:** weekly multi-session trends — TSS load, ACWR, TSB, RPE patterns, peak-power deltas, illness/injury gates.

- For **per-activity forward cascades** (single-session signals → next 1–2 sessions) → `references/adaptation_rules.md`.
- For **block templates, progressions, and block selection** → `references/block_templates.md`.

> **Citation currency** — adaptation-rule citations last verified **2026-05-26**. Re-verify against current literature at every skill audit; ACWR methodology is contested (Lolli 2019, Impellizzeri 2020) — treat thresholds as directional, not as hard rules. Anchor authorities: `governance/bibliography.md#coggan-andrew` (PMC framework); auxiliary critiques at `governance/bibliography.md#auxiliary-citations`.

## Sub-prompt contract

- **Inputs:** weekly summary JSON from `intervals_icu_api.py --weekly-summary` (CTL/ATL/TSB, ACWR, completion rate, peak-power deltas) + wellness/readiness signal from `--wellness 14` (rendered via `references/readiness_template.md`) + RPE trend from `rpe_trend.py` (when frontmatter-scan available) + illness/injury flags surfaced by the athlete.
- **Outputs:** adaptation decisions for **next week** — load delta, intensity adjustment, progression cap, abort criteria, illness/injury gates. Decisions are *proposed* in the Weekly Review output; the athlete confirms before `plans/active_plan.md` is edited (per SKILL.md Coaching Process Rule 1 / Validation Gate).
- **Invocation:** `workflows/plan.md` → Weekly Review step. Multi-signal — multiple decision trees can fire simultaneously; rule-priority section below resolves conflicts.

---

## Adaptation Decision Trees

Claude follows these IF/THEN rules after each weekly review. Multiple rules may trigger simultaneously — apply all that match.

### Training Load Adaptation

**IF** actual weekly TSS < 80% of planned for 2+ sessions:
- **THEN** reduce next week's target TSS by 5-10%
- **WHY** athlete may be struggling with prescribed load; avoid accumulating fatigue from incomplete sessions
- **ACTION** adjust interval duration down one progression level

**IF** actual weekly TSS > 110% of planned consistently (2+ weeks):
- **THEN** flag for FTP retest — athlete may be training below actual ability
- **ACTION** suggest scheduling FTP test within next 1-2 weeks

**IF** completion rate < 60% for a week (fewer than 3 of 4 sessions completed):
- **THEN** reassess plan difficulty; consider dropping one intensity day
- **ACTION** reduce next week to 3 sessions; add the 4th only if athlete confirms availability

**IF** 2 sessions skipped in a week (3+ skipped → next rule, which forbids compression):
- **THEN** compress remaining week — do NOT try to "catch up" missed sessions
- **ACTION** prioritize the most important remaining session; drop or shorten others
- **EXAMPLES**:
  - 1 session skipped: mark as `skipped`, no compensation. Continue next scheduled session as planned.
  - 2 sessions skipped: keep the highest-priority remaining session at full TSS, reduce others by 20%. Never double up sessions on a single day.
  - 3+ sessions skipped: treat the week as partial recovery; do not attempt to compress all missed work into remaining days.

**IF** 3+ sessions skipped in a single week:
- **THEN** treat as involuntary rest week — do NOT attempt catch-up
- **ACWR CHECK** after the missed week: if ACWR < 0.8, ease back at 50% volume for 3 days before resuming structured training
- **ACTION** shift remaining block schedule forward by 1 week; do not compress
- **WHY** cramming missed work risks injury and immune suppression, especially if the reason for missing was illness or life stress

### Workload Ratio (ACWR)

ACWR (Acute:Chronic Workload Ratio) = ATL ÷ CTL. Measures training load spikes relative to fitness. Reference: Gabbett (2016).

> **Caveat**: ACWR thresholds (0.8-1.3 safe zone) originate from team sport injury research (rugby, cricket, football) and have been challenged for mathematical coupling artifacts (Lolli et al., 2019) and weak evidence for the U-shaped risk curve in endurance sports (Impellizzeri et al., 2020). Treat these as directional guidelines, not hard rules. Always interpret ACWR alongside TSB, RPE trends, and HR indicators — not as a sole decision-maker.

**IF** ACWR > 1.5:
- **THEN** dangerous training load spike — mandatory recovery before next hard session
- **WHY** rapid load increase relative to fitness is the strongest predictor of injury/overtraining
- **ACTION** insert 2-3 days of Z1-Z2 only; reduce next week's planned TSS by 20%

**IF** ACWR > 1.3 (but ≤ 1.5):
- **THEN** elevated injury/overtraining risk — caution
- **ACTION** reduce next week's target TSS by 10%; avoid adding sessions or volume

**IF** ACWR < 0.8:
- **THEN** underprepared — training stimulus insufficient relative to recent fitness
- **ACTION** increase next week's TSS by max 10%; do not spike by more than 10%/week

**IF** ACWR 0.8-1.3:
- **THEN** safe zone — no intervention needed from ACWR perspective

### Fatigue Management

**IF** TSB < -30:
- **THEN** recommend extra recovery day or reduced session intensity
- **WHY** high negative TSB indicates accumulated fatigue; injury/burnout risk
- **ACTION** insert easy day before next hard session; consider moving next rest week earlier

**IF** TSB < -40:
- **THEN** enforce recovery — replace next hard session with Z1-Z2 endurance
- **ACTION** no intensity work until TSB > -25

**IF** TSB > +15 (not in a taper):
- **THEN** athlete is detraining; increase training stimulus
- **ACTION** bump next week's TSS by 10% or add one session

### Performance Indicators

**IF** 20-minute peak power increases >3% week-over-week:
- **THEN** flag FTP update — current FTP may underestimate actual threshold
- **ACTION** **suggest a mid-block FTP retest** — do NOT derive a new FTP from the training peak. A 20-min *training* peak is an unpaced effort, not a maximal test, so converting it via ×0.95 sets zones off a number the athlete never rode to threshold. Confirm the gain with a dedicated test before changing FTP — aligns with `adaptation_rules.md` → Upside actions ("Do NOT silently raise FTP"). When a test does happen, apply the implausible-jump guardrail in `block_templates.md` → Mid-Plan FTP Update before locking in a large change.

**IF** 5-minute peak power increases >5% week-over-week:
- **THEN** VO2max responding well — maintain or progress VO2max work
- **ACTION** continue current VO2max progression level

**IF** peak powers stagnant or declining for 3+ weeks:
- **THEN** plateau detected — consider changing stimulus
- **ACTION** suggest block change (e.g., switch from SS-focused to VO2max block)

**IF** intervals.icu eFTP runs >~5% above the set FTP for 2+ consecutive weeks:
- **THEN** the set FTP likely under-represents true threshold (the field test may have been mis-paced, or fitness has outrun the last test)
- **ACTION** flag an FTP retest, or propose adopting eFTP/CP as the working threshold per `references/block_templates.md` → Critical Power (CP) / eFTP. Do NOT silently raise FTP — confirm via the implausible-jump guardrail in `block_templates.md` → Mid-Plan FTP Update before any large change.

### Heart Rate Indicators

**IF** average HR elevated >5% at same power output vs. prior weeks:
- **THEN** flag fatigue concern — possible overreaching, illness, or environmental factor
- **ACTION** ask athlete about sleep, stress, hydration; recommend extra recovery if no clear cause

**IF** cardiac drift >8% in endurance sessions (see `workout_analysis.md` for 3-tier scale: <5% good, 5-8% acceptable, >8% flag):
- **THEN** aerobic fitness needs work or session fueling was inadequate
- **ACTION** add more Z2 volume; check nutrition/hydration habits

**IF** HR fails to reach expected levels during high-intensity work across 2+ consecutive hard sessions:
- **THEN** possible deep fatigue or overtraining
- **ACTION** recommend 3-5 days easy before resuming intensity
- **NOTE** a single-session shortfall is NOT this rule: with elevated RPE, drop one progression level next session (`references/block_templates.md` → VO2max fatigue note); with normal RPE and power on target, the intervals may simply be too short (`references/workout_analysis.md` → VO2max failure modes)

### Session Execution Quality

**IF** power fade >10% across intervals within a session:
- **THEN** pacing issue or insufficient recovery
- **ACTION** coach on even pacing strategy; check recovery between sessions

**IF** power consistently 5%+ above targets:
- **THEN** FTP may be set too low
- **ACTION** flag for retest; do NOT simply raise targets without testing

**IF** power consistently 5%+ below targets:
- **THEN** FTP may be set too high, or fatigue accumulation
- **ACTION** check recent TSB; if TSB > -20, consider FTP reduction

### Illness / Injury

**IF** athlete reports illness symptoms:
- **Severity 1 (above-neck only — e.g., head cold, mild congestion)**:
  - Reduce intensity to Z1-Z2 only, maintain 50% of planned volume for 3-5 days
  - Resume structured work only when symptoms fully resolve
- **Severity 2 (below-neck or systemic — e.g., chest congestion, fever, body aches, GI distress)**:
  - Full rest. No training until 48 hours symptom-free.
  - Resume at 50% volume and intensity for the first week back
- **ACTION** shift remaining block schedule forward (do not compress missed weeks)
- **WHY** training while ill delays recovery, risks myocarditis (viral + high-intensity), and suppresses immune function

**IF** athlete reports injury:
- **THEN** stop all training involving the affected area. Recommend medical evaluation.
- **IF** cleared for modified training: substitute with unaffected-area work (e.g., upper body if knee injury; easy spinning if shoulder injury)
- **NEVER** prescribe "push through" for injury or illness — this is a hard safety gate

### RPE Trend Escalation

**IF** `rising_rpe_at_constant_if` fires (`rpe_trend.py`: ΔRPE ≥ +1.0 between consecutive 2-week windows at |ΔIF| ≤ 0.03) OR session RPE ≥ 8 for all sessions for 2+ consecutive weeks at same or lower IF:
- **THEN** functional overreaching signal — recovery needed before breakdown occurs
- **ACTION** prescribe 5 days of Z1-only riding (active recovery), then reassess
- **WHY** rising RPE at constant intensity is the earliest reliable indicator of overreaching; PMC/TSB alone cannot detect this because TSS is RPE-blind

**IF** performance is still depressed after a full FOR de-load (the 5-day Z1 block above) — power targets unreachable, peak powers down, RPE still elevated at low IF for another 1–2 weeks:
- **THEN** this is **non-functional overreaching (NFOR)**, not FOR — the de-load did not restore performance, so the load exceeded the supercompensation window
- **ACTION** extend recovery to a full **easy week (or two)**: Z1–Z2 only, ~40–50% normal volume; no intensity until peak powers AND RPE-at-IF both recover. Re-baseline FTP downward if targets still miss after recovery.
- **IF symptoms persist beyond ~3 weeks of genuine rest** (chronic fatigue, mood disturbance, sustained performance decrement, elevated resting HR) → treat as suspected **overtraining syndrome (OTS)**: stop structured training and advise a medical review. OTS recovery is measured in months, not weeks.
- **WHY** FOR resolves in days and is followed by supercompensation; NFOR needs weeks and yields no supercompensation; OTS needs months. Naming the tier early stops a weeks-long problem becoming a months-long one.

**IF** session RPE consistently declining at same IF for 2+ weeks:
- **THEN** positive adaptation — fitness is improving
- **ACTION** note as confirmation that current plan is working; consider progressing to next intensity level

**IF** RPE:IF mismatch detected on a single session (see `references/workout_analysis.md` → RPE:Power Mismatch Detection):
- **THEN** flag in weekly review but do not trigger plan-level changes from a single data point
- **ACTION** track trend; only act when pattern persists across 2+ weeks

### Rule Priority

When multiple adaptation rules fire simultaneously, apply the most conservative (protective) action. Priority order:

1. **Safety** (always wins): Illness/injury stop, TSB < -40 enforcement, ACWR > 1.5, HR fails to reach expected levels, can't complete sessions → enforce recovery before any other action
2. **Fatigue management** (overrides performance): RPE trend escalation (≥8 for 2+ weeks), TSB < -30, ACWR > 1.3, elevated HR +5-10%, 3+ missed sessions → reduce load even if performance indicators are positive
3. **Performance indicators** (informational): FTP retest flags, peak power improvements, positive RPE trends → note and schedule testing, but do not override fatigue-driven decisions
4. **Load & session execution** (lowest): pacing adjustments, progression level changes → apply only after safety and fatigue rules are satisfied

Example conflict: "ACWR > 1.3 → reduce load" + "20min peak +3% → flag FTP retest" → reduce load first; note FTP retest for after load normalizes.
