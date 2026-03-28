#!/usr/bin/env python3
"""Offline unit tests for pure functions — no API calls required.

Run: python -m unittest tests.test_pure_functions -v
"""

import math
import os
import sys
import tempfile
import unittest
import warnings

# Add scripts/ to path so we can import without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from intervals_icu_api import (
    _clean_watts,
    compute_np,
    compute_peaks,
    compute_zones,
    compute_drift,
    detect_indoor,
    interval_stats,
    detect_ftp_test,
    fmt_time,
    extract_id,
    parse_power_curve,
    parse_streams,
    POWER_ZONES,
)
from generate_zwo import (
    _validate_power,
    SteadyState,
    Warmup,
    Cooldown,
    IntervalsT,
    FreeRide,
    MaxEffort,
    Ramp,
    TextEvent,
    ZwiftWorkout,
    workout_from_dict,
    create_zwo_xml,
    calculate_workout_stats,
)
from batch_generate_zwo import batch_generate
from pmc_calculator import _ewa_constant, compute_pmc
from intervals_icu_api import analyze_power_profile, POWER_PROFILE


# ===================================================================
# intervals_icu_api.py
# ===================================================================

class TestCleanWatts(unittest.TestCase):
    def test_none_replaced(self):
        self.assertEqual(_clean_watts([None, 100, None]), [0, 100, 0])

    def test_negative_replaced(self):
        self.assertEqual(_clean_watts([-5, 200, -1]), [0, 200, 0])

    def test_clean_passthrough(self):
        self.assertEqual(_clean_watts([100, 200, 300]), [100, 200, 300])

    def test_empty(self):
        self.assertEqual(_clean_watts([]), [])


class TestComputeNP(unittest.TestCase):
    def test_short_input_returns_none(self):
        self.assertIsNone(compute_np([200] * 29))

    def test_constant_power(self):
        # Constant 200W for 60s — NP should equal 200
        np_val = compute_np([200] * 60)
        self.assertAlmostEqual(np_val, 200.0, places=0)

    def test_known_input(self):
        # 30 samples at 100W then 30 at 300W — NP > average (200)
        watts = [100] * 30 + [300] * 30
        np_val = compute_np(watts)
        self.assertIsNotNone(np_val)
        self.assertGreater(np_val, 200)

    def test_empty_returns_none(self):
        self.assertIsNone(compute_np([]))
        self.assertIsNone(compute_np(None))


class TestComputePeaks(unittest.TestCase):
    def test_known_samples(self):
        # 60 samples: first 30 at 300W, last 30 at 100W
        watts = [300] * 30 + [100] * 30
        peaks = compute_peaks(watts)
        self.assertIn("5s", peaks)
        self.assertEqual(peaks["5s"], 300.0)
        self.assertIn("30s", peaks)
        self.assertEqual(peaks["30s"], 300.0)
        # 1min (60s) average = (300*30 + 100*30)/60 = 200
        self.assertIn("1min", peaks)
        self.assertAlmostEqual(peaks["1min"], 200.0, places=1)

    def test_short_input(self):
        peaks = compute_peaks([200] * 3)
        # Only durations <= 3 are possible — none of our standard durations fit
        self.assertEqual(peaks, {})

    def test_empty(self):
        self.assertEqual(compute_peaks([]), {})


class TestComputeZones(unittest.TestCase):
    def test_single_zone(self):
        # All samples at 50% FTP = Z1 (0–55%)
        ftp = 200
        watts = [100] * 100  # 100W = 50% of 200
        secs, pcts = compute_zones(watts, ftp)
        self.assertEqual(pcts["Z1"], 100.0)
        for z in ["Z2", "Z3", "Z4", "Z5", "Z6", "Z7"]:
            self.assertEqual(pcts[z], 0.0)

    def test_empty(self):
        self.assertEqual(compute_zones([], 200), ({}, {}))

    def test_no_ftp(self):
        self.assertEqual(compute_zones([100], 0), ({}, {}))


