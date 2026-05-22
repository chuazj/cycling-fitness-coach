#!/usr/bin/env python3
"""Tests for zwo_lint.py — the .zwo file linter.

Run: python -m unittest tests.test_zwo_lint -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from zwo_lint import lint_xml, lint_file, format_report, build_parser

VALID_ZWO = (
    '<workout_file><author>x</author><name>Test</name>'
    '<description></description><sportType>bike</sportType><tags></tags>'
    '<workout><SteadyState Duration="600" Power="0.75"/></workout></workout_file>'
)


class TestLintSkeleton(unittest.TestCase):
    def test_malformed_xml_is_e1(self):
        findings = lint_xml("<workout_file><not-closed>")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "E1")
        self.assertEqual(findings[0]["severity"], "error")

    def test_valid_file_has_no_e1(self):
        findings = lint_xml(VALID_ZWO)
        self.assertFalse(any(f["code"] == "E1" for f in findings))

    def test_format_report_clean(self):
        report = format_report("x.zwo", [], None)
        self.assertIn("0 error(s)", report)

    def test_format_report_lists_findings(self):
        f = [{"severity": "error", "code": "E1", "message": "bad", "location": ""}]
        report = format_report("x.zwo", f, None)
        self.assertIn("ERROR E1", report)


class TestLintFileIO(unittest.TestCase):
    def test_lint_file_clean(self):
        with tempfile.NamedTemporaryFile("w", suffix=".zwo", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(VALID_ZWO)
            path = fh.name
        try:
            result = lint_file(path, ftp=200)
            self.assertEqual(result["error_count"], 0)
        finally:
            os.unlink(path)

    def test_lint_file_non_utf8_is_w7(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".zwo", delete=False) as fh:
            # cp1252 'é' (0xE9) is not valid UTF-8
            fh.write(b'<workout_file><name>caf\xe9</name><workout/></workout_file>')
            path = fh.name
        try:
            result = lint_file(path, ftp=200)
            self.assertTrue(any(f["code"] == "W7" for f in result["findings"]))
        finally:
            os.unlink(path)


class TestLintCliParser(unittest.TestCase):
    def test_file_positional(self):
        ns = build_parser().parse_args(["w.zwo"])
        self.assertEqual(ns.file, "w.zwo")
        self.assertIsNone(ns.ftp)

    def test_ftp_and_output(self):
        ns = build_parser().parse_args(["w.zwo", "--ftp", "188", "-o", "r.json"])
        self.assertEqual(ns.ftp, 188)
        self.assertEqual(ns.output, "r.json")


class TestLintErrors(unittest.TestCase):
    def _codes(self, xml):
        return {f["code"] for f in lint_xml(xml)}

    def test_e2_wrong_root(self):
        self.assertIn("E2", self._codes(
            "<not_workout><workout/></not_workout>"))

    def test_e3_no_workout(self):
        self.assertIn("E3", self._codes(
            "<workout_file><name>x</name></workout_file>"))

    def test_e4_unknown_interval(self):
        self.assertIn("E4", self._codes(
            '<workout_file><workout><Bogus Duration="60"/></workout></workout_file>'))

    def test_e5_power_out_of_range(self):
        self.assertIn("E5", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="60" Power="2.5"/></workout></workout_file>'))

    def test_e6_warmup_wrong_direction(self):
        self.assertIn("E6", self._codes(
            '<workout_file><workout>'
            '<Warmup Duration="300" PowerLow="0.8" PowerHigh="0.4"/>'
            '</workout></workout_file>'))

    def test_e7_zero_duration(self):
        self.assertIn("E7", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="0" Power="0.75"/></workout></workout_file>'))

    def test_e8_textevent_in_intervalst(self):
        self.assertIn("E8", self._codes(
            '<workout_file><workout>'
            '<IntervalsT Repeat="3" OnDuration="60" OffDuration="60" '
            'OnPower="1.1" OffPower="0.5">'
            '<textevent timeoffset="10" message="go"/></IntervalsT>'
            '</workout></workout_file>'))

    def test_e5_non_numeric_power(self):
        self.assertIn("E5", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="60" Power="abc"/></workout></workout_file>'))

    def test_e7_missing_duration(self):
        self.assertIn("E7", self._codes(
            '<workout_file><workout>'
            '<SteadyState Power="0.75"/></workout></workout_file>'))

    def test_e7_intervalst_missing_onduration(self):
        self.assertIn("E7", self._codes(
            '<workout_file><workout>'
            '<IntervalsT Repeat="3" OffDuration="60" OnPower="1.1" OffPower="0.5"/>'
            '</workout></workout_file>'))

    def test_clean_file_no_errors(self):
        self.assertEqual(self._codes(VALID_ZWO), set())


class TestLintWarnings(unittest.TestCase):
    def _codes(self, xml):
        return {f["code"] for f in lint_xml(xml)}

    def test_w1_unknown_attribute(self):
        self.assertIn("W1", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="60" Power="0.75" Bogus="1"/>'
            '</workout></workout_file>'))

    def test_w2_textevent_past_duration(self):
        self.assertIn("W2", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="60" Power="0.75">'
            '<textevent timeoffset="90" message="late"/></SteadyState>'
            '</workout></workout_file>'))

    def test_w3_both_cadence_forms(self):
        self.assertIn("W3", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="60" Power="0.75" Cadence="90" '
            'CadenceLow="85" CadenceHigh="95"/></workout></workout_file>'))

    def test_w4_ftptest_without_freeride(self):
        self.assertIn("W4", self._codes(
            '<workout_file><workout ftptest="1">'
            '<SteadyState Duration="1200" Power="1.0"/></workout></workout_file>'))

    def test_w5_erg_inert_power_cue(self):
        self.assertIn("W5", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="600" Power="0.75">'
            '<textevent timeoffset="10" message="drop to 250 W"/></SteadyState>'
            '</workout></workout_file>'))

    def test_w6_erg_micro_rep(self):
        self.assertIn("W6", self._codes(
            '<workout_file><workout>'
            '<IntervalsT Repeat="8" OnDuration="20" OffDuration="40" '
            'OnPower="1.2" OffPower="0.5"/></workout></workout_file>'))

    def test_w1_cadence_range_on_freeride_and_maxeffort_ok(self):
        # FreeRide/MaxEffort legitimately carry a cadence range — must not trip W1.
        for tag in ("FreeRide", "MaxEffort"):
            xml = (f'<workout_file><workout>'
                   f'<{tag} Duration="600" CadenceLow="85" CadenceHigh="95"/>'
                   f'</workout></workout_file>')
            self.assertNotIn("W1", self._codes(xml), tag)

    def test_w5_plain_watt_label_not_flagged(self):
        # An informational watt label is not an ERG-inert *command* — no W5.
        self.assertNotIn("W5", self._codes(
            '<workout_file><workout>'
            '<SteadyState Duration="600" Power="0.95">'
            '<textevent timeoffset="10" message="Threshold 185W"/></SteadyState>'
            '</workout></workout_file>'))

    def test_w6_erg_short_rep(self):
        findings = lint_xml(
            '<workout_file><workout>'
            '<IntervalsT Repeat="5" OnDuration="60" OffDuration="60" '
            'OnPower="1.15" OffPower="0.5"/></workout></workout_file>')
        w6 = [f for f in findings if f["code"] == "W6"]
        self.assertEqual(len(w6), 1)
        self.assertIn("short rep", w6[0]["message"])

    def test_clean_file_no_warnings(self):
        self.assertEqual(self._codes(VALID_ZWO), set())


if __name__ == "__main__":
    unittest.main()
