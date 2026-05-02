# Workflow: Activity Analysis & Weekly Summary

Covers Workflow 1 (single activity analysis) and Workflow 8 (weekly training summary).

---

## 1. Workout Analysis (API-First)

When user pastes an intervals.icu URL or activity ID:

**Step 1:** Extract activity ID from URL.

**Step 2:** Run the analysis script (credentials auto-loaded from .env):
- If user provides FTP/weight: `python scripts/intervals_icu_api.py --activity {ID} --ftp {FTP} --weight {W} -o output.json`
- Otherwise (default): `python scripts/intervals_icu_api.py --activity {ID} --use-athlete-profile -o output.json`

The script outputs JSON with:
- Activity details (distance, time, power, HR, cadence, `power_data_quality`, `context`)
- `data_warnings[]` — flags for estimated power, outdoor no-power, etc. **Check this first — estimated power invalidates power-based analysis; shift to HR/RPE feedback.**
- Interval breakdown (per-interval power, NP, HR, cadence, duration, intensity)
- Computed metrics: NP, IF, TSS, VI, EF, peak powers, zone distribution, cardiac drift
- `interval_consistency` — split into `hard_intervals` (work) and `easy_intervals` (recovery) for accurate consistency stats
- `ftp_test` — auto-detected via activity name keywords, 20min peak heuristic, or ramp test duration; returns `detection_methods` (list — multiple heuristics can match simultaneously: `"activity_name"`, `"20min_effort_heuristic"`, `"ramp_test"`), `estimated_ftp_20min` (`20min x 0.95`), `estimated_ftp_ramp` (`1min x 0.75`)
- `source: "intervals.icu"` — identifies data source

**Step 3:** Provide coaching analysis using the output:

```
## Workout Analysis: [Name] - [Date]
**Quick Stats**: [Duration] | NP: [X]W | IF: [X.XX] | TSS: [X]
### Execution Rating: [pass/warn/fail]
### Interval Review
[Lap-by-lap target vs actual, consistency]
### Key Takeaways
- What went well
- What to improve
### Next Session
[Specific recommendation]

**Session RPE (1-10)?** — reply with a number, or skip. Used for RPE:Power mismatch detection (see `references/workout_analysis.md` → Session RPE).
```

### HR-Only Analysis Template (when `power_data_quality` == "estimated")

Use this template instead of the standard template when `data_warnings` includes "estimated_power":

```
## Workout Analysis: [Name] - [Date]
**Quick Stats**: [Duration] | Avg HR: [X]bpm | Max HR: [X]bpm | Distance: [X]km
### Effort Assessment
- **Effort Level**: [Zone estimate from HR zones in training_zones.md]
- **Cardiac Response**: [Normal/Elevated/Suppressed for effort type]
- **Duration Adequacy**: [Appropriate for goal?]
### Key Takeaways
- [HR-based observations]
- [RPE-based observations if available]
### Note
Power data is estimated (no power meter). All power metrics (NP, IF, TSS, zones) are unreliable. Recommendations based on HR, duration, and perceived effort.

**Session RPE (1-10)?** — especially important when power is estimated
```

**Step 4:** Save analysis to Obsidian vault:
- Write the full coaching analysis (frontmatter + markdown) to:
  `{vault}/cycling-fitness-coach/workout-reviews/YYYY-MM-DD {Activity Name}.md`
- Use the `Write` tool (direct file write to vault folder)
- Open in Obsidian: `obsidian open path="cycling-fitness-coach/workout-reviews/YYYY-MM-DD {Activity Name}.md"`

**Step 5:** Update the active plan with this session's result:
- Read `plans/active_plan.md` → `## Current Week Schedule` table
- Find the row matching the analyzed session by day/date (e.g., activity dated 02 Apr → row whose `Day` column matches that date)
- Update the row's **Status** column from `pending` → `completed` (or `modified` if the session significantly deviated from plan, `skipped` if not done)
- Append a one-line entry under the `**Completed session notes:**` block (or create the block if missing) with: avg power + % FTP, NP/IF/TSS, key observation (cardiac drift, fade, etc.), execution rating, RPE if provided
- If no matching row exists (unplanned outdoor ride), append a new row to `## Current Week Schedule` with `Status: completed` and a brief note

**Example completed-session note:**
```
- **D3 (02 Apr)**: 189/191W (98-100% FTP), NP 188W, IF 0.98, TSS 75, cardiac drift +3.1%. 5/5. RPE 7.
```

**IMPORTANT:** This step is mandatory after every workout analysis. Stale plan state causes wrong target lookup and missed adaptation triggers in future sessions. The schema is documented in `references/plan_state_schema.md`. If `plans/active_plan.md` does not exist, skip this step (athlete has no active plan).