class TestComputeDrift(unittest.TestCase):
    def test_flat_ef(self):
        # Constant power and HR — drift should be ~0%
        watts = [200] * 200
        hr = [150] * 200
        drift = compute_drift(watts, hr)
        self.assertAlmostEqual(drift, 0.0, places=1)

    def test_positive_drift(self):
        # HR increases in second half (EF drops) — positive drift
        watts = [200] * 200
        hr = [140] * 100 + [160] * 100
        drift = compute_drift(watts, hr)
        self.assertIsNotNone(drift)
        self.assertGreater(drift, 0)

    def test_short_returns_none(self):
        self.assertIsNone(compute_drift([200] * 30, [150] * 30))

    def test_empty_returns_none(self):
        self.assertIsNone(compute_drift([], []))


class TestDetectIndoor(unittest.TestCase):
    def test_virtualride_trainer_none(self):
        self.assertTrue(detect_indoor(None, "VirtualRide"))

    def test_regular_ride_trainer_true(self):
        self.assertTrue(detect_indoor(True, "Ride"))

    def test_regular_ride_trainer_false(self):
        self.assertFalse(detect_indoor(False, "Ride"))

    def test_virtualrun_trainer_none(self):
        self.assertTrue(detect_indoor(None, "VirtualRun"))

    def test_regular_ride_trainer_none(self):
        self.assertFalse(detect_indoor(None, "Ride"))

    def test_empty_sport_type_no_trainer(self):
        self.assertFalse(detect_indoor(False, ""))


class TestIntervalStats(unittest.TestCase):
    def test_with_type_field(self):
        laps = [
            {"average_watts": 250, "type": "WORK"},
            {"average_watts": 120, "type": "RECOVERY"},
            {"average_watts": 248, "type": "WORK"},
            {"average_watts": 118, "type": "RECOVERY"},
        ]
        result = interval_stats(laps)
        self.assertIsNotNone(result)
        self.assertEqual(result["hard_intervals"]["n"], 2)
        self.assertEqual(result["easy_intervals"]["n"], 2)

    def test_without_type_field(self):
        laps = [
            {"average_watts": 250},
            {"average_watts": 120},
            {"average_watts": 248},
        ]
        result = interval_stats(laps)
        self.assertIsNotNone(result)
        # 75% of max (250) = 187.5 — 250 and 248 are hard, 120 is easy
        self.assertEqual(result["hard_intervals"]["n"], 2)
        self.assertEqual(result["easy_intervals"]["n"], 1)

    def test_single_lap_returns_none(self):
        self.assertIsNone(interval_stats([{"average_watts": 200}]))

    def test_over_under_with_type(self):
        # Over-unders: both ~threshold power, but type field distinguishes
        laps = [
            {"average_watts": 200, "type": "WORK"},
            {"average_watts": 180, "type": "RECOVERY"},
            {"average_watts": 198, "type": "WORK"},
            {"average_watts": 178, "type": "RECOVERY"},
        ]
        result = interval_stats(laps)
        self.assertEqual(result["hard_intervals"]["n"], 2)
        self.assertEqual(result["easy_intervals"]["n"], 2)


class TestDetectFtpTest(unittest.TestCase):
    def test_name_match(self):
        result = detect_ftp_test("FTP Test Ride", {}, 3600)
        self.assertIsNotNone(result)
        self.assertTrue(result["likely_ftp_test"])
        self.assertIn("activity_name", result["detection_methods"])

    def test_20min_heuristic(self):
        # 20min power at 95% FTP, duration 2400s, generic name
        result = detect_ftp_test("Morning Ride", {"20min": 177}, 2400, ftp_ref=186)
        self.assertIsNotNone(result)
        self.assertIn("20min_effort_heuristic", result["detection_methods"])
        self.assertAlmostEqual(result["estimated_ftp_20min"], 177 * 0.95, places=1)

    def test_ramp_test(self):
        result = detect_ftp_test("Ramp Test", {"1min": 300}, 900, ftp_ref=186)
        self.assertIsNotNone(result)
        self.assertIn("ramp_test", result["detection_methods"])
        self.assertAlmostEqual(result["estimated_ftp_ramp"], 300 * 0.75, places=1)

    def test_below_lower_bound(self):
        # 20min power below 80% of FTP — should not trigger heuristic
        result = detect_ftp_test("Morning Ride", {"20min": 140}, 2400, ftp_ref=186)
        self.assertIsNone(result)

    def test_above_upper_bound(self):
        # 20min power above 150% of FTP (I-4) — should not trigger heuristic
        result = detect_ftp_test("Morning Ride", {"20min": 300}, 2400, ftp_ref=186)
        self.assertIsNone(result)

    def test_structured_workout_excluded(self):
        result = detect_ftp_test("Sweet Spot Intervals", {"20min": 180}, 3600, ftp_ref=186)
        self.assertIsNone(result)

    def test_no_detection(self):
        result = detect_ftp_test("Easy Spin", {}, 1800)
        self.assertIsNone(result)


