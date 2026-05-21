#!/usr/bin/env python3
"""intervals.icu API client — façade.

Preserves the public import surface (`from intervals_icu_api import X`) and the
CLI entrypoint. Implementation lives in the `intervals_icu` package.
"""
import sys

# Force UTF-8 on Windows (default cp1252 cannot encode CJK activity names or
# em-dashes in warning messages). stdout for JSON output, stderr for WARNING lines.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from intervals_icu.api_client import IntervalsIcuClient, load_env
from intervals_icu.metrics import (
    _clean_watts, compute_np, compute_peaks, compute_zones, compute_drift,
    interval_stats, detect_ftp_test, detect_indoor, fmt_time, extract_id,
    parse_power_curve, parse_streams, analyze_power_profile,
    POWER_ZONES, POWER_PROFILE,
)
from intervals_icu.activity import analyze, weekly_summary
from intervals_icu.wellness import wellness_summary
from intervals_icu.readiness import readiness_check, format_readiness_check
from intervals_icu.cli import apply_compact, build_parser, main

if __name__ == "__main__":
    main()