**Step 6:** FTP Change Propagation (conditional — only when `metrics.ftp_test` is present in script output):

When the analysis script detects an FTP test, propagate the new FTP into the active plan. Zones are %FTP-relative (see `references/training_zones.md`) so no static watts table needs recalculation — workouts auto-scale on the next ZWO regeneration. **Always confirm with the athlete before making changes.**

1. **Present the result and ask for confirmation:**
   ```
   FTP Test Detected: {20min_avg}W × 0.95 = {estimated_ftp}W
   Current FTP: {old_ftp}W → Proposed: {new_ftp}W ({+/-X%})

   Confirm new FTP, or override? (e.g., "set 200W" / "yes" / "keep current")
   ```
   - If ramp test: use `estimated_ftp_ramp` (1min × 0.75) instead
   - If athlete overrides (e.g., rounds up based on training data), use their value
   - If athlete says "keep current" → skip all updates below

2. **After confirmation, update `plans/active_plan.md`:**

   **A. Athlete Profile section** — update three fields:
   - `FTP` → new value (e.g., `200W`)
   - `FTP Last Tested` → activity date (`YYYY-MM-DD`)
   - If a `W/kg` field exists in the table, recompute as `new_ftp / weight` to 2 decimals

   **B. FTP Test History section** — append a row (create the section if missing, see schema in `references/plan_state_schema.md` → FTP Test History):
   ```
   | {date} | {protocol: 20min/ramp} | {raw_avg}W | {formula_estimate}W | {confirmed}W | {pacing notes / fade %} |
   ```
   If the athlete overrode the formula value, note the rationale in the pacing-notes column.

   **C. (Optional) intervals.icu profile sync** — remind the athlete to update their FTP at https://intervals.icu/settings so future `--use-athlete-profile` calls pick up the new value. The skill does NOT write to intervals.icu.

3. **Print a change summary:**
   ```
   FTP Updated: {old}W → {new}W (+{X}W / +{X}%)
   W/kg: {old} → {new}
   plans/active_plan.md updated | FTP Test History appended
   Reminder: update FTP at intervals.icu/settings
   ```

**IMPORTANT:** Do NOT skip confirmation. The athlete may want to round up/down based on training context, or keep the current FTP if the test was compromised.

**Step 7:** Adapt Forward — per-activity cascade check (propose-and-confirm):

After Step 5 (tracker updated with this session) and Step 6 (FTP propagation, if triggered), run the per-activity adaptation check against the next 1–2 training sessions. Full rules, thresholds, and worked example: `references/adaptation_rules.md`.

1. **Resolve prescribed targets** for the analyzed session (layered source — see `adaptation_rules.md` §1):
   - Prefer `plans/active_plan.md` → Current Week Schedule row (`Target TSS` + `Key Interval` %FTP range).
   - Fall back to session-type defaults if plan file is stale/missing.
   - Off-plan / unplanned → switch to day-intent branch (`adaptation_rules.md` §5).

2. **Classify the deviation** across 4 signals (TSS, IF, zone distribution, cardiac drift) — green/yellow/red per `adaptation_rules.md` §2. Roll up to an overall severity (worst-of-signals; TSS-red and zone-violation-red always dominate).

3. **Apply protection overrides FIRST** (`adaptation_rules.md` §4):
   - Rest day next → never override with work.
   - FTP test within 3 days → downgrade the preceding session, never the test.
   - Taper week → protective cascades only.
   - Illness already declared → skip cascade; periodization rules apply.
   - Keystone next → yellow preserves keystone (add readiness check); red downgrades.

4. **Apply cascade matrix** (`adaptation_rules.md` §3) after protection overrides resolve:
   - Green → no change. Skip to step 6 below.
   - Yellow/Red → generate proposed edits for the next 1–2 training rows in `plans/active_plan.md` → Current Week Schedule.

5. **Upside check** (`adaptation_rules.md` §6) — only fires on 2+ consecutive on-plan sessions at power ≥ prescribed; never on a single session. Propose FTP retest window or next-keystone progression level.

6. **Present proposal** using the output format in `adaptation_rules.md` §7:

   ```
   ### Adaptation Check

   **Signal review:** [4-row + Overall severity table]
   **Protection checks:** [applicable overrides or "None triggered"]
   **Proposed cascade:** [Date | Session | Current | Proposed | Reason table]

   **Apply changes? (yes / no / modify)**
   ```

