# Workflow: Training Plan Creation & Weekly Review

Covers **Create Plan** and **Weekly Review & Adaptation**. The SKILL.md → Workflow Dispatch table is the authoritative router.

---

## Create Training Plan

When user requests a training plan ("create a training plan", "start a macro plan", "build me a plan"):

**Step 0:** Check if `plans/active_plan.md` exists. If yes, ask user: archive it (rename to `plans/archived_{date}_{plan_type}.md`) or overwrite? Do not create a second plan file.

**Step 1:** Read `references/periodization.md` for block selection rules and progression tables.

**Step 2:** Gather/confirm athlete profile:
- FTP (current, last test date)
- Weight
- Available training days (default: Tue, Thu, Sat + 1 flex). After Step 3, check `training_day_pattern` from bootstrap output — if it matches, confirm; if it differs, present the detected pattern and ask the athlete to choose.
- **Goal** — pick from the 5-goal taxonomy in `references/periodization.md` → Block Selection Logic. If unclear, ask the athlete: *"Are you targeting a specific event in the next 12 weeks? If yes, what kind (gravel/sportive, criterium, time trial)? If no, do you want to raise FTP or build aerobic base?"*

  | Goal ID | When to pick |
  |---|---|
  | `ftp_improvement` *(default)* | No event; just want to get fitter |
  | `gravel_endurance` | Long mixed-surface event (gran fondo, gravel race, sportive) in next 12 wk |
  | `criterium` | Short repeated-attack racing (40-90 min crits) |
  | `tt` | Time trial / hill climb (20-60 min sustained) |
  | `base` | Off-season; no event in next 12 wk |

  Save goal in `plans/active_plan.md` → Athlete Profile → Goal field. Used downstream by the Weekly Review workflow to interpret peak-power deltas in goal-appropriate context.

**Step 2b (Validation Gate — Coaching Process Rule 1):** Present your athlete assessment and get confirmation before proceeding:
- Summarize what you know: current fitness level, training history, strengths/limiters
- State the training approach you intend to take and why
- Flag zone confidence level:
  - **validated**: FTP from intervals.icu profile AND last test <8 weeks ago
  - **stale**: FTP from intervals.icu but last test >8 weeks ago
  - **self-reported**: FTP provided by athlete without test documentation
  - **unknown**: No FTP available
- If zones are `stale`, `self-reported`, or `unknown` → inform the athlete that Week 1-2 will include a field test (per Coaching Process Rule 4), and power targets are provisional until then
- **Wait for athlete confirmation before proceeding to Step 3**

**Step 3:** Bootstrap PMC from intervals.icu:
```bash
python scripts/pmc_calculator.py --bootstrap --days 90
```
This provides: current CTL/ATL/TSB, 4-week average weekly TSS, peak powers, and daily TSS history.

If zone confidence is not `validated`, insert a field test session into Week 1 (preferred) or Week 2 using the protocol from `references/periodization.md` → FTP Test Protocols.

**Step 4:** Design the block structure:
- Look up the goal in `references/periodization.md` → Block Selection Logic → Goal taxonomy table:
  - `ftp_improvement` → FTP Builder block (4 weeks)
  - `gravel_endurance` → Endurance Block + extended Sat long ride; 6-12 weeks keyed to event date
  - `criterium` → VO2max Block with sprint/NM secondary work; 4 weeks (repeat 2-3 cycles for crit season)
  - `tt` → FTP Builder + extended Threshold intervals; 4-6 weeks
  - `base` → Polarized Block (or Endurance for <6h/wk volume); 8-12 weeks continuous, no taper
- Set baseline weekly TSS from bootstrap data (`weekly_tss_avg_last_4`)
- Apply fitness-state modifiers (Block Selection Logic → Fitness-state modifiers): CTL-based, TSB-based, FTP-recency-based, training-history-based
- Build week-by-week TSS targets using the block template
- Note the **key metric** for the goal in the plan summary (e.g., for `gravel_endurance` → track Sat long-ride NP and durability; for `criterium` → track 1-min and 5-min peaks)

**Step 5:** Generate Week 1 detailed schedule:
- Assign sessions to each training day following TSS distribution rules
- Select interval progressions appropriate for athlete's level
- Calculate per-session target TSS

**Step 6:** Write `plans/active_plan.md` following `references/plan_state_schema.md`:
- All sections: Athlete Profile, Plan Overview, Block Structure, Current Week Schedule, PMC Snapshot, PMC History, Weekly Review Log, Peak Power Trends, Adaptation Log

