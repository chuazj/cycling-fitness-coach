# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code skill** (not a standalone application). It provides cycling coaching capabilities: intervals.icu workout analysis via API, training feedback, Zwift workout (.zwo) file generation, multi-week periodized training plans with PMC tracking, and weekly adaptive reviews. The skill entry point is `SKILL.md`.

**Repo layout**: Git working copy lives under `~/OneDrive/code/claude_skill/Cycling/cycling-fitness-coach/` (origin: `github.com/chuazj/cycling-fitness-coach`). Claude loads the skill from `~/.claude/skills/cycling-fitness-coach/` — keep in sync after every commit:
`cd ~/.claude/skills/cycling-fitness-coach && git fetch ~/OneDrive/code/claude_skill/Cycling/cycling-fitness-coach master && git merge --ff-only FETCH_HEAD`. Never edit install path directly — manual file copies leave its git in a "dirty content matches a working-copy commit" state that requires `git stash` before the next clean merge.

## Reading guide for this file

- **Running a script** → `references/cli_reference.md` (canonical CLI invocations for every script).
- **Modifying wellness/readiness/FTP-detection/analysis internals** → **read `references/internals.md` first.** It documents the schema invariants and signal-mode behaviour the Rules below assume.
- **Coaching content (block templates, weekly adaptation, etc.)** → SKILL.md's Reference Files table is the authoritative router.

## Committing

- **Git identity is not configured globally.** Plain `git commit` fails with `Author identity unknown`. Use env vars per command:
  ```bash
  GIT_AUTHOR_NAME='chuazj' GIT_AUTHOR_EMAIL='zijian@hotmail.sg' \
  GIT_COMMITTER_NAME='chuazj' GIT_COMMITTER_EMAIL='zijian@hotmail.sg' \
  git commit -m "..."
  ```
  Do **NOT** run `git config --global user.*` to "fix" this — the unset state is intentional (per `~/.claude/CLAUDE.md` Git Safety Protocol).
- **Push auth uses `gh` (HTTPS via stored token).** SSH is not configured (no GitHub-registered key). If `gh auth status` shows logged-out, the user must run `gh auth login` themselves — that flow is interactive.

## Wellness signal changes

- **Test fixtures exclude today from baseline**: `wellness_summary()` uses `history = daily[:-1]`. To test an N-day baseline rule (CV-trend needs 14d, RHR/HRV band-check/respiration need 7d), provide **N+1 daily records** — sending N gives only N-1 history days and the rule silently won't fire.
- **Signal-change sync list** (when adding/modifying a wellness rule, all 5 must update): code (`scripts/intervals_icu/wellness.py`, verdict layer in `readiness.py`) → tests (`tests/test_with_mocks.py`, `tests/test_internal_helpers.py`) → Fatigue Indicators (`references/training_zones.md`) → shared readiness template (`references/readiness_template.md` — single source for both workflows) → Gating? table (`workflows/advise.md` → Readiness signals table). Skip any → doc/code drift.

## Eval harness limitations (skill-creator/run_eval.py)

The `skill-creator` plugin's `run_eval.py` cannot reliably validate description changes for *this* skill once installed. Two failure modes:

1. **Real-skill shadowing**: with `~/.claude/skills/cycling-fitness-coach/` in place, the harness's slash-command shim loses routing to the real skill — Claude invokes the real skill name (not the shim's UUID name), so every positive scores `triggered=False`. Workaround: `mv ~/.claude/skills/cycling-fitness-coach{,.disabled-by-eval}` before the run (always wrap in a `trap` to restore on exit).
2. **First-tool-must-be-Skill/Read**: even with the install path isolated, the harness counts any first-tool-call other than `Skill`/`Read` as no-trigger. Substantive queries like "build me a training plan" route through `superpowers:brainstorming` first, which fails the check. Baseline scored 0/10 positives even on a clean description.

