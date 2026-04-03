# Plan State Schema

Documents the exact structure of `plans/active_plan.md` — the single source of truth for the active training plan. Claude reads and updates this file across conversations.

## File Location

Fixed convention: `plans/active_plan.md`

- Created by Workflow 4 (Create Training Plan)
- Read by Workflows 1, 5, 6
- Updated by Workflows 4, 5

Only one active plan exists at a time. To start a new plan, the old file is archived (renamed with date suffix) or overwritten after user confirmation.

---

## Section Reference

### `## Athlete Profile`

Static athlete data. Set at plan creation; updated only if athlete reports changes.

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| FTP | `{value}W` | `192W` | Updated after successful FTP test |
| Weight | `{value}kg` | `74kg` | |
| FTP Last Tested | `YYYY-MM-DD` | `2026-03-01` | Updated after FTP test completion |
| Training Days | comma-separated | `Tue, Thu, Sat, +1 flex` | |
| Goal | free text | `FTP improvement` | |

### `## Plan Overview`

High-level plan metadata. Updated when advancing weeks or changing phase.

| Field | Format | Valid Values | Notes |
|-------|--------|-------------|-------|
| Plan Type | string | `FTP Builder`, `VO2max Block`, `Endurance Block`, `Polarized Block` | From `references/periodization.md` |
| Start Date | `YYYY-MM-DD` | any date | Monday of first training week |
| End Date | `YYYY-MM-DD` | any date | Sunday of last training week |
| Total Weeks | integer | 3-8 | |
| Current Week | integer | 1 to Total Weeks | Incremented during weekly review |
| Current Phase | string | `Build 1`, `Build 2`, `Build 3`, `Recovery`, etc. | From block structure |

### `## Block Structure`

Overview table of all weeks in the plan. Written at creation; not modified after.

| Column | Type | Description |
|--------|------|-------------|
| Week | int | 1-indexed week number |
| Phase | string | Phase name from periodization block template |
| Focus | string | Brief description of week's training emphasis |
| Target Weekly TSS | int | Planned total TSS for the week |
| Recovery? | `Yes`/`No` | Whether this is a recovery/deload week |

### `## Current Week Schedule`

Detailed session table for the active week. **Replaced entirely** when advancing to next week.

Header format: `## Current Week Schedule (Week {N}: {Mon date}-{Sun date})`

| Column | Type | Valid Values | Description |
|--------|------|-------------|-------------|
| Day | string | `Tue`, `Thu`, `Sat`, `Flex` | Training day |
| Session | string | e.g., `Sweet Spot`, `Threshold`, `VO2max`, `Endurance`, `FTP Test` | Session type |
| Duration | string | e.g., `60min`, `90min` | Planned duration |
| Key Interval | string | e.g., `2×20min @ 88-94%` | Main interval description |
| Target TSS | int | Planned session TSS |
| ZWO File | string | filename, e.g., `week1_tue_ss.zwo` | Generated .zwo filename |
| Status | string | `pending`, `completed`, `skipped`, `modified` | Session completion status |

**Status transitions:**
- `pending` → `completed`: after activity analysis confirms session was executed
- `pending` → `skipped`: athlete reports not doing the session
- `pending` → `modified`: session was done but significantly deviated from plan
- Only forward transitions; never revert a status

### `## Week {N+1} Schedule (Preview)` *(optional)*

Read-only preview of the next week's schedule. Generated during weekly review to give the athlete visibility into upcoming sessions. **Replaced or removed** when the current week advances.

Same column format as `## Current Week Schedule`. Day column may use relative labels (e.g., `D1`, `D2`) when exact dates are TBD.

### `## PMC Snapshot`

Current PMC values. **Overwritten** with latest values during weekly review.

| Field | Format | Description |
|-------|--------|-------------|
| Date | `YYYY-MM-DD` | Date of snapshot |
| CTL (Fitness) | float, 1 decimal | Chronic Training Load (42-day EWA) |
| ATL (Fatigue) | float, 1 decimal | Acute Training Load (7-day EWA) |
| TSB (Form) | float, 1 decimal | Training Stress Balance (CTL - ATL) |
| ACWR | float, 2 decimals | Acute:Chronic Workload Ratio (ATL ÷ CTL); null if CTL = 0 |
| Status | string | Interpretation: see status rules below |