**Step 7:** Generate Week 1 workout files:
- Create JSON array of workout definitions (one per session)
- Run batch generation:
```bash
python scripts/batch_generate_zwo.py --input {week_json} --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp {FTP}
# <ZWIFT_WORKOUTS_DIR> = user's Zwift custom workouts folder (see SKILL.md → Zwift Workout Directory). Confirm path with user first.
```

**Step 8:** Save plan summary to Obsidian vault:
- Write to: `{vault}/cycling-fitness-coach/training-plans/YYYY-MM {Plan Name}.md`
- Include: plan overview, block structure table, Week 1 schedule, PMC baseline, peak power baseline
- Open in Obsidian: `obsidian open path="cycling-fitness-coach/training-plans/YYYY-MM {Plan Name}.md"`

**Step 9:** Present plan summary for user approval:
```
## Training Plan: {Plan Type}
**Duration**: {N} weeks ({start} → {end})
**Baseline**: CTL {X} | ATL {X} | TSB {X} | Avg Weekly TSS: {X}

### Block Structure
| Week | Phase | Focus | Target TSS |
|------|-------|-------|------------|
| ...  | ...   | ...   | ...        |

### Week 1 Schedule
| Day | Session | Key Interval | Target TSS | Fuel |
|-----|---------|--------------|------------|------|
| ... | ...     | ...          | ...        | {one-line cue from fueling.md → Quick-Reference} |

**Workout files**: Generated in the user's Zwift custom workouts folder (e.g. `%LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\week1\` on Windows) — see SKILL.md → Zwift Workout Directory
**Peak Power Baseline**: 5s: {X}W | 1min: {X}W | 5min: {X}W | 20min: {X}W
**Fueling reference**: see `references/fueling.md` → Quick-Reference for per-session cues; full pre/during/post detail in the rest of that doc.
```

---

## Weekly Review & Adaptation

When user requests a weekly review ("review my week", "weekly check-in", "how did I do this week"):

**Step 1:** Read `plans/active_plan.md` for current state (week number, schedule, PMC snapshot). If the file does not exist, inform user that no active plan is found and suggest creating one via the Create Plan workflow.
Read `references/plan_state_schema.md` for update rules.

**Step 2:** Run PMC weekly update:
```bash
python scripts/pmc_calculator.py --weekly-update \
  --week {N} --plan-start {start_date} \
  --prev-ctl {ctl} --prev-atl {atl} \
  --planned-tss '{"Tue":{X},"Thu":{X},"Sat":{X},"Flex":{X}}'
```

**Step 3:** Optionally run detailed analysis on specific activities:
```bash
python scripts/intervals_icu_api.py --activity {id} --use-athlete-profile -o output.json
```

**Step 3b (recommended):** Pull wellness/readiness summary for the review week:
```bash
python scripts/intervals_icu_api.py --wellness 14 -o wellness.json
```
Use the 14-day window so the latest 7 training days have a 7-day baseline. Skip if athlete doesn't log wellness (script returns `error` field — note in review output and proceed without).

**Step 3c (recommended):** Aggregate RPE trends from Obsidian workout reviews:
```bash
python scripts/rpe_trend.py --vault-path "<CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews" --weeks 2 -o rpe_trend.json
```
Returns per-session-type 2-week-vs-prior-2-week RPE deltas at constant IF. Detects functional overreaching earlier than PMC/TSB (which is RPE-blind). If `overall_flag: rising_rpe_at_constant_if`, escalate per `references/periodization.md` → RPE Trend Escalation. Skip silently if no Obsidian reviews exist yet (script returns `error` field).

**Step 4:** Apply adaptation decision trees from `references/periodization.md`:
- Check all IF/THEN rules: load adaptation, fatigue management, performance indicators, HR indicators, session execution
- List all triggered rules and proposed actions