Implication: for description changes, **ship on writing-skills rubric grounds** rather than blocking on an eval GREEN bar. Iron-Law discipline ("RED test before edit") only applies when the eval is a viable measurement instrument — for installed user-level skills, it isn't. Full trace: commits `86dacdd` (F3 probe) → `8a90a81` (F1+F2+F3 description rewrite) → `8e539d5` (F4 frontmatter cleanup) on master.

## Architecture

```
SKILL.md                        ← Skill router: triggers, coaching rules, workflow dispatch table
workflows/
  analyze.md                    ← Activity Analysis + Weekly Training Summary
  plan.md                       ← Create Plan + Weekly Review
  generate.md                   ← ZWO Generation
  advise.md                     ← Training Advice + Mid-Week Check-In + Race Peaking
scripts/
  intervals_icu_api.py          ← Thin re-export façade + CLI entry point (preserves the `from intervals_icu_api import …` surface)
  intervals_icu/                ← intervals.icu API client package (split from the former monolith in the W1 refactor)
    api_client.py               ← HTTP client, auth, .env loading
    metrics.py                  ← Pure metric computation (NP, IF, TSS, zones, peaks, cardiac drift, power profile)
    activity.py                 ← Single-activity analysis + weekly training summary
    wellness.py                 ← WHOOP wellness fields, baselines, Yellow/Red flag detection
    readiness.py                ← Pre-ride readiness verdict engine
    cli.py                      ← argparse definition + mode dispatch
  fit_ingest.py                 ← Local .fit file analysis — intervals.icu fallback (same analysis JSON; needs fitparse)
  generate_zwo.py               ← Zwift .zwo XML generator using dataclasses for interval types
  pmc_calculator.py             ← PMC bootstrap (90-day history) + weekly update (planned vs actual, CTL/ATL/TSB, peaks)
  batch_generate_zwo.py         ← Batch .zwo generation from JSON array (full week of workouts)
  zwo_lint.py                   ← ZWO linter — validates .zwo vs canonical element reference + hygiene rules (exit 0/1/2)
  sparkline.py                  ← Pure-Python ASCII sparkline helper for Peak Power Trends visualization
  rpe_trend.py                  ← RPE trend aggregator (Obsidian frontmatter scan + functional-overreaching detection)
  prediction_tracker.py         ← W5 validation loop: predict/reconcile/seed forecasts, recalibration triggers
references/
  cli_reference.md              ← Canonical CLI invocations for every script
  internals.md                  ← Implementation notes — read before modifying wellness/FTP-detection/analysis code
  training_zones.md             ← Power/HR zone definitions, TID model, weekly structure
  workout_analysis.md           ← Analysis framework, coaching response templates, ERG mode guidance
  zwo_format.md                 ← Zwift XML element spec and examples (local subset; canonical ref: h4l/zwift-workout-file-reference)
  intervals_icu_api.md          ← intervals.icu API endpoints, auth, data models
  setup.md                      ← Credentials, Zwift workout directory, Obsidian vault paths & folder structure
  block_templates.md            ← Block templates, TSS distribution, progressive overload, warmup/cooldown, FTP test protocols, Block Selection Logic
  weekly_adaptation.md          ← Weekly adaptation decision trees (load, ACWR, TSB, RPE, HR, illness/injury, rule priority)
  race_taper.md                 ← Race / event peaking — 2-week and 1-week taper structures, TSB projection
  durability_strength.md        ← Concurrent strength training, heat adaptation overlay, durability concept
  fueling.md                    ← Pre/during/post-ride nutrition, carb targets, gut training, GI troubleshooting
  menstrual_cycle_training.md   ← Female-athlete coaching — cycle/contraceptive autoregulation, symptom tiers, RED-S red flag
  plan_state_schema.md          ← Structure spec for plans/active_plan.md
  obsidian_templates.md         ← Frontmatter templates for workout reviews, plans, weekly reviews
  readiness_template.md         ← Shared per-metric rendering for wellness/readiness blocks (used by advise.md + plan.md)
  adaptation_rules.md           ← Per-activity forward-cascade adaptation rules (signals → severity → next-session adjustments)
  prediction_calibration.md     ← W5 predict→measure→calibrate loop: models, ledger, recalibration triggers
  rule_registry.md              ← Orphan-prevention catalogue of standing coaching rules (W4)
governance/
  bibliography.md               ← Methodology authorities + auxiliary citations + currency log + evidence tiers
  audit_protocol.md             ← Quarterly audit cadence, scope, triggering mechanism, currently-queued actions
  artifacts.md                  ← Output artifact index — every file the skill writes, schema, gitignore status, emitter
audits/
  README.md                     ← Index + naming convention
  cycling-coach-*.md            ← Dated audit artifacts (writing-skills, methodology-currency, eval-suite-refresh, output-contract, refactor-proposal)
plans/
  active_plan.md                ← Active training plan state (generated by Create Plan workflow; gitignored — local-only)
  block_history.md              ← Archive of completed blocks (created on first block rollover; gitignored — local-only)
tests/
  test_pure_functions.py        ← Offline unit tests for pure functions (no API calls)
  test_with_mocks.py            ← Tests with mocked HTTP responses
  test_internal_helpers.py      ← Unit tests for the intervals_icu package's decomposed helpers
  test_cli.py                   ← CLI argument parsing tests
  test_pmc_integration.py       ← PMC bootstrap/weekly with mocked API
  test_fit_ingest.py            ← .fit file ingestion tests
  test_prediction_tracker.py    ← Prediction tracker tests (W5 validation loop)
  test_zwo_lint.py              ← ZWO linter tests
  fixtures/                     ← Mock API responses (activity.json, intervals.json, power_curve.json)
evals/
  evals.json                    ← Skill evaluation definitions
  README.md                     ← Eval set authoring notes
  results/                      ← Per-iteration eval result JSON archive (gitignored)
  trigger_eval.json             ← Workflow trigger matching tests (28 queries: 16 positive, 12 negative)
assets/
  template_sweetspot.zwo        ← Example Zwift workout XML
.env                            ← intervals.icu credentials (not committed)
```

