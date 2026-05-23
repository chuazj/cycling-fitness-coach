# Obsidian Templates & CLI Commands

Reference for writing cycling coaching notes to the Obsidian vault.

**Vault path**: Resolved per-user via `CYCLING_VAULT_PATH` (see `references/setup.md` → Obsidian Integration → Vault Location). Notes are written under `<CYCLING_VAULT_PATH>/cycling-fitness-coach/`. If unset, prompt the user for the vault subfolder before writing.

## File Naming Convention

Workout reviews use a **three-bucket category convention**: `YYYY-MM-DD <Category> - <Description>.md`. The `<Category>` slot is one of `Outdoor`, `AdHoc`, or **empty** (for structured block sessions, where the description begins with the structured marker like `W1 D1` or `RTN D2`). The ` - ` separator (space-dash-space) is always present.

| Type | Pattern | Example |
|------|---------|---------|
| Workout review — structured block | `YYYY-MM-DD - <W#D# or RTN D#> <Session Name>.md` | `2026-04-03 - W1 D3 Threshold 2x18.md` |
| Workout review — outdoor (unplanned) | `YYYY-MM-DD Outdoor - <Ride Name>.md` | `2026-05-23 Outdoor - WCH Thomson Mandai Group Ride.md` |
| Workout review — ad-hoc / maintenance | `YYYY-MM-DD AdHoc - <Session Name>.md` | `2026-05-21 AdHoc - Sweet Spot 2x20.md` |
| Training plan | `YYYY-MM-DD {Plan Name}.md` | `2026-03-31 Block 3 FTP Builder.md` |
| Weekly review | `YYYY-MM-DD Week {N} Review.md` | `2026-04-06 Week 1 Review.md` |

**Category-selection rules** (workout reviews):
- **Structured block** — empty category — when the activity belongs to an active block week (`W#D#`) or a return-to-training week (`RTN D#`). This applies even if the session happened outdoors (e.g., `2026-03-22 - W4 D1 Holland x Mandai.md` — planned outdoor block session).
- **Outdoor** — when the ride is outdoor **and** not part of a structured block (free ride, group ride, social ride). Maintenance-dose outdoor rides also use `Outdoor`, not `AdHoc`.
- **AdHoc** — when the ride is an indoor/trainer maintenance session outside a structured block (Block paused → ad-hoc weekly quality + Z2 days).

## Frontmatter Templates

### Workout Reviews

```yaml
---
date: "YYYY-MM-DD"
type: workout-review
session: "Session Name"
session_type: sweet-spot|threshold|vo2max|over-under|endurance|recovery|ftp-test
tss: X
if: X.XX
rating: pass|warn|fail
rpe: null            # Session RPE on a 1-10 scale (Borg CR-10), filled in after the ride
whoop_recovery: X    # WHOOP recovery score 0-100 (pre-ride snapshot from intervals.icu wellness)
whoop_sleep_h: X.X   # Hours slept previous night (sleepSecs / 3600)
whoop_hrv: X         # WHOOP HRV in ms, pre-ride snapshot
tags:
  - cycling
  - workout-review
  - {session_type}
  - indoor|outdoor
---
```

**Always quote the `date` field** (e.g., `"2026-05-09"`). YAML parses bare numeric-looking dates as integers, which `scripts/rpe_trend.py` will skip with a stderr warning. Quoting forces string parsing and avoids silent data loss in trend reports.

**WHOOP fields are mandatory when WHOOP data is available** — they enable cross-session "response given recovery state" trending (e.g., "how do I respond to Threshold on yellow days?"). Set to `null` only when WHOOP data is genuinely unavailable for that day.

Keep the rest of the frontmatter lean — only fields used for filtering/sorting/trending across notes. Detailed metrics (NP, VI, HR, cadence, peaks, distance, duration, block/week/day) belong in the body text.

### Training Plans

```yaml
---
date: YYYY-MM-DD
type: training-plan
plan: "Plan Name"
duration: "N weeks"
start: YYYY-MM-DD
end: YYYY-MM-DD
ftp: 200
tags:
  - cycling
  - training-plan
---
```

### Weekly Reviews

```yaml
---
date: YYYY-MM-DD
type: weekly-review
week: N
phase: "Phase Name"
planned_tss: X
actual_tss: X
completion: X%
tags:
  - cycling
  - weekly-review
---
```

## CLI Commands

Open a note in Obsidian:
```bash
obsidian open path="cycling-fitness-coach/workout-reviews/FILENAME.md"
```

Search existing notes:
```bash
obsidian search query="W3 D1" path="cycling-fitness-coach"
```

Read a note:
```bash
obsidian read path="cycling-fitness-coach/workout-reviews/FILENAME.md"
```
