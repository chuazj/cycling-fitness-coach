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
