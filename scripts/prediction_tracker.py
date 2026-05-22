#!/usr/bin/env python3
"""
Prediction Tracker for Cycling Fitness Coach (W5 — predict → measure → calibrate).

Logs forecasts (RPE-at-IF, FTP-gain) to a JSONL ledger, reconciles them against
actual outcomes, and flags when a forecasting model needs recalibration.

No third-party dependencies.

Usage:
    python prediction_tracker.py --mode seed-baseline --vault-path "<reviews dir>"
    python prediction_tracker.py --mode predict --type rpe_at_if --if 0.84 \
        --slot morning --session-date 2026-06-02 --session-type Threshold
    python prediction_tracker.py --mode predict --type ftp_gain --start-ftp 188 \
        --block-label "FTP Builder, 4wk" --block-end 2026-06-28
    python prediction_tracker.py --mode reconcile --vault-path "<reviews dir>"
    python prediction_tracker.py --mode reconcile --vault-path "<reviews dir>" \
        --new-ftp 196 --ftp-test-date 2026-06-28
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Force UTF-8 on Windows (output and error messages may carry non-ASCII).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# scripts/ is on sys.path when run as `python scripts/prediction_tracker.py`
# and in tests (which insert scripts/ on the path) — so rpe_trend imports directly.
from rpe_trend import collect_reviews

# Generic default forecasting model (the scaffold). The athlete-calibrated
# instance lives in plans/athlete_calibration.md; --seed-baseline produces it.
# if_rpe_base: ordered [upper_exclusive_IF, expected_RPE] rows — first row whose
# bound exceeds the IF wins. The final row's bound (2.0) is an upper sentinel.
DEFAULT_MODEL = {
    "if_rpe_base": [[0.65, 3], [0.75, 5], [0.85, 6], [0.92, 8], [2.0, 9]],
    "corrections": {"post_3pm": 2},
    "ftp_gain_pct": [2.0, 4.0],
}

RPE_TRIGGER_WINDOW = 5        # reconciled RPE predictions per slot
RPE_TRIGGER_THRESHOLD = 1.0   # |mean signed delta| RPE that fires recalibration
FTP_TRIGGER_WINDOW = 2        # consecutive completed blocks


def predict_rpe(model, if_value, slot):
    """Predicted session RPE = base-table lookup by IF + slot correction.

    `slot` is "morning" or "post_3pm"; the post_3pm correction is additive.
    """
    base = model["if_rpe_base"]
    rpe = base[-1][1]
    for bound, value in base:
        if if_value < bound:
            rpe = value
            break
    if slot == "post_3pm":
        rpe += model["corrections"].get("post_3pm", 0)
    return min(rpe, 10)  # RPE is a 1-10 scale; corrections must not push it off-scale


def predict_ftp_gain(model, start_ftp):
    """Predicted post-block FTP range from the per-block %-gain model."""
    low_pct, high_pct = model["ftp_gain_pct"]
    return {
        "pct_low": low_pct,
        "pct_high": high_pct,
        "watts_low": round(start_ftp * (1 + low_pct / 100)),
        "watts_high": round(start_ftp * (1 + high_pct / 100)),
    }


def load_ledger(path):
    """Read the JSONL ledger -> list of record dicts. Missing file -> [].

    Malformed lines are skipped with a WARNING to stderr (includes 1-based line
    number and a short snippet) so a single corrupt line never aborts the read.
    Empty/whitespace-only lines are silently skipped.
    """
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                snippet = line[:72] + ("..." if len(line) > 72 else "")
                print(
                    f"WARNING: ledger line {lineno} is not valid JSON — skipping."
                    f" Snippet: {snippet!r}",
                    file=sys.stderr,
                )
    return records


def save_ledger(path, records):
    """Rewrite the JSONL ledger — one JSON object per line."""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def next_id(records):
    """Next sequential prediction id, e.g. 'P004'. Empty ledger -> 'P001'."""
    nums = []
    for rec in records:
        rid = rec.get("id", "")
        if isinstance(rid, str) and rid.startswith("P") and rid[1:].isdigit():
            nums.append(int(rid[1:]))
    return "P%03d" % ((max(nums) + 1) if nums else 1)


CALIBRATION_HEADER = """\
# Athlete Prediction Calibration

