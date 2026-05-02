# Skill Evaluations

This directory holds the evaluation suite for the cycling-fitness-coach skill.

## Files

- `evals.json` — End-to-end coaching scenarios (workout analysis, training advice, ZWO generation, etc.). Each entry has a prompt, expected output, and a list of `expectations` to grade against.
- `trigger_eval.json` — Dispatch / routing tests: confirms the right workflow file is selected for a given user phrasing.
- `results/` — Per-run outputs from an external eval harness (one timestamped subdirectory per run). Empty by default; not git-tracked.

## Running

The eval harness lives outside this repo. To run a scoring pass, point the harness at `evals.json` (or `trigger_eval.json`) and write outputs into `results/<YYYY-MM-DD_HHMMSS>/`. The `.gitkeep` file preserves the `results/` directory in git so harness paths resolve cleanly on a fresh clone.

When updating evals, prefer adding new entries over editing existing ones — historical results stay comparable.