class TestFmtTime(unittest.TestCase):
    def test_minutes_seconds(self):
        self.assertEqual(fmt_time(125), "2m 05s")

    def test_hours(self):
        self.assertEqual(fmt_time(3661), "1h 01m")

    def test_zero(self):
        self.assertEqual(fmt_time(0), "0m 00s")


class TestExtractId(unittest.TestCase):
    def test_raw_id(self):
        self.assertEqual(extract_id("i126468486"), "i126468486")

    def test_numeric_id(self):
        self.assertEqual(extract_id("17478304236"), "17478304236")

    def test_url(self):
        self.assertEqual(
            extract_id("https://intervals.icu/activities/i126468486"),
            "i126468486",
        )

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            extract_id("not-a-valid-id")


class TestParsePowerCurve(unittest.TestCase):
    def test_normal_dict(self):
        data = {"secs": [5, 60, 300, 1200], "watts": [450, 300, 250, 210]}
        peaks = parse_power_curve(data)
        self.assertEqual(peaks["5s"], 450)
        self.assertEqual(peaks["1min"], 300)
        self.assertEqual(peaks["5min"], 250)
        self.assertEqual(peaks["20min"], 210)

    def test_missing_keys_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            peaks = parse_power_curve({"unexpected": "data"})
            self.assertEqual(len(w), 1)
            self.assertIn("Unexpected power curve format", str(w[0].message))
        self.assertEqual(peaks, {})

    def test_empty_input(self):
        self.assertEqual(parse_power_curve({}), {})
        self.assertEqual(parse_power_curve(None), {})
        self.assertEqual(parse_power_curve([]), {})


class TestParseStreams(unittest.TestCase):
    def test_dict_format(self):
        data = {"watts": [100, 200], "heartrate": [120, 130]}
        result = parse_streams(data)
        self.assertEqual(result["watts"], [100, 200])
        self.assertEqual(result["heartrate"], [120, 130])

    def test_list_format(self):
        data = [
            {"type": "watts", "data": [100, 200]},
            {"type": "heartrate", "data": [120, 130]},
        ]
        result = parse_streams(data)
        self.assertEqual(result["watts"], [100, 200])

    def test_empty(self):
        self.assertEqual(parse_streams({}), {})
        self.assertEqual(parse_streams(None), {})
        self.assertEqual(parse_streams([]), {})


# ===================================================================
# generate_zwo.py
# ===================================================================

class TestValidatePower(unittest.TestCase):
    def test_in_range(self):
        _validate_power(0.0)
        _validate_power(1.0)
        _validate_power(2.0)

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            _validate_power(-0.1)
        with self.assertRaises(ValueError):
            _validate_power(2.1)


class TestDataclasses(unittest.TestCase):
    def test_steady_state(self):
        ss = SteadyState(duration=300, power=0.88)
        self.assertEqual(ss.duration, 300)
        self.assertEqual(ss.power, 0.88)

    def test_warmup_valid(self):
        wu = Warmup(duration=600, power_low=0.25, power_high=0.75)
        self.assertEqual(wu.power_low, 0.25)

    def test_cooldown_invalid_direction(self):
        with self.assertRaises(ValueError):
            Cooldown(duration=300, power_low=0.25, power_high=0.75)

    def test_intervalst_auto_duration(self):
        it = IntervalsT(repeat=5, on_duration=30, off_duration=30, on_power=1.2, off_power=0.5)
        self.assertEqual(it.duration, 300)  # 5 * (30 + 30)

    def test_steady_state_invalid_power(self):
        with self.assertRaises(ValueError):
            SteadyState(duration=300, power=2.5)

    def test_warmup_invalid_direction(self):
        with self.assertRaises(ValueError):
            Warmup(duration=300, power_low=0.75, power_high=0.25)


