#!/usr/bin/env python3
"""
Prediction Tracker for Cycling Fitness Coach (W5 — predict → measure → calibrate).

Logs forecasts (RPE-at-IF, FTP-gain) to a JSONL ledger, reconciles them against
actual outcomes, and flags when a forecasting model needs recalibration.

No third-party dependencies.

Usage:
    python prediction_tracker.py --mode seed-baseline --vault-path "<reviews dir>"
    python prediction_tracker.py --mode predict --type rpe_at_if --if 0.84 \
        --slot morning --session-date 2026-06-02 --session-type Threshold
    python prediction_tracker.py --mode predict --type ftp_gain --start-ftp 188 \
        --block-label "FTP Builder, 4wk" --block-end 2026-06-28
    python prediction_tracker.py --mode reconcile --vault-path "<reviews dir>"
    python prediction_tracker.py --mode reconcile --vault-path "<reviews dir>" \
        --new-ftp 196 --ftp-test-date 2026-06-28
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Force UTF-8 on Windows (output and error messages may carry non-ASCII).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# scripts/ is on sys.path when run as `python scripts/prediction_tracker.py`
# and in tests (which insert scripts/ on the path) — so rpe_trend imports directly.
from rpe_trend import collect_reviews

# Generic default forecasting model (the scaffold). The athlete-calibrated
# instance lives in plans/athlete_calibration.md; --seed-baseline produces it.
# if_rpe_base: ordered [upper_exclusive_IF, expected_RPE] rows — first row whose
# bound exceeds the IF wins. The final row's bound (2.0) is an upper sentinel.
DEFAULT_MODEL = {
    "if_rpe_base": [[0.65, 3], [0.75, 5], [0.85, 6], [0.92, 8], [2.0, 9]],
    "corrections": {"post_3pm": 2},
    "ftp_gain_pct": [2.0, 4.0],
}

RPE_TRIGGER_WINDOW = 5        # reconciled RPE predictions per slot
RPE_TRIGGER_THRESHOLD = 1.0   # |mean signed delta| RPE that fires recalibration
FTP_TRIGGER_WINDOW = 2        # consecutive completed blocks


def predict_rpe(model, if_value, slot):
    """Predicted session RPE = base-table lookup by IF + slot correction.

    `slot` is "morning" or "post_3pm"; the post_3pm correction is additive.
    """
    base = model["if_rpe_base"]
    rpe = base[-1][1]
    for bound, value in base:
        if if_value < bound:
            rpe = value
            break
    if slot == "post_3pm":
        rpe += model["corrections"].get("post_3pm", 0)
    return rpe


def predict_ftp_gain(model, start_ftp):
    """Predicted post-block FTP range from the per-block %-gain model."""
    low_pct, high_pct = model["ftp_gain_pct"]
    return {
        "pct_low": low_pct,
        "pct_high": high_pct,
        "watts_low": round(start_ftp * (1 + low_pct / 100)),
        "watts_high": round(start_ftp * (1 + high_pct / 100)),
    }


if __name__ == "__main__":
    main()
