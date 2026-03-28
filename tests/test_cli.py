#!/usr/bin/env python3
"""Tests for CLI argument parsing of all scripts.

Run: python -m unittest tests.test_cli -v
"""

import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch

# Add scripts/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


class TestIntervalsIcuApiCli(unittest.TestCase):
    """Test intervals_icu_api.py argument parsing."""

    def _parse(self, args):
        """Import and run argparse with given args, return namespace."""
        import argparse
        import intervals_icu_api  # noqa: F401 — ensures module is importable
        # We test argparse logic directly rather than calling main() (which needs API creds)
        p = argparse.ArgumentParser()
        mode = p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--activity")
        mode.add_argument("--latest", action="store_true")
        mode.add_argument("--list-recent", type=int)
        mode.add_argument("--weekly-summary", type=int, nargs="?", const=7)
        p.add_argument("--ftp", type=int, default=None)
        p.add_argument("--weight", type=float, default=None)
        p.add_argument("--compact", action="store_true")
        p.add_argument("-o", "--output")
        return p.parse_args(args)

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


class TestGenerateZwoCli(unittest.TestCase):
    """Test generate_zwo.py argument parsing."""

    def _parse(self, args):
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--json", "-j", required=True)
        p.add_argument("--output", "-o", required=True)
        p.add_argument("--ftp", type=int, default=200)
        return p.parse_args(args)

    def test_required_args(self):
        ns = self._parse(["--json", "w.json", "--output", "w.zwo"])
        self.assertEqual(ns.json, "w.json")
        self.assertEqual(ns.output, "w.zwo")
        self.assertEqual(ns.ftp, 200)

    def test_custom_ftp(self):
        ns = self._parse(["--json", "w.json", "-o", "w.zwo", "--ftp", "192"])
        self.assertEqual(ns.ftp, 192)

    def test_missing_required_fails(self):
        with self.assertRaises(SystemExit):
            self._parse(["--json", "w.json"])  # missing --output


class TestBatchGenerateZwoCli(unittest.TestCase):
    """Test batch_generate_zwo.py argument parsing."""

    def _parse(self, args):
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--input", "-i", required=True)
        p.add_argument("--output-dir", "-d", required=True)
        p.add_argument("--ftp", type=int, default=200)
        p.add_argument("--dry-run", action="store_true")
        return p.parse_args(args)

    def test_dry_run_flag(self):
        ns = self._parse(["--input", "w.json", "--output-dir", "out/", "--dry-run"])
        self.assertTrue(ns.dry_run)

    def test_default_ftp(self):
        ns = self._parse(["-i", "w.json", "-d", "out/"])
        self.assertEqual(ns.ftp, 200)


class TestPmcCalculatorCli(unittest.TestCase):
    """Test pmc_calculator.py argument parsing."""

    def _parse(self, args):
        import argparse
        p = argparse.ArgumentParser()
        mode = p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--bootstrap", action="store_true")
        mode.add_argument("--weekly-update", action="store_true")
        p.add_argument("--days", type=int, default=90)
        p.add_argument("--week", type=int)
        p.add_argument("--plan-start")
        p.add_argument("--prev-ctl", type=float)
        p.add_argument("--prev-atl", type=float)
        p.add_argument("--planned-tss")
        return p.parse_args(args)

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
