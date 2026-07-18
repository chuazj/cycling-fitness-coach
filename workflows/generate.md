# Workflow: Zwift Workout Generation

Covers single and batch ZWO file generation. The SKILL.md → Workflow Dispatch table is the authoritative router.

**Validation gate (abbreviated)** — Coaching Process Rule 1 applies in compact form for one-off workout generation: in Step 1, confirm the athlete's **FTP source** (intervals.icu profile vs explicit `--ftp`) and **zone confidence** (validated / stale / self-reported / unknown — see `references/training_zones.md`). If `self-reported` or `unknown`, flag the resulting `.zwo` power targets as **provisional** in the output template and recommend an FTP test before the next structured block (Rule 4). Full athlete-state assessment is not required for one-off generation — that lives in `workflows/plan.md` Step 2b.

---

## ZWO Generation

When user requests a workout file ("build a workout", "create a ZWO", workout generation request):

**Step 1:** Gather requirements — clarify before generating:
- Workout type (sweet spot, threshold, VO2max, over-unders, endurance, recovery, FTP test)
- Duration constraint (total session time)
- Current FTP (check `plans/active_plan.md` → Athlete Profile, or run with `--use-athlete-profile` to auto-fetch from intervals.icu)
- Specific targets if any (e.g., "3x10min at 95%")

**Step 2:** Design the workout structure:
- **Warm-up / Cool-down**: use the canonical structures in `references/block_templates.md` → Warmup and Cooldown Standards (Standard Warmup 10min: 40→65% ramp, 2min @75%, 75→95% ramp, 1min @50%; Standard Cooldown 5min: 55→35% ramp). Add a 1-2min opener at FTP for threshold+ sessions
- **Main set**: Intervals matched to workout type and athlete's current block progression
- **FTP test sessions**: the test effort itself MUST be a `<FreeRide>` segment with `show_avg="1"` — never `<SteadyState>`. In ERG mode a SteadyState block holds the rider at the *current* FTP, so there is nothing to test; FreeRide hands power control back to the rider. Set `ftptest="1"` on the `<workout>` element. See `references/zwo_format.md` → FTP Test Attribute.
- Reference `references/training_zones.md` for zone boundaries and cadence targets
- Reference `references/block_templates.md` for progression context if part of a training block
- **Flex-day workouts**: if generating a Flex or recovery session, check whether the block's ERG-variety slot is still open — a sim-mode or free-ride workout (no ERG) fills it and builds self-pacing skill. At least one per block (`references/block_templates.md` → FTP Builder block notes; registry: `references/rule_registry.md`).

**Step 3:** Generate the .zwo file using one of:

**Option A — Script (preferred for complex workouts):**
```bash
python scripts/generate_zwo.py --json workout_def.json --output workout.zwo --ftp 200
```

**Option B — Batch generation (full week):**
```bash
# --output-dir must be the user's Zwift custom workouts folder (see references/setup.md → Zwift Workout Directory), NOT a repo path.
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
| Text events | 3-5 per workout; each `timeoffset` < its interval's duration; reword ERG-inert "drop to X W" cues as "tap intensity down ~N%" | Project CLAUDE.md |
| IntervalsT cues | No `<textevent>` children inside `<IntervalsT>` — flatten to `<SteadyState>` pairs (`generate_zwo.py` raises ValueError) | `references/zwo_format.md` |
| Encoding | UTF-8 (not Windows cp1252) | CLAUDE.md conventions |
| FTP test | Test effort is a `<FreeRide>` (never `<SteadyState>` — ERG holds current FTP); `ftptest="1"` on `<workout>` + `show_avg="1"` on the FreeRide | `references/zwo_format.md` |
| Tag reference | Consult h4l/zwift-workout-file-reference for attribute validation | CLAUDE.md conventions |
| Recovery intervals | Between VO2max reps ≈ work duration @ 40-50% FTP; between SS/Threshold reps ~5min @ 50-55% FTP | `references/block_templates.md` → Warmup/Cooldown Standards |
| Lint pass | Run `zwo_lint.py` on the finished file — 0 errors required; review warnings | `scripts/zwo_lint.py` |

**Lint an existing or hand-edited `.zwo`:** `python scripts/zwo_lint.py <file.zwo> --ftp <athlete FTP>`. The linter catches the known anti-patterns (textevent-in-IntervalsT, offset past duration, ERG-inert power cues, FTP-test-as-SteadyState, ERG short reps) and reports the workout's NP-based modeled stats. A clean generated file should lint with 0 errors.

**Step 5:** Save and report:
- Save to the user's Zwift custom workouts folder — see `references/setup.md` → Zwift Workout Directory for the platform-specific path (`%LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\` on Windows, `~/Documents/Zwift/Workouts/<athlete_id>/` on macOS/Linux). Confirm the path with the user before writing.
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
- **IntervalsT with text events**: `generate_zwo.py` raises `ValueError` — `<textevent>` firing inside `<IntervalsT>` is unspecified. Flatten the interval to explicit `<SteadyState>` work+recovery pairs and cue those.
- **`--ftp` omitted**: the script warns and falls back to 200 W for the TSS estimate — re-run with the athlete's real FTP for accurate numbers.
- **Missing cadence**: Optional but recommended — add `Cadence`, `CadenceLow`/`CadenceHigh`, or `CadenceResting` attributes.
- **XML encoding issues**: Always use `encoding="utf-8"` when writing. Windows defaults to cp1252 which breaks special characters.
- **Zwift not showing workout**: Restart Zwift after adding .zwo files. Check file is in correct Workouts subfolder.
- **intervals.icu unreachable**: ZWO generation needs no API. If you were fetching the athlete's FTP from intervals.icu and it's down, pass `--ftp <watts>` explicitly (the script warns and falls back to 200 W otherwise). For activity-data outages see `workflows/analyze.md` → Error Handling.

### Batch Generation Notes

- Input JSON format: array of workout dicts, each with `filename` field + standard interval schema
- Always `--dry-run` first to validate and preview stats
- Output includes per-workout TSS, duration, and IF estimates
- See `scripts/batch_generate_zwo.py` for full input schema
