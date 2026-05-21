#!/usr/bin/env python3
"""Unit tests for the private helpers extracted in the W1 decomposition.

Run: py -3 -m unittest tests.test_internal_helpers -v
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from intervals_icu.wellness import (
    _build_daily, _history_value_lists, _baseline_maturity, _hrv_baseline,
    _compute_baseline, _flag_rhr, _flag_hrv_band, _flag_hrv_cv_trend,
    _flag_respiration, _flag_spo2, _flag_absolute, _recovery_slope_3day,
    _latest_date_age_days, _subjective_stale, _training_load,
    _progression_signal, _days_with_whoop_data, _overall_status, _baseline_note,
)
from intervals_icu.activity import (
    _compute_power_metrics, _compute_stream_metrics, _build_lap_list,
    _build_activity_block,
)


def _daily_record(date, **overrides):
    """Build a daily-shaped record (post-_build_daily snake_case keys) with defaults."""
    rec = {
        "date": date, "resting_hr": None, "hrv": None, "sleep_hours": None,
        "sleep_quality": None, "sleep_score": None, "fatigue": None,
        "soreness": None, "stress": None, "mood": None, "weight": None,
        "readiness": None, "respiration": None, "spo2": None,
    }
    rec.update(overrides)
    return rec


class TestWellnessHelpers(unittest.TestCase):

    def test_build_daily_maps_fields_and_derives_sleep_hours(self):
        raw = [{"id": "2026-05-20", "restingHR": 48, "hrv": 70,
                "sleepSecs": 27000, "readiness": 75, "spO2": 97}]
        daily = _build_daily(raw)
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["date"], "2026-05-20")
        self.assertEqual(daily[0]["resting_hr"], 48)
        self.assertEqual(daily[0]["sleep_hours"], 7.5)   # 27000s / 3600
        self.assertEqual(daily[0]["spo2"], 97)

    def test_overall_status_is_worst_severity(self):
        self.assertEqual(_overall_status([]), "green")
        self.assertEqual(_overall_status([{"severity": "yellow"}]), "yellow")
        self.assertEqual(
            _overall_status([{"severity": "yellow"}, {"severity": "red"}]), "red")

    def test_history_value_lists_3_records(self):
        daily = [
            _daily_record("2026-05-18", hrv=60),
            _daily_record("2026-05-19", hrv=62),
            _daily_record("2026-05-20", hrv=64),  # latest, excluded from history
        ]
        history, value_lists, sizes, partial = _history_value_lists(daily)
        self.assertEqual(len(history), 2)
        self.assertEqual(len(value_lists["hrvs"]), 2)
        self.assertEqual(sizes["hrv"], 2)
        self.assertIs(partial, False)

    def test_history_value_lists_single_record(self):
        daily = [_daily_record("2026-05-20", hrv=60)]
        history, value_lists, sizes, partial = _history_value_lists(daily)
        self.assertIs(partial, True)
        self.assertEqual(history, [])

    def test_baseline_maturity_preliminary(self):
        sizes = {"resting_hr": 3, "hrv": 3, "sleep_hours": 3,
                 "readiness": 3, "respiration": 3, "spo2": 3}
        maturity, _ = _baseline_maturity(sizes)
        self.assertEqual(maturity, "preliminary")

    def test_baseline_maturity_stable(self):
        sizes = {"resting_hr": 14, "hrv": 14, "sleep_hours": 14,
                 "readiness": 14, "respiration": 14, "spo2": 14}
        maturity, _ = _baseline_maturity(sizes)
        self.assertEqual(maturity, "stable")

    def test_baseline_maturity_insufficient(self):
        sizes = {"resting_hr": 0, "hrv": 0, "sleep_hours": 0,
                 "readiness": 0, "respiration": 0, "spo2": 0}
        maturity, _ = _baseline_maturity(sizes)
        self.assertEqual(maturity, "insufficient")

    def test_baseline_maturity_consolidating(self):
        # min size 10 → 7 <= 10 < 14 → consolidating tier
        sizes = {"resting_hr": 10, "hrv": 10, "sleep_hours": 10,
                 "readiness": 10, "respiration": 10, "spo2": 10}
        maturity, _ = _baseline_maturity(sizes)
        self.assertEqual(maturity, "consolidating")

    def test_hrv_baseline_avg_and_keys(self):
        frag = _hrv_baseline([60, 62, 58, 61, 59, 63, 60])
        self.assertEqual(frag["hrv_avg"], 60.4)
        self.assertIn("hrv_7d_mean", frag)
        self.assertIn("hrv_cv_pct", frag)

    def test_compute_baseline_rhr_avg(self):
        value_lists = {"rhrs": [48, 50, 49], "hrvs": [], "sleeps": [],
                       "readinesses": [], "respirations": [], "spo2s": []}
        baseline = _compute_baseline(value_lists)
        self.assertEqual(baseline["resting_hr_avg"], 49.0)

    def test_flag_rhr_red(self):
        latest = {"resting_hr": 60}
        baseline = {"resting_hr_avg": 48}
        sizes = {"resting_hr": 7}
        flags = _flag_rhr(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "red")

    def test_flag_rhr_suppressed_below_n7(self):
        latest = {"resting_hr": 54}
        baseline = {"resting_hr_avg": 48}
        sizes = {"resting_hr": 4}
        self.assertEqual(_flag_rhr(latest, baseline, sizes), [])

    def test_flag_rhr_yellow(self):
        # delta = 54 - 48 = 6 bpm → 5-9 bpm band → yellow
        latest = {"resting_hr": 54}
        baseline = {"resting_hr_avg": 48}
        sizes = {"resting_hr": 7}
        flags = _flag_rhr(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "yellow")

    def test_flag_hrv_band_single_day_yellow(self):
        # band lower edge = 60.0 - 0.5*4.0 = 58.0. Today below, yesterday above
        # the band → today-only branch → yellow.
        latest = {"hrv": 50}
        daily = [_daily_record("2026-05-19", hrv=62),  # yesterday: above band
                 _daily_record("2026-05-20", hrv=50)]  # today: below band
        baseline = {"hrv_7d_mean": 60.0, "hrv_7d_sd": 4.0}
        sizes = {"hrv": 7}
        flags = _flag_hrv_band(latest, daily, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "yellow")
        self.assertEqual(flags[0]["signal"], "HRV")

    def test_flag_hrv_band_two_day_red(self):
        # band lower edge = 58.0. Both today and yesterday below band →
        # 2-consecutive-day escalation → red (only the red fires).
        latest = {"hrv": 50}
        daily = [_daily_record("2026-05-19", hrv=51),  # yesterday: below band
                 _daily_record("2026-05-20", hrv=50)]  # today: below band
        baseline = {"hrv_7d_mean": 60.0, "hrv_7d_sd": 4.0}
        sizes = {"hrv": 7}
        flags = _flag_hrv_band(latest, daily, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "red")
        self.assertEqual(flags[0]["signal"], "HRV")

    def test_flag_hrv_cv_trend_rising(self):
        baseline = {"hrv_cv_trend": {"recent_cv_pct": 14.0, "prior_cv_pct": 11.0,
                                     "delta_pp": 3.0, "rising": True}}
        flags = _flag_hrv_cv_trend(baseline)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "yellow")
        self.assertEqual(flags[0]["signal"], "HRV_CV")

    def test_flag_respiration_red(self):
        latest = {"respiration": 16.5}
        baseline = {"respiration_avg": 14.0}  # +2.5 over baseline
        sizes = {"respiration": 7}
        flags = _flag_respiration(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "red")

    def test_flag_respiration_yellow(self):
        # delta = 15.5 - 14.0 = 1.5/min → between +1 and +2 → yellow
        latest = {"respiration": 15.5}
        baseline = {"respiration_avg": 14.0}
        sizes = {"respiration": 7}
        flags = _flag_respiration(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "yellow")

    def test_flag_spo2_red_floor(self):
        latest = {"spo2": 88}
        baseline = {}  # immature baseline — red floor still fires
        sizes = {"spo2": 0}
        flags = _flag_spo2(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "red")

    def test_flag_spo2_baseline_relative_yellow(self):
        # spo2 95, baseline 98 → -3.0pp (≤ -2.0pp) with a mature baseline,
        # and ≥90% so the red floor stays silent → baseline-relative yellow.
        latest = {"spo2": 95}
        baseline = {"spo2_avg": 98}
        sizes = {"spo2": 7}
        flags = _flag_spo2(latest, baseline, sizes)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["severity"], "yellow")

    def test_flag_absolute_sleep_yellow(self):
        latest = {"sleep_hours": 5.0}
        flags = _flag_absolute(latest)
        self.assertTrue(any(f["signal"] == "sleep" and f["severity"] == "yellow"
                            for f in flags))

    def test_flag_absolute_recovery_red(self):
        latest = {"readiness": 30}
        flags = _flag_absolute(latest)
        self.assertTrue(any(f["signal"] == "recovery" and f["severity"] == "red"
                            for f in flags))

    def test_recovery_slope_3day_alarm(self):
        daily = [
            _daily_record("2026-05-17", readiness=80),
            _daily_record("2026-05-18", readiness=80),
            _daily_record("2026-05-19", readiness=78),
            _daily_record("2026-05-20", readiness=65),
        ]
        slope, flag = _recovery_slope_3day(daily)
        self.assertEqual(slope["delta"], -15)
        self.assertIs(slope["alarm"], True)
        self.assertIsNotNone(flag)

    def test_recovery_slope_3day_too_few_records(self):
        daily = [_daily_record("2026-05-19", readiness=80),
                 _daily_record("2026-05-20", readiness=75)]
        self.assertEqual(_recovery_slope_3day(daily), (None, None))

    def test_latest_date_age_days_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(_latest_date_age_days({"date": today}), 0)

    def test_latest_date_age_days_malformed(self):
        self.assertIsNone(_latest_date_age_days({"date": "not-a-date"}))

    def test_subjective_stale_all_ones(self):
        latest = {"fatigue": 1, "soreness": 1, "stress": 1}
        self.assertIs(_subjective_stale(latest), True)

    def test_subjective_stale_mixed(self):
        latest = {"fatigue": 3, "soreness": 1, "stress": 1}
        self.assertIs(_subjective_stale(latest), False)

    def test_training_load_computes_tsb(self):
        wellness = [{"id": "2026-05-20", "ctl": 32.1, "atl": 35.0}]
        self.assertEqual(_training_load(wellness),
                         {"ctl": 32.1, "atl": 35.0, "tsb": -2.9})

    def test_days_with_whoop_data_excludes_empty(self):
        daily = [
            _daily_record("2026-05-18", hrv=60),
            _daily_record("2026-05-19", readiness=70),
            _daily_record("2026-05-20"),  # no whoop fields
        ]
        self.assertEqual(_days_with_whoop_data(daily), 2)

    def test_progression_signal_none_when_criteria_unmet(self):
        daily = [_daily_record("2026-05-20", hrv=50)]
        wellness = [{"id": "2026-05-20"}]
        baseline = {}  # no hrv_7d_mean/sd → criteria unmet
        sizes = {"hrv": 1}
        self.assertIsNone(_progression_signal(daily, wellness, baseline, sizes))

    def test_progression_signal_fires(self):
        # upper band = 60.0 + 0.5*4.0 = 62.0. Last 3 daily HRV all above band,
        # CTL rising (wellness[-1].ctl 34 > wellness[-8].ctl 30) → fires.
        daily = [_daily_record("2026-05-18", hrv=65),
                 _daily_record("2026-05-19", hrv=66),
                 _daily_record("2026-05-20", hrv=67)]
        wellness = [
            {"id": "2026-05-13", "ctl": 30.0},  # wellness[-8]
            {"id": "2026-05-14", "ctl": 30.5},
            {"id": "2026-05-15", "ctl": 31.0},
            {"id": "2026-05-16", "ctl": 31.5},
            {"id": "2026-05-17", "ctl": 32.0},
            {"id": "2026-05-18", "ctl": 32.5},
            {"id": "2026-05-19", "ctl": 33.0},
            {"id": "2026-05-20", "ctl": 34.0},  # wellness[-1]
        ]
        baseline = {"hrv_7d_mean": 60.0, "hrv_7d_sd": 4.0}
        sizes = {"hrv": 7}
        sig = _progression_signal(daily, wellness, baseline, sizes)
        self.assertIsNotNone(sig)
        self.assertIn("ctl_today", sig)

    def test_baseline_note_stable_is_none(self):
        self.assertIsNone(_baseline_note("stable", [14, 14, 14]))

    def test_baseline_note_insufficient_is_string(self):
        note = _baseline_note("insufficient", [])
        self.assertIsInstance(note, str)
        self.assertTrue(len(note) > 0)
        self.assertIn("No historical baseline", note)

    def test_baseline_note_preliminary(self):
        note = _baseline_note("preliminary", [3, 5, 4])
        self.assertIsInstance(note, str)
        self.assertTrue(len(note) > 0)

    def test_baseline_note_consolidating(self):
        note = _baseline_note("consolidating", [10, 12, 11])
        self.assertIsInstance(note, str)
        self.assertTrue(len(note) > 0)


class TestActivityHelpers(unittest.TestCase):

    # ------------------------------------------------------------------
    # _build_lap_list
    # ------------------------------------------------------------------

    def test_build_lap_list_maps_interval_fields(self):
        intervals = [{"label": "Work 1", "type": "WORK", "elapsed_time": 300,
                      "moving_time": 300, "average_watts": 180}]
        laps = _build_lap_list(intervals)
        self.assertEqual(len(laps), 1)
        self.assertEqual(laps[0]["name"], "Work 1")
        self.assertEqual(laps[0]["type"], "WORK")
        self.assertEqual(laps[0]["average_watts"], 180)
        self.assertEqual(laps[0]["lap_index"], 0)

    def test_build_lap_list_skips_non_dict_entries(self):
        self.assertEqual(_build_lap_list([None, "x", 5]), [])

    def test_build_lap_list_empty_input(self):
        self.assertEqual(_build_lap_list([]), [])

    def test_build_lap_list_uses_type_when_label_missing(self):
        # label absent → falls back to type
        intervals = [{"type": "REST"}]
        laps = _build_lap_list(intervals)
        self.assertEqual(laps[0]["name"], "REST")

    def test_build_lap_list_preserves_lap_index_across_mixed_entries(self):
        # Non-dict entries are skipped but idx still increments (enumerate)
        intervals = [None, {"label": "Work 1", "type": "WORK"}]
        laps = _build_lap_list(intervals)
        self.assertEqual(len(laps), 1)
        self.assertEqual(laps[0]["lap_index"], 1)  # idx was 1 at the valid entry

    # ------------------------------------------------------------------
    # _compute_power_metrics
    # ------------------------------------------------------------------

    def _activity_with_all_fields(self):
        return {
            "icu_weighted_avg_watts": 190,
            "icu_average_watts": 175,
            "icu_intensity": 89.0,      # → IF = 0.890
            "icu_training_load": 75,
            "average_heartrate": 150,
        }

    def test_compute_power_metrics_happy_path(self):
        a = self._activity_with_all_fields()
        warnings = []
        m = _compute_power_metrics(a, [200] * 100, ftp=188, weight=74,
                                   moving_time=3600, fetch_warnings=warnings)
        self.assertEqual(m["normalized_power"], 190)
        self.assertEqual(m["intensity_factor"], 0.89)   # 89.0/100 = 0.890
        self.assertEqual(m["tss"], 75.0)                # pre-computed
        self.assertIn("power_to_weight", m)
        self.assertEqual(m["power_to_weight"], round(175 / 74, 2))
        # No warnings expected on the happy path
        self.assertEqual(warnings, [])

    def test_compute_power_metrics_fallback_when_icu_intensity_and_tss_absent(self):
        # Omit icu_intensity and icu_training_load → force NP/FTP fallback
        a = {
            "icu_weighted_avg_watts": 190,
            "icu_average_watts": 175,
            "average_heartrate": 150,
            # icu_intensity intentionally absent
            # icu_training_load intentionally absent
        }
        warnings = []
        m = _compute_power_metrics(a, [200] * 100, ftp=188, weight=74,
                                   moving_time=3600, fetch_warnings=warnings)
        expected_if = round(190 / 188, 3)
        self.assertEqual(m["intensity_factor"], expected_if)
        # TSS fallback: (3600 * IF**2 / 3600) * 100
        expected_tss = round((3600 * (190 / 188) ** 2) / 3600 * 100, 1)
        self.assertEqual(m["tss"], expected_tss)
        self.assertEqual(warnings, [])

    def test_compute_power_metrics_no_normalized_power_when_no_stream_and_no_api(self):
        # icu_weighted_avg_watts absent, watts=[] → np_val stays None
        a = {"icu_average_watts": 175, "average_heartrate": 150}
        warnings = []
        m = _compute_power_metrics(a, [], ftp=188, weight=74,
                                   moving_time=3600, fetch_warnings=warnings)
        self.assertIsNone(m["normalized_power"])
        # IF and TSS require np_val → both absent
        self.assertNotIn("intensity_factor", m)
        self.assertNotIn("tss", m)

    def test_compute_power_metrics_out_of_range_if_appends_warning(self):
        # icu_intensity = 250 → IF = 2.50 → out of [0.3, 2.0] → recompute from NP
        a = {
            "icu_weighted_avg_watts": 190,
            "icu_average_watts": 175,
            "icu_intensity": 250,   # → IF = 2.5, out of range
            "average_heartrate": 150,
        }
        warnings = []
        m = _compute_power_metrics(a, [200] * 100, ftp=188, weight=74,
                                   moving_time=3600, fetch_warnings=warnings)
        # Should have fallen back to NP/FTP
        self.assertEqual(m["intensity_factor"], round(190 / 188, 3))
        self.assertEqual(len(warnings), 1)
        self.assertIn("if_out_of_range", warnings[0])

    # ------------------------------------------------------------------
    # _compute_stream_metrics
    # ------------------------------------------------------------------

    def test_compute_stream_metrics_no_streams(self):
        # Both has_power_stream and has_hr_stream False
        warnings = []
        m = _compute_stream_metrics(
            watts=[], hr=[], power_curve={},
            has_power_stream=False, has_hr_stream=False,
            ftp=188, fetch_warnings=warnings,
        )
        self.assertIsNone(m["zone_seconds"])
        self.assertIsNone(m["zone_percent"])
        self.assertIsNone(m["cardiac_drift"])
        # peak_powers falls back to empty dict, warning appended
        self.assertEqual(m["peak_powers"], {})
        self.assertEqual(len(warnings), 1)
        self.assertIn("unavailable", warnings[0])

    def test_compute_stream_metrics_with_power_and_hr_streams_no_curve(self):
        # Provide a real watts + hr list, no power_curve → zones populated,
        # peaks computed from stream, cardiac_drift computed
        watts = [150] * 60 + [200] * 60  # 120 samples spanning Z2/Z3
        hr = [140] * 120
        warnings = []
        m = _compute_stream_metrics(
            watts=watts, hr=hr, power_curve={},
            has_power_stream=True, has_hr_stream=True,
            ftp=188, fetch_warnings=warnings,
        )
        self.assertIsNotNone(m["zone_seconds"])
        self.assertIsNotNone(m["zone_percent"])
        self.assertIsInstance(m["peak_powers"], dict)
        self.assertGreater(len(m["peak_powers"]), 0)
        self.assertIsNotNone(m["cardiac_drift"])
        # A warning about curve fallback should be appended
        self.assertEqual(len(warnings), 1)
        self.assertIn("peak powers computed from streams", warnings[0])

    def test_compute_stream_metrics_uses_power_curve_when_present(self):
        # When power_curve is non-empty, peak_powers == power_curve; no warning
        power_curve = {"5s": 350, "1min": 270, "5min": 220, "20min": 195}
        watts = [150] * 60
        warnings = []
        m = _compute_stream_metrics(
            watts=watts, hr=[], power_curve=power_curve,
            has_power_stream=True, has_hr_stream=False,
            ftp=188, fetch_warnings=warnings,
        )
        self.assertEqual(m["peak_powers"], power_curve)
        self.assertIsNone(m["cardiac_drift"])  # has_hr_stream=False
        self.assertEqual(warnings, [])

    # ------------------------------------------------------------------
    # _build_activity_block
    # ------------------------------------------------------------------

    def test_build_activity_block_fields(self):
        a = {"id": 99, "name": "Test", "type": "Ride",
             "start_date_local": "2026-01-01T06:00:00", "distance": 30000,
             "elapsed_time": 3700, "total_elevation_gain": 120,
             "max_heartrate": 175, "average_cadence": 88, "icu_joules": 1800000}
        block = _build_activity_block(a, moving_time=3600, avg_w=175, max_watts=310,
                                      avg_hr=155, has_power=True, trainer=True,
                                      is_indoor=True, activity_id=99)
        self.assertEqual(block["distance_km"], 30.0)
        self.assertEqual(block["kilojoules"], 1800.0)
        self.assertEqual(block["power_data_quality"], "measured")
        self.assertEqual(block["context"], "indoor")

    def test_build_activity_block_none_guards(self):
        # No icu_joules key → kilojoules None; has_power=False → estimated;
        # is_indoor=False → outdoor
        a = {"id": 7, "name": "Outdoor Ride", "type": "Ride"}
        block = _build_activity_block(a, moving_time=2400, avg_w=None, max_watts=None,
                                      avg_hr=None, has_power=False, trainer=False,
                                      is_indoor=False, activity_id=7)
        self.assertIsNone(block["kilojoules"])
        self.assertEqual(block["power_data_quality"], "estimated")
        self.assertEqual(block["context"], "outdoor")


if __name__ == "__main__":
    unittest.main()
