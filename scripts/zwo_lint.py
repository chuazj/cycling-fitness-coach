#!/usr/bin/env python3
"""
Zwift Workout (.zwo) File Linter

Validates an existing .zwo file against the canonical Zwift element reference
(h4l/zwift-workout-file-reference) and the project's ZWO hygiene rules. Collects
every finding in one pass; reports human-readable output + optional JSON.

Usage:
    python zwo_lint.py path/to/workout.zwo [--ftp 188] [-o report.json]

Exit codes: 0 = clean (warnings allowed), 1 = errors found, 2 = file unreadable.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

# Force UTF-8 on Windows (default cp1252 cannot encode Unicode in report output).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_zwo import erg_rep_severity, workout_from_xml, calculate_workout_stats

KNOWN_INTERVALS = {"Warmup", "Cooldown", "SteadyState", "Ramp",
                   "IntervalsT", "FreeRide", "MaxEffort"}

# Canonical valid attributes per element (h4l zwift-workout-file-reference).
VALID_ATTRS = {
    "Warmup": {"Duration", "PowerLow", "PowerHigh", "Cadence",
               "CadenceLow", "CadenceHigh", "show_avg"},
    "Cooldown": {"Duration", "PowerLow", "PowerHigh", "Cadence",
                 "CadenceLow", "CadenceHigh", "show_avg"},
    "Ramp": {"Duration", "PowerLow", "PowerHigh", "Cadence",
             "CadenceLow", "CadenceHigh", "show_avg"},
    "SteadyState": {"Duration", "Power", "Cadence", "CadenceLow",
                    "CadenceHigh", "show_avg"},
    "IntervalsT": {"Repeat", "OnDuration", "OffDuration", "OnPower", "OffPower",
                   "Cadence", "CadenceResting", "CadenceLow", "CadenceHigh"},
    "FreeRide": {"Duration", "FlatRoad", "ftptest", "show_avg", "Cadence",
                 "CadenceLow", "CadenceHigh"},
    "MaxEffort": {"Duration", "Cadence", "CadenceLow", "CadenceHigh"},
}

# ERG-inert cue patterns — power *commands* that ERG mode silently ignores.
# Command verbs, or a "to/at NNN W" transition/hold instruction. A bare watt
# label ("Threshold 185W") is informational, not a command — not flagged.
ERG_POWER_CUE = re.compile(
    r"\b(drop to|increase to|raise to|lower to)\b"
    r"|\b(?:to|at)\s+\d+\s?[Ww]\b", re.IGNORECASE)


def _finding(severity: str, code: str, message: str, location: str = "") -> dict:
    """Build one lint finding."""
    return {"severity": severity, "code": code, "message": message,
            "location": location}


POWER_ATTRS = ("Power", "PowerLow", "PowerHigh", "OnPower", "OffPower")


def _fattr(elem, attr):
    """float attribute or None (None also if unparseable)."""
    v = elem.get(attr)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _iattr(elem, attr):
    """int attribute or None (None also if unparseable)."""
    v = elem.get(attr)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _check_interval(elem, loc: str, findings: list) -> None:
    """Run per-interval error + warning checks (E5-E8, W1-W3, W5-W6) on one element."""
    tag = elem.tag

    # E5 — power attributes in 0.0-2.0
    for attr in POWER_ATTRS:
        v = elem.get(attr)
        if v is None:
            continue
        fv = _fattr(elem, attr)
        if fv is None:
            findings.append(_finding("error", "E5",
                f"{attr}='{v}' is not a number", loc))
        elif not (0.0 <= fv <= 2.0):
            findings.append(_finding("error", "E5",
                f"{attr}={fv} is outside 0.0-2.0 (FTP fraction)", loc))

    # E6 — ramp direction
    if tag == "Warmup":
        lo, hi = _fattr(elem, "PowerLow"), _fattr(elem, "PowerHigh")
        if lo is not None and hi is not None and lo > hi:
            findings.append(_finding("error", "E6",
                f"Warmup PowerLow ({lo}) > PowerHigh ({hi}) — must ramp up", loc))
    elif tag == "Cooldown":
        lo, hi = _fattr(elem, "PowerLow"), _fattr(elem, "PowerHigh")
        if lo is not None and hi is not None and lo < hi:
            findings.append(_finding("error", "E6",
                f"Cooldown PowerLow ({lo}) < PowerHigh ({hi}) — must ramp down", loc))

    # E7 — durations present, numeric, and > 0
    duration_attrs = ("OnDuration", "OffDuration") if tag == "IntervalsT" else ("Duration",)
    for da in duration_attrs:
        v = elem.get(da)
        if v is None:
            findings.append(_finding("error", "E7",
                f"<{tag}> missing {da}", loc))
            continue
        dv = _iattr(elem, da)
        if dv is None:
            findings.append(_finding("error", "E7",
                f"{da}='{v}' is not an integer", loc))
        elif dv <= 0:
            findings.append(_finding("error", "E7",
                f"{da}={dv} must be > 0", loc))

    # E8 — textevent inside IntervalsT
    if tag == "IntervalsT" and elem.findall("textevent"):
        findings.append(_finding("error", "E8",
            "<textevent> child inside <IntervalsT> — firing semantics are "
            "unspecified; flatten to <SteadyState> work+recovery pairs", loc))

    # W1 — unknown attributes
    for attr in elem.keys():
        if attr not in VALID_ATTRS.get(tag, set()):
            findings.append(_finding("warning", "W1",
                f"unknown attribute '{attr}' on <{tag}>", loc))

    # W2 — textevent offset within its interval's duration
    parent_dur = _iattr(elem, "Duration")
    if parent_dur is not None:
        for te in elem.findall("textevent"):
            off = _iattr(te, "timeoffset")
            if off is not None and off >= parent_dur:
                findings.append(_finding("warning", "W2",
                    f"textevent timeoffset={off}s >= interval Duration "
                    f"{parent_dur}s — the cue never fires", loc))

    # W3 — both fixed and range cadence
    if elem.get("Cadence") is not None and (
            elem.get("CadenceLow") is not None
            or elem.get("CadenceHigh") is not None):
        findings.append(_finding("warning", "W3",
            "both Cadence (fixed) and CadenceLow/CadenceHigh (range) set — "
            "Zwift behavior is undefined; use one", loc))

    # W5 — ERG-inert power-command cues
    for te in elem.findall("textevent"):
        msg = te.get("message", "")
        if ERG_POWER_CUE.search(msg):
            findings.append(_finding("warning", "W5",
                f'textevent "{msg}" looks like an ERG-inert power command — in '
                f'ERG mode the trainer holds power; reword as "tap intensity '
                f'±N%"', loc))

    # W6 — ERG short/micro work reps
    if tag == "IntervalsT":
        dur, pw = _iattr(elem, "OnDuration"), _fattr(elem, "OnPower")
    elif tag == "SteadyState":
        dur, pw = _iattr(elem, "Duration"), _fattr(elem, "Power")
    else:
        dur, pw = None, None
    if dur is not None and pw is not None:
        sev = erg_rep_severity(dur, pw)
        if sev == "micro":
            findings.append(_finding("warning", "W6",
                f"ERG micro-interval: {dur}s rep at {pw:.2f} FTP — the trainer "
                f"cannot track a step this short; design >=2-3min reps", loc))
        elif sev == "short":
            findings.append(_finding("warning", "W6",
                f"ERG short rep: {dur}s rep at {pw:.2f} FTP — first ~3-5s lost "
                f"to ERG settling; >=2-3min reps recommended", loc))


def lint_xml(xml_string: str) -> list:
    """Run all structural lint checks on a .zwo XML string. Returns a findings list."""
    findings: list = []
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        findings.append(_finding("error", "E1", f"XML is not well-formed: {e}"))
        return findings  # nothing else can be checked

    # E2 — root element
    if root.tag != "workout_file":
        findings.append(_finding("error", "E2",
            f"Root element is <{root.tag}>, expected <workout_file>"))

    # E3 — <workout> present
    workout_elem = root.find("workout")
    if workout_elem is None:
        findings.append(_finding("error", "E3", "No <workout> element found"))
        return findings  # cannot check intervals

    for idx, elem in enumerate(workout_elem):
        if elem.tag == "textevent":
            continue  # textevents are checked via their parent interval
        loc = f"{elem.tag}[{idx}]"
        # E4 — known interval type
        if elem.tag not in KNOWN_INTERVALS:
            findings.append(_finding("error", "E4",
                f"Unknown interval element <{elem.tag}>", loc))
            continue
        _check_interval(elem, loc, findings)

    # W4 — ftptest workout with no FreeRide segment
    if workout_elem.get("ftptest") == "1" and not workout_elem.findall("FreeRide"):
        findings.append(_finding("warning", "W4",
            'workout has ftptest="1" but no <FreeRide> segment — the FTP-test '
            'effort should be FreeRide, not SteadyState (ERG holds current FTP)'))

    return findings


def lint_file(path: str, ftp: int = 200) -> dict:
    """Lint a .zwo file. Returns a result dict. Raises FileNotFoundError/OSError
    for unreadable files — the caller maps those to exit code 2."""
    with open(path, "rb") as fh:
        raw = fh.read()

    findings: list = []
    try:
        xml_string = raw.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding("warning", "W7",
            "File is not valid UTF-8 — Zwift expects UTF-8 encoding."))
        xml_string = raw.decode("utf-8", errors="replace")

    findings.extend(lint_xml(xml_string))
    # Modeled stats — only attempt when the file has no structural errors,
    # since workout_from_xml is strict and would raise on a broken file.
    stats = None
    if not any(f["severity"] == "error" for f in findings):
        try:
            workout = workout_from_xml(xml_string)
            stats = calculate_workout_stats(workout, ftp=ftp)
        except Exception:
            stats = None

    return {
        "file": path,
        "findings": findings,
        "error_count": sum(1 for f in findings if f["severity"] == "error"),
        "warning_count": sum(1 for f in findings if f["severity"] == "warning"),
        "stats": stats,
    }


def format_report(file_path: str, findings: list, stats) -> str:
    """Render a human-readable lint report."""
    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warning"]
    lines = [f"Lint: {file_path}"]
    for f in findings:
        loc = f" [{f['location']}]" if f["location"] else ""
        lines.append(f"  {f['severity'].upper()} {f['code']}{loc}: {f['message']}")
    if not findings:
        lines.append("  OK — no issues found.")
    if stats is not None:
        tss = stats["estimated_tss"]
        tss_s = tss if tss is not None else "unmodeled"
        lines.append(f"  Modeled: {stats['total_duration_min']}min  "
                     f"IF {stats['estimated_if']}  TSS {tss_s}  "
                     f"({stats['tss_method']})")
        if stats.get("tss_warning"):
            lines.append(f"  Note: {stats['tss_warning']}")
    else:
        lines.append("  Modeled stats unavailable.")
    lines.append(f"  {len(errors)} error(s), {len(warns)} warning(s)")
    return "\n".join(lines)


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(description="Lint a Zwift .zwo workout file")
    p.add_argument("file", help="Path to the .zwo file to lint")
    p.add_argument("--ftp", type=int, default=None,
                   help="FTP in watts for the modeled-stats line (50-500). "
                        "Defaults to 200 with a warning.")
    p.add_argument("-o", "--output", help="Write the JSON report to this file")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.ftp is None:
        print("WARNING: --ftp not supplied — using 200W for modeled stats.",
              file=sys.stderr)
        args.ftp = 200
    if not (50 <= args.ftp <= 500):
        parser.error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")

    try:
        result = lint_file(args.file, ftp=args.ftp)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"ERROR: cannot read {args.file}: {e}", file=sys.stderr)
        sys.exit(2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        print(f"Report written to {args.output}", file=sys.stderr)

    print(format_report(args.file, result["findings"], result["stats"]))
    sys.exit(1 if result["error_count"] > 0 else 0)


if __name__ == "__main__":
    main()