class TestWorkoutFromDict(unittest.TestCase):
    def test_round_trip(self):
        data = {
            "name": "Test Workout",
            "description": "A test",
            "workout": [
                {"type": "Warmup", "duration": 600, "power_low": 0.40, "power_high": 0.75},
                {"type": "SteadyState", "duration": 1200, "power": 0.88},
                {"type": "Cooldown", "duration": 300, "power_low": 0.55, "power_high": 0.35},
            ],
        }
        workout = workout_from_dict(data)
        self.assertEqual(workout.name, "Test Workout")
        self.assertEqual(len(workout.intervals), 3)
        self.assertIsInstance(workout.intervals[0], Warmup)
        self.assertIsInstance(workout.intervals[1], SteadyState)
        self.assertIsInstance(workout.intervals[2], Cooldown)

    def test_missing_type_raises(self):
        data = {"workout": [{"duration": 300, "power": 0.88}]}
        with self.assertRaises(ValueError):
            workout_from_dict(data)

    def test_intervalst_from_dict(self):
        data = {
            "name": "IntervalsT Test",
            "workout": [
                {"type": "IntervalsT", "repeat": 4, "on_duration": 180,
                 "off_duration": 180, "on_power": 1.2, "off_power": 0.5}
            ],
        }
        workout = workout_from_dict(data)
        self.assertIsInstance(workout.intervals[0], IntervalsT)
        self.assertEqual(workout.intervals[0].repeat, 4)
        self.assertEqual(workout.intervals[0].on_power, 1.2)

    def test_ramp_from_dict(self):
        data = {
            "name": "Ramp Test",
            "workout": [
                {"type": "Ramp", "duration": 600, "power_low": 0.5, "power_high": 1.0}
            ],
        }
        workout = workout_from_dict(data)
        self.assertIsInstance(workout.intervals[0], Ramp)
        self.assertEqual(workout.intervals[0].power_low, 0.5)

    def test_freeride_from_dict(self):
        data = {
            "name": "FreeRide Test",
            "workout": [
                {"type": "FreeRide", "duration": 300, "flat_road": True}
            ],
        }
        workout = workout_from_dict(data)
        self.assertIsInstance(workout.intervals[0], FreeRide)
        self.assertTrue(workout.intervals[0].flat_road)

    def test_maxeffort_from_dict(self):
        data = {
            "name": "MaxEffort Test",
            "workout": [{"type": "MaxEffort", "duration": 30}],
        }
        workout = workout_from_dict(data)
        self.assertIsInstance(workout.intervals[0], MaxEffort)
        self.assertEqual(workout.intervals[0].duration, 30)

    def test_text_events_from_dict(self):
        data = {
            "name": "TextEvent Test",
            "workout": [
                {"type": "SteadyState", "duration": 600, "power": 0.88,
                 "text_events": [{"timeoffset": 0, "message": "Go!"}]}
            ],
        }
        workout = workout_from_dict(data)
        self.assertEqual(len(workout.intervals[0].text_events), 1)
        self.assertEqual(workout.intervals[0].text_events[0].message, "Go!")


class TestCreateZwoXml(unittest.TestCase):
    def test_contains_expected_elements(self):
        workout = ZwiftWorkout(
            name="Test",
            intervals=[
                Warmup(duration=300, power_low=0.25, power_high=0.75),
                SteadyState(duration=600, power=0.88),
            ],
        )
        xml = create_zwo_xml(workout)
        self.assertIn('<?xml version="1.0"', xml)
        self.assertIn("<name>Test</name>", xml)
        self.assertIn("<Warmup", xml)
        self.assertIn("<SteadyState", xml)
        self.assertIn('Power="0.88"', xml)

    def test_ftp_test_attribute(self):
        workout = ZwiftWorkout(name="FTP Test", is_ftp_test=True, intervals=[])
        xml = create_zwo_xml(workout)
        self.assertIn('ftptest="1"', xml)


class TestCalculateWorkoutStats(unittest.TestCase):
    def test_known_workout(self):
        workout = ZwiftWorkout(
            name="Test",
            intervals=[
                SteadyState(duration=3600, power=0.88),  # 1hr at 88%
            ],
        )
        stats = calculate_workout_stats(workout, ftp=200)
        self.assertEqual(stats["total_duration_min"], 60.0)
        # TSS for 1hr at IF=0.88: 0.88^2 * 100 = 77.44
        self.assertAlmostEqual(stats["estimated_tss"], 77, delta=1)
        self.assertAlmostEqual(stats["estimated_avg_intensity"], 0.88, places=2)

    def test_tss_method_key_exists(self):
        workout = ZwiftWorkout(
            name="Test",
            intervals=[SteadyState(duration=300, power=0.75)],
        )
        stats = calculate_workout_stats(workout, ftp=200)
        self.assertIn("tss_method", stats)
        self.assertIn("avg_power", stats["tss_method"])


