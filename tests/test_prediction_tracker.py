#!/usr/bin/env python3
"""Unit tests for scripts/prediction_tracker.py (W5 validation loop)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

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
    seed_baseline,
    reconcile,
    check_rpe_trigger,
    attribute_rpe,
    check_ftp_trigger,
    build_parser,
    run_predict,
    main,
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

    def test_rpe_capped_at_10(self):
        # base 9 (IF >= 0.92) + post_3pm correction 2 = 11 -> must cap at 10
        self.assertEqual(predict_rpe(DEFAULT_MODEL, 0.95, "post_3pm"), 10)

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


class TestSeedBaseline(unittest.TestCase):
    def _review(self, if_val, rpe):
        return {"date": "2026-04-01", "session_type": "Threshold", "if": if_val, "rpe": rpe}

    def test_fits_bucket_mean(self):
        # Two reviews in the 0.75-0.85 bucket: RPE 6 and 8 -> mean 7
        reviews = [self._review(0.80, 6), self._review(0.82, 8)]
        model = seed_baseline(reviews)
        self.assertEqual(predict_rpe(model, 0.80, "morning"), 7)

    def test_empty_bucket_keeps_default(self):
        # No reviews at all -> every bucket keeps the DEFAULT_MODEL value
        model = seed_baseline([])
        self.assertEqual(model["if_rpe_base"], DEFAULT_MODEL["if_rpe_base"])

    def test_does_not_mutate_default_model(self):
        seed_baseline([self._review(0.80, 6), self._review(0.82, 8)])
        self.assertEqual(DEFAULT_MODEL["if_rpe_base"][2], [0.85, 6])

    def test_corrections_carried_over(self):
        model = seed_baseline([self._review(0.80, 7)])
        self.assertEqual(model["corrections"], DEFAULT_MODEL["corrections"])
        self.assertEqual(model["ftp_gain_pct"], DEFAULT_MODEL["ftp_gain_pct"])


class TestReconcile(unittest.TestCase):
    def _open_rpe(self, when, predicted, stype="Threshold", slot="morning"):
        return {"id": "P001", "type": "rpe_at_if", "made": "2026-05-01",
                "reconcile_when": when,
                "inputs": {"if": 0.84, "slot": slot, "session_type": stype},
                "predicted": predicted, "status": "open",
                "actual": None, "reconciled": None, "delta": None}

    def _review(self, date, rpe, stype="Threshold"):
        return {"date": date, "session_type": stype, "if": 0.84, "rpe": float(rpe)}

    def test_rpe_exact_date_match(self):
        recs = [self._open_rpe("2026-05-10", 6)]
        recs, just = reconcile(recs, [self._review("2026-05-10", 8)])
        self.assertEqual(len(just), 1)
        self.assertEqual(recs[0]["status"], "reconciled")
        self.assertEqual(recs[0]["actual"], 8.0)
        self.assertEqual(recs[0]["delta"], 2.0)

    def test_rpe_within_two_days(self):
        recs = [self._open_rpe("2026-05-10", 6)]
        recs, just = reconcile(recs, [self._review("2026-05-12", 7)])
        self.assertEqual(recs[0]["status"], "reconciled")

    def test_rpe_no_match_stays_open(self):
        recs = [self._open_rpe("2026-05-10", 6)]
        recs, just = reconcile(recs, [self._review("2026-05-20", 7)])
        self.assertEqual(just, [])
        self.assertEqual(recs[0]["status"], "open")

    def test_rpe_session_type_must_match(self):
        recs = [self._open_rpe("2026-05-10", 6, stype="VO2max")]
        recs, just = reconcile(recs, [self._review("2026-05-10", 8, stype="Threshold")])
        self.assertEqual(recs[0]["status"], "open")

    def test_ftp_gain_inside_range(self):
        rec = {"id": "P002", "type": "ftp_gain", "made": "2026-05-01",
               "reconcile_when": "2026-05-28",
               "inputs": {"start_ftp": 188, "block": "FTP Builder, 4wk"},
               "predicted": {"pct_low": 2.0, "pct_high": 4.0,
                             "watts_low": 192, "watts_high": 196},
               "status": "open", "actual": None, "reconciled": None, "delta": None}
        recs, just = reconcile([rec], [], new_ftp=194, ftp_test_date="2026-05-28")
        self.assertEqual(recs[0]["status"], "reconciled")
        self.assertEqual(recs[0]["delta"], "inside")
        self.assertEqual(recs[0]["actual"], {"ftp": 194, "pct": 3.2})

    def test_ftp_gain_outside_range(self):
        rec = {"id": "P003", "type": "ftp_gain", "made": "2026-05-01",
               "reconcile_when": "2026-05-28",
               "inputs": {"start_ftp": 188, "block": "FTP Builder, 4wk"},
               "predicted": {"pct_low": 2.0, "pct_high": 4.0,
                             "watts_low": 192, "watts_high": 196},
               "status": "open", "actual": None, "reconciled": None, "delta": None}
        recs, just = reconcile([rec], [], new_ftp=190, ftp_test_date="2026-05-28")
        self.assertTrue(recs[0]["delta"].startswith("outside"))

    def test_ftp_gain_not_reconciled_without_new_ftp(self):
        rec = {"id": "P004", "type": "ftp_gain", "made": "2026-05-01",
               "reconcile_when": "2026-05-28",
               "inputs": {"start_ftp": 188, "block": "x"},
               "predicted": {"pct_low": 2.0, "pct_high": 4.0,
                             "watts_low": 192, "watts_high": 196},
               "status": "open", "actual": None, "reconciled": None, "delta": None}
        recs, just = reconcile([rec], [])
        self.assertEqual(recs[0]["status"], "open")


class TestTriggers(unittest.TestCase):
    def _rpe(self, delta, slot, day):
        return {"type": "rpe_at_if", "status": "reconciled", "delta": delta,
                "reconciled": "2026-05-%02d" % day,
                "inputs": {"slot": slot}}

    def test_rpe_trigger_fires_on_sustained_bias(self):
        recs = [self._rpe(2, "morning", d) for d in range(1, 6)]
        flags = check_rpe_trigger(recs)
        self.assertEqual(flags["morning"]["status"], "recalibration_needed")
        self.assertEqual(flags["morning"]["mean_delta"], 2.0)

    def test_rpe_trigger_ok_when_noise_cancels(self):
        # +1, -1, +1, -1, 0 -> mean 0.0 -> ok (noise, not bias)
        deltas = [1, -1, 1, -1, 0]
        recs = [self._rpe(deltas[i], "morning", i + 1) for i in range(5)]
        flags = check_rpe_trigger(recs)
        self.assertEqual(flags["morning"]["status"], "ok")

    def test_rpe_trigger_insufficient_data(self):
        recs = [self._rpe(2, "morning", d) for d in range(1, 4)]
        flags = check_rpe_trigger(recs)
        self.assertEqual(flags["morning"]["status"], "insufficient_data")

    def test_attribute_post_3pm_only(self):
        flags = {"morning": {"status": "ok", "mean_delta": 0.2},
                 "post_3pm": {"status": "recalibration_needed", "mean_delta": 1.6}}
        self.assertEqual(attribute_rpe(flags), "post_3pm correction constant")

    def test_attribute_both_slots_same_sign(self):
        flags = {"morning": {"status": "recalibration_needed", "mean_delta": 1.4},
                 "post_3pm": {"status": "recalibration_needed", "mean_delta": 1.8}}
        self.assertIn("base table", attribute_rpe(flags))

    def test_ftp_trigger_fires_when_both_outside(self):
        recs = [{"type": "ftp_gain", "status": "reconciled", "reconciled": "2026-04-01",
                 "delta": "outside (1.0pp below range)"},
                {"type": "ftp_gain", "status": "reconciled", "reconciled": "2026-05-01",
                 "delta": "outside (0.5pp above range)"}]
        self.assertEqual(check_ftp_trigger(recs)["status"], "recalibration_needed")

    def test_ftp_trigger_ok_when_one_inside(self):
        recs = [{"type": "ftp_gain", "status": "reconciled", "reconciled": "2026-04-01",
                 "delta": "inside"},
                {"type": "ftp_gain", "status": "reconciled", "reconciled": "2026-05-01",
                 "delta": "outside (0.5pp above range)"}]
        self.assertEqual(check_ftp_trigger(recs)["status"], "ok")


class TestCLI(unittest.TestCase):
    def test_parser_predict_args(self):
        args = build_parser().parse_args(
            ["--mode", "predict", "--type", "rpe_at_if", "--if", "0.84",
             "--slot", "post_3pm", "--session-date", "2026-06-02",
             "--session-type", "Threshold"])
        self.assertEqual(args.mode, "predict")
        self.assertEqual(args.if_value, 0.84)
        self.assertEqual(args.slot, "post_3pm")

    def test_parser_rejects_unknown_mode(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--mode", "bogus"])

    def test_run_predict_appends_record(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")  # missing -> DEFAULT_MODEL
            args = build_parser().parse_args(
                ["--mode", "predict", "--type", "rpe_at_if", "--if", "0.84",
                 "--slot", "morning", "--session-date", "2026-06-02",
                 "--session-type", "Threshold",
                 "--ledger-path", ledger, "--calibration-path", cal])
            result = run_predict(args)
            self.assertEqual(result["logged"]["id"], "P001")
            self.assertEqual(result["logged"]["predicted"], 6)
            self.assertEqual(result["logged"]["status"], "open")
            self.assertEqual(len(load_ledger(ledger)), 1)

    def test_run_predict_second_record_increments_id(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            base = ["--mode", "predict", "--type", "ftp_gain", "--start-ftp", "188",
                    "--block-label", "FTP Builder, 4wk", "--block-end", "2026-06-28",
                    "--ledger-path", ledger, "--calibration-path", cal]
            run_predict(build_parser().parse_args(base))
            result = run_predict(build_parser().parse_args(base))
            self.assertEqual(result["logged"]["id"], "P002")

    def test_predict_rpe_without_if_exits(self):
        argv = ["prog", "--mode", "predict", "--type", "rpe_at_if",
                "--session-date", "2026-06-02", "--session-type", "Threshold"]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit):
                main()


class TestLoadLedgerMalformed(unittest.TestCase):
    """I-4: load_ledger must skip malformed lines with a WARNING, not crash."""

    def _write_ledger(self, path, lines):
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    def test_malformed_line_skipped_returns_valid_records(self):
        """One valid, one corrupt, one valid -> 2 valid records returned, no exception."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            self._write_ledger(path, [
                '{"id": "P001", "type": "rpe_at_if"}',
                'NOT_VALID_JSON{{{',
                '{"id": "P002", "type": "ftp_gain"}',
            ])
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                records = load_ledger(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["id"], "P001")
            self.assertEqual(records[1]["id"], "P002")

    def test_malformed_line_emits_warning_with_line_number(self):
        """The WARNING must mention the 1-based line number of the bad line."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            self._write_ledger(path, [
                '{"id": "P001", "type": "rpe_at_if"}',
                'CORRUPTED_LINE',
                '{"id": "P002", "type": "ftp_gain"}',
            ])
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                load_ledger(path)
            warning = buf.getvalue()
            self.assertIn("WARNING", warning)
            self.assertIn("2", warning)  # 1-based line number of bad line

    def test_empty_and_whitespace_lines_silently_skipped(self):
        """Blank/whitespace-only lines produce no WARNING and no crash."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            self._write_ledger(path, [
                '{"id": "P001", "type": "rpe_at_if"}',
                '',
                '   ',
                '{"id": "P002", "type": "ftp_gain"}',
            ])
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                records = load_ledger(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(buf.getvalue(), "")  # no warnings

    def test_multiple_malformed_lines_all_warned(self):
        """Two bad lines -> two warnings emitted, one good record returned."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            self._write_ledger(path, [
                'BAD_LINE_1',
                '{"id": "P001", "type": "rpe_at_if"}',
                'BAD_LINE_2',
            ])
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                records = load_ledger(path)
            self.assertEqual(len(records), 1)
            warning_count = buf.getvalue().count("WARNING")
            self.assertEqual(warning_count, 2)


class TestCLIRangeValidation(unittest.TestCase):
    """M-5: --if, --start-ftp, --new-ftp must be validated in main()."""

    def _run_main(self, argv):
        """Run main() with given argv, return (exit_code_or_None, stderr_text).

        Returns (None, '') if no SystemExit raised (i.e. command completed).
        Returns (exit_code, stderr_text) on SystemExit.
        """
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with patch.object(sys, "argv", argv):
                try:
                    main()
                    return (None, buf.getvalue())
                except SystemExit as e:
                    return (e.code, buf.getvalue())

    # --- --if validation ---

    def test_if_out_of_range_high_exits(self):
        code, _ = self._run_main(
            ["prog", "--mode", "predict", "--type", "rpe_at_if",
             "--if", "5.0", "--session-date", "2026-06-02", "--session-type", "Threshold"])
        self.assertIsNotNone(code)
        self.assertNotEqual(code, 0)

    def test_if_out_of_range_low_exits(self):
        code, _ = self._run_main(
            ["prog", "--mode", "predict", "--type", "rpe_at_if",
             "--if", "0.1", "--session-date", "2026-06-02", "--session-type", "Threshold"])
        self.assertIsNotNone(code)
        self.assertNotEqual(code, 0)

    def test_if_in_range_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "rpe_at_if",
                 "--if", "0.84", "--session-date", "2026-06-02", "--session-type", "Threshold",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)  # no exit -> success

    def test_if_boundary_low_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "rpe_at_if",
                 "--if", "0.3", "--session-date", "2026-06-02", "--session-type", "Threshold",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)

    def test_if_boundary_high_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "rpe_at_if",
                 "--if", "1.5", "--session-date", "2026-06-02", "--session-type", "Threshold",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)

    def test_if_not_supplied_does_not_trip_validation(self):
        """seed-baseline mode with no --if must not trigger IF range check."""
        with tempfile.TemporaryDirectory() as d:
            # vault_path must exist for collect_reviews to not error
            vault = os.path.join(d, "reviews")
            os.makedirs(vault)
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "seed-baseline",
                 "--vault-path", vault,
                 "--calibration-path", cal,
                 "--ledger-path", os.path.join(d, "ledger.jsonl")])
            # May exit 0 or None (success) — just must NOT exit with argparse error (code 2)
            self.assertNotEqual(code, 2)

    # --- --start-ftp validation ---

    def test_start_ftp_out_of_range_high_exits(self):
        code, _ = self._run_main(
            ["prog", "--mode", "predict", "--type", "ftp_gain",
             "--start-ftp", "50000",
             "--block-label", "FTP Builder", "--block-end", "2026-06-28"])
        self.assertIsNotNone(code)
        self.assertNotEqual(code, 0)

    def test_start_ftp_out_of_range_low_exits(self):
        code, _ = self._run_main(
            ["prog", "--mode", "predict", "--type", "ftp_gain",
             "--start-ftp", "10",
             "--block-label", "FTP Builder", "--block-end", "2026-06-28"])
        self.assertIsNotNone(code)
        self.assertNotEqual(code, 0)

    def test_start_ftp_in_range_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "ftp_gain",
                 "--start-ftp", "188",
                 "--block-label", "FTP Builder", "--block-end", "2026-06-28",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)

    def test_start_ftp_boundary_50_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "ftp_gain",
                 "--start-ftp", "50",
                 "--block-label", "FTP Builder", "--block-end", "2026-06-28",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)

    def test_start_ftp_boundary_500_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            cal = os.path.join(d, "cal.md")
            code, _ = self._run_main(
                ["prog", "--mode", "predict", "--type", "ftp_gain",
                 "--start-ftp", "500",
                 "--block-label", "FTP Builder", "--block-end", "2026-06-28",
                 "--ledger-path", ledger, "--calibration-path", cal])
            self.assertEqual(code, None)

    # --- --new-ftp validation ---

    def test_new_ftp_out_of_range_exits(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            code, _ = self._run_main(
                ["prog", "--mode", "reconcile",
                 "--new-ftp", "9999",
                 "--ftp-test-date", "2026-06-28",
                 "--ledger-path", ledger])
            self.assertIsNotNone(code)
            self.assertNotEqual(code, 0)

    def test_new_ftp_in_range_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            code, _ = self._run_main(
                ["prog", "--mode", "reconcile",
                 "--new-ftp", "196",
                 "--ftp-test-date", "2026-06-28",
                 "--ledger-path", ledger])
            self.assertEqual(code, None)

    def test_new_ftp_not_supplied_does_not_trip_validation(self):
        """reconcile mode without --new-ftp must not trigger FTP range check."""
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.jsonl")
            code, _ = self._run_main(
                ["prog", "--mode", "reconcile",
                 "--ledger-path", ledger])
            self.assertEqual(code, None)

    # --- error message format ---

    def test_if_error_message_format(self):
        """Error message must follow sibling script style."""
        code, stderr = self._run_main(
            ["prog", "--mode", "predict", "--type", "rpe_at_if",
             "--if", "5.0", "--session-date", "2026-06-02", "--session-type", "Threshold"])
        self.assertNotEqual(code, 0)
        self.assertIn("0.3", stderr)
        self.assertIn("1.5", stderr)
        self.assertIn("5.0", stderr)

    def test_start_ftp_error_message_format(self):
        """FTP error message must include the 50-500 range and the bad value."""
        code, stderr = self._run_main(
            ["prog", "--mode", "predict", "--type", "ftp_gain",
             "--start-ftp", "50000",
             "--block-label", "FTP Builder", "--block-end", "2026-06-28"])
        self.assertNotEqual(code, 0)
        self.assertIn("50", stderr)
        self.assertIn("500", stderr)
        self.assertIn("50000", stderr)


if __name__ == "__main__":
    unittest.main()
