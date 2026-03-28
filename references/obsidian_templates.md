# Obsidian Templates & CLI Commands

Reference for writing cycling coaching notes to the Obsidian vault.

## Frontmatter Templates

### Workout Reviews

```yaml
---
date: YYYY-MM-DD
type: workout-review
week: N
day: N
session: "Session Name"
ftp: 192
np: X
if: X.XX
tss: X
rating: pass|warn|fail
rpe: null
rpe_match: null
tags:
  - cycling
  - workout-review
---
```

### Training Plans

```yaml
---
date: YYYY-MM-DD
type: training-plan
plan: "Plan Name"
duration: "N weeks"
start: YYYY-MM-DD
end: YYYY-MM-DD
ftp: 192
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
