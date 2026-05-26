# Per-Activity Adaptation Rules

Reference for Claude-as-coach: **per-activity forward-cascade rules**. Runs after every workout analysis. Compares actual vs prescribed across 4 signals, classifies deviation, and proposes edits to the next 1–2 sessions in `plans/active_plan.md` → Current Week Schedule (or Week N+1 Schedule (Preview) if cascade lands in next week).

**Scope — what this layer does NOT cover:**
- Weekly trend / multi-session adaptation (ACWR, TSB, completion rate, RPE trends) → see `weekly_adaptation.md`.
- Block-level changes (phase transitions, FTP retest, block type switch) → weekly review workflow.
- This layer proposes *immediate next-session* cascades. The weekly review may further adjust the block.

**Operating mode: propose-and-confirm.** Never edit the schedule silently. Always show the diff and wait for `yes` / `no` / `modify`.

## Sub-prompt contract

- **Inputs:** completed-activity analysis JSON from `intervals_icu_api.py --activity <id>` or `fit_ingest.py` fallback — fields used: `np`, `if`, `tss`, zone distribution, `duration_moving`, RPE (if collected from athlete this session). Prescribed targets resolved from `plans/active_plan.md` → Current Week Schedule, then session-type defaults, then day-intent branch (see §1).
- **Outputs:** per-signal deviation classification (4 signals — TSS, IF, zone-distribution, RPE) + propose-and-confirm cascade edits to next 1–2 sessions in `plans/active_plan.md` → Current Week Schedule (or Week N+1 Schedule (Preview) if cascade lands in the next week).
- **Invocation:** `workflows/analyze.md` → Step 7 (Adapt Forward) — fires after every workout analysis. NOT invoked by Weekly Review (that uses `weekly_adaptation.md`); the two layers compose without overlap.

---

## 1. Prescribed-Targets Source (layered)

To compute deviation, resolve the prescribed targets for the analyzed session in this order:

1. **`plans/active_plan.md` → Current Week Schedule** — use `Target TSS` column and `Key Interval` %FTP range (derive target IF as midpoint of %FTP range × 0.97 adjustment for duration). Preferred when plan file is current.
2. **Session-type defaults** (table below) — use when `plans/active_plan.md` is stale or missing, or session name maps to a known type. Match by keywords in the activity name (e.g., "Sweet Spot", "Threshold", "VO2max").
3. **Unplanned / off-plan activity** (no matching plan row AND no name keyword match) — no prescribed TSS/IF; use **day-intent branch** (Section 5).

### Session-Type Defaults (fallback targets)

> **Reading this table — Target IF is *session-level*, not work-interval %FTP.** A "Sweet Spot" session prescribed at 88–94% FTP for the work intervals will land at session IF ~0.82–0.88 because the session also includes warmup, cooldown, and inter-interval recovery — those drag the overall IF below the work-interval power. See `references/training_zones.md` for **work-interval %FTP prescription targets** and `references/block_templates.md` for block-level workout structure. The two sets of numbers are not in conflict; they describe different parts of the same session.

| Session type (name contains) | Target IF | Primary zone | Z2 % floor | Contaminating zones |
|---|---|---|---|---|
| Recovery / Easy Spin | 0.50–0.60 | Z1 | — | Z3+ any content |
| Endurance / Z2 | 0.65–0.75 | Z2 | ≥60% | Z4+ any content |
| Sweet Spot | 0.82–0.88 | Z3–Z4 (SS) | — | Z5+ any content |
| Threshold | 0.88–0.95 | Z4 | — | — |
| Over-Unders | 0.85–0.92 | Z4+Z5 mix | — | Sustained Z6+ (brief surges OK) |
| VO2max | 0.85–0.92 | Z5 (work), Z2 (recovery) | — | Sustained Z6+ |
| FTP Test | 0.95–1.05 | Z4 (effort block) | — | — |

If session type is ambiguous, look at the prior week's same-slot session in `plans/active_plan.md` (or the archived previous block) for a hint.

---

## 2. Four Signals + Severity Thresholds

Compute each signal independently. Overall severity = worst-of-signals, except TSS-red always triggers cascade.

### A. TSS Deviation (actual ÷ prescribed − 1)

| Severity | Overshoot | Undershoot |
|----------|-----------|------------|
| Green | 0% to +15% | 0% to −15% |
| Yellow | +15% to +30% | −15% to −30% |
| Red | >+30% | >−30% (or session skipped / aborted) |

### B. IF Deviation (|actual IF − target IF|)

