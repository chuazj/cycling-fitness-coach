# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code skill** (not a standalone application). It provides cycling coaching capabilities: intervals.icu workout analysis via API, training feedback, Zwift workout (.zwo) file generation, multi-week periodized training plans with PMC tracking, and weekly adaptive reviews. The skill entry point is `SKILL.md`.

**Repo layout**: Git working copy lives under `~/OneDrive/code/claude_skill/Cycling/cycling-fitness-coach/` (origin: `github.com/chuazj/cycling-fitness-coach`). Claude loads the skill from `~/.claude/skills/cycling-fitness-coach/` — keep the two in sync (working copy → install path).

## Running Scripts

**Dependency:** `pip install requests`

### Activity Analysis (intervals.icu)
```bash
# Credentials auto-loaded from .env (INTERVALS_ICU_ATHLETE_ID, INTERVALS_ICU_API_KEY)
python scripts/intervals_icu_api.py \
  --activity i126468486 \
  --ftp 200 --weight 70

# With intervals.icu URL
python scripts/intervals_icu_api.py \
  --activity https://intervals.icu/activities/i126468486 \
  --ftp 200

# Auto-fetch FTP/weight from athlete profile
python scripts/intervals_icu_api.py \
  --activity i126468486 --use-athlete-profile

# List recent activities
python scripts/intervals_icu_api.py --list-recent 10

# Fetch most recent activity
python scripts/intervals_icu_api.py --latest --use-athlete-profile -o output.json

# Output to file
python scripts/intervals_icu_api.py --activity i126468486 -o output.json
```
Output is JSON to stdout (use `-o file.json` to save).

### Zwift Workout Generation
```bash
python scripts/generate_zwo.py --json workout_def.json --output workout.zwo --ftp 200
```

### PMC Calculator (Performance Management Chart)
```bash
# Bootstrap: pull 90-day history, compute current CTL/ATL/TSB + peak powers
python scripts/pmc_calculator.py --bootstrap --days 90

# Weekly update: compare planned vs actual for a training week
python scripts/pmc_calculator.py --weekly-update \
  --week 1 --plan-start 2026-03-31 \
  --prev-ctl 30.7 --prev-atl 31.6 \
  --planned-tss '{"Mon":72,"Wed":75,"Fri":68,"Sat":68,"Sun":55}'
```

### Batch Zwift Workout Generation
```bash
# Generate all .zwo files for a week from JSON array.
# --output-dir must be the user's Zwift custom workouts folder (see SKILL.md → Zwift Workout Directory),
# NOT a repo path. Substitute <ZWIFT_WORKOUTS_DIR> with the platform-specific path:
#   Windows:       %LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\
#   macOS/Linux:   ~/Documents/Zwift/Workouts/<athlete_id>/
python scripts/batch_generate_zwo.py --input week_workouts.json --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp 200
```

### Weekly Training Summary
```bash
# Aggregate last 7 days: total TSS, zone distribution, power profile, auto-FTP detection
python scripts/intervals_icu_api.py --weekly-summary -o output.json
```

### Wellness / Readiness Summary
```bash
# Aggregate last 14 days of wellness records: RHR, HRV, sleep, fatigue/soreness/stress
# Computes baseline and flags deviations against Yellow/Red Flag rules in training_zones.md
python scripts/intervals_icu_api.py --wellness 14 -o wellness.json
```
Returns `error` field if athlete doesn't log wellness in intervals.icu (or no wearable sync). Used by the Mid-Week Check-In and Weekly Review workflows.

### Sparkline (Peak Power Trends visualization)
```bash
# Render a single duration's trend
python scripts/sparkline.py --label "20min" --series "195,198,201,200,205" --unit W
# -> 20min: ▁▃▅▅█  195→205W (+5.1%, +10W over 5 points)

# Use empty entry for missing-week gap
python scripts/sparkline.py --label "1min" --series "310,,315,320,318" --unit W
# -> 1min: ▁ ▅█▇  310→318W (+2.6%, +8W over 4 points)
```
Pure-Python ASCII sparkline (no matplotlib). Used by the Weekly Review workflow to refresh the sparkline subblock under `## Peak Power Trends` in `plans/active_plan.md`. For programmatic use, import `render_sparkline()` or `render_peak_power_trends_block()` from `scripts/sparkline.py`.

### RPE Trend Aggregator
```bash
# Scan Obsidian workout reviews and detect rising-RPE-at-constant-IF (overreaching signal)
python scripts/rpe_trend.py --vault-path "<CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews" --weeks 2 -o rpe_trend.json
```
Reads YAML frontmatter from each `.md`, extracts `(date, session_type, if, rpe)`, compares last `--weeks` weeks to the prior `--weeks` weeks per session type. Flags `rising_rpe_at_constant_if` when ΔRPE ≥ 1.0 with ΔIF within ±0.03. Used by the Weekly Review workflow. Returns `error` field if no usable reviews found (silent skip in workflow).

