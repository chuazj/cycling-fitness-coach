#!/usr/bin/env python3
"""Tests using mocked HTTP responses — no live API calls.

Run: python -m unittest tests.test_with_mocks -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add scripts/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from intervals_icu_api import IntervalsIcuClient, analyze, weekly_summary, apply_compact

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def make_mock_response(status_code=200, json_data=None):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


class TestClientAuth(unittest.TestCase):
    """Test IntervalsIcuClient._get() error handling."""

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")

    @patch.object(IntervalsIcuClient, "_get")
    def test_get_activity_calls_correct_endpoint(self, mock_get):
        mock_get.return_value = {"id": "i999"}
        self.client.get_activity("i999")
        mock_get.assert_called_once_with("/activity/i999")

    def test_401_raises_auth_error(self):
        mock_resp = make_mock_response(status_code=401)
        with patch.object(self.client.session, "get", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as ctx:
                self.client._get("/activity/i999")
            self.assertIn("Authentication failed", str(ctx.exception))
            self.assertIn("401", str(ctx.exception))

    def test_404_raises_not_found(self):
        mock_resp = make_mock_response(status_code=404)
        with patch.object(self.client.session, "get", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as ctx:
                self.client._get("/activity/i999")
            self.assertIn("Not found", str(ctx.exception))

    def test_429_retries_then_raises(self):
        mock_resp = make_mock_response(status_code=429)
        with patch.object(self.client.session, "get", return_value=mock_resp):
            with patch("intervals_icu_api.time.sleep") as mock_sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    self.client._get("/activity/i999")
                self.assertIn("after 3 attempts", str(ctx.exception))
                # Should have retried twice (with delays 2s and 4s)
                self.assertEqual(mock_sleep.call_count, 2)

    def test_429_succeeds_on_retry(self):
        fail_resp = make_mock_response(status_code=429)
        ok_resp = make_mock_response(status_code=200, json_data={"id": "i999"})
        with patch.object(self.client.session, "get", side_effect=[fail_resp, ok_resp]):
            with patch("intervals_icu_api.time.sleep"):
                result = self.client._get("/activity/i999")
                self.assertEqual(result["id"], "i999")

    def test_502_retries(self):
        fail_resp = make_mock_response(status_code=502)
        ok_resp = make_mock_response(status_code=200, json_data={"ok": True})
        with patch.object(self.client.session, "get", side_effect=[fail_resp, ok_resp]):
            with patch("intervals_icu_api.time.sleep"):
                result = self.client._get("/test")
                self.assertEqual(result["ok"], True)


class TestClientNetworkErrors(unittest.TestCase):
    """Test _get() handling of ConnectionError and Timeout."""

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")

    def test_connection_error_retries_then_raises(self):
        import requests
        with patch.object(self.client.session, "get",
                          side_effect=requests.ConnectionError("connection refused")):
            with patch("intervals_icu_api.time.sleep") as mock_sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    self.client._get("/test")
                self.assertIn("ConnectionError", str(ctx.exception))
                self.assertIn("after 3 attempts", str(ctx.exception))
                self.assertEqual(mock_sleep.call_count, 2)

    def test_timeout_retries_then_raises(self):
        import requests
        with patch.object(self.client.session, "get",
                          side_effect=requests.Timeout("read timed out")):
            with patch("intervals_icu_api.time.sleep") as mock_sleep:
                with self.assertRaises(RuntimeError) as ctx:
                    self.client._get("/test")
                self.assertIn("Timeout", str(ctx.exception))
                self.assertEqual(mock_sleep.call_count, 2)

    def test_connection_error_succeeds_on_retry(self):
        import requests
        ok_resp = make_mock_response(status_code=200, json_data={"ok": True})
        with patch.object(self.client.session, "get",
                          side_effect=[requests.ConnectionError("fail"), ok_resp]):
            with patch("intervals_icu_api.time.sleep"):
                result = self.client._get("/test")
                self.assertEqual(result["ok"], True)


class TestAnalyzeWithMocks(unittest.TestCase):
    """Test analyze() orchestration with mocked API responses."""

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")
        self.activity_data = load_fixture("activity.json")
        self.intervals_data = load_fixture("intervals.json")
        self.power_curve_data = load_fixture("power_curve.json")

    def test_analyze_returns_complete_result(self):
        # Mock all API calls
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):

            result = analyze(self.client, "i999999", ftp=186, weight=75)

        # Verify key fields present
        self.assertEqual(result["source"], "intervals.icu")
        self.assertIn("activity", result)
        self.assertIn("metrics", result)
        self.assertIn("laps", result)

        # Verify activity data
        self.assertEqual(result["activity"]["id"], "i999999")
        self.assertEqual(result["activity"]["context"], "indoor")
        self.assertTrue(result["activity"]["trainer"])

        # Verify metrics use pre-computed values
        self.assertEqual(result["metrics"]["normalized_power"], 172)
        self.assertAlmostEqual(result["metrics"]["intensity_factor"], 0.92, places=2)

    def test_analyze_with_missing_streams(self):
        """analyze() should handle missing streams gracefully."""
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", side_effect=Exception("streams unavailable")), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):

            result = analyze(self.client, "i999999", ftp=186, weight=75)

        # Should still succeed with partial data
        self.assertEqual(result["source"], "intervals.icu")
        # Streams failure logged in data_warnings
        self.assertIn("data_warnings", result)
        self.assertTrue(any("streams" in w for w in result["data_warnings"]))

    def test_analyze_with_missing_power_curve(self):
        """analyze() should handle missing power curve gracefully."""
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", side_effect=Exception("no power curve")):

            result = analyze(self.client, "i999999", ftp=186, weight=75)

        self.assertEqual(result["source"], "intervals.icu")
        # Power curve failure logged in data_warnings
        self.assertIn("data_warnings", result)
        self.assertTrue(any("power_curve" in w for w in result["data_warnings"]))


class TestDataCompleteness(unittest.TestCase):
    """Test data_completeness field and stream validation in analyze()."""

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")
        self.activity_data = load_fixture("activity.json")
        self.intervals_data = load_fixture("intervals.json")
        self.power_curve_data = load_fixture("power_curve.json")

    def test_complete_when_all_fetches_succeed(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertEqual(result["data_completeness"], "complete")

    def test_partial_when_streams_fail(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", side_effect=Exception("fail")), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertIn("partial", result["data_completeness"])
        self.assertIn("streams", result["data_completeness"])

    def test_partial_when_all_concurrent_fail(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", side_effect=Exception("fail")), \
             patch.object(self.client, "get_streams", side_effect=Exception("fail")), \
             patch.object(self.client, "get_power_curve", side_effect=Exception("fail")):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertIn("partial", result["data_completeness"])
        self.assertIn("intervals", result["data_completeness"])
        self.assertIn("streams", result["data_completeness"])
        self.assertIn("power_curve", result["data_completeness"])

    def test_zones_none_when_no_power_stream(self):
        """Zone distribution should be None (not absent) when streams empty."""
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=[]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        # Explicit None, not absent key
        self.assertIn("zone_percent", result["metrics"])
        self.assertIsNone(result["metrics"]["zone_percent"])
        self.assertIn("zone_seconds", result["metrics"])
        self.assertIsNone(result["metrics"]["zone_seconds"])

    def test_cardiac_drift_none_when_no_streams(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=[]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertIn("cardiac_drift", result["metrics"])
        self.assertIsNone(result["metrics"]["cardiac_drift"])

    def test_estimated_power_warning(self):
        """Activities without device_watts should get estimated_power warning."""
        activity = dict(self.activity_data)
        activity["device_watts"] = False
        activity["trainer"] = False
        activity["type"] = "Ride"
        with patch.object(self.client, "get_activity", return_value=activity), \
             patch.object(self.client, "get_intervals", return_value=[]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value={}):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertTrue(any("estimated_power" in w for w in result["data_warnings"]))
        self.assertTrue(any("outdoor_no_power" in w for w in result["data_warnings"]))

    def test_short_streams_complete_but_zones_none(self):
        """Streams fetch succeeds but <30 samples: data_completeness='complete', zones=None, warning emitted."""
        short_streams = {"watts": [200] * 20, "heartrate": [140] * 20}  # only 20 samples
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=[]), \
             patch.object(self.client, "get_streams", return_value=short_streams), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        # Fetch succeeded, so data_completeness is "complete"
        self.assertEqual(result["data_completeness"], "complete")
        # But streams too short for zone/drift analysis
        self.assertIsNone(result["metrics"]["zone_percent"])
        self.assertIsNone(result["metrics"]["cardiac_drift"])
        # Warning should be emitted
        self.assertTrue(any("streams_too_short" in w for w in result["data_warnings"]))


class TestWeeklySummaryOptimization(unittest.TestCase):
    """Test that weekly_summary fetches power curves only for top-3 TSS activities."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_fetches_only_top_3_by_tss(self):
        """Should call get_power_curve at most 3 times, for highest-TSS activities."""
        from datetime import datetime, timedelta
        now = datetime.now()
        activities = [
            {"id": f"i{i}", "name": f"Ride {i}", "moving_time": 3600,
             "start_date_local": (now - timedelta(days=i)).strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": tss, "icu_intensity": 80, "icu_joules": 500000}
            for i, tss in enumerate([40, 80, 60, 100, 30], start=1)
        ]
        power_curve_calls = []

        def mock_power_curve(aid):
            power_curve_calls.append(aid)
            return {"secs": [1200], "watts": [200]}

        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve", side_effect=mock_power_curve):
            result = weekly_summary(self.client, days=7, ftp=192, weight=74)

        # Should fetch exactly 3 power curves (top-3 TSS: 100, 80, 60)
        self.assertEqual(len(power_curve_calls), 3)
        # The top-TSS activity IDs should be fetched
        self.assertIn("i4", power_curve_calls)  # TSS 100
        self.assertIn("i2", power_curve_calls)  # TSS 80
        self.assertIn("i3", power_curve_calls)  # TSS 60

    def test_no_activities_returns_error(self):
        with patch.object(self.client, "list_activities", return_value=[]):
            result = weekly_summary(self.client, days=7)
        self.assertIn("error", result)
        self.assertEqual(result["activity_count"], 0)

    def test_fewer_than_3_activities(self):
        """Should handle fewer than 3 activities without error."""
        from datetime import datetime, timedelta
        now = datetime.now()
        activities = [
            {"id": "i1", "name": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 85, "icu_joules": 600000}
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve",
                          return_value={"secs": [1200], "watts": [210]}):
            result = weekly_summary(self.client, days=7, ftp=192, weight=74)
        self.assertEqual(result["activity_count"], 1)

    def test_ftp_suggestion_above_3pct(self):
        """FTP suggestion should trigger when 20min peak implies >3% increase."""
        from datetime import datetime, timedelta
        now = datetime.now()
        ftp = 192
        # 20min peak of 213W → suggested FTP = 213 * 0.95 = 202.35 → 202W → +5.2% > 3%
        activities = [
            {"id": "i1", "name": "Hard Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 90, "icu_joules": 700000}
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve",
                          return_value={"secs": [1200], "watts": [213]}):
            result = weekly_summary(self.client, days=7, ftp=ftp, weight=74)
        self.assertTrue(result["ftp_update_suggested"])
        self.assertGreater(result["suggested_ftp"], ftp)

    def test_ftp_suggestion_within_3pct(self):
        """FTP suggestion should NOT trigger when 20min peak implies <=3% increase."""
        from datetime import datetime, timedelta
        now = datetime.now()
        ftp = 192
        # 20min peak of 200W → suggested FTP = 200 * 0.95 = 190W → -1% ≤ 3%
        activities = [
            {"id": "i1", "name": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 60, "icu_intensity": 80, "icu_joules": 500000}
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve",
                          return_value={"secs": [1200], "watts": [200]}):
            result = weekly_summary(self.client, days=7, ftp=ftp, weight=74)
        self.assertFalse(result["ftp_update_suggested"])


class TestCompactMode(unittest.TestCase):
    """Test apply_compact filtering using the real module-level function."""

    def test_compact_removes_vi_ef_zone_seconds(self):
        result = {
            "metrics": {
                "normalized_power": 180,
                "variability_index": 1.05,
                "efficiency_factor": 1.2,
                "zone_seconds": {"Z1": 100, "Z2": 200},
                "zone_percent": {"Z1": 33, "Z2": 67},
                "tss": 55,
            },
            "laps": [
                {"name": "Lap 1", "average_watts": 180, "distance": 5000, "max_watts": 300, "intensity": 0.9},
            ],
        }
        result = apply_compact(result)

        self.assertNotIn("variability_index", result["metrics"])
        self.assertNotIn("efficiency_factor", result["metrics"])
        self.assertNotIn("zone_seconds", result["metrics"])
        self.assertIn("zone_percent", result["metrics"])
        self.assertIn("tss", result["metrics"])
        self.assertNotIn("distance", result["laps"][0])
        self.assertNotIn("max_watts", result["laps"][0])
        self.assertIn("average_watts", result["laps"][0])

    def test_compact_preserves_essential_fields(self):
        """Compact mode must preserve all coaching-essential fields."""
        result = {
            "activity": {"id": "i1", "name": "Ride"},
            "data_completeness": "complete",
            "data_warnings": [],
            "metrics": {
                "normalized_power": 180,
                "intensity_factor": 0.94,
                "tss": 55,
                "peak_powers": {"5s": 500, "20min": 200},
                "zone_percent": {"Z1": 10, "Z2": 50, "Z3": 40},
                "cardiac_drift": 3.2,
                "variability_index": 1.05,
                "efficiency_factor": 1.2,
                "zone_seconds": {"Z1": 100},
            },
            "laps": [],
        }
        result = apply_compact(result)
        # All essential fields preserved
        for key in ("normalized_power", "intensity_factor", "tss", "peak_powers",
                     "zone_percent", "cardiac_drift"):
            self.assertIn(key, result["metrics"])


if __name__ == "__main__":
    unittest.main()
