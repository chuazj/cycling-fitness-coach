# Workflow: Zwift Workout Generation

Covers Workflow 3 (single and batch ZWO file generation).

---

## 3. Zwift Workout Generation

When user requests a workout file ("build a workout", "create a ZWO", workout generation request):

**Step 1:** Gather requirements — clarify before generating:
- Workout type (sweet spot, threshold, VO2max, over-unders, endurance, recovery, FTP test)
- Duration constraint (total session time)
- Current FTP (check CLAUDE.md or ask)
- Specific targets if any (e.g., "3x10min at 95%")

**Step 2:** Design the workout structure:
- **Warm-up**: 10-15 min progressive ramp (45-50% → 75% FTP), include 1-2min opener at FTP for threshold+ sessions
- **Main set**: Intervals matched to workout type and athlete's current block progression
- **Cool-down**: 5-10 min ramp down (60% → 35% FTP)
- Reference `references/training_zones.md` for zone boundaries and cadence targets
- Reference `references/periodization.md` for progression context if part of a training block

**Step 3:** Generate the .zwo file using one of:

**Option A — Script (preferred for complex workouts):**
```bash
python scripts/generate_zwo.py --json workout_def.json --output workout.zwo --ftp 200
```

**Option B — Batch generation (full week):**
```bash
# --output-dir must be the user's Zwift custom workouts folder (see SKILL.md → Zwift Workout Directory), NOT a repo path.
python scripts/batch_generate_zwo.py --input week_workouts.json --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp 200
# Dry run first to validate (safe to use any path — does not write files):
python scripts/batch_generate_zwo.py --input week_workouts.json --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp 200 --dry-run
```

**Option C — Direct XML (simple workouts):**
Write XML directly using the templates and tag spec in `references/zwo_format.md` and the example file `assets/template_sweetspot.zwo`.

**Step 4:** Validate before saving:

| Check | Rule | Reference |
|-------|------|-----------|
| Power range | All values 0.0-2.0 (FTP fractions) | `generate_zwo.py._validate_power()` |
| Warmup direction | `power_low` ≤ `power_high` (ramps up) | CLAUDE.md conventions |
| Cooldown direction | `power_low` ≥ `power_high` (ramps down) | CLAUDE.md conventions |
| Duration | All durations in seconds, > 0 | — |
| Cadence | Match workout type targets | `references/training_zones.md` |
| Text events | 3-5 per workout (interval starts, cadence, motivation, form) | Project CLAUDE.md |
| Encoding | UTF-8 (not Windows cp1252) | CLAUDE.md conventions |
| FTP test | Set `ftptest="1"` on `<workout>` element + `show_avg="1"` on FreeRide | `references/zwo_format.md` |
| Tag reference | Consult h4l/zwift-workout-file-reference for attribute validation | CLAUDE.md conventions |

**Step 5:** Save and report:
- Save to the user's Zwift custom workouts folder — see SKILL.md → Zwift Workout Directory for the platform-specific path (`%LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\` on Windows, `~/Documents/Zwift/Workouts/<athlete_id>/` on macOS/Linux). Confirm the path with the user before writing.
- Use naming convention: `W[week]_D[day]_[Type]_[Detail].zwo`
- Remind user to restart Zwift if it's running (Zwift doesn't hot-reload .zwo files)

**Output template:**

```
## Workout: [Name]
**Duration**: Xmin | **Est. TSS**: X | **Target IF**: X.XX
**Structure**:
- Warmup: [duration, ramp range]
- Main Set: [intervals x duration @ intensity]
- Cooldown: [duration, ramp range]
**Execution Notes**: [Cadence targets, pacing tips, what to focus on]
**File**: [path to generated .zwo]
```

### Error Handling

- **Power out of range**: `_validate_power()` raises ValueError for values outside 0.0-2.0. Fix the input value.
- **Warmup/Cooldown direction wrong**: `__post_init__` validation catches this. Swap power_low/power_high.
- **Missing cadence**: Optional but recommended — add `Cadence`, `CadenceLow`/`CadenceHigh`, or `CadenceResting` attributes.
- **XML encoding issues**: Always use `encoding="utf-8"` when writing. Windows defaults to cp1252 which breaks special characters.
- **Zwift not showing workout**: Restart Zwift after adding .zwo files. Check file is in correct Workouts subfolder.

### Batch Generation Notes

- Input JSON format: array of workout dicts, each with `filename` field + standard interval schema
- Always `--dry-run` first to validate and preview stats
- Output includes per-workout TSS, duration, and IF estimates
- See `scripts/batch_generate_zwo.py` for full input schema