No build or lint infrastructure exists. Tests: `python -m unittest discover tests -v`

## Architecture

```
SKILL.md                        ← Skill router: triggers, coaching rules, workflow dispatch table
workflows/
  analyze.md                    ← Activity Analysis + Weekly Training Summary
  plan.md                       ← Create Plan + Weekly Review
  generate.md                   ← ZWO Generation
  advise.md                     ← Training Advice + Mid-Week Check-In + Race Peaking
scripts/
  intervals_icu_api.py          ← intervals.icu API client + metrics computation (NP, IF, TSS, zones, peaks, cardiac drift)
  generate_zwo.py               ← Zwift .zwo XML generator using dataclasses for interval types
  pmc_calculator.py             ← PMC bootstrap (90-day history) + weekly update (planned vs actual, CTL/ATL/TSB, peaks)
  batch_generate_zwo.py         ← Batch .zwo generation from JSON array (full week of workouts)
  sparkline.py                  ← Pure-Python ASCII sparkline helper for Peak Power Trends visualization
  rpe_trend.py                  ← RPE trend aggregator (Obsidian frontmatter scan + functional-overreaching detection)
references/
  training_zones.md             ← Power/HR zone definitions, TID model, weekly structure
  workout_analysis.md           ← Analysis framework, coaching response templates, ERG mode guidance
  zwo_format.md                 ← Zwift XML element spec and examples (local subset; canonical ref: h4l/zwift-workout-file-reference)
  intervals_icu_api.md          ← intervals.icu API endpoints, auth, data models
  periodization.md              ← Block templates, TSS distribution, progressive overload, adaptation decision trees, durability
  fueling.md                    ← Pre/during/post-ride nutrition, carb targets, gut training, GI troubleshooting
  plan_state_schema.md          ← Structure spec for plans/active_plan.md
  obsidian_templates.md         ← Frontmatter templates for workout reviews, plans, weekly reviews
plans/
  active_plan.md                ← Active training plan state (generated by Create Plan workflow, not pre-existing)
  block_history.md              ← Archive of completed blocks (athlete-specific; created on first block rollover)
tests/
  test_pure_functions.py        ← Offline unit tests for pure functions (no API calls)
  test_with_mocks.py            ← Tests with mocked HTTP responses
  test_cli.py                   ← CLI argument parsing tests
  test_pmc_integration.py       ← PMC bootstrap/weekly with mocked API
  fixtures/                     ← Mock API responses (activity.json, intervals.json, power_curve.json)
evals/
  evals.json                    ← Skill evaluation definitions
  trigger_eval.json             ← Workflow trigger matching tests
assets/
  template_sweetspot.zwo        ← Example Zwift workout XML
.env                            ← intervals.icu credentials (not committed)
```

**Data flows:**
- **Activity analysis:** intervals.icu link → `intervals_icu_api.py` extracts ID, authenticates via API key, fetches activity/intervals/streams/power-curve, computes metrics → JSON output → Claude provides coaching analysis using reference docs.
- **Plan creation:** `pmc_calculator.py --bootstrap` → PMC baseline → Claude designs block using `periodization.md` rules → writes `plans/active_plan.md` → `batch_generate_zwo.py` generates week's .zwo files.
- **Weekly review:** `pmc_calculator.py --weekly-update` → planned vs actual comparison → Claude applies adaptation decision trees → updates `plans/active_plan.md` → generates next week's .zwo files.

## Key Conventions

### Rules (must follow when generating code/files)

