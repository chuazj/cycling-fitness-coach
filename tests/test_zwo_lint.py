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


if __name__ == "__main__":
    unittest.main()
