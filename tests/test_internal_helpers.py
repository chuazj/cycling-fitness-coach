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


if __name__ == "__main__":
    unittest.main()
