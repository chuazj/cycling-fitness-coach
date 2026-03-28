# Workflow: Training Plan Creation & Weekly Review

Covers Workflow 4 (create training plan) and Workflow 5 (weekly review & adaptation).

---

## 4. Create Training Plan

When user requests a training plan ("create a training plan", "start a macro plan", "build me a plan"):

**Step 0:** Check if `plans/active_plan.md` exists. If yes, ask user: archive it (rename to `plans/archived_{date}_{plan_type}.md`) or overwrite? Do not create a second plan file.

**Step 1:** Read `references/periodization.md` for block selection rules and progression tables.

**Step 2:** Gather/confirm athlete profile:
- FTP (current, last test date)
- Weight
- Available training days (default: Tue, Thu, Sat + 1 flex). After Step 3, check `training_day_pattern` from bootstrap output — if it matches, confirm; if it differs, present the detected pattern and ask the athlete to choose.
- Goal (default: FTP improvement)

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
python scripts/pmc_calculator.py --bootstrap --days 90 --ftp {FTP}
```
This provides: current CTL/ATL/TSB, 4-week average weekly TSS, peak powers, and daily TSS history.

If zone confidence is not `validated`, insert a field test session into Week 1 (preferred) or Week 2 using the protocol from `references/periodization.md` → FTP Test Protocols.

**Step 4:** Design the block structure:
- Select block type based on goal and current fitness (see `references/periodization.md` → Block Selection Logic)
- Set baseline weekly TSS from bootstrap data (`weekly_tss_avg_last_4`)
- Apply CTL-based and TSB-based adjustments
- Build week-by-week TSS targets using the block template

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
python scripts/batch_generate_zwo.py --input {week_json} --output-dir plans/workouts/week1/ --ftp {FTP}
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
| Day | Session | Key Interval | Target TSS |
|-----|---------|--------------|------------|
| ... | ...     | ...          | ...        |

**Workout files**: Generated in plans/workouts/week1/
**Peak Power Baseline**: 5s: {X}W | 1min: {X}W | 5min: {X}W | 20min: {X}W
```

---

## 5. Weekly Review & Adaptation

When user requests a weekly review ("review my week", "weekly check-in", "how did I do this week"):

**Step 1:** Read `plans/active_plan.md` for current state (week number, schedule, PMC snapshot). If the file does not exist, inform user that no active plan is found and suggest creating one via Workflow 4.
Read `references/plan_state_schema.md` for update rules.

**Step 2:** Run PMC weekly update:
```bash
python scripts/pmc_calculator.py --weekly-update \
  --week {N} --plan-start {start_date} \
  --prev-ctl {ctl} --prev-atl {atl} \
  --planned-tss '{"Tue":{X},"Thu":{X},"Sat":{X},"Flex":{X}}' \
  --ftp {FTP}
```

**Step 3:** Optionally run detailed analysis on specific activities:
```bash
python scripts/intervals_icu_api.py --activity {id} --use-athlete-profile -o output.json
```

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

### Peak Powers This Week
| Duration | Previous Best | This Week | Delta |
|----------|-------------|-----------|-------|
| ... | ... | ... | ... |

### Adaptation Recommendations
{List triggered rules and proposed changes}
For each recommendation, explain (Coaching Process Rule 3):
- What rule triggered it and what data drove the decision
- What the proposed change achieves physiologically
- How it connects to the athlete's stated goal

### Proposed Week {N+1} Schedule
| Day | Session | Key Interval | Target TSS |
|-----|---------|--------------|------------|
| ... | ...     | ...          | ...        |
```

**Step 5b (Mid-Plan FTP Change):** If an FTP test was detected in any analyzed activity this week (via `ftp_test` in Workflow 1 output):
1. Present the estimated new FTP and ask athlete to confirm
2. Follow `references/periodization.md` → Mid-Plan FTP Update rules:
   - Update `active_plan.md` Athlete Profile (FTP value + Last Tested date)
   - If FTP change > 5%: recalculate remaining weeks' target TSS
   - Regenerate current week's pending ZWO files and all future weeks with new FTP
3. Log the FTP change in the Adaptation Log with rationale
4. Include the FTP update in the review summary presented in Step 6

**Step 6:** Wait for user approval before applying changes.

**Step 7:** After approval:
- Generate next week's ZWO files via `batch_generate_zwo.py`
- Update `plans/active_plan.md`: advance week, new schedule, PMC history, peak powers, review log, adaptation log
- Save weekly review to Obsidian vault:
  `{vault}/cycling-fitness-coach/weekly-reviews/YYYY Week N Review.md`
- Open in Obsidian: `obsidian open path="cycling-fitness-coach/weekly-reviews/YYYY Week N Review.md"`