# ===================================================================
# pmc_calculator.py
# ===================================================================

class TestEwaConstant(unittest.TestCase):
    def test_42_day(self):
        self.assertAlmostEqual(_ewa_constant(42), 1 / 42)

    def test_7_day(self):
        self.assertAlmostEqual(_ewa_constant(7), 1 / 7)


class TestComputePmc(unittest.TestCase):
    def test_known_tss_sequence(self):
        # 7 days of known TSS, starting from 0 CTL/ATL
        daily = [
            ("2026-03-01", 50),
            ("2026-03-02", 60),
            ("2026-03-03", 0),
            ("2026-03-04", 70),
            ("2026-03-05", 0),
            ("2026-03-06", 55),
            ("2026-03-07", 0),
        ]
        result = compute_pmc(daily)

        # Manually compute expected values
        k_ctl = 1 / 42
        k_atl = 1 / 7
        ctl = 0.0
        atl = 0.0
        for _, tss in daily:
            ctl = ctl + k_ctl * (tss - ctl)
            atl = atl + k_atl * (tss - atl)

        self.assertAlmostEqual(result["ctl"], round(ctl, 1), places=1)
        self.assertAlmostEqual(result["atl"], round(atl, 1), places=1)
        self.assertAlmostEqual(result["tsb"], round(ctl - atl, 1), places=1)
        self.assertEqual(len(result["history"]), 7)

    def test_empty_input(self):
        result = compute_pmc([])
        self.assertEqual(result["ctl"], 0.0)
        self.assertEqual(result["atl"], 0.0)
        self.assertEqual(result["tsb"], 0.0)

    def test_initial_values(self):
        daily = [("2026-03-01", 0)]
        result = compute_pmc(daily, initial_ctl=40.0, initial_atl=50.0)
        # One day of 0 TSS — both should decay toward 0
        self.assertLess(result["ctl"], 40.0)
        self.assertLess(result["atl"], 50.0)


# ===================================================================
# batch_generate_zwo.py
# ===================================================================

class TestBatchGenerate(unittest.TestCase):
    def _make_workout(self, filename, power=0.88):
        return {
            "filename": filename,
            "name": f"Test {filename}",
            "workout": [
                {"type": "SteadyState", "duration": 600, "power": power}
            ],
        }

    def test_happy_path(self):
        workouts = [self._make_workout("w1.zwo"), self._make_workout("w2.zwo")]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200)
            self.assertEqual(result["workouts_generated"], 2)
            self.assertEqual(result["workouts_failed"], 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "w1.zwo")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "w2.zwo")))
            # Verify UTF-8 content
            with open(os.path.join(tmpdir, "w1.zwo"), "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('<?xml version="1.0"', content)

    def test_missing_filename(self):
        workouts = [{"name": "No Filename", "workout": [
            {"type": "SteadyState", "duration": 300, "power": 0.75}
        ]}]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200)
            self.assertEqual(result["workouts_generated"], 0)
            self.assertEqual(result["workouts_failed"], 1)
            self.assertIn("filename", result["errors"][0]["error"])

    def test_dry_run(self):
        workouts = [self._make_workout("test.zwo")]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200, dry_run=True)
            self.assertEqual(result["workouts_generated"], 1)
            self.assertTrue(result["dry_run"])
            # File should NOT be written in dry-run
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "test.zwo")))

    def test_error_collection(self):
        workouts = [
            self._make_workout("good.zwo"),
            {"filename": "bad.zwo", "workout": [{"duration": 300}]},  # missing type
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200)
            self.assertEqual(result["workouts_generated"], 1)
            self.assertEqual(result["workouts_failed"], 1)
            self.assertEqual(result["errors"][0]["filename"], "bad.zwo")

    def test_total_stats_accumulation(self):
        workouts = [
            self._make_workout("w1.zwo", power=0.88),
            self._make_workout("w2.zwo", power=0.75),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200)
            # Two 10-min workouts
            self.assertAlmostEqual(result["total_duration_min"], 20.0, places=1)
            self.assertGreater(result["total_estimated_tss"], 0)


