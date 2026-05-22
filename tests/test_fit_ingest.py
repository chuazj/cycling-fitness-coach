#!/usr/bin/env python3
"""Tests for fit_ingest.py — the .fit-file analysis fallback."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fit_ingest import _extract, _import_fitparse, analyze_local


class _FakeMsg:
    """Stands in for a fitparse message — only get_value is used."""
    def __init__(self, values):
        self._v = values
    def get_value(self, key):
        return self._v.get(key)


class _FakeFitFile:
    """Stands in for fitparse.FitFile — only get_messages is used."""
    def __init__(self, by_type):
        self._by_type = by_type
    def get_messages(self, name):
        return list(self._by_type.get(name, []))


class TestExtract(unittest.TestCase):
    """_extract maps fitparse messages → (records, metadata)."""

    def test_records_mapped_in_order(self):
        ff = _FakeFitFile({"record": [
            _FakeMsg({"power": 200, "heart_rate": 140, "cadence": 90}),
            _FakeMsg({"power": 210, "heart_rate": 142, "cadence": 91}),
        ]})
        records, meta = _extract(ff, "test_ride")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["watts"], 200)
        self.assertEqual(records[0]["seconds"], 0)
        self.assertEqual(records[1]["seconds"], 1)
        self.assertEqual(records[1]["heartrate"], 142)

    def test_metadata_device_watts_true_when_power_present(self):
        ff = _FakeFitFile({"record": [_FakeMsg({"power": 200})]})
        _, meta = _extract(ff, "ride")
        self.assertTrue(meta["device_watts"])
        self.assertEqual(meta["name"], "ride")

    def test_metadata_device_watts_false_without_power(self):
        ff = _FakeFitFile({"record": [_FakeMsg({"heart_rate": 140})]})
        _, meta = _extract(ff, "ride")
        self.assertFalse(meta["device_watts"])

    def test_laps_mapped(self):
        ff = _FakeFitFile({
            "record": [_FakeMsg({"power": 200})],
            "lap": [_FakeMsg({"avg_power": 205, "total_elapsed_time": 300,
                              "avg_heart_rate": 145})],
        })
        _, meta = _extract(ff, "ride")
        self.assertEqual(len(meta["laps"]), 1)
        self.assertEqual(meta["laps"][0]["average_watts"], 205)
        self.assertEqual(meta["laps"][0]["type"], "")

    def test_session_metadata_used(self):
        ff = _FakeFitFile({
            "record": [_FakeMsg({"power": 200})],
            "session": [_FakeMsg({"sport": "cycling", "sub_sport": "virtual_activity",
                                  "total_distance": 25000, "total_elapsed_time": 3600})],
        })
        _, meta = _extract(ff, "ride")
        self.assertEqual(meta["distance_m"], 25000)
        self.assertTrue(meta["trainer"])

    def test_no_records_empty(self):
        ff = _FakeFitFile({})
        records, meta = _extract(ff, "ride")
        self.assertEqual(records, [])
        self.assertFalse(meta["device_watts"])


class TestImportFitparse(unittest.TestCase):
    def test_missing_fitparse_raises_with_install_hint(self):
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) \
            else __builtins__.__import__

        def fake_import(name, *a, **k):
            if name == "fitparse":
                raise ImportError("no module named fitparse")
            return real_import(name, *a, **k)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(RuntimeError) as cm:
                _import_fitparse()
        self.assertIn("pip install fitparse", str(cm.exception))


class TestAnalyzeLocal(unittest.TestCase):
    """analyze_local — synthetic records → the analyze() dict shape."""

    ANALYZE_KEYS = ("activity", "data_completeness", "data_warnings",
                    "fetch_errors", "laps", "metrics", "streams_available",
                    "ftp_reference", "source")

    def _meta(self, **over):
        m = {"name": "Test Ride", "sport_type": "Ride", "start_date_local": "",
             "distance_m": 0, "moving_time_s": 3600, "elapsed_time_s": 3600,
             "total_elevation_gain": 0, "device_watts": True, "trainer": True,
             "laps": []}
        m.update(over)
        return m

    def test_power_ride_metrics(self):
        records = [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90}
                   for i in range(3600)]
        result = analyze_local(records, self._meta(), ftp=200, weight=70)
        self.assertEqual(result["source"], "fit_file")
        self.assertAlmostEqual(result["metrics"]["normalized_power"], 200, delta=1)
        self.assertEqual(result["metrics"]["intensity_factor"], 1.0)
        self.assertEqual(result["metrics"]["tss"], 100.0)

    def test_dict_shape_matches_analyze(self):
        records = [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90}
                   for i in range(120)]
        result = analyze_local(records, self._meta(moving_time_s=120),
                               ftp=200, weight=70)
        for key in self.ANALYZE_KEYS:
            self.assertIn(key, result)
        self.assertEqual(result["fetch_errors"], {})

    def test_no_power_ride(self):
        records = [{"seconds": i, "watts": None, "heartrate": 140, "cadence": None}
                   for i in range(120)]
        result = analyze_local(records, self._meta(device_watts=False),
                               ftp=200, weight=70)
        self.assertIsNone(result["metrics"]["normalized_power"])
        self.assertIsNone(result["metrics"].get("tss"))
        self.assertTrue(any("estimated_power" in w for w in result["data_warnings"]))


if __name__ == "__main__":
    unittest.main()
