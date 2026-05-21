#!/usr/bin/env python3
"""Unit tests for scripts/prediction_tracker.py (W5 validation loop)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from prediction_tracker import (
    DEFAULT_MODEL,
    predict_rpe,
    predict_ftp_gain,
    load_ledger,
    save_ledger,
    next_id,
    load_calibration,
    write_calibration,
)


class TestPredict(unittest.TestCase):
    def test_rpe_base_lookup(self):
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.60, "morning"), 3)
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.84, "morning"), 6)
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.95, "morning"), 9)

    def test_rpe_post_3pm_correction(self):
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.84, "post_3pm"), 8)

    def test_rpe_boundary_is_upper_exclusive(self):
        # 0.65 falls into the 0.65-0.75 bucket, not the <0.65 bucket
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.65, "morning"), 5)

    def test_ftp_gain_range(self):
        result = predict_ftp_gain(DEFAULT_MODEL, 188)
        self.assertEqual(result["pct_low"], 2.0)
        self.assertEqual(result["pct_high"], 4.0)
        self.assertEqual(result["watts_low"], 192)   # 188 * 1.02 = 191.76 -> 192
        self.assertEqual(result["watts_high"], 196)  # 188 * 1.04 = 195.52 -> 196


class TestLedgerIO(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(load_ledger("/no/such/ledger.jsonl"), [])

    def test_round_trip(self):
        recs = [{"id": "P001", "type": "rpe_at_if"}, {"id": "P002", "type": "ftp_gain"}]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            save_ledger(path, recs)
            self.assertEqual(load_ledger(path), recs)

    def test_next_id_empty(self):
        self.assertEqual(next_id([]), "P001")

    def test_next_id_increments_from_max(self):
        self.assertEqual(next_id([{"id": "P001"}, {"id": "P004"}, {"id": "P002"}]), "P005")


class TestCalibrationIO(unittest.TestCase):
    def test_missing_file_returns_default_copy(self):
        model = load_calibration("/no/such/calibration.md")
        self.assertEqual(model, DEFAULT_MODEL)
        model["corrections"]["post_3pm"] = 99  # mutating the copy
        self.assertEqual(DEFAULT_MODEL["corrections"]["post_3pm"], 2)  # original intact

    def test_write_then_load_round_trip(self):
        custom = {"if_rpe_base": [[0.75, 4], [2.0, 8]], "corrections": {"post_3pm": 1},
                  "ftp_gain_pct": [1.5, 3.5]}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "athlete_calibration.md")
            write_calibration(path, custom)
            self.assertEqual(load_calibration(path), custom)

    def test_written_file_is_human_readable_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "athlete_calibration.md")
            write_calibration(path, DEFAULT_MODEL)
            text = open(path, encoding="utf-8").read()
            self.assertIn("# Athlete Prediction Calibration", text)
            self.assertIn("```json", text)


if __name__ == "__main__":
    unittest.main()
