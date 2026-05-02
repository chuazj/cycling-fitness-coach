#!/usr/bin/env python3
"""
RPE Trend Aggregator for Cycling Fitness Coach.

Scans Obsidian workout-review markdown files, extracts (date, session_type, IF, RPE)
tuples from YAML frontmatter, and compares the last `--weeks` weeks to the prior
`--weeks` weeks (symmetric windows) to detect rising-RPE-at-constant-IF trends.

Detects the "rising RPE at constant IF" pattern that periodization.md flags as a
functional-overreaching signal — earlier than PMC/TSB can detect, because TSS is
RPE-blind.

No third-party dependencies — uses a minimal flat-frontmatter parser.

Usage:
    python rpe_trend.py --vault-path "/path/to/vault/cycling-fitness-coach/workout-reviews"
    python rpe_trend.py --vault-path "..." --weeks 4 -o trend.json
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Force UTF-8 stdout on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_frontmatter(content):
    """Parse a small flat YAML frontmatter block at the start of a markdown file.

    Supports:
      - String values (with optional single/double quotes)
      - Integer/float values
      - `null`, `none`, empty -> Python None
    Skips:
      - Comment lines, blank lines, list items (`- foo`), nested keys (anything
        appearing after a `key:` with no value, e.g. the lines under `tags:`).

    Returns {} if no frontmatter delimiters found.
    """
    if not content.startswith("---"):
        return {}
    # Find closing --- (followed by newline OR end-of-file)
    end_match = re.search(r"\n---\s*(\n|$)", content)
    if not end_match:
        return {}
    fm_text = content[3:end_match.start()].strip()
    out = {}
    in_list_block = False
    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # List item under a previous key (e.g. tags:)
        if stripped.startswith("- "):
            in_list_block = True
            continue
        # Indented continuation (list under tags:, etc.)
        if line.startswith((" ", "\t")) and in_list_block:
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()
        if not val:
            # Either a nested-block parent (like `tags:`) — note we entered list mode
            in_list_block = True
            continue
        in_list_block = False
        # Strip matching quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        # Type coerce
        if val.lower() in ("null", "none"):
            val = None
        else:
            # Try int, then float, else keep string
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
        out[key] = val
    return out


def collect_reviews(vault_path):
    """Walk the vault directory and parse frontmatter from all .md files.

    Returns a list of dicts (one per review file with usable RPE+IF data),
    sorted by date ascending. Files missing date / IF / RPE are silently skipped
    — this is normal for older reviews written before RPE collection started.
    """
    if not os.path.isdir(vault_path):
        return [], f"vault path does not exist or is not a directory: {vault_path}"

    reviews = []
    for entry in os.listdir(vault_path):
        if not entry.endswith(".md"):
            continue
        path = os.path.join(vault_path, entry)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"WARNING: cannot read {path}: {e}", file=sys.stderr)
            continue
        fm = parse_frontmatter(content)
        if fm.get("type") != "workout-review":
            continue
        rpe = fm.get("rpe")
        if_val = fm.get("if")
        date = fm.get("date")
        if rpe is None or if_val is None or date is None:
            continue
        try:
            # Date can be either a "YYYY-MM-DD" string OR an int (YAML parses
            # bare numbers; users sometimes mistype). Coerce to string.
            date_str = str(date)
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        reviews.append({
            "date": date_str,
            "session_type": fm.get("session_type") or "unknown",
            "if": float(if_val),
            "rpe": float(rpe),
            "tss": fm.get("tss"),
            "rating": fm.get("rating"),
            "filename": entry,
        })
    reviews.sort(key=lambda r: r["date"])
    return reviews, None


def compute_trend(reviews, weeks=4):
    """Compute RPE trend over the last `weeks` weeks vs the prior `weeks` weeks.

    Per session-type, computes:
      - n (sessions in recent window)
      - recent_avg_rpe, prior_avg_rpe, delta_rpe
      - avg_if_recent, avg_if_prior, delta_if
      - flag: "rising_rpe_at_constant_if" when delta_rpe >= 1.0 AND |delta_if| <= 0.03
              "falling_rpe_at_constant_if" when delta_rpe <= -1.0 AND |delta_if| <= 0.03
              else None

    Periodization.md → RPE Trend Escalation: rising RPE ≥1 point at same IF for
    2+ weeks → functional overreaching signal. We use 1 RPE point as the
    threshold and ±0.03 IF as "constant" (within typical session noise).
    """
    if not reviews:
        return {}

    today = datetime.strptime(reviews[-1]["date"], "%Y-%m-%d")
    recent_start = today - timedelta(weeks=weeks)
    prior_start = recent_start - timedelta(weeks=weeks)

    by_type_recent = defaultdict(list)
    by_type_prior = defaultdict(list)

    # Window convention: prior = (prior_start, recent_start], recent = (recent_start, today].
    # Both windows are half-open with the same shape — lower-exclusive, upper-inclusive.
    # The shared boundary date (recent_start) belongs to prior (its upper edge); the
    # outer edge `today` belongs to recent (its upper edge). prior_start itself is
    # excluded — the prior window starts one day after it.
    for r in reviews:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        if d > today or d <= prior_start:
            continue
        bucket = by_type_recent if d > recent_start else by_type_prior
        bucket[r["session_type"]].append(r)

    result = {}
    for session_type in set(list(by_type_recent.keys()) + list(by_type_prior.keys())):
        recent = by_type_recent.get(session_type, [])
        prior = by_type_prior.get(session_type, [])
        if not recent:
            continue

        recent_rpe = round(sum(r["rpe"] for r in recent) / len(recent), 2)
        recent_if = round(sum(r["if"] for r in recent) / len(recent), 3)

        entry = {
            "n_recent": len(recent),
            "n_prior": len(prior),
            "recent_avg_rpe": recent_rpe,
            "recent_avg_if": recent_if,
            "flag": None,
        }

        if prior:
            prior_rpe = round(sum(r["rpe"] for r in prior) / len(prior), 2)
            prior_if = round(sum(r["if"] for r in prior) / len(prior), 3)
            delta_rpe = round(recent_rpe - prior_rpe, 2)
            delta_if = round(recent_if - prior_if, 3)
            entry.update({
                "prior_avg_rpe": prior_rpe,
                "prior_avg_if": prior_if,
                "delta_rpe": delta_rpe,
                "delta_if": delta_if,
            })
            if delta_rpe >= 1.0 and abs(delta_if) <= 0.03:
                entry["flag"] = "rising_rpe_at_constant_if"
            elif delta_rpe <= -1.0 and abs(delta_if) <= 0.03:
                entry["flag"] = "falling_rpe_at_constant_if"

        result[session_type] = entry

    return result


def summarize(reviews, vault_path, weeks=4):
    """Top-level summary suitable for JSON output / coaching consumption."""
    if not reviews:
        return {
            "vault_path": vault_path,
            "review_count": 0,
            "windows_weeks": weeks,
            "error": (
                f"No workout-review markdown files with usable rpe+if frontmatter found "
                f"in {vault_path}. Ensure reviews include `rpe: <1-10>` and `if: <0.0-1.5>` fields."
            ),
        }

    by_type = compute_trend(reviews, weeks=weeks)

    # Overall flag if any session type shows rising_rpe_at_constant_if
    overall_flags = [t for t, v in by_type.items() if v.get("flag") == "rising_rpe_at_constant_if"]

    return {
        "vault_path": vault_path,
        "review_count": len(reviews),
        "windows_weeks": weeks,
        "date_range": [reviews[0]["date"], reviews[-1]["date"]],
        "by_session_type": by_type,
        "overall_flag": "rising_rpe_at_constant_if" if overall_flags else None,
        "flagged_session_types": overall_flags,
        "interpretation": (
            "Functional overreaching signal — rising RPE at same IF detected in: "
            f"{', '.join(overall_flags)}. See `references/periodization.md` "
            "→ RPE Trend Escalation for action."
            if overall_flags else "No overreaching signal detected."
        ),
        "recent_reviews": reviews[-min(10, len(reviews)):],
    }


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(
        description="Aggregate RPE trends from Obsidian workout-review frontmatter"
    )
    p.add_argument("--vault-path", required=True,
                   help="Path to Obsidian workout-reviews directory "
                        "(typically <CYCLING_VAULT_PATH>/cycling-fitness-coach/workout-reviews/)")
    p.add_argument("--weeks", type=int, default=2,
                   help="Window size in weeks (compares last N weeks vs prior N weeks; default: 2)")
    p.add_argument("-o", "--output",
                   help="Write summary JSON to file (default: stdout)")
    return p


def main():
    args = build_parser().parse_args()
    if args.weeks < 1 or args.weeks > 26:
        print(f"ERROR: --weeks must be between 1 and 26 (got {args.weeks})", file=sys.stderr)
        sys.exit(1)

    reviews, err = collect_reviews(args.vault_path)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    summary = summarize(reviews, args.vault_path, weeks=args.weeks)
    out = json.dumps(summary, indent=2, default=str, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
