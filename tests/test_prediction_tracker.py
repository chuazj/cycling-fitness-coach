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


if __name__ == "__main__":
    unittest.main()
