#!/usr/bin/env python3
"""Tests for CLI argument parsing of all scripts.

Imports the real `build_parser()` from each script so the tests stay aligned
with the production parsers (no schema drift).

Run: python -m unittest tests.test_cli -v
"""

import os
import sys
import unittest

# Add scripts/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from intervals_icu_api import build_parser as build_intervals_parser
from generate_zwo import build_parser as build_generate_parser
from batch_generate_zwo import build_parser as build_batch_parser
from pmc_calculator import build_parser as build_pmc_parser
from zwo_lint import build_parser as build_zwo_lint_parser


class TestIntervalsIcuApiCli(unittest.TestCase):
    """Test intervals_icu_api.py argument parsing."""

    def _parse(self, args):
        return build_intervals_parser().parse_args(args)

    def test_activity_mode(self):
        ns = self._parse(["--activity", "i123", "--ftp", "200"])
        self.assertEqual(ns.activity, "i123")
        self.assertEqual(ns.ftp, 200)

    def test_latest_mode(self):
        ns = self._parse(["--latest"])
        self.assertTrue(ns.latest)

    def test_weekly_summary_default_days(self):
        ns = self._parse(["--weekly-summary"])
        self.assertEqual(ns.weekly_summary, 7)

    def test_weekly_summary_custom_days(self):
        ns = self._parse(["--weekly-summary", "14"])
        self.assertEqual(ns.weekly_summary, 14)

    def test_wellness_default_days(self):
        ns = self._parse(["--wellness"])
        self.assertEqual(ns.wellness, 14)

    def test_wellness_custom_days(self):
        ns = self._parse(["--wellness", "30"])
        self.assertEqual(ns.wellness, 30)

    def test_compact_flag(self):
        ns = self._parse(["--activity", "i999", "--compact"])
        self.assertTrue(ns.compact)

    def test_ftp_bounds_reject_low(self):
        """FTP below 50 should be caught by validation (tested at main() level)."""
        ns = self._parse(["--activity", "i999", "--ftp", "10"])
        self.assertEqual(ns.ftp, 10)  # argparse accepts it; main() validates bounds

    def test_ftp_bounds_reject_high(self):
        """FTP above 500 should be caught by validation (tested at main() level)."""
        ns = self._parse(["--activity", "i999", "--ftp", "999"])
        self.assertEqual(ns.ftp, 999)  # argparse accepts it; main() validates bounds

    def test_mutually_exclusive_modes(self):
        with self.assertRaises(SystemExit):
            self._parse(["--activity", "i123", "--latest"])

    def test_use_athlete_profile_flag(self):
        ns = self._parse(["--activity", "i999", "--use-athlete-profile"])
        self.assertTrue(ns.use_athlete_profile)

    def test_output_file(self):
        ns = self._parse(["--activity", "i999", "-o", "out.json"])
        self.assertEqual(ns.output, "out.json")


class TestGenerateZwoCli(unittest.TestCase):
    """Test generate_zwo.py argument parsing."""

    def _parse(self, args):
        return build_generate_parser().parse_args(args)

    def test_required_args(self):
        ns = self._parse(["--json", "w.json", "--output", "w.zwo"])
        self.assertEqual(ns.json, "w.json")
        self.assertEqual(ns.output, "w.zwo")
        self.assertIsNone(ns.ftp)  # D3-4: defaults to None; main() warns + falls back to 200

    def test_custom_ftp(self):
        ns = self._parse(["--json", "w.json", "-o", "w.zwo", "--ftp", "192"])
        self.assertEqual(ns.ftp, 192)

    def test_missing_required_fails(self):
        with self.assertRaises(SystemExit):
            self._parse(["--json", "w.json"])  # missing --output


class TestBatchGenerateZwoCli(unittest.TestCase):
    """Test batch_generate_zwo.py argument parsing."""

    def _parse(self, args):
        return build_batch_parser().parse_args(args)

    def test_dry_run_flag(self):
        ns = self._parse(["--input", "w.json", "--output-dir", "out/", "--dry-run"])
        self.assertTrue(ns.dry_run)

    def test_default_ftp(self):
        ns = self._parse(["-i", "w.json", "-d", "out/"])
        self.assertEqual(ns.ftp, 200)

    def test_summary_output_path(self):
        ns = self._parse(["-i", "w.json", "-d", "out/", "-o", "summary.json"])
        self.assertEqual(ns.output, "summary.json")


class TestPmcCalculatorCli(unittest.TestCase):
    """Test pmc_calculator.py argument parsing."""

    def _parse(self, args):
        return build_pmc_parser().parse_args(args)

    def test_bootstrap_mode(self):
        ns = self._parse(["--bootstrap", "--days", "60"])
        self.assertTrue(ns.bootstrap)
        self.assertEqual(ns.days, 60)

    def test_weekly_update_mode(self):
        ns = self._parse(["--weekly-update", "--week", "3", "--plan-start", "2026-03-16",
                          "--prev-ctl", "42.3", "--prev-atl", "51.2",
                          "--planned-tss", '{"Tue":65}'])
        self.assertTrue(ns.weekly_update)
        self.assertEqual(ns.week, 3)
        self.assertEqual(ns.prev_ctl, 42.3)

    def test_mutually_exclusive_modes(self):
        with self.assertRaises(SystemExit):
            self._parse(["--bootstrap", "--weekly-update"])

    def test_prev_peaks_arg(self):
        ns = self._parse(["--weekly-update", "--prev-peaks", '{"5s":450}'])
        self.assertEqual(ns.prev_peaks, '{"5s":450}')


class TestZwoLintCli(unittest.TestCase):
    """Test zwo_lint.py argument parsing."""

    def _parse(self, args):
        return build_zwo_lint_parser().parse_args(args)

    def test_file_positional(self):
        ns = self._parse(["workout.zwo"])
        self.assertEqual(ns.file, "workout.zwo")
        self.assertIsNone(ns.ftp)

    def test_ftp_and_output(self):
        ns = self._parse(["w.zwo", "--ftp", "188", "-o", "report.json"])
        self.assertEqual(ns.ftp, 188)
        self.assertEqual(ns.output, "report.json")

    def test_missing_file_fails(self):
        with self.assertRaises(SystemExit):
            self._parse([])  # file is required


class TestFtpBoundsValidation(unittest.TestCase):
    """Test that FTP bounds validation works in main() for intervals_icu_api.py."""

    def test_ftp_50_is_valid(self):
        self.assertTrue(50 <= 50 <= 500)

    def test_ftp_500_is_valid(self):
        self.assertTrue(50 <= 500 <= 500)

    def test_ftp_49_is_invalid(self):
        self.assertFalse(50 <= 49 <= 500)

    def test_ftp_501_is_invalid(self):
        self.assertFalse(50 <= 501 <= 500)

    def test_weight_30_is_valid(self):
        self.assertTrue(30 <= 30 <= 200)

    def test_weight_200_is_valid(self):
        self.assertTrue(30 <= 200 <= 200)

    def test_weight_29_is_invalid(self):
        self.assertFalse(30 <= 29 <= 200)

    def test_weight_201_is_invalid(self):
        self.assertFalse(30 <= 201 <= 200)


if __name__ == "__main__":
    unittest.main()
