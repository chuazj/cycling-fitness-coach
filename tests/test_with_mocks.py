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

from intervals_icu_api import (
    IntervalsIcuClient,
    analyze,
    apply_compact,
    format_readiness_check,
    weekly_summary,
    wellness_summary,
)

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


class TestFetchErrorsField(unittest.TestCase):
    """B6: analyze() output exposes a structured fetch_errors dict
    so programmatic consumers can quickly check which concurrent fetch failed.
    """

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")
        self.activity_data = load_fixture("activity.json")
        self.intervals_data = load_fixture("intervals.json")
        self.power_curve_data = load_fixture("power_curve.json")

    def test_fetch_errors_empty_on_full_success(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertIn("fetch_errors", result)
        self.assertEqual(result["fetch_errors"], {})

    def test_fetch_errors_records_streams_failure(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", side_effect=Exception("boom")), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertIn("streams", result["fetch_errors"])
        self.assertIn("boom", result["fetch_errors"]["streams"])
        self.assertNotIn("intervals", result["fetch_errors"])
        self.assertNotIn("power_curve", result["fetch_errors"])

    def test_fetch_errors_records_all_three(self):
        with patch.object(self.client, "get_activity", return_value=self.activity_data), \
             patch.object(self.client, "get_intervals", side_effect=Exception("intervals_boom")), \
             patch.object(self.client, "get_streams", side_effect=Exception("streams_boom")), \
             patch.object(self.client, "get_power_curve", side_effect=Exception("curve_boom")):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertEqual(set(result["fetch_errors"].keys()), {"intervals", "streams", "power_curve"})


class TestIFOutOfRangeWarning(unittest.TestCase):
    """B3: When icu_intensity is out of plausible range [0.3, 2.0],
    the stored value is dropped with a warning rather than silently."""

    def setUp(self):
        self.client = IntervalsIcuClient("test_athlete", "test_key")
        self.intervals_data = load_fixture("intervals.json")
        self.power_curve_data = load_fixture("power_curve.json")

    def _activity_with_intensity(self, intensity_pct):
        a = load_fixture("activity.json")
        a["icu_intensity"] = intensity_pct
        return a

    def test_out_of_range_high_drops_with_warning(self):
        # icu_intensity=250 means IF=2.5, well above the 2.0 ceiling
        a = self._activity_with_intensity(250)
        with patch.object(self.client, "get_activity", return_value=a), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        # IF should fall back to NP/FTP (172/192 ≈ 0.896)
        self.assertAlmostEqual(result["metrics"]["intensity_factor"], 0.896, places=2)
        # Warning should surface in data_warnings
        self.assertTrue(any("if_out_of_range" in w for w in result["data_warnings"]),
                        f"Expected if_out_of_range warning, got: {result['data_warnings']}")

    def test_in_range_no_warning(self):
        a = self._activity_with_intensity(92)  # IF=0.92, valid
        with patch.object(self.client, "get_activity", return_value=a), \
             patch.object(self.client, "get_intervals", return_value=self.intervals_data["icu_intervals"]), \
             patch.object(self.client, "get_streams", return_value={}), \
             patch.object(self.client, "get_power_curve", return_value=self.power_curve_data):
            result = analyze(self.client, "i999", ftp=192, weight=74)
        self.assertAlmostEqual(result["metrics"]["intensity_factor"], 0.92, places=2)
        self.assertFalse(any("if_out_of_range" in w for w in result["data_warnings"]))


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

    def test_excludes_non_cycling_from_top3(self):
        """Top-3 power curve selection must skip non-cycling activities even when
        their TSS is higher. A Run-with-high-TSS would otherwise pollute week_peaks
        with non-cycling power data (some watches estimate run power)."""
        from datetime import datetime, timedelta
        now = datetime.now()
        activities = [
            # Run with highest TSS — must NOT be selected for power curve fetch
            {"id": "run1", "name": "Marathon", "type": "Run", "moving_time": 14400,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 200, "icu_intensity": 80, "icu_joules": 800000},
            # 3 cycling rides with lower TSS — all 3 should be selected
            {"id": "ride1", "name": "Z2", "type": "Ride", "moving_time": 3600,
             "start_date_local": (now - timedelta(days=1)).strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 85, "icu_joules": 500000},
            {"id": "ride2", "name": "Tempo", "type": "VirtualRide", "moving_time": 3600,
             "start_date_local": (now - timedelta(days=2)).strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 60, "icu_intensity": 80, "icu_joules": 450000},
            {"id": "ride3", "name": "Recovery", "type": "Ride", "moving_time": 3600,
             "start_date_local": (now - timedelta(days=3)).strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 50, "icu_intensity": 75, "icu_joules": 400000},
        ]
        power_curve_calls = []

        def mock_power_curve(aid):
            power_curve_calls.append(aid)
            return {"secs": [1200], "watts": [200]}

        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve", side_effect=mock_power_curve):
            result = weekly_summary(self.client, days=7, ftp=192, weight=74)

        # Run with highest TSS must NOT be fetched
        self.assertNotIn("run1", power_curve_calls)
        # All 3 cycling rides should be fetched
        self.assertEqual(set(power_curve_calls), {"ride1", "ride2", "ride3"})
        # Activity count reflects cycling-only aggregation
        self.assertEqual(result["activity_count"], 3)

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

    def test_power_profile_populated_when_weight_provided(self):
        """weekly_summary should expose the full week_peaks dict and call
        analyze_power_profile when weight is provided so the workflow's
        Power Profile table can be filled."""
        from datetime import datetime
        now = datetime.now()
        activities = [
            {"id": "i1", "name": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 90, "icu_joules": 600000}
        ]
        # Curve covers all profile durations
        curve = {"secs": [5, 60, 300, 1200], "watts": [800, 400, 280, 220]}
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve", return_value=curve):
            result = weekly_summary(self.client, days=7, ftp=200, weight=70)

        self.assertIn("week_peaks", result)
        self.assertEqual(set(result["week_peaks"].keys()), {"5s", "1min", "5min", "20min"})
        self.assertEqual(result["week_peaks"]["5s"], 800.0)
        self.assertEqual(result["week_peaks"]["20min"], 220.0)

        self.assertIn("power_profile", result)
        profile = result["power_profile"]
        self.assertIn("w_per_kg", profile)
        # 800/70 ≈ 11.43 W/kg for 5s
        self.assertAlmostEqual(profile["w_per_kg"]["5s"], 11.43, places=2)
        self.assertIn("profile_type", profile)

    def test_power_profile_omitted_when_no_weight(self):
        """If weight is missing/zero, power_profile is skipped (W/kg meaningless)."""
        from datetime import datetime
        now = datetime.now()
        activities = [
            {"id": "i1", "name": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 50, "icu_intensity": 80, "icu_joules": 500000}
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve",
                          return_value={"secs": [1200], "watts": [200]}):
            result = weekly_summary(self.client, days=7, ftp=200, weight=0)
        self.assertNotIn("power_profile", result)
        # week_peaks should still be populated (it doesn't need weight)
        self.assertIn("week_peaks", result)

    def test_power_curve_errors_empty_on_success(self):
        """When all power-curve fetches succeed, the errors dict is present but empty."""
        from datetime import datetime
        now = datetime.now()
        activities = [
            {"id": "ride1", "name": "Z2", "type": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 80, "icu_joules": 500000},
        ]
        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve",
                          return_value={"secs": [1200], "watts": [200]}):
            result = weekly_summary(self.client, days=7, ftp=192, weight=74)
        self.assertIn("power_curve_errors", result)
        self.assertEqual(result["power_curve_errors"], {})

    def test_power_curve_errors_records_per_activity_failures(self):
        """Per-activity power-curve fetch errors should surface keyed by activity id —
        mirrors analyze()'s fetch_errors pattern so callers can distinguish
        'no peaks because no activities' from 'no peaks because fetch failed'."""
        from datetime import datetime, timedelta
        now = datetime.now()
        activities = [
            {"id": "ride1", "name": "Z2", "type": "Ride", "moving_time": 3600,
             "start_date_local": now.strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 80, "icu_intensity": 80, "icu_joules": 500000},
            {"id": "ride2", "name": "Tempo", "type": "Ride", "moving_time": 3600,
             "start_date_local": (now - timedelta(days=1)).strftime("%Y-%m-%dT08:00:00"),
             "icu_training_load": 70, "icu_intensity": 85, "icu_joules": 450000},
        ]

        def selective_failure(aid):
            if aid == "ride2":
                raise RuntimeError("HTTP 503 from intervals.icu")
            return {"secs": [1200], "watts": [200]}

        with patch.object(self.client, "list_activities", return_value=activities), \
             patch.object(self.client, "get_power_curve", side_effect=selective_failure):
            result = weekly_summary(self.client, days=7, ftp=192, weight=74)
        self.assertIn("power_curve_errors", result)
        self.assertIn("ride2", result["power_curve_errors"])
        self.assertIn("503", result["power_curve_errors"]["ride2"])
        self.assertNotIn("ride1", result["power_curve_errors"])
        # Successful fetch should still produce week_peaks
        self.assertIn("week_peaks", result)

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


class TestWellnessSummary(unittest.TestCase):
    """Test wellness_summary aggregator + Yellow/Red flag detection."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def _wellness_record(self, date, **kwargs):
        return {"id": date, **kwargs}

    def test_no_wellness_returns_error(self):
        with patch.object(self.client, "get_wellness", return_value=[]):
            result = wellness_summary(self.client, days=14)
        self.assertIn("error", result)
        self.assertEqual(result["days_with_data"], 0)

    def test_fetch_failure_returns_error(self):
        def boom(*a, **kw):
            raise RuntimeError("network down")
        with patch.object(self.client, "get_wellness", side_effect=boom):
            result = wellness_summary(self.client, days=14)
        self.assertIn("error", result)
        self.assertIn("network down", result["error"])

    def test_single_record_partial_baseline_suppresses_deviation_flags(self):
        """A single daily wellness record can't fire RHR/HRV deviation flags
        because there's no historical baseline to compare against."""
        records = [
            self._wellness_record("2026-04-27", restingHR=80, hrv=40),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertTrue(result["partial_baseline"])
        self.assertEqual(result["history_days"], 0)
        self.assertEqual(result["baseline"], {})
        # No RHR/HRV flag should fire — baseline is empty
        deviation_flags = [f for f in result["flags"] if f["signal"] in ("RHR", "HRV")]
        self.assertEqual(deviation_flags, [])
        self.assertIsNotNone(result["baseline_note"])

    def test_single_record_still_fires_latest_day_only_flags(self):
        """Single-record windows can still fire sleep <6h and subjective ≥4 flags."""
        records = [
            self._wellness_record("2026-04-27", sleepSecs=18000, fatigue=4),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertTrue(result["partial_baseline"])
        signals = {f["signal"] for f in result["flags"]}
        self.assertIn("sleep", signals)
        self.assertIn("fatigue", signals)

    def test_baseline_excludes_latest_day(self):
        """Baseline averages history only — today is compared against rolling baseline."""
        records = [
            self._wellness_record("2026-04-25", restingHR=50),
            self._wellness_record("2026-04-26", restingHR=52),
            self._wellness_record("2026-04-27", restingHR=80),  # Latest — excluded
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        # Baseline = avg of first two days only (50 + 52) / 2 = 51
        self.assertEqual(result["baseline"]["resting_hr_avg"], 51.0)
        self.assertEqual(result["latest"]["resting_hr"], 80)

    # NOTE: Original n=2-history flag-firing tests removed — superseded by
    # TestWellnessFlagFiringAtMatureBaseline below, which asserts the same
    # firing logic at n=7 history (R1: deviation flags require ≥7 days of
    # history to fire, since shorter windows are statistically noise).

    def test_yellow_flag_short_sleep(self):
        records = [
            self._wellness_record("2026-04-26", sleepSecs=27000),
            # 5h sleep last night = 18000s
            self._wellness_record("2026-04-27", sleepSecs=18000),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        sleep_flags = [f for f in result["flags"] if f["signal"] == "sleep"]
        self.assertEqual(len(sleep_flags), 1)
        self.assertEqual(sleep_flags[0]["value"], 5.0)

    def test_subjective_fatigue_flag(self):
        records = [
            self._wellness_record("2026-04-26", fatigue=2),
            self._wellness_record("2026-04-27", fatigue=4),  # worst tier
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        fatigue_flags = [f for f in result["flags"] if f["signal"] == "fatigue"]
        self.assertEqual(len(fatigue_flags), 1)
        self.assertEqual(fatigue_flags[0]["severity"], "yellow")

    def test_all_green_status(self):
        records = [
            self._wellness_record("2026-04-25", restingHR=50, hrv=70, sleepSecs=27000),
            self._wellness_record("2026-04-26", restingHR=51, hrv=71, sleepSecs=28800),
            self._wellness_record("2026-04-27", restingHR=51, hrv=72, sleepSecs=27000),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["overall_status"], "green")
        self.assertEqual(result["flags"], [])

    def test_records_sorted_ascending(self):
        """Should sort regardless of API response order."""
        records = [
            self._wellness_record("2026-04-27", restingHR=55),
            self._wellness_record("2026-04-25", restingHR=50),
            self._wellness_record("2026-04-26", restingHR=52),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        dates = [d["date"] for d in result["daily"]]
        self.assertEqual(dates, ["2026-04-25", "2026-04-26", "2026-04-27"])

    def test_sleep_hours_conversion(self):
        records = [
            self._wellness_record("2026-04-27", sleepSecs=27000),  # 7.5h
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["latest"]["sleep_hours"], 7.5)

    # Whoop-synced fields (readiness/respiration/spO2/sleepScore) — plan §10
    # intervals.icu API key for SpO2 is `spO2` (camelCase), not `spo2`.

    def test_extracts_whoop_synced_fields(self):
        records = [
            self._wellness_record(
                "2026-05-12",
                restingHR=60, hrv=48.3, sleepSecs=29940,
                readiness=57.0, respiration=13.4, spO2=94.0, sleepScore=97.0,
            ),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        latest = result["latest"]
        self.assertEqual(latest["readiness"], 57.0)
        self.assertEqual(latest["respiration"], 13.4)
        self.assertEqual(latest["spo2"], 94.0)
        self.assertEqual(latest["sleep_score"], 97.0)

    def test_red_flag_recovery_below_34(self):
        records = [
            self._wellness_record("2026-05-10", readiness=60),
            self._wellness_record("2026-05-11", readiness=55),
            self._wellness_record("2026-05-12", readiness=25),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(len(recovery_flags), 1)
        self.assertEqual(recovery_flags[0]["severity"], "red")
        self.assertEqual(recovery_flags[0]["value"], 25)
        self.assertEqual(result["overall_status"], "red")

    def test_yellow_flag_recovery_34_to_66(self):
        records = [
            self._wellness_record("2026-05-10", readiness=80),
            self._wellness_record("2026-05-11", readiness=75),
            self._wellness_record("2026-05-12", readiness=50),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(len(recovery_flags), 1)
        self.assertEqual(recovery_flags[0]["severity"], "yellow")

    def test_green_recovery_67_plus_no_flag(self):
        records = [
            self._wellness_record("2026-05-10", readiness=70),
            self._wellness_record("2026-05-11", readiness=72),
            self._wellness_record("2026-05-12", readiness=80),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(recovery_flags, [])

    def test_recovery_threshold_boundary_34(self):
        """Recovery == 34 should be yellow, not red (red is <34)."""
        records = [
            self._wellness_record("2026-05-11", readiness=70),
            self._wellness_record("2026-05-12", readiness=34),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(recovery_flags[0]["severity"], "yellow")

    def test_recovery_threshold_boundary_67(self):
        """Recovery == 67 should fire no flag (green starts at 67)."""
        records = [
            self._wellness_record("2026-05-11", readiness=70),
            self._wellness_record("2026-05-12", readiness=67),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(recovery_flags, [])

    def test_recovery_absent_no_flag(self):
        """No readiness in record → no recovery flag, no crash."""
        records = [
            self._wellness_record("2026-05-11", restingHR=55),
            self._wellness_record("2026-05-12", restingHR=56),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(recovery_flags, [])

    def test_recovery_in_baseline(self):
        """readiness should be averaged into baseline like rhr/hrv/sleep."""
        records = [
            self._wellness_record("2026-05-10", readiness=60),
            self._wellness_record("2026-05-11", readiness=80),
            self._wellness_record("2026-05-12", readiness=50),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        # baseline = mean of history (first 2 days) = (60+80)/2 = 70
        self.assertEqual(result["baseline"]["readiness_avg"], 70.0)

    def test_recovery_zero_is_valid_red_flag(self):
        """Recovery=0 is Whoop's lowest valid value (total wreck); must fire red.
        Guards against a truthiness regression (`if d['readiness']` would skip 0)."""
        records = [
            self._wellness_record("2026-05-11", readiness=50),
            self._wellness_record("2026-05-12", readiness=0),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(len(recovery_flags), 1)
        self.assertEqual(recovery_flags[0]["severity"], "red")
        self.assertEqual(recovery_flags[0]["value"], 0)

    def test_recovery_fires_under_partial_baseline(self):
        """Recovery uses absolute thresholds, not deviation — must fire even with
        a single record (where RHR/HRV deviation flags are suppressed)."""
        records = [
            self._wellness_record("2026-05-12", readiness=20, restingHR=80, hrv=40),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertTrue(result["partial_baseline"])
        recovery_flags = [f for f in result["flags"] if f["signal"] == "recovery"]
        self.assertEqual(len(recovery_flags), 1)
        self.assertEqual(recovery_flags[0]["severity"], "red")
        # RHR and HRV flags should be suppressed (no baseline)
        deviation_flags = [f for f in result["flags"] if f["signal"] in ("RHR", "HRV")]
        self.assertEqual(deviation_flags, [])

    def test_latest_date_age_zero_when_logged_today(self):
        """A record dated today should produce latest_date_age_days = 0."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        records = [
            self._wellness_record("2026-04-25", restingHR=50),
            self._wellness_record(today, restingHR=52),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["latest_date_age_days"], 0)

    def test_latest_date_age_positive_when_stale(self):
        """A record dated several days ago should produce a positive age —
        coaching templates use this to flag stale-readiness data."""
        from datetime import datetime, timedelta
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        records = [
            self._wellness_record("2026-04-25", restingHR=50),
            self._wellness_record(three_days_ago, restingHR=52),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["latest_date_age_days"], 3)

    def test_latest_date_age_none_for_malformed_date(self):
        """A malformed date string should leave latest_date_age_days as None
        rather than raising — wellness coaching must degrade, not crash."""
        records = [
            self._wellness_record("not-a-date", restingHR=52),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertIsNone(result["latest_date_age_days"])

    def test_respiration_in_baseline(self):
        """respiration should be averaged into baseline (for illness-onset detection)."""
        records = [
            self._wellness_record("2026-05-10", respiration=13.0),
            self._wellness_record("2026-05-11", respiration=13.4),
            self._wellness_record("2026-05-12", respiration=15.0),
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["baseline"]["respiration_avg"], 13.2)


def _series(start_day, count, **kwargs):
    """Helper: build N consecutive daily wellness records from start_day with the same kwargs."""
    from datetime import date, timedelta
    base = date.fromisoformat(start_day)
    return [{"id": (base + timedelta(days=i)).isoformat(), **kwargs} for i in range(count)]


class TestBaselineMaturity(unittest.TestCase):
    """R1+R8: per-metric baseline sample sizes, tiered maturity, days_with_whoop_data."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_baseline_sample_sizes_per_metric(self):
        """baseline_sample_sizes dict reports count of non-null history values per metric.
        Latest day is excluded (it's compared against history, not part of it)."""
        records = [
            {"id": "2026-05-09", "restingHR": 58},
            {"id": "2026-05-10", "restingHR": 59, "hrv": 50},
            {"id": "2026-05-11", "restingHR": 60, "hrv": 52},
            {"id": "2026-05-12", "restingHR": 61},  # latest
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        sizes = result["baseline_sample_sizes"]
        self.assertEqual(sizes["resting_hr"], 3)
        self.assertEqual(sizes["hrv"], 2)

    def test_baseline_maturity_preliminary_when_below_7(self):
        records = _series("2026-05-01", 5, restingHR=58, hrv=50, respiration=13.0)
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["baseline_maturity"], "preliminary")
        self.assertIn("preliminary", (result.get("baseline_note") or "").lower())

    def test_baseline_maturity_consolidating_when_7_to_13(self):
        records = _series("2026-05-01", 8, restingHR=58, hrv=50, respiration=13.0)
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["baseline_maturity"], "consolidating")

    def test_baseline_maturity_stable_when_14_plus(self):
        records = _series("2026-05-01", 15, restingHR=58, hrv=50, respiration=13.0)
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["baseline_maturity"], "stable")
        # Stable baseline → no maturity warning
        self.assertIsNone(result.get("baseline_note"))

    def test_baseline_maturity_insufficient_when_no_history(self):
        records = [{"id": "2026-05-12", "restingHR": 60}]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["baseline_maturity"], "insufficient")

    def test_rhr_deviation_suppressed_when_sample_size_below_7(self):
        """With only 3 days of history, RHR deviation flag is noise — suppress."""
        records = [
            {"id": "2026-05-09", "restingHR": 50},
            {"id": "2026-05-10", "restingHR": 52},
            {"id": "2026-05-11", "restingHR": 51},
            {"id": "2026-05-12", "restingHR": 62},  # +11 vs ~51 baseline
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual([f for f in result["flags"] if f["signal"] == "RHR"], [])

    def test_rhr_deviation_fires_when_sample_size_at_or_above_7(self):
        records = _series("2026-05-01", 7, restingHR=50)
        records.append({"id": "2026-05-08", "restingHR": 62})  # +12 vs 50
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        rhr_flags = [f for f in result["flags"] if f["signal"] == "RHR"]
        self.assertEqual(len(rhr_flags), 1)
        self.assertEqual(rhr_flags[0]["severity"], "red")

    def test_hrv_deviation_suppressed_when_sample_size_below_7(self):
        records = [
            {"id": "2026-05-09", "hrv": 70},
            {"id": "2026-05-10", "hrv": 72},
            {"id": "2026-05-11", "hrv": 60},  # -15% vs 71
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual([f for f in result["flags"] if f["signal"] == "HRV"], [])

    def test_days_with_whoop_data_counts_records_with_at_least_one_whoop_field(self):
        records = [
            {"id": "2026-05-08"},  # null everything
            {"id": "2026-05-09", "restingHR": 58},
            {"id": "2026-05-10", "readiness": 70},
            {"id": "2026-05-11", "hrv": 50},
            {"id": "2026-05-12"},  # null everything
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual(result["days_with_whoop_data"], 3)
        # days_with_data (legacy) preserved for back-compat
        self.assertEqual(result["days_with_data"], 5)

    def test_days_with_whoop_data_excludes_manual_only_sleep_entries(self):
        """sleep_hours can be entered manually via the intervals.icu UI, so it
        is NOT a Whoop-only signal. A record with only sleepSecs populated
        (no other Whoop field) must NOT count as a Whoop-synced day."""
        records = [
            {"id": "2026-05-02", "sleepSecs": 28800, "sleepQuality": 2,
             "fatigue": 1, "soreness": 1},  # manual entry, no Whoop autosync
            {"id": "2026-05-12", "restingHR": 60, "hrv": 50, "readiness": 70,
             "sleepSecs": 28800, "sleepScore": 95},  # genuine Whoop sync
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        # Only the 2026-05-12 record has Whoop-exclusive fields populated
        self.assertEqual(result["days_with_whoop_data"], 1)


class TestRespirationFlag(unittest.TestCase):
    """R4: respiration deviation flag (illness-onset early warning)."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_respiration_flag_fires_above_baseline_plus_2(self):
        records = _series("2026-05-01", 8, respiration=13.0)
        records[-1] = {"id": "2026-05-08", "respiration": 15.5}  # latest +2.5
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        resp_flags = [f for f in result["flags"] if f["signal"] == "respiration"]
        self.assertEqual(len(resp_flags), 1)
        self.assertEqual(resp_flags[0]["severity"], "yellow")

    def test_respiration_flag_suppressed_when_baseline_immature(self):
        records = [
            {"id": "2026-05-09", "respiration": 13.0},
            {"id": "2026-05-10", "respiration": 13.0},
            {"id": "2026-05-11", "respiration": 15.5},  # +2.5
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual([f for f in result["flags"] if f["signal"] == "respiration"], [])

    def test_respiration_flag_no_fire_within_normal_range(self):
        records = _series("2026-05-01", 8, respiration=13.0)
        records[-1] = {"id": "2026-05-08", "respiration": 14.5}  # +1.5, under +2 threshold
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertEqual([f for f in result["flags"] if f["signal"] == "respiration"], [])


class TestWellnessSummaryLiftedFields(unittest.TestCase):
    """R6: Recovery slope + subjective-stale + training_load lifted from readiness_check."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_wellness_summary_includes_recovery_slope_3day(self):
        records = [
            {"id": "2026-05-09", "readiness": 80},
            {"id": "2026-05-10", "readiness": 75},
            {"id": "2026-05-11", "readiness": 70},
            {"id": "2026-05-12", "readiness": 65},  # -15 vs 80 (3 days ago)
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertIn("recovery_slope_3day", result)
        slope = result["recovery_slope_3day"]
        self.assertEqual(slope["today"], 65)
        self.assertEqual(slope["three_days_ago"], 80)
        self.assertEqual(slope["delta"], -15)
        slope_flags = [f for f in result["flags"] if f["signal"] == "recovery_slope"]
        self.assertEqual(len(slope_flags), 1)

    def test_recovery_slope_no_alarm_when_stable(self):
        records = [
            {"id": "2026-05-09", "readiness": 70},
            {"id": "2026-05-10", "readiness": 72},
            {"id": "2026-05-11", "readiness": 71},
            {"id": "2026-05-12", "readiness": 73},  # +3 vs 70
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        slope = result["recovery_slope_3day"]
        self.assertEqual(slope["delta"], 3)
        self.assertEqual([f for f in result["flags"] if f["signal"] == "recovery_slope"], [])

    def test_subjective_stale_warning_when_all_filled_are_1(self):
        records = [{"id": "2026-05-12", "fatigue": 1, "soreness": 1, "stress": 1, "mood": 1}]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertTrue(result["subjective_stale_warning"])

    def test_no_subjective_stale_when_varied(self):
        records = [{"id": "2026-05-12", "fatigue": 1, "soreness": 2, "stress": 1}]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertFalse(result["subjective_stale_warning"])

    def test_no_subjective_stale_when_fewer_than_3_fields(self):
        """Threshold: only suspect 'stale' when 3+ fields are filled and all equal 1."""
        records = [{"id": "2026-05-12", "fatigue": 1, "soreness": 1}]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        self.assertFalse(result["subjective_stale_warning"])

    def test_wellness_summary_includes_training_load(self):
        records = [
            {"id": "2026-05-11", "restingHR": 58, "ctl": 45.0, "atl": 50.0},
            {"id": "2026-05-12", "restingHR": 60, "ctl": 48.0, "atl": 62.0},
        ]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        tl = result["training_load"]
        self.assertEqual(tl["ctl"], 48.0)
        self.assertEqual(tl["atl"], 62.0)
        self.assertEqual(tl["tsb"], -14.0)

    def test_training_load_none_when_absent(self):
        records = [{"id": "2026-05-12", "restingHR": 60}]
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        tl = result["training_load"]
        self.assertIsNone(tl["ctl"])
        self.assertIsNone(tl["atl"])
        self.assertIsNone(tl["tsb"])


class TestFormatReadinessCheckLabel(unittest.TestCase):
    """R2: HRV/RHR labels must reflect actual baseline sample size, not hardcoded 14d."""

    def _base_result(self, **overrides):
        result = {
            "date": "2026-05-16",
            "lookback_days": 14,
            "verdict_band": "GREEN",
            "verdict": "GREEN — all session types clear.",
            "ceiling": "No restrictions",
            "data_age_days": 0,
            "sleep": {"hours": 8.0, "score": 95, "status": "green", "note": None},
            "recovery": {"score": 72, "band": "green", "slope_3day": None},
            "hrv": {"today": 50.0, "baseline": 48.0, "sample_size": 4},
            "resting_hr": {"today": 58, "baseline": 60.0, "sample_size": 4},
            "tsb": {"ctl": None, "atl": None, "tsb": None},
            "subjective": {"fatigue": None, "soreness": None, "stress": None, "mood": None,
                           "stale_warning": False, "stale_note": None},
            "flags": [],
            "overall_status": "green",
        }
        result.update(overrides)
        return result

    def test_label_reflects_actual_sample_size_below_14(self):
        text = format_readiness_check(self._base_result())
        self.assertIn("4d baseline", text)
        self.assertNotIn("14d baseline", text)

    def test_label_says_14d_only_when_actually_14_plus(self):
        result = self._base_result(
            hrv={"today": 50.0, "baseline": 48.0, "sample_size": 14},
            resting_hr={"today": 58, "baseline": 60.0, "sample_size": 14},
        )
        text = format_readiness_check(result)
        self.assertIn("14d baseline", text)


# ---------------------------------------------------------------------------
# Updates to pre-existing wellness tests now that flags require ≥7d history.
# The old tests asserted flag firing at n=2 history (3 records total). After R1,
# RHR/HRV deviation flags are suppressed when sample_size < 7 (noise floor).
# These tests are re-expressed at n=7 history so they continue to assert the
# flag-firing logic (their original intent), just with realistic baseline depth.
# ---------------------------------------------------------------------------
class TestWellnessFlagFiringAtMatureBaseline(unittest.TestCase):
    """Re-expression of older RHR/HRV deviation tests at matured baseline."""

    def setUp(self):
        self.client = IntervalsIcuClient("test", "test")

    def test_red_flag_rhr_elevated_10bpm_at_mature_baseline(self):
        records = _series("2026-05-01", 7, restingHR=51)
        records.append({"id": "2026-05-08", "restingHR": 62})  # +11 vs 51
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        red = [f for f in result["flags"] if f["severity"] == "red" and f["signal"] == "RHR"]
        self.assertEqual(len(red), 1)
        self.assertEqual(result["overall_status"], "red")

    def test_yellow_flag_rhr_elevated_5bpm_at_mature_baseline(self):
        records = _series("2026-05-01", 7, restingHR=51)
        records.append({"id": "2026-05-08", "restingHR": 57})  # +6 vs 51
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        yellow = [f for f in result["flags"]
                  if f["severity"] == "yellow" and f["signal"] == "RHR"]
        self.assertEqual(len(yellow), 1)

    def test_yellow_flag_hrv_depressed_at_mature_baseline(self):
        records = _series("2026-05-01", 7, hrv=70)
        records.append({"id": "2026-05-08", "hrv": 60})  # -14% vs 70
        with patch.object(self.client, "get_wellness", return_value=records):
            result = wellness_summary(self.client, days=14)
        hrv_flags = [f for f in result["flags"] if f["signal"] == "HRV"]
        self.assertEqual(len(hrv_flags), 1)
        self.assertEqual(hrv_flags[0]["severity"], "yellow")


if __name__ == "__main__":
    unittest.main()