# ===================================================================
# Edge case tests (CQ-2)
# ===================================================================

class TestComputeDriftEdgeCases(unittest.TestCase):
    def test_all_zero_power_returns_none(self):
        # All zero watts — EF = 0/avg_hr = 0, should return None
        watts = [0] * 200
        hr = [150] * 200
        self.assertIsNone(compute_drift(watts, hr))

    def test_mixed_none_power(self):
        # Half None, half valid — should compute from valid pairs only
        watts = [None] * 100 + [200] * 100
        hr = [140] * 100 + [150] * 100
        drift = compute_drift(watts, hr)
        # First half has no valid pairs (all None power) → e1 = None → returns None
        self.assertIsNone(drift)

    def test_zero_hr_returns_none(self):
        # Zero HR in both halves — no valid pairs
        watts = [200] * 200
        hr = [0] * 200
        self.assertIsNone(compute_drift(watts, hr))


class TestComputeNPEdgeCases(unittest.TestCase):
    def test_exactly_30_samples(self):
        # Minimum valid input: exactly 30 samples
        np_val = compute_np([200] * 30)
        self.assertAlmostEqual(np_val, 200.0, places=0)

    def test_31_samples_constant(self):
        # 31 samples constant → NP = constant
        np_val = compute_np([150] * 31)
        self.assertAlmostEqual(np_val, 150.0, places=0)

    def test_all_zeros(self):
        np_val = compute_np([0] * 60)
        self.assertAlmostEqual(np_val, 0.0, places=0)


class TestWorkoutFromDictEdgeCases(unittest.TestCase):
    def test_unknown_type_raises(self):
        data = {"workout": [{"type": "UnknownInterval", "duration": 300}]}
        with self.assertRaises(ValueError):
            workout_from_dict(data)

    def test_power_out_of_range_raises(self):
        data = {"workout": [{"type": "SteadyState", "duration": 300, "power": 2.5}]}
        with self.assertRaises(ValueError):
            workout_from_dict(data)

    def test_negative_power_raises(self):
        data = {"workout": [{"type": "SteadyState", "duration": 300, "power": -0.1}]}
        with self.assertRaises(ValueError):
            workout_from_dict(data)


