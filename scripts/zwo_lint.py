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
import sys
import xml.etree.ElementTree as ET

# Force UTF-8 on Windows (default cp1252 cannot encode Unicode in report output).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KNOWN_INTERVALS = {"Warmup", "Cooldown", "SteadyState", "Ramp",
                   "IntervalsT", "FreeRide", "MaxEffort"}


def _finding(severity: str, code: str, message: str, location: str = "") -> dict:
    """Build one lint finding."""
    return {"severity": severity, "code": code, "message": message,
            "location": location}


def lint_xml(xml_string: str) -> list:
    """Run all structural lint checks on a .zwo XML string. Returns a findings list."""
    findings: list = []
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        findings.append(_finding("error", "E1", f"XML is not well-formed: {e}"))
        return findings  # nothing else can be checked
    # E2-E8 / W1-W6 added in later tasks.
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
    stats = None  # modeled stats wired in Task 8

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
    args = build_parser().parse_args()

    if args.ftp is None:
        print("WARNING: --ftp not supplied — using 200W for modeled stats.",
              file=sys.stderr)
        args.ftp = 200
    if not (50 <= args.ftp <= 500):
        build_parser().error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")

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
