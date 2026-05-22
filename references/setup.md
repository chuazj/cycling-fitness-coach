# Setup — credentials, Obsidian vault, Zwift workout directory

Per-user setup that doesn't change per-session. **Read this once at the start of any session that needs to invoke a script or write notes.**

## Dependencies

**Required:** `requests` (`pip install requests`) — intervals.icu API client (`scripts/intervals_icu_api.py`). All other scripts are stdlib-only.

**Optional:** `fitparse` (`pip install fitparse`) — required only for `scripts/fit_ingest.py`, the `.fit`-file analysis fallback used when an activity has not synced to intervals.icu. All other scripts are stdlib-only except `requests` (for the intervals.icu API client).

---

## intervals.icu API Integration

This skill queries the intervals.icu API directly to fetch activity data, intervals, power streams, and power curves.

### Credentials

Stored in `.env` at project root (loaded automatically by the script):
```
INTERVALS_ICU_ATHLETE_ID=your_athlete_id
INTERVALS_ICU_API_KEY=your_key_here
```

API key is permanent — no token refresh needed. Get yours from https://intervals.icu/settings.

### URL Pattern

intervals.icu links: `https://intervals.icu/activities/i[numeric_id]` or `https://intervals.icu/activities/[numeric_id]`
Extract ID with: `intervals\.icu/activities/(i?\d+)` (also accepts plain numeric IDs like `17478304236`)

### Subjective Wellness Scale Convention

`wellness_summary()` flags elevated subjective fatigue/soreness/stress when the value is **≥4** on intervals.icu's default 1-4 scale (where 1=best, 4=worst). intervals.icu lets athletes flip the direction (4=best, 1=worst) in their wellness settings — if you have flipped it, the flags will not fire correctly (your "worst" 1 would never satisfy `≥4`). Either keep the default direction OR update `wellness_summary` thresholds locally to match your scale.

This convention does NOT affect Whoop-synced fields (Recovery, RHR, HRV, sleep, respiration, SpO2) which use Whoop's absolute bands regardless of user preference.

## Obsidian Integration

Workout analyses, training plans, and weekly reviews are saved to the Obsidian vault for persistent tracking.

> **Note on env vars below**: `CYCLING_VAULT_PATH` and `ZWIFT_WORKOUT_DIR` are Claude-facing conventions only — no script in `scripts/` reads them. Setting them in your shell has no effect on script behavior. They exist so Claude has a consistent place to pick up per-user paths without re-asking every session.

### Vault Location

Claude reads `CYCLING_VAULT_PATH` for your Obsidian vault subfolder for cycling notes (e.g., `<vault>/cycling-fitness-coach/`). If unset, Claude will prompt for the path before writing notes.

### Zwift Workout Directory

Generated `.zwo` files are written **directly to the user's Zwift custom workout folder** (NOT to `plans/workouts/` in the repo). Default locations:

- **Windows**: `%LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\`
- **macOS/Linux**: `~/Documents/Zwift/Workouts/<athlete_id>/`

Claude reads `ZWIFT_WORKOUT_DIR` as an override. Always confirm the target path with the user before writing — Zwift custom workout folder layout depends on the local install. After writing, mention the full path so the user can find them in Zwift's "Custom Workouts" list.

### Folder Structure

```
cycling-fitness-coach/
  workout-reviews/     ← Individual workout analyses
  training-plans/      ← Training plan summaries
  weekly-reviews/      ← Weekly review reports
```

### Writing Notes

Use the `Write` tool to create markdown files directly in the vault folder. Obsidian auto-detects changes. For frontmatter templates and CLI commands, see `references/obsidian_templates.md`.