class TestBatchGenerateEdgeCases(unittest.TestCase):
    def test_empty_workout_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate([], tmpdir, ftp=200)
            self.assertEqual(result["workouts_generated"], 0)
            self.assertEqual(result["workouts_failed"], 0)

    def test_invalid_power_in_batch(self):
        workouts = [
            {"filename": "bad.zwo", "name": "Bad", "workout": [
                {"type": "SteadyState", "duration": 300, "power": 3.0}
            ]}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_generate(workouts, tmpdir, ftp=200)
            self.assertEqual(result["workouts_generated"], 0)
            self.assertEqual(result["workouts_failed"], 1)


class TestParsePowerCurveEdgeCases(unittest.TestCase):
    def test_mismatched_lengths(self):
        # secs and watts arrays of different lengths
        data = {"secs": [5, 60], "watts": [450]}
        peaks = parse_power_curve(data)
        # Should handle gracefully — only 1 valid pair
        self.assertIn("5s", peaks)

    def test_none_watts_values(self):
        # Some watts values are None
        data = {"secs": [5, 60, 300], "watts": [450, None, 250]}
        peaks = parse_power_curve(data)
        self.assertIn("5s", peaks)

    def test_list_format(self):
        # Power curve as list of dicts (alternative format)
        data = [{"secs": 5, "value": 450}, {"secs": 60, "value": 300}]
        peaks = parse_power_curve(data)
        # Depending on implementation, may return {} with warning
        self.assertIsInstance(peaks, dict)


class TestIntervalStatsEdgeCases(unittest.TestCase):
    def test_all_zero_watts(self):
        laps = [{"average_watts": 0}, {"average_watts": 0}]
        # All zero watts → work_laps is empty (filter requires > 0)
        self.assertIsNone(interval_stats(laps))

    def test_none_average_watts(self):
        laps = [{"average_watts": None}, {"average_watts": 200}]
        # Only 1 valid lap → returns None (needs >= 2)
        self.assertIsNone(interval_stats(laps))


# ===================================================================
# New feature tests (Phase 2)
# ===================================================================

class TestComputePmcAcwr(unittest.TestCase):
    """Test ACWR calculation in compute_pmc."""

    def test_acwr_present_in_result(self):
        daily = [("2026-03-01", 50)]
        result = compute_pmc(daily)
        self.assertIn("acwr", result)

    def test_acwr_none_when_empty(self):
        result = compute_pmc([])
        self.assertIsNone(result["acwr"])

    def test_acwr_none_when_ctl_zero(self):
        # With zero initial CTL and zero TSS, CTL stays 0
        result = compute_pmc([("2026-03-01", 0)])
        # CTL will be 0 (started at 0, 0 TSS)
        self.assertIsNone(result["acwr"])

    def test_acwr_with_initial_values(self):
        daily = [("2026-03-01", 0)]
        result = compute_pmc(daily, initial_ctl=50.0, initial_atl=60.0)
        # ACWR = ATL / CTL; both decay from initial values
        self.assertIsNotNone(result["acwr"])
        self.assertGreater(result["acwr"], 0)

    def test_acwr_in_history_entries(self):
        daily = [("2026-03-01", 50), ("2026-03-02", 60)]
        result = compute_pmc(daily)
        for entry in result["history"]:
            self.assertIn("acwr", entry)

    def test_acwr_high_atl_low_ctl(self):
        # 7 days of high TSS from zero baseline → high ATL, low CTL → ACWR >> 1
        daily = [("2026-03-01", 100)] + [(f"2026-03-0{i}", 100) for i in range(2, 8)]
        result = compute_pmc(daily)
        self.assertIsNotNone(result["acwr"])
        self.assertGreater(result["acwr"], 1.3)  # Should indicate training spike


class TestAnalyzePowerProfile(unittest.TestCase):
    """Test power profile analysis."""

    def test_basic_profile(self):
        peaks = {"5s": 750, "1min": 350, "5min": 250, "20min": 200}
        result = analyze_power_profile(peaks, 186, 75)
        self.assertIn("profile_type", result)
        self.assertIn("w_per_kg", result)
        self.assertIn("categories", result)
        self.assertIn("strengths", result)
        self.assertIn("weaknesses", result)

    def test_w_per_kg_calculation(self):
        peaks = {"5s": 750, "1min": 375, "5min": 300, "20min": 225}
        result = analyze_power_profile(peaks, 200, 75)
        self.assertAlmostEqual(result["w_per_kg"]["5s"], 10.0, places=1)
        self.assertAlmostEqual(result["w_per_kg"]["1min"], 5.0, places=1)
        self.assertAlmostEqual(result["w_per_kg"]["5min"], 4.0, places=1)
        self.assertAlmostEqual(result["w_per_kg"]["20min"], 3.0, places=1)

    def test_sprinter_profile(self):
        # Very strong 5s/1min, weak 5min/20min
        peaks = {"5s": 1500, "1min": 700, "5min": 250, "20min": 180}
        result = analyze_power_profile(peaks, 186, 75)
        self.assertEqual(result["profile_type"], "sprinter")

    def test_time_trialist_profile(self):
        # Strong 20min relative to 5s/1min
        peaks = {"5s": 800, "1min": 350, "5min": 350, "20min": 320}
        result = analyze_power_profile(peaks, 300, 75)
        self.assertEqual(result["profile_type"], "time_trialist")

    def test_empty_peaks(self):
        result = analyze_power_profile({}, 186, 75)
        # With no data, profile type should be "unknown" or "all_rounder"
        self.assertIn(result["profile_type"], ("unknown", "all_rounder"))
        self.assertEqual(result["w_per_kg"], {})

    def test_partial_peaks(self):
        # Only some durations available
        peaks = {"5min": 300, "20min": 250}
        result = analyze_power_profile(peaks, 200, 75)
        self.assertIn("5min", result["w_per_kg"])
        self.assertIn("20min", result["w_per_kg"])
        self.assertNotIn("5s", result["w_per_kg"])

    def test_power_profile_constant_exists(self):
        # Verify the reference table exists and has expected structure
        self.assertIn("5s", POWER_PROFILE)
        self.assertIn("1min", POWER_PROFILE)
        self.assertIn("5min", POWER_PROFILE)
        self.assertIn("20min", POWER_PROFILE)
        for duration in POWER_PROFILE:
            self.assertIn("untrained", POWER_PROFILE[duration])
            self.assertIn("excellent", POWER_PROFILE[duration])


# ===================================================================
# Phase 4: Edge case tests
# ===================================================================

class TestComputeZonesEdgeCases(unittest.TestCase):
    def test_all_z7(self):
        """All samples above 150% FTP should land in Z7."""
        watts = [400] * 100  # all 400W
        ftp = 200  # 200% FTP = Z7
        zs, zp = compute_zones(watts, ftp)
        self.assertEqual(zp.get("Z7"), 100.0)
        for z in ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]:
            self.assertEqual(zp.get(z, 0), 0.0)

    def test_all_z1(self):
        """All samples below 55% FTP should land in Z1."""
        watts = [50] * 100  # 25% of 200W
        ftp = 200
        zs, zp = compute_zones(watts, ftp)
        self.assertEqual(zp.get("Z1"), 100.0)