**Step 5:** Present review summary:
```
## Week {N} Review

### Planned vs Actual
| Day | Planned TSS | Actual TSS | Status |
|-----|------------|------------|--------|
| ... | ...        | ...        | ...    |
| **Total** | {X} | {X} | {completion}% |

**Completion rate**: Auto-compute from the schedule — count sessions with Status `completed` or `modified` divided by total non-blank sessions. Present as percentage in the Total row. Also available from `pmc_calculator.py --weekly-update` output as `completion_rate`.

### PMC Update
CTL: {prev} → {new} | ATL: {prev} → {new} | TSB: {prev} → {new} | ACWR: {X.XX}
Status: {interpretation}
ACWR Zone: {safe/caution/danger/underprepared}

### Readiness (from --wellness, if available)
**Overall:** {green/yellow/red}
- RHR trend: latest {X} bpm vs 14-day baseline {Y} bpm ({delta:+} bpm)
- HRV trend: latest {X} vs baseline {Y} ({delta_pct:+}%)
- Sleep: avg {X}h over week (target ≥7h)
- Flags: {list of yellow/red flags from wellness_summary, or "None"}

If yellow/red flags present, weight the adaptation recommendation toward recovery (Rule Priority 1-2 in `references/periodization.md` → Adaptation Decision Trees → Rule Priority).

### RPE Trend (from rpe_trend.py, if Obsidian reviews exist)
**Overall flag:** {none / rising_rpe_at_constant_if}
| Session Type | n recent | Recent avg RPE | Recent avg IF | Δ RPE | Δ IF | Flag |
|--------------|----------|---------------|---------------|-------|------|------|
| ... | ... | ... | ... | ... | ... | ... |

If `rising_rpe_at_constant_if` fires for any session type, this is a **functional overreaching signal** that PMC/TSB cannot detect (TSS is RPE-blind). Escalate per `references/periodization.md` → RPE Trend Escalation: prescribe 5 days of Z1-only riding (active recovery), then reassess.

### Peak Powers This Week
| Duration | Previous Best | This Week | Delta |
|----------|-------------|-----------|-------|
| ... | ... | ... | ... |

**Sparkline of trend (across all weeks of this plan)** — render per-duration using `scripts/sparkline.py` from the `## Peak Power Trends` table in `plans/active_plan.md`:
```
5s:    ▁▃▂▆█  450→480W (+6.7%, +30W over 5 points)
1min:  ▁▂▄▇█  310→320W (+3.2%, +10W over 5 points)
5min:  ▁▃▅▆█  240→252W (+5.0%, +12W over 5 points)
20min: ▁▄▅▆█  195→205W (+5.1%, +10W over 5 points)
```
Embed this block under the Peak Powers This Week table. Then when updating `plans/active_plan.md` in Step 7, append the new week's row to `## Peak Power Trends` and re-render the sparkline block at the bottom of that section so the next mid-week check-in sees fresh trend data.

### Adaptation Recommendations
{List triggered rules and proposed changes}
For each recommendation, explain (Coaching Process Rule 3):
- What rule triggered it and what data drove the decision
- What the proposed change achieves physiologically
- How it connects to the athlete's stated goal

### Proposed Week {N+1} Schedule
| Day | Session | Key Interval | Target TSS | Fuel |
|-----|---------|--------------|------------|------|
| ... | ...     | ...          | ...        | {one-line cue from fueling.md → Quick-Reference} |
```

**Step 5b (Mid-Plan FTP Change):** If an FTP test was detected in any analyzed activity this week (via `ftp_test` in Activity Analysis output):
1. Present the estimated new FTP and ask athlete to confirm
2. Follow `references/periodization.md` → Mid-Plan FTP Update rules:
   - Update `active_plan.md` Athlete Profile (FTP value + Last Tested date)
   - If FTP change > 5%: recalculate remaining weeks' target TSS
   - Regenerate current week's pending ZWO files and all future weeks with new FTP
3. Log the FTP change in the Adaptation Log with rationale
4. Include the FTP update in the review summary presented in Step 5

**Step 6 (default — no approval needed):** Save the weekly review to the Obsidian vault as a historical record.

This is **default-on** for the Weekly Review workflow — write happens immediately after presenting the review in Step 5, without waiting for the adaptation-approval step. Rationale: the review captures what *happened* (planned vs actual, PMC, RPE trends, wellness flags) regardless of whether the athlete ends up accepting the proposed adaptations. Skipping the write loses the historical trail.

- Write path: `{vault}/cycling-fitness-coach/weekly-reviews/YYYY Week N Review.md`
- Frontmatter: see `references/obsidian_templates.md` → weekly-review template
- Open in Obsidian: `obsidian open path="cycling-fitness-coach/weekly-reviews/YYYY Week N Review.md"`
- **Opt-out**: only skip if the athlete explicitly says "don't save", "skip note", or similar. Briefly mention the save in your Step 5 response so they have the chance: e.g., *"Saving this review to Obsidian — say 'skip note' if you'd rather not."*

**Step 7:** Wait for user approval on the adaptation proposal.

**Step 8:** After approval, apply changes:
- Generate next week's ZWO files via `batch_generate_zwo.py`
- Update `plans/active_plan.md`: advance week, new schedule, PMC history, peak powers, review log, adaptation log
- (If the Obsidian write was deferred or skipped in Step 6 due to user opt-out, do not retroactively write here — respect the opt-out.)
