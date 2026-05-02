#!/usr/bin/env python3
"""
ASCII sparkline helper for cycling-fitness-coach.

Renders a sequence of numbers as a Unicode sparkline plus a delta summary.
Used by the Weekly Review workflow to visualize Peak Power Trends in
plans/active_plan.md without adding a matplotlib dependency.

Usage (CLI):
    python sparkline.py --label "5s" --series 450,460,455,470,480 --unit W
    # ->  5s: ▁▄▃▆█  450->480W (+6.7%, +30W over 5 points)

Usage (module):
    from sparkline import render_sparkline
    line = render_sparkline("5s", [450,460,455,470,480], unit="W")
"""

import argparse
import sys

# Force UTF-8 stdout on Windows (sparkline blocks are non-ASCII)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


# 8-level Unicode block sparkline characters
SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(series):
    """Render a list of numbers as a Unicode block sparkline string.

    Empty/None values in the series are rendered as a single space (gap).
    A single value renders as the middle block. A flat series renders as the
    middle block repeated. Bins values into 8 levels using min-max scaling.
    """
    if not series:
        return ""
    cleaned = [v for v in series if v is not None]
    if not cleaned:
        return " " * len(series)
    lo, hi = min(cleaned), max(cleaned)
    if hi == lo:
        # Flat series — middle block for each non-null
        return "".join(SPARK_BLOCKS[3] if v is not None else " " for v in series)
    out = []
    for v in series:
        if v is None:
            out.append(" ")
            continue
        # Map v to 0..7
        idx = round((v - lo) / (hi - lo) * (len(SPARK_BLOCKS) - 1))
        out.append(SPARK_BLOCKS[idx])
    return "".join(out)


def render_sparkline(label, series, unit=""):
    """Render a labeled sparkline with first->last delta summary.

    Returns a single-line string suitable for embedding in markdown tables
    or plan-state files. Format:
        {label}: {spark}  {first}->{last}{unit} ({pct_change}%, {abs_change}{unit} over N points)

    Returns empty string if series is empty or all-None.
    """
    if not series:
        return ""
    cleaned = [v for v in series if v is not None]
    if not cleaned:
        return f"{label}: (no data)"

    spark = sparkline(series)
    first, last = cleaned[0], cleaned[-1]
    abs_change = last - first

    if first == 0:
        # Avoid divide-by-zero; report absolute only
        return f"{label}: {spark}  {first}→{last}{unit} ({abs_change:+}{unit} over {len(cleaned)} points)"

    pct = round(abs_change / first * 100, 1)
    sign = "+" if abs_change >= 0 else ""
    return (f"{label}: {spark}  {first}→{last}{unit} "
            f"({sign}{pct}%, {sign}{abs_change}{unit} over {len(cleaned)} points)")


def render_peak_power_trends_block(trends):
    """Render a Peak Power Trends block as multiple sparkline lines.

    Args:
        trends: dict mapping duration label -> list of weekly peak values.
                e.g., {"5s": [450, 460, 480], "1min": [310, 315, 320],
                       "5min": [240, 248, 252], "20min": [195, 200, 205]}

    Returns:
        Newline-separated sparkline lines, one per duration. Suitable for
        embedding under a `## Peak Power Trends (sparkline)` section in
        plans/active_plan.md.
    """
    lines = []
    # Stable order: standard durations first, then any extras alphabetical
    standard = ["5s", "15s", "30s", "1min", "2min", "5min", "10min", "20min", "30min", "1hr"]
    seen = set()
    ordered = [d for d in standard if d in trends]
    seen.update(ordered)
    extras = sorted(d for d in trends if d not in seen)
    ordered.extend(extras)

    for dur in ordered:
        line = render_sparkline(dur, trends[dur], unit="W")
        if line:
            lines.append(line)
    return "\n".join(lines)


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(
        description="Render a numeric series as a Unicode sparkline with delta summary"
    )
    p.add_argument("--label", required=True,
                   help="Label for the sparkline (e.g., '5s', '20min')")
    p.add_argument("--series", required=True,
                   help="Comma-separated numeric values, e.g. '450,460,455,470,480'. "
                        "Use empty entries for gaps, e.g. '450,,460' for missing-week.")
    p.add_argument("--unit", default="",
                   help="Optional unit suffix on numbers (e.g., 'W', 'bpm')")
    return p


def _parse_series(text):
    """Parse '450,460,,480' into [450, 460, None, 480]."""
    out = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece:
            out.append(None)
            continue
        try:
            # Accept ints when possible, else float
            v = int(piece) if "." not in piece else float(piece)
        except ValueError:
            raise SystemExit(f"sparkline.py: invalid numeric value '{piece}' in --series")
        out.append(v)
    return out


def main():
    args = build_parser().parse_args()
    series = _parse_series(args.series)
    print(render_sparkline(args.label, series, unit=args.unit))


if __name__ == "__main__":
    main()
