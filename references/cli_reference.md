# CLI Reference — Canonical Script Invocations

Command examples for every script in the skill. Workflows generally embed the specific invocation they need; consult this file when adding or modifying a CLI surface, or when looking up flag/output details outside a workflow context.

**Dependencies:** `pip install requests` (core). The `.fit` ingest parse layer (`scripts/fit_ingest.py`) additionally needs `pip install fitparse`.

**Tests:** `python -m unittest discover tests -v` (666 tests across 8 files, runs in ~0.1s — run before AND after any script change).

## Activity Analysis (intervals.icu)
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
Output is JSON to stdout (use `-o file.json` to save). Add `--compact` to omit rarely-used fields (variability index, efficiency factor, zone seconds, and per-lap distance/max_watts/intensity) for token-efficient output — available on `--activity`/`--latest`.

## Local .fit File Analysis (intervals.icu fallback)
```bash
# Analyze a ride that exists only on Strava/Garmin/Zwift and never synced to intervals.icu.
# Emits the same analysis JSON as --activity (source: "fit_file"). Needs: pip install fitparse
python scripts/fit_ingest.py --file ride.fit --ftp 200 --weight 70 -o output.json
```

## Zwift Workout Generation
```bash
python scripts/generate_zwo.py --json workout_def.json --output workout.zwo --ftp 200
```

## ZWO Linting
```bash
# Validate a .zwo against the canonical element reference + project hygiene rules.
# Exit 0 = clean, 1 = warnings, 2 = errors. Reports NP-based modeled stats.
python scripts/zwo_lint.py workout.zwo --ftp 200
```

## PMC Calculator (Performance Management Chart)
```bash
# Bootstrap: pull 90-day history, compute current CTL/ATL/TSB + peak powers
python scripts/pmc_calculator.py --bootstrap --days 90

# Weekly update: compare planned vs actual for a training week
python scripts/pmc_calculator.py --weekly-update \
  --week 1 --plan-start 2026-03-31 \
  --prev-ctl 30.7 --prev-atl 31.6 \
  --planned-tss '{"Mon":72,"Wed":75,"Fri":68,"Sat":68,"Sun":55}'
```

## Batch Zwift Workout Generation
```bash
# Generate all .zwo files for a week from JSON array.
# --output-dir must be the user's Zwift custom workouts folder (see references/setup.md → Zwift Workout Directory),
# NOT a repo path. Substitute <ZWIFT_WORKOUTS_DIR> with the platform-specific path:
#   Windows:       %LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\
#   macOS/Linux:   ~/Documents/Zwift/Workouts/<athlete_id>/
python scripts/batch_generate_zwo.py --input week_workouts.json --output-dir "<ZWIFT_WORKOUTS_DIR>/week1/" --ftp 200
```

## Weekly Training Summary
```bash
# Aggregate last 7 days: total TSS, zone distribution, power profile, auto-FTP detection
python scripts/intervals_icu_api.py --weekly-summary -o output.json
```

## Wellness / Readiness Summary
```bash
# Aggregate last 14 days of wellness records: RHR, HRV, sleep, fatigue/soreness/stress
# Computes baseline and flags deviations against Yellow/Red Flag rules in training_zones.md
python scripts/intervals_icu_api.py --wellness 14 -o wellness.json
```
Returns `error` field if athlete doesn't log wellness in intervals.icu (or no wearable sync). Used by the Weekly Review workflow (needs daily array for trend).

## Readiness Check (pre-ride verdict)
```bash
# Single GREEN / YELLOW-HIGH / YELLOW-LOW / RED verdict + session-type ceiling
# Wraps wellness_summary, adds sleep-score tiebreaker, recovery slope, baseline-maturity guard
python scripts/intervals_icu_api.py --readiness-check -o readiness.json
```
Used by the Mid-Week Check-In workflow. Deviation flags (RHR/HRV/respiration) auto-suppressed when sample size <7 to avoid noise. See `references/training_zones.md` → Fatigue Indicators for thresholds.

### Signal-mode contract (canonical)

`--readiness-check` classifies the available signals into a mode and adapts the verdict; `signal_mode` is on both `--readiness-check` and `--wellness` output:

| Mode | Available signals | Verdict bands | Banner |
|---|---|---|---|
| `full` | WHOOP Recovery present | GREEN / YELLOW-HIGH / YELLOW-LOW / RED | none |
| `reduced` | HRV and/or RHR, no Recovery | GREEN / YELLOW-LOW / RED | reduced-signal |
| `minimal` | sleep / subjective only | GREEN / YELLOW-LOW / RED | minimal-signal |
| `insufficient` | nothing usable | INSUFFICIENT-DATA | — |

A non-WHOOP athlete still gets a valid verdict — `reduced` mode green-lights all session types on a clean HRV + RHR + sleep day, with an explicit reduced-signal banner in the output. There is no YELLOW-HIGH band outside `full` mode (it is a WHOOP-Recovery subdivision). Subjective-override tiebreakers (Mid-Week Check-In) apply in `full` mode only — `reduced`/`minimal` have no YELLOW-HIGH band to subdivide.

## Sparkline (Peak Power Trends visualization)
```bash
# Render a single duration's trend
python scripts/sparkline.py --label "20min" --series "195,198,201,200,205" --unit W
# -> 20min: ▁▃▅▅█  195→205W (+5.1%, +10W over 5 points)

# Use empty entry for missing-week gap
python scripts/sparkline.py --label "1min" --series "310,,315,320,318" --unit W
# -> 1min: ▁ ▅█▇  310→318W (+2.6%, +8W over 4 points)
```
Pure-Python ASCII sparkline (no matplotlib). Used by the Weekly Review workflow to refresh the sparkline subblock under `## Peak Power Trends` in `plans/active_plan.md`. For programmatic use, import `render_sparkline()` or `render_peak_power_trends_block()` from `scripts/sparkline.py`.

## RPE Trend Aggregator
```bash
# Scan Obsidian workout reviews and detect rising-RPE-at-constant-IF (overreaching signal)
python scripts/rpe_trend.py --vault-path "<CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews" --weeks 2 -o rpe_trend.json
```

## Prediction Tracker (W5 validation loop)
```bash
# Seed the athlete forecasting model from existing Obsidian reviews (one-time)
python scripts/prediction_tracker.py --mode seed-baseline --vault-path "<CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews"
# Log a forecast (per hard session / per block)
python scripts/prediction_tracker.py --mode predict --type rpe_at_if --if 0.84 --slot morning --session-date 2026-06-02 --session-type Threshold
# Reconcile open predictions against actuals; emits recalibration flags
python scripts/prediction_tracker.py --mode reconcile --vault-path "<CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews" -o prediction_report.json
```
Ledger (`plans/prediction_ledger.jsonl`) and athlete model (`plans/athlete_calibration.md`) are gitignored PII.
Reads YAML frontmatter from each `.md`, extracts `(date, session_type, if, rpe)`, compares last `--weeks` weeks to the prior `--weeks` weeks per session type. Flags `rising_rpe_at_constant_if` when ΔRPE ≥ 1.0 with ΔIF within ±0.03. Used by the Weekly Review workflow. Returns `error` field if no usable reviews found (silent skip in workflow).