| Severity | Gap |
|----------|-----|
| Green | ≤ 0.05 |
| Yellow | 0.05–0.10 |
| Red | > 0.10 (always red if prescribed session is Z1/Z2 and actual IF > target + 0.10) |

### C. Zone Distribution

Check two things: primary zone coverage and contaminating-zone content.

| Severity | Primary zone coverage | Contaminating zone content |
|----------|----------------------|---------------------------|
| Green | ≥ floor from Section 1 table | < 5% |
| Yellow | 40% to floor | 5–10% |
| Red | < 40% | ≥ 10% (zone violation) |

**Zone violation (red) dominates**: e.g., 14% Z5+ on a prescribed Z2 ride → red regardless of TSS or IF numbers.

### D. Cardiac Drift

| Severity | Drift |
|----------|-------|
| Green | < 5% |
| Yellow | 5–8% |
| Red | > 8% |

Drift is interpreted alongside ambient conditions (heat/hydration) — a yellow drift with a known heat cause is not the same as unexplained yellow drift. Note context but don't downgrade the signal.

---

## 3. Cascade Actions (overall severity → next sessions)

**Next session** = the next non-rest training row in `plans/active_plan.md` → Current Week Schedule, chronologically after the analyzed session (or in the Week N+1 preview if the analyzed session was the last of the current week).
**Second session** = the one after that.

