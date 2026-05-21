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

    def test_clean_file_no_errors(self):
        self.assertEqual(self._codes(VALID_ZWO), set())


if __name__ == "__main__":
    unittest.main()
