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
`references/periodization.md` → FTP Builder → Block-level coaching notes. The
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