Athlete-calibrated forecasting model for the W5 validation loop. The JSON block
below is the operative model read by `scripts/prediction_tracker.py`. Regenerated
by `--mode seed-baseline`; edited by the coach (propose-and-confirm) when the
weekly review fires a `recalibration_needed` flag. Methodology + the generic
default: `references/prediction_calibration.md`.
"""


def load_calibration(path):
    """Read the model from athlete_calibration.md's fenced JSON block.

    Missing file -> a deep copy of DEFAULT_MODEL (the generic scaffold).
    """
    if not os.path.isfile(path):
        return json.loads(json.dumps(DEFAULT_MODEL))
    with open(path, encoding="utf-8") as f:
        content = f.read()
    marker = content.find("```json")
    if marker == -1:
        raise ValueError(f"{path}: no ```json model block found")
    start = content.index("\n", marker) + 1
    end = content.find("```", start)
    if end == -1:
        raise ValueError(f"{path}: unterminated ```json block")
    return json.loads(content[start:end])


def write_calibration(path, model):
    """Write athlete_calibration.md — prose header + a fenced JSON model block."""
    block = "```json\n" + json.dumps(model, indent=2) + "\n```\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(CALIBRATION_HEADER + "\n" + block)


def seed_baseline(reviews):
    """Fit the IF->RPE base table from existing workout reviews.

    For each IF bucket in DEFAULT_MODEL['if_rpe_base'], take the mean RPE of all
    reviews whose IF falls in that bucket (lower-inclusive, upper-exclusive) and
    round to the nearest integer. Buckets with no review data keep the
    DEFAULT_MODEL value. `corrections` and `ftp_gain_pct` are carried over from
    DEFAULT_MODEL unchanged — the existing reviews lack the time-of-day and
    per-block data needed to fit them (see the design spec, Section F).

    `reviews` is the list returned by rpe_trend.collect_reviews() — each item
    has 'if' and 'rpe' float keys.
    """
    model = json.loads(json.dumps(DEFAULT_MODEL))  # deep copy
    base = model["if_rpe_base"]
    lower = 0.0
    for row in base:
        bound = row[0]
        bucket = [r["rpe"] for r in reviews if lower <= r["if"] < bound]
        if bucket:
            row[1] = round(sum(bucket) / len(bucket))
        lower = bound
    return model


def _slot_of(record):
    """The slot a prediction was made for; defaults to 'morning'."""
    return record.get("inputs", {}).get("slot", "morning")


def reconcile(records, reviews, new_ftp=None, ftp_test_date=None):
    """Fill in actuals for open predictions. Mutates and returns `records`,
    plus the list of records reconciled in this run.

    rpe_at_if: matched to a workout review whose session type matches and whose
        date is within +/-2 days of the prediction's reconcile_when; nearest
        date wins; each review is consumed at most once.
    ftp_gain: reconciled only when new_ftp + ftp_test_date are supplied (the
        coach passes them from analyze.md Step 6's confirmed FTP test) and the
        test date is on or after the prediction's `made` date.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    just = []
    used_reviews = set()

    for rec in records:
        if rec.get("status") != "open":
            continue

        if rec["type"] == "rpe_at_if":
            target = datetime.strptime(rec["reconcile_when"], "%Y-%m-%d")
            want_type = (rec["inputs"].get("session_type") or "").lower()
            best = None  # (gap_days, index, review)
            for idx, rv in enumerate(reviews):
                if idx in used_reviews:
                    continue
                if want_type and want_type not in (rv["session_type"] or "").lower():
                    continue
                gap = abs((datetime.strptime(rv["date"], "%Y-%m-%d") - target).days)
                if gap <= 2 and (best is None or gap < best[0]):
                    best = (gap, idx, rv)
            if best is not None:
                _, idx, rv = best
                used_reviews.add(idx)
                rec["actual"] = rv["rpe"]
                rec["delta"] = round(rv["rpe"] - rec["predicted"], 2)
                rec["status"] = "reconciled"
                rec["reconciled"] = today
                just.append(rec)

        elif rec["type"] == "ftp_gain" and new_ftp is not None:
            if ftp_test_date and ftp_test_date < rec["made"]:
                continue
            start = rec["inputs"]["start_ftp"]
            actual_pct = round((new_ftp - start) / start * 100, 1)
            p = rec["predicted"]
            if actual_pct < p["pct_low"]:
                delta = "outside (%.1fpp below range)" % (p["pct_low"] - actual_pct)
            elif actual_pct > p["pct_high"]:
                delta = "outside (%.1fpp above range)" % (actual_pct - p["pct_high"])
            else:
                delta = "inside"
            rec["actual"] = {"ftp": new_ftp, "pct": actual_pct}
            rec["delta"] = delta
            rec["status"] = "reconciled"
            rec["reconciled"] = ftp_test_date or today
            just.append(rec)

    return records, just


def check_rpe_trigger(records):
    """Per slot, over the last RPE_TRIGGER_WINDOW reconciled rpe_at_if
    predictions, flag when |mean signed delta| >= RPE_TRIGGER_THRESHOLD.

    Returns {slot: {status, mean_delta, n}}. status is "recalibration_needed",
    "ok", or "insufficient_data".
    """
    by_slot = {}
    for rec in records:
        if rec["type"] == "rpe_at_if" and rec.get("status") == "reconciled":
            by_slot.setdefault(_slot_of(rec), []).append(rec)
    flags = {}
    for slot, recs in by_slot.items():
        recs = sorted(recs, key=lambda r: r["reconciled"])[-RPE_TRIGGER_WINDOW:]
        if len(recs) < RPE_TRIGGER_WINDOW:
            flags[slot] = {"status": "insufficient_data", "n": len(recs)}
            continue
        mean_delta = round(sum(r["delta"] for r in recs) / len(recs), 2)
        flags[slot] = {
            "status": ("recalibration_needed"
                       if abs(mean_delta) >= RPE_TRIGGER_THRESHOLD else "ok"),
            "mean_delta": mean_delta,
            "n": len(recs),
        }
    return flags


def attribute_rpe(flags):
    """Given check_rpe_trigger() output, name what to recalibrate.

    Both slots flagged with the same-sign bias -> the base table.
    Only post_3pm flagged -> the post_3pm correction constant.
    Otherwise -> None (nothing to attribute).
    """
    fired = {s: f for s, f in flags.items()
             if f.get("status") == "recalibration_needed"}
    if not fired:
        return None
    if len(fired) >= 2:
        signs = {f["mean_delta"] > 0 for f in fired.values()}
        if len(signs) == 1:
            return "base table (bias present in all slots)"
        return "base table and/or corrections (mixed-sign bias — review per slot)"
    slot = next(iter(fired))
    if slot == "post_3pm":
        return "post_3pm correction constant"
    return "base table (morning slot bias)"


def check_ftp_trigger(records):
    """Flag when the last FTP_TRIGGER_WINDOW reconciled ftp_gain predictions all
    landed outside their predicted range.

    Returns {status, n}. status is "recalibration_needed", "ok", or
    "insufficient_data".
    """
    recs = [r for r in records
            if r["type"] == "ftp_gain" and r.get("status") == "reconciled"]
    recs = sorted(recs, key=lambda r: r["reconciled"])[-FTP_TRIGGER_WINDOW:]
    if len(recs) < FTP_TRIGGER_WINDOW:
        return {"status": "insufficient_data", "n": len(recs)}
    all_outside = all(str(r["delta"]).startswith("outside") for r in recs)
    return {
        "status": "recalibration_needed" if all_outside else "ok",
        "n": len(recs),
    }


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    p = argparse.ArgumentParser(
        description="Prediction tracker — log, reconcile, and calibrate forecasts")
    p.add_argument("--mode", required=True,
                   choices=["seed-baseline", "predict", "reconcile"])
    p.add_argument("--ledger-path", default="plans/prediction_ledger.jsonl")
    p.add_argument("--calibration-path", default="plans/athlete_calibration.md")
    p.add_argument("--vault-path",
                   help="Obsidian workout-reviews dir (seed-baseline, reconcile)")
    # predict
    p.add_argument("--type", choices=["rpe_at_if", "ftp_gain"])
    p.add_argument("--if", dest="if_value", type=float)
    p.add_argument("--slot", choices=["morning", "post_3pm"], default="morning")
    p.add_argument("--session-date")
    p.add_argument("--session-type")
    p.add_argument("--start-ftp", type=int)
    p.add_argument("--block-label")
    p.add_argument("--block-end")
    # reconcile
    p.add_argument("--new-ftp", type=int)
    p.add_argument("--ftp-test-date")
    p.add_argument("-o", "--output")
    return p


def run_predict(args):
    """--mode predict: look up the model, append an open ledger record."""
    model = load_calibration(args.calibration_path)
    records = load_ledger(args.ledger_path)
    rec = {"id": next_id(records), "type": args.type,
           "made": datetime.now().strftime("%Y-%m-%d"),
           "status": "open", "actual": None, "reconciled": None, "delta": None}
    if args.type == "rpe_at_if":
        rec["predicted"] = predict_rpe(model, args.if_value, args.slot)
        rec["reconcile_when"] = args.session_date
        rec["inputs"] = {"if": args.if_value, "slot": args.slot,
                         "session_type": args.session_type}
    else:  # ftp_gain
        rec["predicted"] = predict_ftp_gain(model, args.start_ftp)
        rec["reconcile_when"] = args.block_end
        rec["inputs"] = {"start_ftp": args.start_ftp, "block": args.block_label}
    records.append(rec)
    save_ledger(args.ledger_path, records)
    return {"mode": "predict", "logged": rec}


def run_seed(args):
    """--mode seed-baseline: fit the athlete model from Obsidian reviews."""
    reviews, err = collect_reviews(args.vault_path)
    if err:
        return {"mode": "seed-baseline", "error": err}
    model = seed_baseline(reviews)
    write_calibration(args.calibration_path, model)
    return {"mode": "seed-baseline", "reviews_used": len(reviews),
            "written": args.calibration_path, "model": model}


def run_reconcile(args):
    """--mode reconcile: match open predictions to actuals, emit a report."""
    records = load_ledger(args.ledger_path)
    reviews, err = collect_reviews(args.vault_path) if args.vault_path else ([], None)
    records, just = reconcile(records, reviews,
                              new_ftp=args.new_ftp, ftp_test_date=args.ftp_test_date)
    save_ledger(args.ledger_path, records)
    rpe_flags = check_rpe_trigger(records)
    return {
        "mode": "reconcile",
        "reconciled_this_run": len(just),
        "review_load_error": err,
        "open_remaining": sum(1 for r in records if r["status"] == "open"),
        "rpe_trigger": rpe_flags,
        "rpe_attribution": attribute_rpe(rpe_flags),
        "ftp_trigger": check_ftp_trigger(records),
        "just_reconciled": just,
    }


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Range validation — only fires when the arg was actually supplied.
    if args.if_value is not None and not (0.3 <= args.if_value <= 1.5):
        parser.error(
            f"--if must be between 0.3 and 1.5 (got {args.if_value})"
        )
    if args.start_ftp is not None and not (50 <= args.start_ftp <= 500):
        parser.error(
            f"--start-ftp must be between 50 and 500 watts (got {args.start_ftp})"
        )
    if args.new_ftp is not None and not (50 <= args.new_ftp <= 500):
        parser.error(
            f"--new-ftp must be between 50 and 500 watts (got {args.new_ftp})"
        )

    if args.mode == "predict":
        if not args.type:
            print("ERROR: --type is required for --mode predict", file=sys.stderr)
            sys.exit(1)
        if args.type == "rpe_at_if" and args.if_value is None:
            print("ERROR: --if is required for --type rpe_at_if", file=sys.stderr)
            sys.exit(1)
        if args.type == "ftp_gain" and args.start_ftp is None:
            print("ERROR: --start-ftp is required for --type ftp_gain", file=sys.stderr)
            sys.exit(1)
        result = run_predict(args)
    elif args.mode == "seed-baseline":
        if not args.vault_path:
            print("ERROR: --vault-path is required for --mode seed-baseline",
                  file=sys.stderr)
            sys.exit(1)
        result = run_seed(args)
    else:  # reconcile
        result = run_reconcile(args)
    out = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
