#!/usr/bin/env python3
"""Tests for fit_ingest.py — the .fit-file analysis fallback."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fit_ingest import _extract, _import_fitparse, analyze_local, parse_fit


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
        # M-4: use sys.modules patching — deterministic on all Python run contexts.
        # Setting sys.modules["fitparse"] = None makes `import fitparse` raise
        # ImportError without any __builtins__ dict/module branching.
        with mock.patch.dict("sys.modules", {"fitparse": None}):
            with self.assertRaises(RuntimeError) as cm:
                _import_fitparse()
        self.assertIn("pip install fitparse", str(cm.exception))


class TestAnalyzeLocal(unittest.TestCase):
    """analyze_local — synthetic records → the analyze() dict shape."""

    # Keep in sync with activity.analyze()'s return dict (drop-in contract).
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

    def test_sparse_power_skips_zone_drift(self):
        # 200 records, only ~10 with real watts — sparse power must NOT pass the
        # power-stream gate (the gate counts real samples, not record count).
        records = []
        for i in range(200):
            records.append({"seconds": i,
                            "watts": 200 if i < 10 else None,
                            "heartrate": 140, "cadence": None})
        result = analyze_local(records, self._meta(moving_time_s=200),
                               ftp=200, weight=70)
        self.assertIsNone(result["metrics"]["zone_percent"])
        self.assertIsNone(result["metrics"]["cardiac_drift"])

    # ------------------------------------------------------------------
    # I-1: power_profile must NOT appear in metrics (parity with analyze())
    # ------------------------------------------------------------------

    def test_metrics_has_no_power_profile_key(self):
        # analyze() never sets metrics["power_profile"] for a single ride;
        # analyze_local() must not either.
        records = [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90}
                   for i in range(3600)]
        result = analyze_local(records, self._meta(), ftp=200, weight=70)
        self.assertNotIn("power_profile", result["metrics"],
                         "metrics must not contain power_profile (top-level weekly key only)")

    # ------------------------------------------------------------------
    # I-2: data_completeness must reflect missing power, not always "complete"
    # ------------------------------------------------------------------

    def test_no_power_data_completeness_is_partial(self):
        # No power at all → data_completeness starts with "partial"
        records = [{"seconds": i, "watts": None, "heartrate": 140, "cadence": None}
                   for i in range(120)]
        result = analyze_local(records, self._meta(device_watts=False),
                               ftp=200, weight=70)
        self.assertTrue(
            result["data_completeness"].startswith("partial"),
            f"Expected 'partial ...', got: {result['data_completeness']!r}",
        )
        self.assertIn("power", result["data_completeness"])

    def test_no_power_data_completeness_format(self):
        # Exact format: "partial (missing: power)"
        records = [{"seconds": i, "watts": None, "heartrate": 140, "cadence": None}
                   for i in range(120)]
        result = analyze_local(records, self._meta(device_watts=False),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "partial (missing: power)")

    def test_with_power_data_completeness_is_complete(self):
        # When power IS present, "complete" must still be returned.
        records = [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90}
                   for i in range(120)]
        result = analyze_local(records, self._meta(moving_time_s=120),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "complete")

    def test_sparse_power_still_complete(self):
        # <30 real watts triggers streams_too_short warning, but NOT a "partial"
        # completeness — mirrors analyze()'s behavior (warning, not completeness flag).
        records = [{"seconds": i,
                    "watts": 200 if i < 10 else None,
                    "heartrate": 140, "cadence": None}
                   for i in range(200)]
        result = analyze_local(records, self._meta(moving_time_s=200),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "complete")

    # ------------------------------------------------------------------
    # I-3 + M-1: kJ and avg_w must zero-fill None gaps
    # ------------------------------------------------------------------

    def test_kj_includes_none_gaps_as_zero(self):
        # 60 records: first 30 at 200W, next 30 at None (coasting).
        # Correct kJ = (30×200 + 30×0) / 1000 = 6.0 kJ.
        # Bug: skipping None gives (30×200)/1000 = 6.0 kJ for only 30 samples
        # — happens to be the same here; use 300W to make the difference visible.
        # 60 records: 30 @ 300W, 30 @ None → correct = 9.0 kJ, buggy = 9.0 kJ.
        # Better: use uneven split. 40 records: 10 @ 360W, 30 @ None
        #   correct = (10×360 + 30×0)/1000 = 3.6 kJ
        #   buggy   = (10×360)/1000 = 3.6 kJ  (same! bug only shows in avg)
        # For kJ the difference is mathematical only in avg_w (M-1); test separately.
        # kJ bug: sum(watts_present)/1000 vs sum(zero_filled)/1000 are identical
        # because sum([300,300,...None,None]) = sum([300,...]) either way.
        # So I-3 and M-1 are the SAME bug expressed differently: the total energy
        # and average are both already correct for kJ (sum of non-None is the same
        # as sum of zero-filled non-None); the avg_w divisor is the real issue.
        # Correct: avg_w = sum(zero_filled) / len(all_records)
        # Bug:     avg_w = sum(watts_present) / len(watts_present)
        # Test: 10 records at 200W, 10 at None → avg should be 100W (20×samples total)
        records = (
            [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90} for i in range(10)]
            + [{"seconds": i + 10, "watts": None, "heartrate": 140, "cadence": 90}
               for i in range(10)]
        )
        result = analyze_local(records, self._meta(moving_time_s=20), ftp=200, weight=70)
        # avg_w over 20 samples with zero-fill: (10×200 + 10×0) / 20 = 100.0
        self.assertEqual(result["activity"]["average_watts"], 100.0,
                         "avg_w must be computed over ALL records (zero-fill None gaps)")

    def test_kj_zero_fill_over_all_records(self):
        # kJ = sum(zero_filled_watts) / 1000 using ALL records' duration.
        # 20 records: 10 @ 200W, 10 @ None
        # correct kJ = (10*200 + 10*0) / 1000 = 2.0
        # buggy  kJ  = (10*200) / 1000        = 2.0  ← same! (sum unchanged)
        # So kJ itself is unaffected by the zero-fill choice (sum of present watts
        # equals sum of zero-filled watts). The fix is purely in the avg divisor.
        # This test documents that kJ stays correct either way.
        records = (
            [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90} for i in range(10)]
            + [{"seconds": i + 10, "watts": None, "heartrate": 140, "cadence": 90}
               for i in range(10)]
        )
        result = analyze_local(records, self._meta(moving_time_s=20), ftp=200, weight=70)
        self.assertAlmostEqual(result["activity"]["kilojoules"], 2.0, delta=0.1)

    def test_avg_w_none_only_ride_stays_none(self):
        # HR-only ride: avg_w must remain None, not 0.0 (outer guard preserved).
        records = [{"seconds": i, "watts": None, "heartrate": 140, "cadence": None}
                   for i in range(60)]
        result = analyze_local(records, self._meta(device_watts=False, moving_time_s=60),
                               ftp=200, weight=70)
        self.assertIsNone(result["activity"]["average_watts"],
                          "avg_w must be None when no power samples exist")


try:
    import fitparse as _fitparse_mod  # noqa: F401
    _HAS_FITPARSE = True
except ImportError:
    _HAS_FITPARSE = False

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_ride.fit")


@unittest.skipUnless(_HAS_FITPARSE and os.path.exists(_FIXTURE),
                     "requires fitparse + the synthetic sample_ride.fit fixture")
class TestParseFitSmoke(unittest.TestCase):
    """Real-bytes smoke test through actual fitparse on a synthetic fixture."""

    def test_parse_synthetic_fit(self):
        records, metadata = parse_fit(_FIXTURE)
        self.assertEqual(len(records), 60)
        self.assertEqual(records[0]["watts"], 180)
        self.assertTrue(metadata["device_watts"])

    def test_analyze_synthetic_fit_end_to_end(self):
        records, metadata = parse_fit(_FIXTURE)
        result = analyze_local(records, metadata, ftp=200, weight=70)
        self.assertEqual(result["source"], "fit_file")
        # The fixture is a fixed 180-239W ramp; NP/IF are deterministic, so
        # assert concrete values to catch silent metric regressions.
        self.assertAlmostEqual(result["metrics"]["normalized_power"], 210.1,
                               delta=1)
        self.assertAlmostEqual(result["metrics"]["intensity_factor"], 1.05,
                               delta=0.01)


if __name__ == "__main__":
    unittest.main()