7. **On user response:**
   - `yes` → edit the matching session rows in `plans/active_plan.md` → `## Current Week Schedule` (or `## Week N+1 Schedule (Preview)` if cascade lands in next week). Append one line to `plans/active_plan.md` → `## Adaptation Log`:
     ```
     <!-- {date} (per-activity cascade) -->
     - **Trigger**: {severity + signal e.g. "Red zone violation: 14.4% Z5+ on Z2 day"}
     - **Action**: {what was changed in the schedule}
     - **Rationale**: {one-line reason referencing protection rules if applied}
     ```
   - `no` → no schedule edits. Note in session review body: "Adaptation proposed but declined."
   - `modify [instructions]` → apply the modified proposal; still log to Adaptation Log.

8. **Overall Green → skip presentation.** Instead append one line to the session review: "Adaptation check: all signals green, no cascade needed."

**IMPORTANT:** This step is separate from Step 5 (which records the completed session) and Step 6 (which handles FTP changes). Step 7 modifies FUTURE sessions only. Never edit past schedule rows here.

**Plan-Aware Analysis:** If `plans/active_plan.md` exists, cross-reference the analyzed activity against the current week schedule:
- Was this session on-plan? Match by day/date and session type.
- Compare actual power, TSS, and duration against planned targets.
- Note in the analysis whether the athlete is tracking to plan or deviating.
- Update the session Status in the plan file from `pending` to `completed` (or `modified` if significantly different).

**Review most recent workout** (no activity ID needed):
```bash
python scripts/intervals_icu_api.py --latest --use-athlete-profile -o output.json
```

**List recent activities:**
```bash
python scripts/intervals_icu_api.py --list-recent 10
```

**IMPORTANT:** Always use the script above for intervals.icu API calls. Do NOT write inline Python (`python -c "..."`) to query the API — it bypasses encoding, error handling, and credential loading built into the script.

### Fallback: Manual Data Entry

If API unavailable, request screenshots or copy-paste of stats.

### Analysis Checklist

- **Data quality OK?** — check `data_warnings` first; estimated power invalidates power-based analysis
- **Hit power targets?** — +/-3% acceptable; consistent undershoot may mean FTP is set too high
- **Pacing appropriate?** — positive splits (fading power) indicate starting too hard
- **HR normal?** — elevated HR at same power signals fatigue, heat, or dehydration
- **Interval consistency?** — <5% fade across sets is good; progressive fade suggests pacing or fueling issue

For the full analysis framework including session rating, common issues, and load analysis, see `references/workout_analysis.md`.

### Error Handling

- **Authentication (401)**: Tell user to check their API key at https://intervals.icu/settings. Verify `.env` has correct `INTERVALS_ICU_API_KEY`.
- **Not found (404)**: Invalid activity ID. Ask user to verify the URL or ID. Check for copy-paste errors (missing `i` prefix, extra characters).
- **Rate limited (429) / Server error (5xx)**: The script retries automatically (3 attempts with backoff). If it still fails, wait a few minutes and try again.
- **Network/timeout**: Check internet connectivity. Retry once. If persistent, fall back to manual data entry.
- **Script crash (traceback)**: Show the stderr output to the user. Common causes: missing `requests` package (`pip install requests`), malformed `.env` file, Python version < 3.9.
- **Empty/missing data**: If script returns empty intervals, streams, or peaks, note what's missing in the analysis. Partial data is still useful — analyze what's available.

---

## 8. Weekly Training Summary

When user asks "weekly summary", "how was my week", or "training summary":

**Step 1:** Run weekly summary:
```bash
python scripts/intervals_icu_api.py --weekly-summary -o output.json
```

**Step 2:** Present aggregated view:
```
## Weekly Training Summary: {date_range}

**Volume**: {X} hours | {X} km | {X} activities ({X} training / {X} rest days)
**Load**: Total TSS: {X} | Avg IF: {X.XX} | Total kJ: {X}
**Zone Distribution** (by time): Z1 {X}% | Z2 {X}% | Z3 {X}% | Z4 {X}% | Z5+ {X}%

### Power Profile (if peaks available)
| Duration | Best | W/kg | Category |
|----------|------|------|----------|
| 5s | {X}W | {X} | {cat} |
| 1min | {X}W | {X} | {cat} |
| 5min | {X}W | {X} | {cat} |
| 20min | {X}W | {X} | {cat} |
Rider type: {sprinter/time_trialist/pursuiter/all_rounder}
```

**Step 3:** If FTP update suggested by auto-detection, flag it:
```
FTP Update Suggested: 20min best {X}W → estimated FTP {X}W (+{X}% vs current {FTP}W)
Consider scheduling an FTP test to confirm.
```
