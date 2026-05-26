# Output Artifact Index

Single index of every file the skill writes. Read this when you need to know **where** something lands, **what** schema it uses, or **whether** it's gitignored — without grepping through `plan_state_schema.md` + `obsidian_templates.md` + `setup.md` + `CLAUDE.md` + the per-script source.

This file is also the canonical reference for the quarterly audit's Scope 4 (output contract audit — see `references/audit_protocol.md` → Scope per audit). When a script starts emitting a new artifact or the path changes, **add a row here** in the same PR.

## Table of contents

- [Plan state (in-repo, gitignored)](#plan-state-in-repo-gitignored)
- [Script JSON outputs (skill root, gitignored)](#script-json-outputs-skill-root-gitignored)
- [Zwift workout files (external dir)](#zwift-workout-files-external-dir)
- [Obsidian vault notes](#obsidian-vault-notes)
- [Audit artifacts (version-controlled)](#audit-artifacts-version-controlled)
- [Gitignore policy summary](#gitignore-policy-summary)

---

## Plan state (in-repo, gitignored)

The `plans/` directory is gitignored as a whole (single `!plans/.gitkeep` exception). All artifacts below contain athlete PII — FTP, weight, training history, personal notes.

| Artifact | Path | Emitter | Schema | Retention |
|----------|------|---------|--------|-----------|
| Active plan state | `plans/active_plan.md` | Create Plan (`workflows/plan.md` Step 6); updated by Activity Analysis Steps 5/6, Weekly Review Step 7/8 | `references/plan_state_schema.md` | Single canonical file; archived on rollover |
| Archived plan | `plans/archived_{YYYY-MM-DD}_{plan_type}.md` | Create Plan Step 0 (when user has an existing plan + chooses archive) | Mirrors `plan_state_schema.md` at archive time | Indefinite (audit trail of prior blocks) |
| Block history | `plans/block_history.md` | Block rollover (first creation auto-on rollover) | `references/plan_state_schema.md` → Block History | Append-only |
| Prediction ledger | `plans/prediction_ledger.jsonl` | `scripts/prediction_tracker.py --mode predict` (Create Plan Step 5 hard sessions + Weekly Review Step 8 new-week hard sessions); reconciled by `--mode reconcile` | `references/prediction_calibration.md` → Ledger schema | Append-only; reconciled rows mark complete in-place |
| Athlete calibration | `plans/athlete_calibration.md` | Recalibration trigger (`--reconcile` reports `recalibration_needed` → propose-and-confirm edit to model parameters) | `references/prediction_calibration.md` → Model artifacts | Versioned via git? No — gitignored. Audit trail preserved in `## Adaptation Log` of `plans/active_plan.md` |

---

## Script JSON outputs (skill root, gitignored)

Root-anchored gitignore rules in `.gitignore` exclude these specific filenames. If you add a new script output file, **name it from this list** (or extend `.gitignore`); ad-hoc filenames like `data.json` would be tracked. The root anchor means test fixtures with the same names under `tests/fixtures/` are unaffected.

| Filename | Path | Emitter (CLI) | Contents | Notes |
|----------|------|---------------|----------|-------|
| `output.json` | `/output.json` | `intervals_icu_api.py --activity {id} -o output.json` ; `fit_ingest.py --file <ride.fit> -o output.json` | Single-activity analysis (NP, IF, TSS, zones, peaks, cardiac drift, FTP test detection, interval breakdown) | Documented in `references/cli_reference.md` → Activity Analysis |
| `wellness.json` | `/wellness.json` | `intervals_icu_api.py --wellness <N> -o wellness.json` | Daily wellness records + baselines + signal-mode + active flags | Documented in `references/cli_reference.md` → Wellness Summary |
| `readiness.json` | `/readiness.json` | `intervals_icu_api.py --readiness-check -o readiness.json` | Single-verdict pre-ride readiness + ceiling + per-metric block | Documented in `references/cli_reference.md` → Readiness Check |
| `rpe_trend.json` | `/rpe_trend.json` | `rpe_trend.py --vault-path <path> -o rpe_trend.json` | Per-session-type RPE deltas at constant IF, anchored on last review date | Documented in `references/cli_reference.md` → RPE Trend |
| `summary.json` | `/summary.json` | `intervals_icu_api.py --weekly-summary -o summary.json` | 7-day aggregate (volume, TSS, zone distribution, peaks, power profile) | Documented in `references/cli_reference.md` → Weekly Summary |
| `trend.json` | `/trend.json` | (reserved — used by trend-aggregating script variants) | (varies) | Held in the ignore list so it doesn't accidentally get tracked |

---

## Zwift workout files (external dir)

| Artifact | Path | Emitter | Schema | Gitignored? |
|----------|------|---------|--------|-------------|
| Single `.zwo` workout | `<ZWIFT_WORKOUTS_DIR>/W{N}_D{day}_{Type}_{Detail}.zwo` | `scripts/generate_zwo.py --json <def.json> --output <path>` | `references/zwo_format.md` (local subset; canonical: h4l/zwift-workout-file-reference) | n/a — external dir |
| Batch `.zwo` (week) | `<ZWIFT_WORKOUTS_DIR>/week{N}/*.zwo` | `scripts/batch_generate_zwo.py --input <week.json> --output-dir <path>` | Same as single | n/a — external dir |

**`<ZWIFT_WORKOUTS_DIR>` resolution:** see `references/setup.md` → Zwift Workout Directory. Windows: `%LOCALAPPDATA%\Zwift\Workouts\<athlete_id>\`. macOS/Linux: `~/Documents/Zwift/Workouts/<athlete_id>/`. Always confirm the path with the user before writing.

**Restart Zwift after writing:** Zwift doesn't hot-reload `.zwo` files.

---

## Obsidian vault notes

All notes land under the cycling-fitness-coach folder of the user's Obsidian vault (see `references/setup.md` → Obsidian Integration for vault path resolution).

Vault root: `<CYCLING_VAULT_PATH>` — on Windows `C:/Users/zijia/OneDrive/obsidian/zj-obsd-vault/🚴🏼cycling-fitness-coach/` (the emoji prefix is part of the folder name).

| Artifact | Subpath | Emitter | Frontmatter schema | File naming convention |
|----------|---------|---------|--------------------|------------------------|
| Workout review | `workout-reviews/YYYY-MM-DD <Category> - <Description>.md` | Activity Analysis (`workflows/analyze.md` Step 4) | `references/obsidian_templates.md` → Workout Reviews | `<Category>` is `Outdoor`, `AdHoc`, or empty (structured block). ` - ` separator always present. |
| Plan summary | `training-plans/YYYY-MM <Plan Name>.md` | Create Plan (`workflows/plan.md` Step 8) | `references/obsidian_templates.md` → Training Plans | One file per plan/block creation |
| Weekly review | `weekly-reviews/YYYY Week N Review.md` | Weekly Review (`workflows/plan.md` Step 6, default-on) | `references/obsidian_templates.md` → Weekly Reviews | ISO week number; `Wnn` format |
| Audit (Obsidian copy) | `audits/cycling-coach-<topic>-YYYY-MM-DD.md` | Manual (legacy — pre-2026-05-26 audits lived here only) | Same frontmatter as repo audits (see below) | Repo `audits/` is canonical from 2026-05-26 onward; Obsidian copies become read-only mirrors |

**Gitignored?** Obsidian vault is OneDrive-synced, not in the skill repo — gitignore does not apply. PII protection comes from the vault being a private user space.

---

## Audit artifacts (version-controlled)

This is the **only** category of skill-generated artifact that is committed to git. See `references/audit_protocol.md` for the cadence + scope + frontmatter schema that drives it, and `audits/README.md` for the index + naming convention.

| Artifact | Path | Emitter | Schema | Retention |
|----------|------|---------|--------|-----------|
| Audit artifact | `audits/cycling-coach-<topic>-YYYY-MM-DD.md` | Quarterly audit ritual (see `audit_protocol.md`) or ad-hoc rubric check | `references/audit_protocol.md` → Audit artifact format | Indefinite (historical diff target) |
| Audit index | `audits/README.md` | Manual (update on every new audit) | Section structure in `audits/README.md` itself | Single canonical file |

**PII inside audits:** see `audit_protocol.md` → Retention & PII. Audits *about the skill* (methodology, eval, output contract) contain no PII and commit normally. Audits *incorporating athlete data* (e.g., a calibration audit) gitignore the athlete-data section per-audit, or redact before commit. Use a `## Athlete data (gitignored)` collapsible section as the convention.

---

## Gitignore policy summary

For audit Scope 4 (output contract audit), this is the canonical check:

| Category | Gitignore rule | Source |
|----------|----------------|--------|
| Plan state | `plans/*` (with `!plans/.gitkeep` exception) | `.gitignore` |
| Script JSON outputs | Root-anchored: `/output.json`, `/wellness.json`, `/readiness.json`, `/rpe_trend.json`, `/summary.json`, `/trend.json` | `.gitignore` |
| Zwift `.zwo` files | External dir — never inside the repo | n/a |
| Obsidian notes | External vault — never inside the repo | n/a |
| Audits (about the skill) | **Tracked** — committed to git | `audits/` directory is intentionally NOT in `.gitignore` |
| Audits (with athlete data) | Per-audit redaction; section-level `## Athlete data (gitignored)` block | Convention; see `audit_protocol.md` → Retention & PII |

**When adding a new emitter:**

1. Decide the category (which row above).
2. If a new filename pattern: add it to `.gitignore` (root-anchored unless intentionally global), then add a row to this index.
3. If a new path under a category that's already gitignored (e.g., a new file under `plans/`): just add the row here — `.gitignore` already covers it.
4. Run `git status` after a sample emission to confirm the new file shows up untracked, not staged.