- **Power values in .zwo files**: Decimal fractions of FTP (e.g., `0.88` = 88% FTP), not watts; valid range `0.0–2.0`
- **Warmup/Cooldown direction**: Warmup must ramp up (`power_low <= power_high`); Cooldown must ramp down (`power_low >= power_high`) — enforced by `__post_init__` validation
- **Cooldown power naming**: `power_low` is the *start* (higher) value, `power_high` is the *end* (lower) value — matches Zwift XML attribute names, not magnitudes. Opposite semantic to Warmup where naming matches both.
- **Duration**: Always in seconds
- **Zwift XML**: Use `<name>` tags (not `<n>`); set `ftptest="1"` on `<workout>` for FTP test workouts; use `show_avg="1"` on `<FreeRide>` to display running average power on HUD (essential for FTP tests)
- **ZWO tag reference**: See `SKILL.md` → Reference Files → `zwo_format.md` for the canonical external tag-reference URL; consult it for definitive attribute/element specs when generating .zwo files
- **ZWO file encoding**: Always write with `encoding="utf-8"` — Windows defaults to cp1252
- **Script stdout encoding**: Do NOT use `.encode("ascii", "replace").decode()` workarounds; they destroy Unicode data
- **intervals.icu auth**: HTTP Basic Auth; credentials in `.env`, never committed (see SKILL.md for setup)
- **intervals.icu null handling**: API returns `None` for missing values, not absent keys. Use `a.get("field") or 0` only for fields where 0 is equivalent to missing (e.g., `moving_time`, `distance`, `elapsed_time`, `elevation_gain`). Use `x is not None` checks for fields where 0 is a valid distinct value (e.g., IF, TSS, average_watts, average_heartrate, icu_joules)
- **Metrics hierarchy**: NP → IF → TSS (each derived from the previous); prefer intervals.icu pre-computed values, fall back to stream computation
- **Canonical references**: Zone boundaries in `references/training_zones.md`, PMC formulas in `pmc_calculator.py`, block templates in `references/periodization.md` — do not duplicate these values elsewhere
- **Plan state**: `plans/active_plan.md` is the single source of truth for active training plans; structure documented in `references/plan_state_schema.md`
- **Adaptation requires approval**: Claude proposes adaptations based on decision trees in `references/periodization.md`, but waits for user confirmation before modifying the plan
- **Batch ZWO input**: JSON array where each item extends the `workout_from_dict()` schema with a `filename` field
- **ZWO output directory**: Generated .zwo files go to the Zwift custom workouts folder (see SKILL.md → Zwift Workout Directory for path), NOT to `plans/workouts/` in the repo
- **Obsidian vault**: See SKILL.md → Obsidian Integration for canonical paths and folder structure
- **Batch dry-run**: `batch_generate_zwo.py --dry-run` validates and computes stats without writing files
- **FTP/weight bounds**: All scripts validate FTP (50-500W) and weight (30-200kg) — rejects nonsensical values
- **Athlete profile source of truth**: `plans/active_plan.md` → Athlete Profile section holds the current FTP + weight. For one-off script runs, prefer `--use-athlete-profile` (auto-fetches from intervals.icu) over hard-coded `--ftp`/`--weight` flags so values don't drift

### Context (background for debugging/understanding)

- **`data_completeness` field**: `analyze()` output includes `data_completeness` ("complete" or "partial (missing: streams, ...)"). If not "complete", lead coaching analysis with a data quality warning.
- **Stream validation**: `zone_percent`, `zone_seconds`, and `cardiac_drift` are explicitly `None` (not absent) when power/HR streams are too short (fewer than 30 samples). Distinguishes "unavailable" from "no zones used".
- **`--compact` flag**: `intervals_icu_api.py --compact` omits rarely-used fields (VI, EF, zone_seconds, per-interval distance/max_watts/intensity) for token-efficient coaching output
- **`training_day_pattern`**: `pmc_calculator.py --bootstrap` output includes `training_day_pattern` (e.g., `["Tue", "Thu", "Sat"]`) — auto-detected from activity history day-of-week frequency. Use to pre-fill training days in the Create Plan workflow Step 2 instead of asking the athlete.
- **weekly_summary top-3 optimization**: `weekly_summary()` fetches power curves only from the top-3 TSS activities (not all N), reducing API calls significantly for athletes with many weekly rides
- **FTP test detection**: `detect_ftp_test()` returns `detection_methods` (list), not a single string — multiple detection heuristics can match simultaneously. Formula fields are per-method: `estimated_ftp_formula_20min` and `estimated_ftp_formula_ramp` (not a shared `estimated_ftp_formula`)
- **FTP test bounds**: 20-min heuristic triggers only when 80–150% of reference FTP (rejects anomalous data)
- **Indoor/outdoor context**: Derived from `detect_indoor(trainer, sport_type)` — `bool(trainer) or sport_type in ("VirtualRide", "VirtualRun")`. intervals.icu may return `trainer: null` for Zwift activities — `sport_type` fallback handles this.
- **Power profile categories**: Coggan-based W/kg thresholds at 5s, 1min, 5min, 20min. Used by `analyze_power_profile()` to classify rider type (sprinter, time_trialist, pursuiter, all_rounder) and identify strengths/weaknesses.
- **RPE collection**: Session RPE (1-10) collected after workout analysis; compared against IF for mismatch detection (fatigue signal, FTP underestimate). Stored in Obsidian frontmatter as `rpe`. RPE:Power mismatch analysis is noted in body text, not frontmatter.
