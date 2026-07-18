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

    def test_start_time_shifted_to_local_via_activity_offset(self):
        """Q3 audit P1: FIT start_time is UTC; the activity message's
        local_timestamp/timestamp pair gives the UTC offset. A 07:00 SGT
        ride must not be dated the previous day."""
        from datetime import datetime
        ff = _FakeFitFile({
            "record": [_FakeMsg({"power": 200})],
            "session": [_FakeMsg({"start_time": datetime(2026, 7, 17, 23, 0, 0)})],
            "activity": [_FakeMsg({"timestamp": datetime(2026, 7, 18, 1, 0, 0),
                                   "local_timestamp": datetime(2026, 7, 18, 9, 0, 0)})],
        })
        _, meta = _extract(ff, "ride")
        self.assertEqual(meta["start_date_local"], "2026-07-18T07:00:00")
        self.assertFalse(meta.get("start_time_utc_fallback"))

    def test_start_time_utc_fallback_flag_without_activity_message(self):
        from datetime import datetime
        ff = _FakeFitFile({
            "record": [_FakeMsg({"power": 200})],
            "session": [_FakeMsg({"start_time": datetime(2026, 7, 17, 23, 0, 0)})],
        })
        _, meta = _extract(ff, "ride")
        self.assertEqual(meta["start_date_local"], "2026-07-17T23:00:00")
        self.assertTrue(meta["start_time_utc_fallback"])

    def test_no_start_time_no_fallback_flag(self):
        ff = _FakeFitFile({"record": [_FakeMsg({"power": 200})]})
        _, meta = _extract(ff, "ride")
        self.assertFalse(meta.get("start_time_utc_fallback"))


class TestStartTimeUtcWarning(unittest.TestCase):
    def test_analyze_local_warns_when_start_time_is_utc(self):
        meta = {"name": "ride", "start_time_utc_fallback": True}
        result = analyze_local([{"watts": None}], meta, ftp=200, weight=70)
        self.assertTrue(any("start_time_utc" in w for w in result["data_warnings"]),
                        f"expected start_time_utc warning, got {result['data_warnings']}")

    def test_analyze_local_no_utc_warning_when_offset_applied(self):
        meta = {"name": "ride", "start_time_utc_fallback": False}
        result = analyze_local([{"watts": None}], meta, ftp=200, weight=70)
        self.assertFalse(any("start_time_utc" in w for w in result["data_warnings"]))


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
    # I-2: data_completeness mirrors analyze() — "did API fetches succeed",
    # NOT "is the data good". A local .fit has no API fetches, so it is always
    # "complete". No-power is surfaced via the estimated_power data_warning.
    # ------------------------------------------------------------------

    def test_no_power_data_completeness_is_complete(self):
        # No power at all → data_completeness is still "complete" (parity with
        # analyze(): a no-power intervals.icu activity is "complete" too).
        records = [{"seconds": i, "watts": None, "heartrate": 140, "cadence": None}
                   for i in range(120)]
        result = analyze_local(records, self._meta(device_watts=False),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "complete")
        # The no-power case is surfaced via data_warnings, not data_completeness —
        # this is the real, verifiable parity contract.
        self.assertTrue(
            any("estimated_power" in w for w in result["data_warnings"]),
            "no-power ride must carry an estimated_power data_warning",
        )

    def test_with_power_data_completeness_is_complete(self):
        # When power IS present, "complete" must still be returned.
        records = [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90}
                   for i in range(120)]
        result = analyze_local(records, self._meta(moving_time_s=120),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "complete")

    def test_sparse_power_still_complete(self):
        # <30 real watts triggers a streams_too_short warning, but NOT a
        # "partial" completeness — mirrors analyze() (warning, not completeness).
        records = [{"seconds": i,
                    "watts": 200 if i < 10 else None,
                    "heartrate": 140, "cadence": None}
                   for i in range(200)]
        result = analyze_local(records, self._meta(moving_time_s=200),
                               ftp=200, weight=70)
        self.assertEqual(result["data_completeness"], "complete")
        self.assertTrue(
            any("streams_too_short" in w for w in result["data_warnings"]),
            "sparse-power ride must carry a streams_too_short data_warning",
        )

    # ------------------------------------------------------------------
    # M-1: avg_w must divide by ALL records, not just non-None samples.
    # (kJ is unaffected — a None contributes 0 to a sum either way — so there
    # is no separate I-3 bug; kJ is asserted only as a regression guard.)
    # ------------------------------------------------------------------

    def test_avg_w_divides_over_all_records(self):
        # 20 records: 10 @ 200W, 10 @ None. avg_w must be over all 20 samples:
        #   correct: (10*200 + 10*0) / 20 = 100.0
        #   bug:     (10*200) / 10        = 200.0  (divisor too small)
        records = (
            [{"seconds": i, "watts": 200, "heartrate": 140, "cadence": 90} for i in range(10)]
            + [{"seconds": i + 10, "watts": None, "heartrate": 140, "cadence": 90}
               for i in range(10)]
        )
        result = analyze_local(records, self._meta(moving_time_s=20), ftp=200, weight=70)
        self.assertEqual(result["activity"]["average_watts"], 100.0,
                         "avg_w must be computed over ALL records (zero-fill None gaps)")

    def test_kj_unaffected_by_none_gaps(self):
        # Regression guard: kJ = sum(watts) / 1000. A None contributes 0 to the
        # sum either way, so kJ is the same whether or not None is zero-filled.
        # 20 records: 10 @ 200W, 10 @ None → kJ = (10*200) / 1000 = 2.0.
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
