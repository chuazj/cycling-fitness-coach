#!/usr/bin/env python3
"""Integration tests for PMC calculator with mocked API client.

Run: python -m unittest tests.test_pmc_integration -v
"""

import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add scripts/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from pmc_calculator import bootstrap, weekly_update, extract_peak_powers, compute_pmc
from intervals_icu_api import IntervalsIcuClient


def make_activity(date_str, tss, name="Ride", aid=None):
    """Helper to create a mock activity dict."""
    return {
        "id": aid or f"i{abs(hash(date_str)) % 100000}",
        "name": name,
        "start_date_local": f"{date_str}T08:00:00",
        "icu_training_load": tss,
        "type": "VirtualRide",
    }


class TestBootstrapWithMocks(unittest.TestCase):
    """Test bootstrap() with mocked API."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_bootstrap_empty_history(self):
        """No activities in period should return zeroed PMC."""
        with patch.object(self.client, "list_activities", return_value=[]):
            result = bootstrap(self.client, days=90)
        self.assertEqual(result["mode"], "bootstrap")
        self.assertEqual(result["activities_found"], 0)
        self.assertEqual(result["ctl"], 0.0)
        self.assertEqual(result["atl"], 0.0)
        self.assertEqual(result["tsb"], 0.0)
        self.assertEqual(result["peak_powers"], {})

    def test_bootstrap_with_activities(self):
        """Activities should produce non-zero CTL/ATL."""
        today = datetime.now()
        activities = [
            make_activity((today - timedelta(days=i)).strftime("%Y-%m-%d"), tss=60)
            for i in range(1, 15)
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value={"5s": 500, "20min": 200}):
            result = bootstrap(self.client, days=90)
        self.assertGreater(result["ctl"], 0)
        self.assertGreater(result["atl"], 0)
        self.assertEqual(result["activities_found"], 14)

    def test_bootstrap_weekly_avg(self):
        """Weekly average should reflect recent training."""
        today = datetime.now()
        # 7 activities in last 7 days, 60 TSS each = ~420/week
        activities = [
            make_activity((today - timedelta(days=i)).strftime("%Y-%m-%d"), tss=60)
            for i in range(1, 8)
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value={}):
            result = bootstrap(self.client, days=90)
        # Weekly avg over 4 weeks (only 1 week has data): 420 / 4 = 105
        self.assertGreater(result["weekly_tss_avg_last_4"], 0)


class TestWeeklyUpdateWithMocks(unittest.TestCase):
    """Test weekly_update() with mocked API."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_weekly_update_completion_rate(self):
        """Completion rate should reflect actual vs planned."""
        plan_start = "2026-03-16"
        activities = [
            make_activity("2026-03-16", tss=65),
            make_activity("2026-03-18", tss=70),
        ]
        planned = {"Tue": 65, "Thu": 70, "Sat": 80, "Flex": 55}
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value={}):
            result = weekly_update(
                self.client, week_num=1, plan_start=plan_start,
                prev_ctl=40.0, prev_atl=45.0, planned_tss=planned,
            )
        # Actual: 65 + 70 = 135, Planned: 270
        self.assertEqual(result["mode"], "weekly_update")
        self.assertEqual(result["week"], 1)
        self.assertAlmostEqual(result["completion_rate"], 135 / 270, places=2)

    def test_weekly_update_no_activities(self):
        """Empty week should yield 0 completion."""
        with patch.object(self.client, "list_activities", return_value=[]), \
             patch("pmc_calculator.extract_peak_powers", return_value={}):
            result = weekly_update(
                self.client, week_num=1, plan_start="2026-03-16",
                prev_ctl=40.0, prev_atl=45.0,
                planned_tss={"Tue": 65, "Thu": 70},
            )
        self.assertEqual(result["actual_tss"]["total"], 0)
        self.assertEqual(result["completion_rate"], 0)

    def test_weekly_update_peak_deltas(self):
        """Peak power deltas should compute correctly."""
        activities = [make_activity("2026-03-16", tss=80)]
        prev_peaks = {"5s": 400, "20min": 190}
        new_peaks = {"5s": 420, "20min": 195}
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value=new_peaks):
            result = weekly_update(
                self.client, week_num=1, plan_start="2026-03-16",
                prev_ctl=40.0, prev_atl=45.0,
                planned_tss={"Tue": 80},
                prev_peaks=prev_peaks,
            )
        self.assertIn("5s", result["peak_power_deltas"])
        self.assertIn("+", result["peak_power_deltas"]["5s"])


class TestExtractPeakPowers(unittest.TestCase):
    """Test extract_peak_powers() with mocked client."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_empty_activities(self):
        result = extract_peak_powers([], self.client)
        self.assertEqual(result, {})

    def test_no_tss_activities(self):
        """Activities without TSS should be filtered out."""
        activities = [{"id": "i1", "icu_training_load": None}]
        result = extract_peak_powers(activities, self.client)
        self.assertEqual(result, {})

    def test_concurrent_failures_still_return_partial(self):
        """Some power curve fetches failing should not crash."""
        activities = [
            {"id": "i1", "icu_training_load": 80},
            {"id": "i2", "icu_training_load": 60},
        ]
        def mock_power_curve(aid):
            if aid == "i1":
                return {"secs": [5, 60, 300, 1200], "watts": [500, 300, 250, 200]}
            raise Exception("fetch failed")

        with patch.object(self.client, "get_power_curve", side_effect=mock_power_curve):
            result = extract_peak_powers(activities, self.client)
        # Should have peaks from i1 at least
        self.assertIn("5s", result)
        self.assertEqual(result["5s"], 500)


class TestTrainingDayPattern(unittest.TestCase):
    """Test training_day_pattern in bootstrap output."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_pattern_detects_frequent_days(self):
        """Should return most frequent training days."""
        today = datetime.now()
        # Create activities on known days: mostly Tue/Thu/Sat pattern
        activities = []
        for week in range(4):
            base = today - timedelta(weeks=week)
            # Find this week's Tuesday (weekday 1)
            tue = base - timedelta(days=base.weekday() - 1)
            thu = tue + timedelta(days=2)
            sat = tue + timedelta(days=4)
            for d in [tue, thu, sat]:
                activities.append(make_activity(d.strftime("%Y-%m-%d"), tss=60))

        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value={}):
            result = bootstrap(self.client, days=90)

        self.assertIn("training_day_pattern", result)
        pattern = result["training_day_pattern"]
        self.assertGreater(len(pattern), 0)
        self.assertLessEqual(len(pattern), 4)
        # Tue/Thu/Sat should be in the top days
        self.assertIn("Tue", pattern)
        self.assertIn("Thu", pattern)
        self.assertIn("Sat", pattern)

    def test_empty_history_returns_empty_pattern(self):
        with patch.object(self.client, "list_activities", return_value=[]):
            result = bootstrap(self.client, days=90)
        self.assertEqual(result["training_day_pattern"], [])

    def test_single_day_pattern(self):
        """One activity should produce a 1-element pattern."""
        today = datetime.now()
        activities = [make_activity(today.strftime("%Y-%m-%d"), tss=50)]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch("pmc_calculator.extract_peak_powers", return_value={}):
            result = bootstrap(self.client, days=90)
        self.assertEqual(len(result["training_day_pattern"]), 1)


if __name__ == "__main__":
    unittest.main()