| Overall | Next session | Second session |
|---|---|---|
| **Green** | No change | No change |
| **Yellow (overshoot)** | Maintain intensity, cut duration 15–20%; or swap order with following day if that moves intensity later | No change |
| **Yellow (undershoot)** | Hold as planned; add readiness check | No change |
| **Red (overshoot)** | Demote to Z1–Z2 endurance or REST (coach's judgment based on day intent) | Apply yellow cascade (cut duration 15–20%) |
| **Red (undershoot / aborted)** | Hold as planned; add readiness check; flag FTP-overset concern if pattern repeats | No change |

**Tiebreakers when multiple severities are present:**
1. Zone violation (red) always dominates TSS/IF green.
2. TSS red overrides everything else.
3. Between Yellow-overshoot and Yellow-undershoot, apply the Yellow-overshoot branch (more protective).

---

## 4. Protection Overrides (hard gates, apply BEFORE cascade)

These override the cascade matrix — apply them first.

1. **Rest day next** — never override a planned REST with work, regardless of upside signals.
2. **FTP test within next 3 days** — protect the test. Any cascade downgrade lands on the session **before** the test, not the test itself. Never demote the test.
3. **Taper week** (Block W4 or any explicit taper phase) — only protective cascades allowed (downgrade). Never add load.
4. **Illness already declared** (Severity 1 or 2 noted in `plans/active_plan.md` → Adaptation Log within the last 14 days) — skip this cascade entirely; `weekly_adaptation.md` → Illness/Injury rules apply.
5. **Keystone session next** (schedule row flagged `KEYSTONE` in the `Session` or `Key Interval` column) — downgrade only on **red**. Yellow preserves the keystone; add readiness check instead.

---

## 5. Unplanned / Off-Plan Activity Branch

When the analyzed activity has no matching schedule row (e.g., outdoor freestyle on a day without a prescription, or an extra ride):

1. **Locate day intent** from `plans/active_plan.md` → Current Week Schedule: what was the row for that day? (REST, recovery, endurance, threshold, etc.)
2. **Assess against day intent** using absolute-load thresholds (there's no prescribed TSS to compare against):

| Day intent | Absolute-load yellow | Absolute-load red |
|---|---|---|
| REST | Any training activity → yellow | TSS > 50 OR Z4+ > 5 min |
| Recovery / Easy Spin | TSS > 40 OR IF > 0.65 | TSS > 60 OR IF > 0.75 |
| Endurance (Z2) | TSS > 80 OR Z4+ > 10% OR Z5+ > 5% | TSS > 100 OR Z4+ > 20% OR Z5+ > 10% |
| Sweet Spot / Threshold / O/U / VO2max | Treat as a modified prescribed session; fall back to session-type defaults (Section 1) | — |

3. **Append a new row** to `plans/active_plan.md` → Current Week Schedule for the activity (per `workflows/analyze.md` Step 5) and cascade from there.

---

## 6. Symmetric Upside (progress faster)

Upside rules fire **only** when BOTH conditions hold:

1. **Power executed at OR above prescribed** across the session (not just low RPE — RPE-easy at power-undershoot is not upside).
2. **Pattern across 2+ consecutive on-plan sessions** at same intensity tier (SS, Thr, O/U, VO2). Single strong session is never enough.

### Upside actions

| Pattern | Action |
|---|---|
| 2+ on-plan SS/Thr sessions at power ≥ prescribed + 20min peak trending up week-over-week | Flag FTP retest window within next 1–2 weeks. Do NOT silently raise FTP. |
| 2+ on-plan sessions at power ≥ prescribed, no peak-power signal | Propose next progression level on upcoming keystone (e.g., SS 3x15 → 3x16 next cycle) |

### Upside gates (never fire if)

- TSB < −20 (fatigue dominates)
- Rising RPE trend at constant IF for 2+ weeks
- Taper week
- Illness declared in last 14 days

---

## 7. Output Format — Step 7 Adaptation Check

Present after the analysis block, before saving to Obsidian:

```
### Adaptation Check

**Signal review:**
| Signal | Target | Actual | Severity |
|--------|--------|--------|----------|
| TSS | {target} | {actual} | {green/yellow/red ± %} |
| IF | {target range} | {actual} | {green/yellow/red ± gap} |
| Zone mix | {primary ≥X%, contaminating <Y%} | {primary X%, Z5+ Y%} | {green/yellow/red} |
| Drift | <5% | {actual}% | {green/yellow/red} |
| **Overall** | | | **{severity + one-line reason}** |

**Protection checks:**
- {list of applicable overrides from Section 4, or "None triggered"}

**Proposed cascade:**
| Date | Session | Current | Proposed | Reason |
|------|---------|---------|----------|--------|
| {date} | {name} | {plan} | {new plan or "hold"} | {signal reference} |

**Apply changes? (yes / no / modify)**
```

On user response:
- `yes` → edit the matching session rows in `plans/active_plan.md` → `## Current Week Schedule` (or `## Week N+1 Schedule (Preview)` if cascade lands in next week). Append a one-line entry to `plans/active_plan.md` → `## Adaptation Log` noting trigger + action.
- `no` → no schedule edits. Note in the session review body: "Adaptation proposed but declined."
- `modify [instructions]` → apply the modified proposal, still log to Adaptation Log.

---

## 8. Worked Example — RTN Sat L Loop (2026-04-18)

Reproduces the manual decision made without this layer to verify rule correctness.

**Inputs (from activity):**
- TSS 91, IF 0.786, VI 1.385, Z5+ 14.4%, cardiac drift −2.27%
- Day intent (from active plan): `Z2 Endurance Outdoor 50-70min` → treat as prescribed Endurance.
- Prescribed targets (Section 1, Endurance): TSS ~60, IF 0.65–0.75, Z2 ≥60%, Z4+ <5%.

**Signal review:**
| Signal | Target | Actual | Severity |
|---|---|---|---|
| TSS | ~60 | 91 | **Red** (+52%) |
| IF | 0.65–0.75 | 0.786 | Green (gap 0.036, <0.05) |
| Zone mix | Z2 ≥60%, Z5+ <5% | Z5+ 14.4% | **Red** (zone violation) |
| Drift | <5% | −2.27% | Green |

**Overall: Red (TSS red + zone violation red — both fire; zone violation describes the "why").**

**Protection checks:**
- Next session: Sun 19 Apr = REST → **rest-day protection applies**.
- Session after: Mon 20 Apr = SS 3x15 = **keystone** → keystone rule (yellow preserves, red would demote).

**Cascade application:**
- Red overshoot matrix: next session demoted, second session gets yellow cascade.
- Next session = Sun REST → rest-day protection wins → unchanged.
- Second session = Mon SS → matrix assigns yellow cascade (cut duration 15–20%). Keystone override: "yellow preserves keystone + readiness check." → plan holds unchanged, readiness check added. Drift was green so CV load is intact; this protects the zone-violation signal without wasting the keystone.

**Proposed cascade:**
| Date | Session | Current | Proposed | Reason |
|---|---|---|---|---|
| Sun 19 Apr | Pre-SS rest | REST | REST (unchanged, protected) | Rest-day protection |
| Mon 20 Apr | SS 3x15 | Plan holds | Plan holds + pre-ride readiness check | Keystone protection; drift green so CV load OK; zone violation flags discipline, not fatigue |

**Verification:** Matches the manual coach decision (`protect Mon keystone (doubly important after Sat TSS spike)`). Rules reproduce coach judgment. ✅

---

## 9. Integration with Weekly Review

Per-activity cascades are immediate and local (next 1–2 sessions). The weekly review workflow (`weekly_adaptation.md`) may further adjust the block based on trends: if yellow cascades have fired 3+ times in a week, the weekly review should consider broader load reduction or FTP re-evaluation regardless of any single session's cascade decision.

**Rule of thumb**: this layer handles single-event deviations; `weekly_adaptation.md` handles patterns.
