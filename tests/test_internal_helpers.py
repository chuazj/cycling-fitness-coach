#!/usr/bin/env python3
"""Unit tests for the private helpers extracted in the W1 decomposition.

Run: py -3 -m unittest tests.test_internal_helpers -v
"""
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock

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
    _build_activity_block, _aggregate_week, _ftp_update_suggestion,
    _fetch_week_peaks,
)
from intervals_icu.readiness import (
    _recovery_band, _sleep_status, _synthesize_verdict,
    _render_sleep_hrv, _render_vitals, _render_tsb_subjective, _render_verdict_flags,
    _reduced_basis_phrase, _hrv_baseline_mature, format_readiness_check,
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


class TestWeeklySummaryHelpers(unittest.TestCase):

    # ------------------------------------------------------------------
    # _ftp_update_suggestion
    # ------------------------------------------------------------------

    def test_ftp_update_suggested_when_peak_exceeds_threshold(self):
        # 20min peak 220W → suggested round(220*0.95)=209W; vs ftp 188 that is >103%
        frag = _ftp_update_suggestion(220.0, 188)
        self.assertTrue(frag["ftp_update_suggested"])
        self.assertEqual(frag["suggested_ftp"], 209)

    def test_ftp_update_not_suggested_within_threshold(self):
        frag = _ftp_update_suggestion(195.0, 188)   # suggested ~185, within 103%
        self.assertFalse(frag["ftp_update_suggested"])

    def test_ftp_update_none_peak(self):
        self.assertFalse(_ftp_update_suggestion(None, 188)["ftp_update_suggested"])

    def test_ftp_update_max_20min_peak_included_when_not_suggested(self):
        # peak present but below threshold → max_20min_peak still in fragment
        frag = _ftp_update_suggestion(195.0, 188)
        self.assertIn("max_20min_peak", frag)
        self.assertEqual(frag["max_20min_peak"], 195.0)

    def test_ftp_update_max_20min_peak_absent_when_peak_is_none(self):
        # peak=None → max_20min_peak key should NOT appear in fragment
        frag = _ftp_update_suggestion(None, 188)
        self.assertNotIn("max_20min_peak", frag)

    def test_ftp_update_fragment_includes_change_pct_when_suggested(self):
        frag = _ftp_update_suggestion(220.0, 188)
        self.assertIn("ftp_change_pct", frag)
        expected_change_pct = round((209 - 188) / 188 * 100, 1)
        self.assertEqual(frag["ftp_change_pct"], expected_change_pct)

    # ------------------------------------------------------------------
    # _aggregate_week
    # ------------------------------------------------------------------

    def _make_activity(self, type_="Ride", moving_time=3600, tss=80.0,
                       kj_joules=None, if_pct=None, date="2026-05-20"):
        """Build a minimal activity dict for _aggregate_week tests."""
        a = {
            "type": type_,
            "moving_time": moving_time,
            "icu_training_load": tss,
            "start_date_local": "{}T06:00:00".format(date),
        }
        if kj_joules is not None:
            a["icu_joules"] = kj_joules
        if if_pct is not None:
            a["icu_intensity"] = if_pct
        return a

    def test_aggregate_week_excludes_run(self):
        # 2 cycling activities + 1 run → activity_count == 2; total_tss = sum of cycling only
        activities = [
            self._make_activity(type_="Ride", tss=80.0),
            self._make_activity(type_="VirtualRide", tss=60.0),
            self._make_activity(type_="Run", tss=50.0),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["activity_count"], 2)
        self.assertAlmostEqual(result["total_tss"], 140.0)

    def test_aggregate_week_excludes_zero_moving_time(self):
        # activity with moving_time == 0 should be excluded
        activities = [
            self._make_activity(type_="Ride", tss=80.0, moving_time=3600),
            self._make_activity(type_="Ride", tss=50.0, moving_time=0),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["activity_count"], 1)
        self.assertAlmostEqual(result["total_tss"], 80.0)

    def test_aggregate_week_empty_activities(self):
        result = _aggregate_week([])
        self.assertEqual(result["activity_count"], 0)
        self.assertEqual(result["total_tss"], 0.0)
        self.assertEqual(result["total_kj"], 0.0)
        self.assertEqual(result["total_moving_time"], 0)

    def test_aggregate_week_kj_conversion(self):
        # icu_joules = 1_800_000 J → total_kj = 1800.0 kJ
        activities = [
            self._make_activity(type_="Ride", tss=80.0, kj_joules=1_800_000),
        ]
        result = _aggregate_week(activities)
        self.assertAlmostEqual(result["total_kj"], 1800.0)

    def test_aggregate_week_zone_bucketing_z1(self):
        # icu_intensity=45 → computed_if=0.45 < 0.55 → Z1
        activities = [
            self._make_activity(type_="Ride", if_pct=45, moving_time=3600),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["zone_duration"]["Z1"], 3600)
        self.assertEqual(result["zone_duration"]["Z2"], 0)

    def test_aggregate_week_zone_bucketing_z2(self):
        # icu_intensity=65 → computed_if=0.65 in [0.55, 0.75) → Z2
        activities = [
            self._make_activity(type_="Ride", if_pct=65, moving_time=1800),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["zone_duration"]["Z2"], 1800)
        self.assertEqual(result["zone_duration"]["Z1"], 0)

    def test_aggregate_week_zone_bucketing_z3(self):
        # icu_intensity=82 → computed_if=0.82 in [0.75, 0.90) → Z3
        activities = [
            self._make_activity(type_="Ride", if_pct=82, moving_time=2400),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["zone_duration"]["Z3"], 2400)

    def test_aggregate_week_zone_bucketing_z4(self):
        # icu_intensity=98 → computed_if=0.98 in [0.90, 1.05) → Z4
        activities = [
            self._make_activity(type_="Ride", if_pct=98, moving_time=2700),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["zone_duration"]["Z4"], 2700)

    def test_aggregate_week_zone_bucketing_z5plus(self):
        # icu_intensity=110 → computed_if=1.10 >= 1.05 → Z5+
        activities = [
            self._make_activity(type_="Ride", if_pct=110, moving_time=600),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["zone_duration"]["Z5+"], 600)

    def test_aggregate_week_if_out_of_range_excluded_from_zones(self):
        # icu_intensity=25 → computed_if=0.25 < 0.3 → excluded from if_duration_pairs + zone_duration
        activities = [
            self._make_activity(type_="Ride", if_pct=25, moving_time=3600),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["if_duration_pairs"], [])
        self.assertEqual(sum(result["zone_duration"].values()), 0)

    def test_aggregate_week_training_dates_deduped(self):
        # Two activities on the same date → only one unique training date
        activities = [
            self._make_activity(type_="Ride", date="2026-05-20"),
            self._make_activity(type_="VirtualRide", date="2026-05-20"),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(len(result["training_dates"]), 1)

    def test_aggregate_week_if_duration_pairs_built(self):
        # Valid IF on a cycling activity → if_duration_pairs has one entry
        activities = [
            self._make_activity(type_="Ride", if_pct=85, moving_time=3600),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(len(result["if_duration_pairs"]), 1)
        computed_if, duration = result["if_duration_pairs"][0]
        self.assertAlmostEqual(computed_if, 0.85)
        self.assertEqual(duration, 3600)

    def test_aggregate_week_excludes_negative_moving_time(self):
        # guard is `moving_time <= 0` → negative moving_time also excluded
        activities = [
            self._make_activity(type_="Ride", tss=80.0, moving_time=3600),
            self._make_activity(type_="Ride", tss=50.0, moving_time=-1),
        ]
        result = _aggregate_week(activities)
        self.assertEqual(result["activity_count"], 1)
        self.assertAlmostEqual(result["total_tss"], 80.0)

    # ------------------------------------------------------------------
    # _fetch_week_peaks
    # ------------------------------------------------------------------

    def _curve(self, **dur_watts):
        """Build a raw power-curve payload in parse_power_curve's expected form.

        Keys are duration labels ('5s', '1min', '5min', '20min'); values are watts.
        """
        secs_map = {"5s": 5, "1min": 60, "5min": 300, "20min": 1200}
        secs = [secs_map[k] for k in dur_watts]
        watts = [dur_watts[k] for k in dur_watts]
        return {"secs": secs, "watts": watts}

    def _peak_activity(self, aid, tss, type_="Ride"):
        """Minimal activity dict with icu_training_load set for top-3 selection."""
        return {"id": aid, "type": type_, "moving_time": 3600,
                "icu_training_load": tss, "start_date_local": "2026-05-20T06:00:00"}

    def test_fetch_week_peaks_empty_when_no_training_load(self):
        # No activity has icu_training_load → tss_sorted empty → no fetches
        activities = [
            {"id": "a1", "type": "Ride", "moving_time": 3600,
             "start_date_local": "2026-05-20T06:00:00"},  # no icu_training_load
        ]
        client = MagicMock()
        week_peaks, errors, max_20min = _fetch_week_peaks(client, activities)
        self.assertEqual(week_peaks, {})
        self.assertIsNone(max_20min)
        self.assertEqual(errors, {})
        client.get_power_curve.assert_not_called()

    def test_fetch_week_peaks_records_fetch_error(self):
        # get_power_curve raises → activity id captured in power_curve_errors,
        # call returns normally (does not crash)
        activities = [self._peak_activity("ride1", tss=80.0)]
        client = MagicMock()
        client.get_power_curve.side_effect = Exception("HTTP 503 from intervals.icu")
        week_peaks, errors, max_20min = _fetch_week_peaks(client, activities)
        self.assertIn("ride1", errors)
        self.assertEqual(week_peaks, {})
        self.assertIsNone(max_20min)

    def test_fetch_week_peaks_takes_max_across_curves(self):
        # 2 cycling activities, curves give 20min watts 200 and 220 → max wins
        activities = [
            self._peak_activity("ride1", tss=80.0),
            self._peak_activity("ride2", tss=60.0),
        ]
        curves = {
            "ride1": self._curve(**{"20min": 200}),
            "ride2": self._curve(**{"20min": 220}),
        }
        client = MagicMock()
        client.get_power_curve.side_effect = lambda aid: curves[aid]
        week_peaks, errors, max_20min = _fetch_week_peaks(client, activities)
        self.assertEqual(week_peaks["20min"], 220)
        self.assertEqual(max_20min, 220)
        self.assertEqual(errors, {})

    def test_fetch_week_peaks_only_fetches_top_3_by_tss(self):
        # 4 cycling activities → only top-3 by TSS fetched; lowest-TSS curve ignored
        activities = [
            self._peak_activity("low", tss=10.0),    # lowest — excluded
            self._peak_activity("mid1", tss=50.0),
            self._peak_activity("mid2", tss=70.0),
            self._peak_activity("high", tss=100.0),
        ]
        curves = {
            "low": self._curve(**{"20min": 999}),    # distinct — must NOT appear
            "mid1": self._curve(**{"20min": 200}),
            "mid2": self._curve(**{"20min": 210}),
            "high": self._curve(**{"20min": 220}),
        }
        client = MagicMock()
        client.get_power_curve.side_effect = lambda aid: curves[aid]
        week_peaks, errors, max_20min = _fetch_week_peaks(client, activities)
        self.assertEqual(client.get_power_curve.call_count, 3)
        # lowest-TSS distinct curve value (999) must not leak into week_peaks
        self.assertEqual(week_peaks["20min"], 220)
        self.assertEqual(max_20min, 220)
        fetched = {c.args[0] for c in client.get_power_curve.call_args_list}
        self.assertNotIn("low", fetched)


def _minimal_result(**overrides):
    """Build a minimal but realistic result dict matching readiness_check's shape."""
    base = {
        "date": "2026-05-21",
        "data_age_days": 0,
        "verdict": "GREEN — all session types clear.",
        "ceiling": "No restrictions",
        "sleep": {"hours": 7.5, "score": 85, "status": "green", "note": None},
        "hrv": {
            "today": 65.0, "baseline": 62.0, "cv_pct": 8.5,
            "cv_trend": {"rising": False, "prior_cv_pct": 8.0,
                         "recent_cv_pct": 8.5, "delta_pp": 0.5},
            "band_mean_7d": 63.0, "band_sd_7d": 4.0, "sample_size": 10,
        },
        "resting_hr": {"today": 48, "baseline": 47.0, "sample_size": 10},
        "respiration": {"today": 14.2, "baseline": 14.0, "sample_size": 10},
        "spo2": {"today": 97, "baseline": 98.0, "sample_size": 10},
        "recovery": {
            "score": 75, "band": "green",
            "slope_3day": {"delta": -3, "alarm": False,
                           "three_days_ago": 78, "today": 75},
        },
        "tsb": {"ctl": 32.0, "atl": 33.0, "tsb": -1.0},
        "subjective": {"fatigue": 2, "soreness": 2, "stress": 2, "mood": 3,
                       "stale_warning": False, "stale_note": None},
        "flags": [],
        "progression_signal": None,
    }
    base.update(overrides)
    return base


class TestReadinessHelpers(unittest.TestCase):

    # ------------------------------------------------------------------
    # _recovery_band
    # ------------------------------------------------------------------

    def test_recovery_band_thresholds(self):
        self.assertEqual(_recovery_band(80), "green")
        self.assertEqual(_recovery_band(67), "green")
        self.assertEqual(_recovery_band(66), "yellow-high")
        self.assertEqual(_recovery_band(60), "yellow-high")
        self.assertEqual(_recovery_band(50), "yellow-high")
        self.assertEqual(_recovery_band(49), "yellow-low")
        self.assertEqual(_recovery_band(40), "yellow-low")
        self.assertEqual(_recovery_band(34), "yellow-low")
        self.assertEqual(_recovery_band(33), "red")
        self.assertEqual(_recovery_band(20), "red")
        self.assertEqual(_recovery_band(0), "red")

    def test_recovery_band_none_returns_none(self):
        self.assertIsNone(_recovery_band(None))

    # ------------------------------------------------------------------
    # _sleep_status
    # ------------------------------------------------------------------

    def test_sleep_status_green(self):
        status, note = _sleep_status({"sleep_hours": 8.0})
        self.assertEqual(status, "green")
        self.assertIsNone(note)

    def test_sleep_status_exactly_seven_hours(self):
        # ≥7h = green by default
        status, note = _sleep_status({"sleep_hours": 7.0})
        self.assertEqual(status, "green")
        self.assertIsNone(note)

    def test_sleep_status_red_under_six(self):
        status, note = _sleep_status({"sleep_hours": 5.0})
        self.assertEqual(status, "red")

    def test_sleep_status_missing_when_none(self):
        status, note = _sleep_status({"sleep_hours": None})
        self.assertEqual(status, "missing")

    def test_sleep_status_missing_when_key_absent(self):
        status, note = _sleep_status({})
        self.assertEqual(status, "missing")

    def test_sleep_status_score_tiebreaker_keeps_yellow(self):
        # borderline 6-7h with score ≥85 → yellow (not red)
        status, note = _sleep_status({"sleep_hours": 6.5, "sleep_score": 88})
        self.assertEqual(status, "yellow")
        self.assertIsNotNone(note)
        self.assertIn("keeps yellow", note)

    def test_sleep_status_score_tiebreaker_downgrades_to_red(self):
        # borderline 6-7h with score <70 → red
        status, note = _sleep_status({"sleep_hours": 6.5, "sleep_score": 60})
        self.assertEqual(status, "red")
        self.assertIsNotNone(note)
        self.assertIn("downgrades to red", note)

    def test_sleep_status_borderline_no_score(self):
        # borderline 6-7h without score → plain yellow (no note)
        status, note = _sleep_status({"sleep_hours": 6.5})
        self.assertEqual(status, "yellow")
        self.assertIsNone(note)

    def test_sleep_status_borderline_score_in_middle(self):
        # borderline 6-7h, score between 70 and 85 → plain yellow (no note)
        status, note = _sleep_status({"sleep_hours": 6.5, "sleep_score": 77})
        self.assertEqual(status, "yellow")
        self.assertIsNone(note)

    # ------------------------------------------------------------------
    # _synthesize_verdict
    # ------------------------------------------------------------------

    def test_synthesize_verdict_green(self):
        vb, verdict, ceiling = _synthesize_verdict("green", "green", [], "full")
        self.assertEqual(vb, "GREEN")
        self.assertIn("GREEN", verdict)
        self.assertEqual(ceiling, "No restrictions")

    def test_synthesize_verdict_red_from_sleep(self):
        vb, _verdict, _ceiling = _synthesize_verdict("red", "green", [], "full")
        self.assertEqual(vb, "RED")

    def test_synthesize_verdict_red_from_band(self):
        vb, _verdict, _ceiling = _synthesize_verdict("green", "red", [], "full")
        self.assertEqual(vb, "RED")

    def test_synthesize_verdict_red_from_non_recovery_flag(self):
        flags = [{"signal": "HRV", "severity": "red", "rule": "HRV below band 2d"}]
        vb, _verdict, _ceiling = _synthesize_verdict("green", "green", flags, "full")
        self.assertEqual(vb, "RED")

    def test_synthesize_verdict_recovery_flag_excluded_from_gating(self):
        # A yellow "recovery" signal flag must NOT downgrade verdict beyond band
        flags = [{"signal": "recovery", "severity": "yellow",
                  "rule": "Recovery 34-66"}]
        vb, _verdict, _ceiling = _synthesize_verdict("green", "yellow-high", flags, "full")
        # band is yellow-high; recovery flag excluded → stays YELLOW-HIGH
        self.assertEqual(vb, "YELLOW-HIGH")

    def test_synthesize_verdict_yellow_low_from_band(self):
        vb, _verdict, _ceiling = _synthesize_verdict("green", "yellow-low", [], "full")
        self.assertEqual(vb, "YELLOW-LOW")

    def test_synthesize_verdict_yellow_low_from_sleep(self):
        vb, _verdict, _ceiling = _synthesize_verdict("yellow", "green", [], "full")
        self.assertEqual(vb, "YELLOW-LOW")

    def test_synthesize_verdict_yellow_low_from_yellow_flag(self):
        flags = [{"signal": "RHR", "severity": "yellow", "rule": "RHR +6bpm"}]
        vb, _verdict, _ceiling = _synthesize_verdict("green", "green", flags, "full")
        self.assertEqual(vb, "YELLOW-LOW")

    def test_synthesize_verdict_yellow_high_from_band(self):
        vb, _verdict, _ceiling = _synthesize_verdict("green", "yellow-high", [], "full")
        self.assertEqual(vb, "YELLOW-HIGH")

    def test_synthesize_verdict_insufficient_data(self):
        # band=None and sleep_status=green → INSUFFICIENT-DATA
        vb, _verdict, _ceiling = _synthesize_verdict("green", None, [], "full")
        self.assertEqual(vb, "INSUFFICIENT-DATA")

    def test_synthesize_verdict_red_dominates_yellow_band(self):
        # red flag + yellow-high band → RED wins
        flags = [{"signal": "HRV", "severity": "red", "rule": "HRV 2-day below band"}]
        vb, _verdict, _ceiling = _synthesize_verdict("green", "yellow-high", flags, "full")
        self.assertEqual(vb, "RED")

    # ------------------------------------------------------------------
    # _render_sleep_hrv
    # ------------------------------------------------------------------

    def test_render_sleep_hrv_returns_list_of_str(self):
        result = _minimal_result()
        lines = _render_sleep_hrv(result)
        self.assertIsInstance(lines, list)
        self.assertTrue(all(isinstance(ln, str) for ln in lines))

    def test_render_sleep_hrv_contains_date_and_sleep(self):
        result = _minimal_result()
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("2026-05-21", text)
        self.assertIn("Sleep:", text)

    def test_render_sleep_hrv_shows_age_warning_when_stale(self):
        result = _minimal_result(data_age_days=2)
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("2 day(s) old", text)

    def test_render_sleep_hrv_no_age_warning_when_today(self):
        result = _minimal_result(data_age_days=0)
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertNotIn("day(s) old", text)

    def test_render_sleep_hrv_shows_hrv_baseline(self):
        result = _minimal_result()
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("HRV:", text)
        self.assertIn("baseline", text)

    def test_render_sleep_hrv_cv_trend_line_when_rising(self):
        result = _minimal_result()
        result["hrv"]["cv_trend"] = {
            "rising": True, "prior_cv_pct": 8.0,
            "recent_cv_pct": 11.5, "delta_pp": 3.5,
        }
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("CV trend", text)
        self.assertIn("widening variability", text)

    def test_render_sleep_hrv_no_cv_trend_line_when_stable(self):
        result = _minimal_result()
        result["hrv"]["cv_trend"] = {"rising": False}
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertNotIn("CV trend", text)

    # ------------------------------------------------------------------
    # _render_vitals
    # ------------------------------------------------------------------

    def test_render_vitals_returns_list_of_str(self):
        result = _minimal_result()
        lines = _render_vitals(result)
        self.assertIsInstance(lines, list)
        self.assertTrue(all(isinstance(ln, str) for ln in lines))

    def test_render_vitals_contains_recovery_line(self):
        result = _minimal_result()
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("Recovery:", text)

    def test_render_vitals_contains_rhr_and_resp(self):
        result = _minimal_result()
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("RHR:", text)
        self.assertIn("Resp rate:", text)

    def test_render_vitals_slope_line_when_large_delta(self):
        result = _minimal_result()
        result["recovery"]["slope_3day"] = {
            "delta": -12, "alarm": True, "three_days_ago": 80, "today": 68,
        }
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("3-day slope", text)
        self.assertIn("trend alarm", text)

    def test_render_vitals_no_slope_line_when_small_delta(self):
        # delta < 5 → slope line suppressed
        result = _minimal_result()
        result["recovery"]["slope_3day"] = {
            "delta": -3, "alarm": False, "three_days_ago": 75, "today": 72,
        }
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertNotIn("3-day slope", text)

    def test_render_vitals_spo2_fail_tag_below_90(self):
        result = _minimal_result()
        result["spo2"] = {"today": 88, "baseline": 98.0, "sample_size": 10}
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("[FAIL]", text)

    def test_render_vitals_spo2_warn_when_below_baseline(self):
        # today 95, baseline 98 → -3pp ≤ -2.0pp with mature baseline → WARN
        result = _minimal_result()
        result["spo2"] = {"today": 95, "baseline": 98.0, "sample_size": 10}
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("[WARN]", text)

    # ------------------------------------------------------------------
    # _render_tsb_subjective
    # ------------------------------------------------------------------

    def test_render_tsb_subjective_returns_list_of_str(self):
        result = _minimal_result()
        lines = _render_tsb_subjective(result)
        self.assertIsInstance(lines, list)
        self.assertTrue(all(isinstance(ln, str) for ln in lines))

    def test_render_tsb_subjective_contains_tsb(self):
        result = _minimal_result()
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("TSB:", text)

    def test_render_tsb_subjective_contains_subjective(self):
        result = _minimal_result()
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("Subjective:", text)
        self.assertIn("fatigue=2", text)

    def test_render_tsb_subjective_stale_warning_line(self):
        result = _minimal_result()
        result["subjective"] = {
            "fatigue": 1, "soreness": 1, "stress": 1, "mood": 1,
            "stale_warning": True,
            "stale_note": "All values = 1 (best/default) — verify athlete is updating these manually",
        }
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("All values = 1", text)

    def test_render_tsb_subjective_tsb_state_fresh(self):
        result = _minimal_result()
        result["tsb"]["tsb"] = 10.0
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("fresh", text)

    def test_render_tsb_subjective_tsb_state_productive(self):
        result = _minimal_result()
        result["tsb"]["tsb"] = -15.0
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("productive", text)

    def test_render_tsb_subjective_empty_when_no_tsb(self):
        result = _minimal_result()
        result["tsb"] = {"ctl": None, "atl": None, "tsb": None}
        result["subjective"] = {"fatigue": None, "soreness": None,
                                "stress": None, "mood": None,
                                "stale_warning": False, "stale_note": None}
        lines = _render_tsb_subjective(result)
        self.assertEqual(lines, [])

    # ------------------------------------------------------------------
    # _render_verdict_flags
    # ------------------------------------------------------------------

    def test_render_verdict_flags_returns_list_of_str(self):
        result = _minimal_result()
        lines = _render_verdict_flags(result)
        self.assertIsInstance(lines, list)
        self.assertTrue(all(isinstance(ln, str) for ln in lines))

    def test_render_verdict_flags_contains_verdict_and_ceiling(self):
        result = _minimal_result()
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertIn("VERDICT:", text)
        self.assertIn("CEILING:", text)
        self.assertIn("GREEN — all session types clear.", text)

    def test_render_verdict_flags_yellow_flag_shown(self):
        result = _minimal_result(flags=[
            {"signal": "RHR", "severity": "yellow", "rule": "RHR elevated +6bpm"}
        ])
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertIn("Active flags:", text)
        self.assertIn("[YELLOW]", text)
        self.assertIn("RHR elevated +6bpm", text)

    def test_render_verdict_flags_red_flag_shown(self):
        result = _minimal_result(flags=[
            {"signal": "HRV", "severity": "red", "rule": "HRV 2-day below band"}
        ])
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertIn("[RED]", text)

    def test_render_verdict_flags_no_active_flags_section_when_none(self):
        result = _minimal_result(flags=[])
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertNotIn("Active flags:", text)

    def test_render_verdict_flags_progression_signal_shown(self):
        result = _minimal_result(progression_signal={
            "rule": "HRV above band 3d + CTL rising → +5-10% TSS green-light",
            "ctl_today": 34.0,
        })
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertIn("Progression signal:", text)
        self.assertIn("[GREEN-LIGHT]", text)

    def test_render_verdict_flags_no_progression_when_none(self):
        result = _minimal_result(progression_signal=None)
        lines = _render_verdict_flags(result)
        text = "\n".join(lines)
        self.assertNotIn("Progression signal:", text)

    def test_render_verdict_flags_separator_lines_present(self):
        result = _minimal_result()
        lines = _render_verdict_flags(result)
        separator = "─" * 70
        self.assertIn(separator, lines)

    # ------------------------------------------------------------------
    # Branch-gap coverage (code-review follow-up)
    # ------------------------------------------------------------------

    def test_render_vitals_slope_trending_up(self):
        # positive delta ≥5, not an alarm → "trending up" label
        result = _minimal_result()
        result["recovery"]["slope_3day"] = {
            "delta": 8, "alarm": False, "three_days_ago": 65, "today": 73,
        }
        lines = _render_vitals(result)
        text = "\n".join(lines)
        self.assertIn("3-day slope", text)
        self.assertIn("trending up", text)

    def test_render_sleep_hrv_hrv_absent(self):
        # hrv today is None → the entire HRV line is skipped
        result = _minimal_result()
        result["hrv"]["today"] = None
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertNotIn("HRV:", text)

    def test_render_sleep_hrv_hrv_no_baseline(self):
        # hrv present but sample_size 0 → "(no baseline yet)" branch
        result = _minimal_result()
        result["hrv"]["today"] = 65.0
        result["hrv"]["sample_size"] = 0
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("HRV:", text)
        self.assertIn("(no baseline yet)", text)

    def test_render_tsb_subjective_tsb_neutral(self):
        # -10 <= tsb < 5 → "neutral"
        result = _minimal_result()
        result["tsb"]["tsb"] = -1.0
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("neutral", text)

    def test_render_tsb_subjective_tsb_overreached(self):
        # tsb < -30 → "overreached"
        result = _minimal_result()
        result["tsb"]["tsb"] = -35.0
        lines = _render_tsb_subjective(result)
        text = "\n".join(lines)
        self.assertIn("overreached", text)

    def test_synthesize_verdict_missing_sleep(self):
        # "missing" sleep is neither red nor yellow → falls through to the
        # band-driven branch; green band → GREEN verdict.
        vb, _verdict, _ceiling = _synthesize_verdict("missing", "green", [], "full")
        self.assertEqual(vb, "GREEN")

    # ------------------------------------------------------------------
    # M-3: reduced-mode banner accurately reflects HRV baseline maturity
    # ------------------------------------------------------------------

    def test_render_sleep_hrv_reduced_immature_hrv_no_hrv_claim(self):
        # reduced mode + HRV sample_size < MIN_BASELINE_SIZE (7) →
        # banner must NOT claim HRV 7-day band is driving the verdict
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 4  # immature: 4/7
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("REDUCED-SIGNAL", text)
        # Must NOT claim the mature HRV-band-driven wording
        self.assertNotIn("HRV 7-day band", text)
        # Must explain that HRV baseline is still building
        self.assertIn("HRV baseline still building", text)
        # Must clarify what is actually driving the verdict
        self.assertIn("sleep + resting HR", text)

    def test_render_sleep_hrv_reduced_immature_hrv_shows_n_of_min(self):
        # The immature-HRV banner must include a progress indicator (N/7 days)
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 3
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        # Should show something like "3/7 days"
        self.assertIn("3/7", text)

    def test_render_sleep_hrv_reduced_mature_hrv_keeps_existing_wording(self):
        # reduced mode + HRV sample_size >= MIN_BASELINE_SIZE (7) →
        # existing banner wording must be retained unchanged
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 7  # exactly at threshold
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("REDUCED-SIGNAL", text)
        self.assertIn("HRV 7-day band", text)
        # Must NOT show the immature-HRV wording
        self.assertNotIn("HRV baseline still building", text)

    def test_render_sleep_hrv_reduced_mature_hrv_large_sample(self):
        # sample_size well above threshold → mature path, existing wording
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 14
        lines = _render_sleep_hrv(result)
        text = "\n".join(lines)
        self.assertIn("HRV 7-day band", text)
        self.assertNotIn("HRV baseline still building", text)

    # --- M-3: shared basis helper -------------------------------------

    def test_hrv_baseline_mature_threshold(self):
        # Mature iff sample_size >= MIN_BASELINE_SIZE (7).
        self.assertFalse(_hrv_baseline_mature(6))
        self.assertTrue(_hrv_baseline_mature(7))
        self.assertTrue(_hrv_baseline_mature(20))
        self.assertFalse(_hrv_baseline_mature(0))
        self.assertFalse(_hrv_baseline_mature(None))

    def test_reduced_basis_phrase_immature(self):
        # Immature HRV → phrase must NOT reference the HRV band.
        phrase = _reduced_basis_phrase(4)
        self.assertNotIn("HRV 7-day band", phrase)
        self.assertIn("sleep + resting HR", phrase)

    def test_reduced_basis_phrase_mature(self):
        # Mature HRV → phrase references the HRV 7-day band.
        phrase = _reduced_basis_phrase(10)
        self.assertIn("HRV 7-day band", phrase)

    # --- M-3: reduced-GREEN ceiling parenthetical is maturity-aware ---

    def test_synthesize_verdict_reduced_green_immature_ceiling(self):
        # reduced-mode GREEN with an immature HRV baseline → the ceiling
        # parenthetical must NOT claim the HRV band is driving the verdict.
        vb, _verdict, ceiling = _synthesize_verdict(
            "green", None, [], "reduced", hrv_sample_size=4)
        self.assertEqual(vb, "GREEN")
        self.assertNotIn("HRV 7-day band", ceiling)
        self.assertIn("sleep + resting HR", ceiling)

    def test_synthesize_verdict_reduced_green_mature_ceiling(self):
        # reduced-mode GREEN with a mature HRV baseline → existing wording.
        vb, _verdict, ceiling = _synthesize_verdict(
            "green", None, [], "reduced", hrv_sample_size=10)
        self.assertEqual(vb, "GREEN")
        self.assertIn("HRV 7-day band", ceiling)

    def test_synthesize_verdict_reduced_green_default_arg_is_immature(self):
        # hrv_sample_size defaults to 0 → immature → no HRV-band claim.
        # Locks backward-compat: the 4-arg call form still works.
        vb, _verdict, ceiling = _synthesize_verdict("green", None, [], "reduced")
        self.assertEqual(vb, "GREEN")
        self.assertNotIn("HRV 7-day band", ceiling)

    def test_synthesize_verdict_reduced_green_tier_unchanged_by_hrv_arg(self):
        # The verdict TIER and human verdict line must be byte-identical
        # regardless of HRV maturity — only the ceiling parenthetical moves.
        vb_a, verdict_a, _ = _synthesize_verdict(
            "green", None, [], "reduced", hrv_sample_size=4)
        vb_b, verdict_b, _ = _synthesize_verdict(
            "green", None, [], "reduced", hrv_sample_size=20)
        self.assertEqual(vb_a, vb_b)
        self.assertEqual(verdict_a, verdict_b)
        self.assertEqual(vb_a, "GREEN")
        self.assertEqual(verdict_a, "GREEN — all session types clear.")

    # --- M-3: banner ⇔ ceiling agreement (the regression that matters) ---

    def test_reduced_immature_banner_and_ceiling_agree(self):
        # Full render of a reduced-mode GREEN result with an immature HRV
        # baseline: the banner and the CEILING line must reference the SAME
        # signals — neither may claim the HRV band drives the verdict.
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 4
        # Reduced-mode GREEN ceiling, immature → maturity-aware parenthetical.
        _vb, _verdict, ceiling = _synthesize_verdict(
            "green", None, result["flags"], "reduced", hrv_sample_size=4)
        result["ceiling"] = ceiling
        text = format_readiness_check(result)
        # Neither banner nor ceiling oversells HRV.
        self.assertNotIn("HRV 7-day band", text)
        # Both reference the honest basis.
        self.assertGreaterEqual(text.count("sleep + resting HR"), 2)
        # And the ceiling line specifically carries it.
        self.assertIn("CEILING:", text)
        self.assertIn("verdict from sleep + resting HR", ceiling)

    def test_reduced_mature_banner_and_ceiling_agree(self):
        # Paired mature case: both banner and ceiling reference the HRV band.
        result = _minimal_result(signal_mode="reduced")
        result["hrv"]["sample_size"] = 10
        _vb, _verdict, ceiling = _synthesize_verdict(
            "green", None, result["flags"], "reduced", hrv_sample_size=10)
        result["ceiling"] = ceiling
        text = format_readiness_check(result)
        self.assertIn("HRV 7-day band", text)        # banner
        self.assertIn("HRV 7-day band", ceiling)     # ceiling


class TestResolveProfileFtp(unittest.TestCase):
    """W7 — extracted athlete-profile FTP resolution helper."""

    def test_top_level_icu_ftp(self):
        from intervals_icu.cli import _resolve_profile_ftp
        self.assertEqual(_resolve_profile_ftp({"icu_ftp": 250}), (250, "icu_ftp"))

    def test_sport_settings_bike_entry(self):
        from intervals_icu.cli import _resolve_profile_ftp
        profile = {"sportSettings": [{"types": ["Ride", "VirtualRide"], "ftp": 188}]}
        ftp, source = _resolve_profile_ftp(profile)
        self.assertEqual(ftp, 188)
        self.assertIn("sportSettings", source)

    def test_sport_settings_bike_entry_no_ftp(self):
        from intervals_icu.cli import _resolve_profile_ftp
        # bike entry present but no ftp key → ftp_value None, source still reflects sportSettings
        ftp, source = _resolve_profile_ftp({"sportSettings": [{"types": ["Ride"]}]})
        self.assertIsNone(ftp)
        self.assertIn("sportSettings", source)

    def test_no_ftp_anywhere(self):
        from intervals_icu.cli import _resolve_profile_ftp
        self.assertEqual(_resolve_profile_ftp({}), (None, "icu_ftp"))


class TestLoadEnv(unittest.TestCase):
    """W7 — .env parser coverage."""

    def test_parses_quotes_comments_and_setdefault(self):
        import tempfile
        from intervals_icu.api_client import load_env
        keys = ("INTERVALS_ICU_API_KEY", "INTERVALS_ICU_ATHLETE_ID",
                "LOADENV_KEY_WITH_HASH", "LOADENV_PLAIN_KEY")
        saved = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            with tempfile.TemporaryDirectory() as d:
                envp = os.path.join(d, ".env")
                with open(envp, "w", encoding="utf-8") as f:
                    f.write('INTERVALS_ICU_API_KEY="secret123"  # trailing comment\n')
                    f.write("INTERVALS_ICU_ATHLETE_ID=i999\n")
                    f.write("\n# a full-line comment\n")
                    # Quoted value containing a hash — must be preserved.
                    f.write('LOADENV_KEY_WITH_HASH="va # lue"\n')
                    # Unquoted value with a trailing comment — must be stripped.
                    f.write("LOADENV_PLAIN_KEY=plainval  # note\n")
                load_env(envp)
                self.assertEqual(os.environ["INTERVALS_ICU_API_KEY"], "secret123")
                self.assertEqual(os.environ["INTERVALS_ICU_ATHLETE_ID"], "i999")
                # Hash inside a quoted value is preserved, not truncated.
                self.assertEqual(os.environ["LOADENV_KEY_WITH_HASH"], "va # lue")
                # Trailing comment on an unquoted value is stripped.
                self.assertEqual(os.environ["LOADENV_PLAIN_KEY"], "plainval")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
