# Obsidian Templates & CLI Commands

Reference for writing cycling coaching notes to the Obsidian vault.

**Vault path**: Resolved per-user via `CYCLING_VAULT_PATH` (see SKILL.md → Obsidian Integration → Vault Location). Notes are written under `<CYCLING_VAULT_PATH>/cycling-fitness-coach/`. If unset, prompt the user for the vault subfolder before writing.

## File Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Workout review | `YYYY-MM-DD {Activity Name}.md` | `2026-04-03 W1 D3 Threshold 2x18.md` |
| Training plan | `YYYY-MM-DD {Plan Name}.md` | `2026-03-31 Block 3 FTP Builder.md` |
| Weekly review | `YYYY-MM-DD Week {N} Review.md` | `2026-04-06 Week 1 Review.md` |

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
rpe: null   # Session RPE on a 1-10 scale (Borg CR-10), filled in after the ride
tags:
  - cycling
  - workout-review
  - {session_type}
  - indoor|outdoor
---
```

**Always quote the `date` field** (e.g., `"2026-05-09"`). YAML parses bare numeric-looking dates as integers, which `scripts/rpe_trend.py` will skip with a stderr warning. Quoting forces string parsing and avoids silent data loss in trend reports.

Keep frontmatter lean — only fields used for filtering/sorting/trending across notes. Detailed metrics (NP, VI, HR, cadence, peaks, distance, duration, block/week/day) belong in the body text.

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
