#!/usr/bin/env python3
"""Tests for zwo_lint.py — the .zwo file linter.

Run: python -m unittest tests.test_zwo_lint -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from zwo_lint import lint_xml, lint_file, format_report

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

    def test_w8_ftptest_freeride_missing_show_avg(self):
        # FreeRide inside an ftptest workout MUST set show_avg="1" so the
        # running-power-average HUD displays during the test.
        self.assertIn("W8", self._codes(
            '<workout_file><workout ftptest="1">'
            '<Warmup Duration="300" PowerLow="0.4" PowerHigh="0.75"/>'
            '<FreeRide Duration="1200"/>'
            '<Cooldown Duration="300" PowerLow="0.5" PowerHigh="0.35"/>'
            '</workout></workout_file>'))

    def test_w8_not_flagged_when_show_avg_set(self):
        self.assertNotIn("W8", self._codes(
            '<workout_file><workout ftptest="1">'
            '<FreeRide Duration="1200" show_avg="1"/>'
            '</workout></workout_file>'))

    def test_w8_not_flagged_on_non_ftptest_workout(self):
        # show_avg is FTP-test specific; missing on a normal FreeRide is fine.
        self.assertNotIn("W8", self._codes(
            '<workout_file><workout>'
            '<FreeRide Duration="600"/></workout></workout_file>'))

    def test_clean_file_no_warnings(self):
        self.assertEqual(self._codes(VALID_ZWO), set())


class TestLintFuelCueW9(unittest.TestCase):
    """W9 — fuel-cue accuracy on ≤60min Z2 rides (IF ≤ 0.75).

    Runs in lint_file (needs computed stats), so test through lint_file.
    """

    def test_w9_flags_carb_cue_on_short_z2(self):
        # 60min ride at 0.70 IF (Z2) with a "Fuel: 30g/hr carbs" cue should fire.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="3600" Power="0.70">'
               '<textevent timeoffset="600" message="Fuel: 30g/hr carbs"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("W9", codes)

    def test_w9_silent_on_long_ride(self):
        # 90min Z2 — carb fueling is appropriate, no W9.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="5400" Power="0.70">'
               '<textevent timeoffset="600" message="Fuel: 30g/hr carbs"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("W9", codes)

    def test_w9_silent_on_high_intensity_short_ride(self):
        # 45min Threshold — fueling is appropriate at this intensity, no W9.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="2700" Power="0.95">'
               '<textevent timeoffset="600" message="Fuel: 30g/hr carbs"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("W9", codes)

    def test_w9_silent_on_zero_grams_cue(self):
        # "Fuel: water only" or "Fuel: 0g" — no carbs prescribed, no W9.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="3600" Power="0.70">'
               '<textevent timeoffset="600" message="Fuel: water + electrolytes"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("W9", codes)

    def test_w9_silent_on_conditional_grams_without_rate(self):
        # Bare "30g" without /hr is a discretionary mention ("30g if fasted"),
        # not a rate prescription — must not trip W9.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="3600" Power="0.70">'
               '<textevent timeoffset="600" '
               'message="Fuel: water/electrolyte is enough - 30g carb only if fasted"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("W9", codes)

    def test_w9_matches_per_hour_phrasing(self):
        # "30g per hour" should match too (not only /hr).
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="3600" Power="0.70">'
               '<textevent timeoffset="600" message="Fuel: 30g per hour"/>'
               '</SteadyState></workout></workout_file>')
        result = lint_file_for(xml)
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("W9", codes)


class TestLintModeledStats(unittest.TestCase):
    def test_clean_file_reports_stats(self):
        result = lint_file_for(VALID_ZWO)
        self.assertIsNotNone(result["stats"])
        self.assertEqual(result["stats"]["total_duration_min"], 10.0)

    def test_broken_file_stats_none(self):
        broken = ('<workout_file><workout>'
                  '<SteadyState Duration="0" Power="0.75"/></workout></workout_file>')
        result = lint_file_for(broken)
        self.assertIsNone(result["stats"])

    def test_lint_clean_but_unbuildable_stats_none(self):
        # Passes every lint check (Repeat is not an E-check) but workout_from_xml
        # raises — IntervalsT requires repeat > 0. The try/except fallback in
        # lint_file must yield stats=None rather than crashing.
        xml = ('<workout_file><name>x</name><workout>'
               '<IntervalsT Repeat="0" OnDuration="60" OffDuration="60" '
               'OnPower="1.0" OffPower="0.5"/></workout></workout_file>')
        result = lint_file_for(xml)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["warning_count"], 0)
        self.assertIsNone(result["stats"])

    def test_format_report_surfaces_tss_warning(self):
        # A FreeRide workout carries a placeholder-power caveat — it must reach
        # the printed report (Fix 1), not just the -o JSON.
        xml = ('<workout_file><name>x</name><workout>'
               '<SteadyState Duration="300" Power="0.6"/>'
               '<FreeRide Duration="600"/></workout></workout_file>')
        result = lint_file_for(xml)
        self.assertIsNotNone(result["stats"])
        self.assertIsNotNone(result["stats"]["tss_warning"])
        report = format_report("x.zwo", result["findings"], result["stats"])
        self.assertIn("Note:", report)

    def test_format_report_ftptest_no_literal_none(self):
        # ftptest workout: estimated_if/estimated_tss are None — the report must
        # render placeholders, not the literal "None".
        xml = ('<workout_file><name>x</name><workout ftptest="1">'
               '<Warmup Duration="300" PowerLow="0.4" PowerHigh="0.75"/>'
               '<FreeRide Duration="1200" show_avg="1"/>'
               '<Cooldown Duration="300" PowerLow="0.5" PowerHigh="0.35"/>'
               '</workout></workout_file>')
        result = lint_file_for(xml)
        self.assertIsNotNone(result["stats"])
        report = format_report("x.zwo", result["findings"], result["stats"])
        self.assertNotIn("None", report)
        self.assertIn("unmodeled", report)


def lint_file_for(xml):
    """Helper: write xml to a temp .zwo and lint it."""
    with tempfile.NamedTemporaryFile("w", suffix=".zwo", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(xml)
        path = fh.name
    try:
        return lint_file(path, ftp=188)
    finally:
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