**Status rules (TSB):**
- TSB > 10: `Fresh — ready for hard efforts`
- TSB 0 to 10: `Good form — normal training`
- TSB -10 to 0: `Normal training range`
- TSB -20 to -10: `Building fatigue — monitor recovery`
- TSB -30 to -20: `High fatigue — consider extra recovery`
- TSB < -30: `WARNING: Very high fatigue — recovery needed`

**ACWR zone rules:**
- ACWR 0.8-1.3: `Safe zone — normal training`
- ACWR > 1.3 (≤1.5): `Caution — elevated risk, reduce next week by 10%`
- ACWR > 1.5: `Danger — training spike, enforce 2-3 days recovery`
- ACWR < 0.8: `Underprepared — gradually increase load (max +10%/week)`
- ACWR null (CTL = 0): `Insufficient training history — no ACWR assessment`

### `## PMC History`

Append-only log of PMC snapshots. One row per weekly review.

| Column | Type | Description |
|--------|------|-------------|
| Date | `YYYY-MM-DD` | Snapshot date |
| CTL | float | CTL at that date |
| ATL | float | ATL at that date |
| TSB | float | TSB at that date |
| ACWR | float | ACWR at that date (null if CTL = 0) |
| Notes | string | Context (e.g., "Plan start", "Week 1 review", "FTP retest") |

### `## Weekly Review Log`

Append-only log of weekly review summaries. Each review is a subsection:

```markdown
### Week {N} ({date range})
- **Planned TSS**: {total} | **Actual TSS**: {total} | **Completion**: {%}
- **Sessions**: {completed}/{total} completed
- **PMC**: CTL {value} | ATL {value} | TSB {value} | ACWR {value}
- **Key observations**: {1-2 sentences}
- **Adaptations applied**: {list of changes, or "None"}
```

### `## Peak Power Trends`

Running table of peak powers across the plan. Updated during weekly review.

| Column | Type | Description |
|--------|------|-------------|
| Duration | string | `5s`, `1min`, `5min`, `20min` |
| Baseline | int | Pre-plan peak power (from bootstrap) |
| Week N | int or empty | Best peak power during that week |

Empty cells indicate no data for that week yet.

### `## Adaptation Log`

Append-only log of adaptation decisions made by Claude. Format:

```markdown
<!-- Week {N} ({date}) -->
- **Trigger**: {which decision tree rule fired}
- **Action**: {what was changed}
- **Rationale**: {brief explanation}
```

---

## Update Operations

### Marking a session complete

1. Read current week schedule
2. Find matching day row
3. Change Status from `pending` to `completed`
4. Optionally add actual TSS in notes if significantly different from target

### Advancing to next week

1. Increment `Current Week` in Plan Overview
2. Update `Current Phase` if week transitions to new phase
3. Replace `Current Week Schedule` section entirely with new week's sessions
4. Append PMC History row
5. Overwrite PMC Snapshot with new values
6. Update Peak Power Trends table with new week's data
7. Append Weekly Review Log entry

### Applying adaptation

1. Modify next week's schedule (before generating ZWO files)
2. Update Block Structure if target TSS changes
3. Append Adaptation Log entry with trigger, action, rationale

### FTP update

1. Update `FTP` in Athlete Profile
2. Update `FTP Last Tested` date
3. Note: all future power prescriptions automatically adjust (they're % FTP)
4. Recalculate remaining weeks' target TSS if needed

---

## Validation Rules

- `Current Week` must be between 1 and `Total Weeks`
- All dates must be valid `YYYY-MM-DD` format
- `Target Weekly TSS` must be > 0
- Session Status must be one of: `pending`, `completed`, `skipped`, `modified`
- PMC values: CTL and ATL must be ≥ 0; TSB can be negative
- ZWO filenames follow pattern: `week{N}_{day}_{type}.zwo` (lowercase, underscores)