class TestComputePeaksEdgeCases(unittest.TestCase):
    def test_exactly_five_samples(self):
        """With exactly 5 samples, only '5s' peak should exist."""
        watts = [300, 310, 320, 310, 300]
        peaks = compute_peaks(watts)
        self.assertIn("5s", peaks)
        self.assertEqual(peaks["5s"], 308.0)  # rolling 5-sample window best avg

    def test_exactly_sixty_samples(self):
        """With 60 samples, 5s and 1min peaks should exist."""
        watts = [200] * 60
        peaks = compute_peaks(watts)
        self.assertIn("5s", peaks)
        self.assertIn("1min", peaks)
        self.assertEqual(peaks["1min"], 200)


class TestDetectFtpTestEdgeCases(unittest.TestCase):
    def test_ramp_test_no_1min_peak(self):
        """Ramp test detected by name but no 1min peak available."""
        result = detect_ftp_test("ramp test", {"5s": 500}, moving_time=900, ftp_ref=200)
        self.assertIsNotNone(result)
        self.assertTrue(result["likely_ftp_test"])
        self.assertIn("activity_name", result["detection_methods"])
        self.assertIn("ramp_test", result["detection_methods"])
        # No 1min peak → no estimated_ftp_ramp
        self.assertNotIn("estimated_ftp_ramp", result)

    def test_name_match_case_insensitive(self):
        """Detection should be case-insensitive."""
        result = detect_ftp_test("FTP TEST Ride", {}, moving_time=3600, ftp_ref=200)
        self.assertIsNotNone(result)
        self.assertTrue(result["likely_ftp_test"])
        self.assertIn("activity_name", result["detection_methods"])


class TestAnalyzePowerProfileEdgeCases(unittest.TestCase):
    def test_zero_weight(self):
        """Zero weight should return unknown profile."""
        result = analyze_power_profile({"5s": 500, "20min": 200}, ftp=200, weight=0)
        self.assertEqual(result["profile_type"], "unknown")

    def test_none_peak_values(self):
        """None values in peaks dict should be handled."""
        result = analyze_power_profile({"5s": None, "20min": 200}, ftp=200, weight=74)
        # Should still compute for 20min
        self.assertIn("20min", result.get("w_per_kg", {}))

    def test_negative_weight(self):
        """Negative weight should return unknown profile."""
        result = analyze_power_profile({"5s": 500}, ftp=200, weight=-10)
        self.assertEqual(result["profile_type"], "unknown")


class TestIntervalStatsEdgeCases(unittest.TestCase):
    def test_all_work_intervals(self):
        """All intervals typed as WORK should produce hard_intervals stats."""
        laps = [
            {"name": "Lap 1", "type": "WORK", "average_watts": 200, "elapsed_time": 300},
            {"name": "Lap 2", "type": "WORK", "average_watts": 210, "elapsed_time": 300},
            {"name": "Lap 3", "type": "WORK", "average_watts": 205, "elapsed_time": 300},
        ]
        result = interval_stats(laps)
        self.assertIsNotNone(result)
        self.assertIn("hard_intervals", result)
        self.assertEqual(result["hard_intervals"]["n"], 3)


if __name__ == "__main__":
    unittest.main()