**Data flows:**
- **Activity analysis:** intervals.icu link → `intervals_icu_api.py` extracts ID, authenticates via API key, fetches activity/intervals/streams/power-curve, computes metrics → JSON output → Claude provides coaching analysis using reference docs. Fallback for a ride that never synced to intervals.icu: `fit_ingest.py` parses a local `.fit` and emits the same JSON shape.
- **Plan creation:** `pmc_calculator.py --bootstrap` → PMC baseline → Claude designs block using `block_templates.md` rules (and `durability_strength.md` if concurrent strength / heat / long-duration target applies) → writes `plans/active_plan.md` → `batch_generate_zwo.py` generates week's .zwo files.
- **Weekly review:** `pmc_calculator.py --weekly-update` → planned vs actual comparison → Claude applies adaptation decision trees → updates `plans/active_plan.md` → generates next week's .zwo files.

## Key Conventions — Rules (must follow when generating code/files)

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
- **intervals.icu wellness keys (Whoop-sourced)**: Field keys are camelCase as wire-formatted: `restingHR`, `hrv`, `sleepSecs`, `sleepScore`, `sleepQuality`, `readiness`, `respiration`, **`spO2`** (capital O — not `spo2`). `wellness_summary()` normalizes these to snake_case in its output (`spO2` → `spo2`). When reading raw wellness records via `client.get_wellness()`, use the camelCase keys.
- **Metrics hierarchy**: NP → IF → TSS (each derived from the previous); prefer intervals.icu pre-computed values, fall back to stream computation
- **Canonical references**: Zone boundaries in `references/training_zones.md`, PMC formulas in `pmc_calculator.py`, block templates in `references/block_templates.md`, weekly adaptation trees in `references/weekly_adaptation.md`, race taper in `references/race_taper.md`, overlays (strength/heat/durability) in `references/durability_strength.md` — do not duplicate these values elsewhere
- **Plan state**: `plans/active_plan.md` is the single source of truth for active training plans; structure documented in `references/plan_state_schema.md`
- **Adaptation requires approval**: Claude proposes adaptations based on decision trees in `references/weekly_adaptation.md`, but waits for user confirmation before modifying the plan
- **Batch ZWO input**: JSON array where each item extends the `workout_from_dict()` schema with a `filename` field
- **ZWO output directory**: Generated .zwo files go to the Zwift custom workouts folder (see `references/setup.md` → Zwift Workout Directory for path), NOT to `plans/workouts/` in the repo
- **Obsidian vault**: See `references/setup.md` → Obsidian Integration for canonical paths and folder structure
- **Batch dry-run**: `batch_generate_zwo.py --dry-run` validates and computes stats without writing files
- **FTP/weight bounds**: All scripts validate FTP (50-500W) and weight (30-200kg) — rejects nonsensical values
- **Athlete profile source of truth**: `plans/active_plan.md` → Athlete Profile section holds the current FTP + weight. For one-off script runs, prefer `--use-athlete-profile` (auto-fetches from intervals.icu) over hard-coded `--ftp`/`--weight` flags so values don't drift
- **`--use-athlete-profile` resolution chain**: (1) `profile['icu_ftp']` (legacy/some accounts), then (2) walk `profile['sportSettings']` for the bike entry (matches `Ride`/`VirtualRide`/`Cyclocross` types) and use its `ftp`. The script reports the source field on stderr so users can see which path was taken. Same pattern for weight (`icu_weight` only — no per-sport weight). If neither lookup yields a value, the script **prompts interactively** when stdin is a TTY (validates FTP ∈ [50,500] W, weight ∈ [30,200] kg), or **hard-errors** when stdin isn't a TTY (CI/piped) and requires the explicit `--ftp` / `--weight` flag. This avoids silently falling through to the generic 200W/70kg defaults when the user has explicitly opted into profile-driven values
- **The entire `plans/` directory is gitignored**: `.gitignore` ignores `plans/*` with a single `!plans/.gitkeep` exception, so every file under `plans/` — `active_plan.md`, `block_history.md`, `archived_*.md`, `*_regen.json`, `*_original.md`, `prediction_ledger.jsonl`, `athlete_calibration.md` — is excluded by default. All contain athlete PII (FTP, weight, training history, personal notes). Never `git add` them — even by accident via `git add .`. Stage files explicitly.
- **Script-output PII files are also gitignored** (root-anchored globs): `/output*.json`, `/wellness*.json`, `/readiness*.json`, `/rpe_trend*.json`, `/summary*.json`, `/trend*.json`, `/prediction_report*.json` — these match the `-o` filenames documented in `references/cli_reference.md` for `intervals_icu_api.py --weekly-summary`, `--wellness`, `--readiness-check`, `rpe_trend.py`, and `prediction_tracker.py --mode reconcile` (globbed so ad-hoc suffixed variants like `wellness7.json` are also caught). They contain HRV, RHR, sleep, RPE, forecast, and training-load history. **If you add a new script output file, name it to match one of these globs (or extend `.gitignore`)** — do not invent a new ad-hoc filename like `data.json` that would be tracked. The rules are root-anchored so test fixtures with the same names under `tests/fixtures/` are unaffected.
- **New standing coaching rule → rule registry**: when adding a conditional/situational coaching rule to any `references/` doc (a guardrail, conditional adjustment, abort criterion, hygiene rule), add a row to `references/rule_registry.md` AND wire its workflow surface point in the same change. A rule with no workflow surface point is orphaned by definition. See `references/rule_registry.md` for the catalogue and the two surfacing mechanisms (coach-internal `Checks applied` line vs athlete-facing inline note).
- **Tests**: `python -m unittest discover tests -v` (691 tests across 8 files, ~0.1s) — run before AND after any script change.
