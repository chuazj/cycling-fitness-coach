# Prediction Calibration — the W5 Validation Loop

How the skill forecasts, reconciles forecasts against outcomes, and recalibrates
its forecasting models. Operated by `scripts/prediction_tracker.py`.

## The loop

1. **Predict** — when a hard session is scheduled (`plan.md`), or a plan is
   created (`plan.md` Step 9), `prediction_tracker.py --mode predict` logs a
   forecast to `plans/prediction_ledger.jsonl`.
2. **Measure** — the workout review (RPE) or an FTP test (FTP-gain) is the
   actual outcome.
3. **Reconcile** — `--mode reconcile` matches open predictions to actuals,
   fills in the delta, and emits a calibration report.
4. **Calibrate** — when a recalibration trigger fires, the coach proposes a
   model edit; the athlete confirms (propose-and-confirm, never autonomous).

## The two models

### IF -> RPE expectation

Expected session RPE from session IF. A base lookup table (the morning/fresh
expectation) plus additive correction terms. The **operative generic default**
is `DEFAULT_MODEL` in `scripts/prediction_tracker.py`:

| IF bucket | Expected RPE (base, morning/fresh) |
|---|---|
| < 0.65 | 3 |
| 0.65–0.75 | 5 |
| 0.75–0.85 | 6 |
| 0.85–0.92 | 8 |
| ≥ 0.92 | 9 |

Correction terms: `post_3pm: +2`. The athlete-calibrated instance lives in
`plans/athlete_calibration.md`, seeded from existing Obsidian reviews by
`--mode seed-baseline`.

### FTP-gain rate

Expected FTP %-gain per training block. Generic default: the 2–4%/block range in
`references/block_templates.md` → FTP Builder → Block-level coaching notes. The
athlete-calibrated rate lives in `plans/athlete_calibration.md`.

## Recalibration triggers

- **RPE-at-IF:** over the last 5 reconciled `rpe_at_if` predictions within one
  slot (`morning` vs `post_3pm`), `|mean signed delta| ≥ 1.0` RPE — a sustained
  directional bias, not mean absolute noise. Attribution: same-sign bias in both
  slots → recalibrate the base table; bias confined to `post_3pm` → recalibrate
  the `post_3pm` correction constant.
- **FTP-gain:** 2 consecutive completed blocks with actual gain outside the
  predicted range → recalibrate the athlete's personal FTP-gain rate. A single
  miss is noted but does not trigger (blocks get disrupted).

Both are registered in `references/rule_registry.md`.

## Calibration is propose-and-confirm

When `--mode reconcile` reports `recalibration_needed`, the weekly review
surfaces it in the Forecast Accuracy block. The coach proposes the specific edit
to `plans/athlete_calibration.md` (a base-table value, a correction constant, or
the FTP-gain rate) with the supporting deltas; the athlete confirms before the
file is changed. The skill never edits the model autonomously.

## Ledger schema

`plans/prediction_ledger.jsonl` — append-only forecast log, one JSON object per line, gitignored (athlete PII). Each record is created open by `prediction_tracker.py --mode predict` and updated in place by `--mode reconcile`.

| Field | Type | Set at | Notes |
|-------|------|--------|-------|
| `id` | int | predict | Monotonic, 1-based (next after the max existing id). |
| `type` | str | predict | `"rpe_at_if"` or `"ftp_gain"`. |
| `made` | str | predict | Date the prediction was logged (`YYYY-MM-DD`). |
| `predicted` | int or object | predict | `rpe_at_if`: expected RPE (int). `ftp_gain`: `{pct_low, pct_high, watts_low, watts_high}`. |
| `inputs` | object | predict | `rpe_at_if`: `{if, slot, session_type}`. `ftp_gain`: `{start_ftp, block}`. |
| `reconcile_when` | str | predict | When the row becomes due (session date for RPE; block-end date for FTP gain). |
| `status` | str | predict then reconcile | `"open"` until reconciled; reconciled rows mark complete in place. |
| `actual` | num or null | reconcile | Measured outcome; `null` while open. |
| `reconciled` | str or null | reconcile | Date the actual was matched in; `null` while open. |
| `delta` | num or null | reconcile | Signed error (actual minus predicted); `null` while open. |

A reconcile never rewrites prior rows' immutable fields (`id` / `type` / `made` / `predicted` / `inputs`) — it only fills the outcome fields and flips `status`. New fields, if ever added, must be tolerated as absent on old rows (append-only JSONL cannot be back-edited safely). Each row now carries a `schema_version` key (`LEDGER_SCHEMA_VERSION`, currently `1`); loaders are forward-tolerant — a row whose `schema_version` exceeds the supported constant is still read but warns that it was written by a newer `prediction_tracker`. **When you add or change a ledger field, bump `LEDGER_SCHEMA_VERSION` in `prediction_tracker.py`** (and `MODEL_SCHEMA_VERSION` for model-shape changes).

## Model artifacts

`plans/athlete_calibration.md` — the athlete's calibrated model (the two tables above, tuned), gitignored (athlete PII). It holds a single JSON model object with the same shape as the default scaffold in `prediction_tracker.py` (`DEFAULT_MODEL`):

| Key | Type | Meaning |
|-----|------|---------|
| `if_rpe_base` | list of `[upper_exclusive_IF, expected_RPE]` | Ordered IF-to-RPE table; first row whose bound exceeds the IF wins. Final row's bound (`2.0`) is the upper sentinel. |
| `corrections` | object | Additive RPE corrections, e.g. `{"post_3pm": 2}`. |
| `ftp_gain_pct` | `[low_pct, high_pct]` | Expected per-block FTP-gain band (default `[2.0, 4.0]`). |

`--mode seed-baseline` writes this file from the athlete's Obsidian reviews; recalibration triggers propose edits to it (propose-and-confirm, above).

> **Gitignore and retention** for both artifacts: see `governance/artifacts.md` → Prediction ledger / Athlete calibration rows (that index owns the PII/retention policy; this doc owns the field-level schema).
