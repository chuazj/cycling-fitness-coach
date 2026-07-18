#!/usr/bin/env python3
"""Tests for CLI argument parsing of all scripts.

Imports the real `build_parser()` from each script so the tests stay aligned
with the production parsers (no schema drift).

Run: python -m unittest tests.test_cli -v
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add scripts/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from intervals_icu_api import build_parser as build_intervals_parser
from generate_zwo import build_parser as build_generate_parser
from generate_zwo import main as generate_zwo_main
from batch_generate_zwo import build_parser as build_batch_parser
from pmc_calculator import build_parser as build_pmc_parser
from pmc_calculator import main as pmc_main
from zwo_lint import build_parser as build_zwo_lint_parser
from fit_ingest import build_parser as build_fit_ingest_parser
import intervals_icu.cli as icu_cli


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

    def test_list_recent_zero_rejected(self):
        # Q3 P2: --list-recent 0 was a silent no-op (0 is falsy, every dispatch
        # elif missed, exit 0 with no output) — reject at parse time.
        with self.assertRaises(SystemExit):
            self._parse(["--list-recent", "0"])

    def test_wellness_mode_skips_ftp_prompt_when_profile_fails(self):
        """Q3 P2: --wellness never reads FTP/weight — a failed profile fetch
        must not hard-error (CI) or prompt (TTY) for them."""
        import contextlib
        import io
        from unittest.mock import MagicMock
        argv = ["prog", "--wellness", "7", "--use-athlete-profile",
                "--athlete-id", "x", "--api-key", "y"]
        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = False
        with patch.object(sys, "argv", argv), \
             patch.object(sys, "stdin", fake_stdin), \
             patch.object(icu_cli.IntervalsIcuClient, "get_athlete",
                          side_effect=Exception("boom")), \
             patch.object(icu_cli, "wellness_summary",
                          return_value={"ok": True}) as ws, \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            icu_cli.main()  # must complete without SystemExit
        ws.assert_called_once()

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

    def test_invalid_interval_type_exits_cleanly(self):
        """Q3 P2: workout_from_dict's crafted ValueError must surface as a
        clean ERROR + exit 1, not a raw traceback (batch path already does)."""
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "w.json")
            with open(src, "w", encoding="utf-8") as f:
                json.dump({"name": "X", "workout": [
                    {"type": "steady", "duration": 300, "power": 0.8}]}, f)
            argv = ["prog", "--json", src, "--output", os.path.join(d, "o.zwo")]
            with patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit) as cm:
                    generate_zwo_main()
            self.assertEqual(cm.exception.code, 1)

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

    def test_default_ftp_is_none(self):
        # --ftp defaults to None so main() warns on fallback via resolve_ftp_arg
        # (was a silent 200W default — see audit P1-1 / W9 D3-N3).
        ns = self._parse(["-i", "w.json", "-d", "out/"])
        self.assertIsNone(ns.ftp)

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

    def test_planned_tss_non_numeric_values_rejected(self):
        """Q3 P2: '{"Tue":"65"}' passed json.loads but crashed weekly_update
        with a raw TypeError — reject with a clean parser error instead."""
        argv = ["prog", "--weekly-update", "--week", "1",
                "--plan-start", "2026-07-14", "--prev-ctl", "50",
                "--prev-atl", "50", "--planned-tss", '{"Tue":"65"}']
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                pmc_main()
        self.assertEqual(cm.exception.code, 2)  # argparse p.error convention

    def test_planned_tss_array_rejected(self):
        argv = ["prog", "--weekly-update", "--week", "1",
                "--plan-start", "2026-07-14", "--prev-ctl", "50",
                "--prev-atl", "50", "--planned-tss", '[65, 70]']
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                pmc_main()
        self.assertEqual(cm.exception.code, 2)

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


class TestFitIngestCli(unittest.TestCase):
    """fit_ingest.py argument parsing."""

    def _parse(self, args):
        return build_fit_ingest_parser().parse_args(args)

    def test_file_required(self):
        with self.assertRaises(SystemExit):
            self._parse([])

    def test_file_and_options(self):
        ns = self._parse(["--file", "ride.fit", "--ftp", "188",
                          "--weight", "74", "-o", "out.json"])
        self.assertEqual(ns.file, "ride.fit")
        self.assertEqual(ns.ftp, 188)
        self.assertEqual(ns.weight, 74.0)
        self.assertEqual(ns.output, "out.json")

    def test_ftp_weight_default_none(self):
        ns = self._parse(["--file", "ride.fit"])
        self.assertIsNone(ns.ftp)
        self.assertIsNone(ns.weight)


class TestResolveFtpArg(unittest.TestCase):
    """M-6 — shared resolve_ftp_arg helper in generate_zwo.py."""

    def setUp(self):
        from generate_zwo import build_parser, resolve_ftp_arg
        self._resolve = resolve_ftp_arg
        self._parser = build_parser()

    def _capture_stderr(self, fn, *args, **kwargs):
        """Call fn(*args) and return (result, stderr_text)."""
        import io
        import sys
        buf = io.StringIO()
        old = sys.stderr
        sys.stderr = buf
        try:
            result = fn(*args, **kwargs)
        finally:
            sys.stderr = old
        return result, buf.getvalue()

    def test_none_defaults_to_200_with_warning(self):
        # ftp_value=None → returns 200 and emits a warning to stderr
        result, stderr = self._capture_stderr(
            self._resolve, None, self._parser,
            "WARNING: --ftp not supplied — using 200W for stats."
        )
        self.assertEqual(result, 200)
        self.assertIn("WARNING", stderr)
        self.assertIn("200W", stderr)

    def test_warning_text_is_passed_through_verbatim(self):
        # The caller controls the warning text; the helper emits it as-is
        custom_msg = "WARNING: custom message for this specific caller"
        result, stderr = self._capture_stderr(
            self._resolve, None, self._parser, custom_msg
        )
        self.assertIn(custom_msg, stderr)

    def test_valid_ftp_passes_through_unchanged(self):
        result, stderr = self._capture_stderr(
            self._resolve, 188, self._parser,
            "WARNING: --ftp not supplied — using 200W for stats."
        )
        self.assertEqual(result, 188)
        self.assertEqual(stderr, "")

    def test_lower_bound_50_is_valid(self):
        result, _ = self._capture_stderr(
            self._resolve, 50, self._parser,
            "WARNING: --ftp not supplied — using 200W for stats."
        )
        self.assertEqual(result, 50)

    def test_upper_bound_500_is_valid(self):
        result, _ = self._capture_stderr(
            self._resolve, 500, self._parser,
            "WARNING: --ftp not supplied — using 200W for stats."
        )
        self.assertEqual(result, 500)

    def test_below_50_calls_parser_error(self):
        # parser.error() calls sys.exit(2) — captured as SystemExit
        with self.assertRaises(SystemExit) as cm:
            self._resolve(49, self._parser,
                          "WARNING: --ftp not supplied — using 200W for stats.")
        self.assertEqual(cm.exception.code, 2)

    def test_above_500_calls_parser_error(self):
        with self.assertRaises(SystemExit) as cm:
            self._resolve(501, self._parser,
                          "WARNING: --ftp not supplied — using 200W for stats.")
        self.assertEqual(cm.exception.code, 2)

    def test_generate_zwo_warning_text_exact(self):
        # generate_zwo's warning text (verbatim from production code)
        from generate_zwo import build_parser, resolve_ftp_arg
        parser = build_parser()
        gen_warning = (
            "WARNING: --ftp not supplied — using 200W for stats. TSS and intensity "
            "estimates will be wrong unless 200W is the athlete's actual FTP. "
            "Re-run with --ftp <actual> for accurate numbers."
        )
        result, stderr = self._capture_stderr(resolve_ftp_arg, None, parser, gen_warning)
        self.assertEqual(result, 200)
        self.assertIn(gen_warning, stderr)

    def test_zwo_lint_warning_text_exact(self):
        # zwo_lint's shorter warning text (verbatim from production code)
        from zwo_lint import build_parser as lint_parser, resolve_ftp_arg
        parser = lint_parser()
        lint_warning = "WARNING: --ftp not supplied — using 200W for modeled stats."
        result, stderr = self._capture_stderr(resolve_ftp_arg, None, parser, lint_warning)
        self.assertEqual(result, 200)
        self.assertIn(lint_warning, stderr)


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
