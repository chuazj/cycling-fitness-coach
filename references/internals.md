# Internals — Implementation Notes for Debugging / Modifying

Background detail for debugging or modifying the skill's scripts. **Read this file when working on `scripts/intervals_icu/wellness.py`, `readiness.py`, `metrics.py`, `activity.py`, or anything that touches FTP detection, wellness schema, signal mode, or baseline maturity** — the rules in `CLAUDE.md` reference invariants documented here.

Not load-bearing during normal coaching workflows — workflows derive their behaviour from the reference docs and the script output directly.

---

## Activity analysis internals

- **`data_completeness` field**: `analyze()` output includes `data_completeness` ("complete" or "partial (missing: streams, ...)"). If not "complete", lead coaching analysis with a data quality warning.
- **Stream validation**: `zone_percent`, `zone_seconds`, and `cardiac_drift` are explicitly `None` (not absent) when power/HR streams are too short (fewer than 30 samples). Distinguishes "unavailable" from "no zones used".
- **`--compact` flag**: `intervals_icu_api.py --compact` omits rarely-used fields (VI, EF, zone_seconds, per-interval distance/max_watts/intensity) for token-efficient coaching output.
- **`training_day_pattern`**: `pmc_calculator.py --bootstrap` output includes `training_day_pattern` (e.g., `["Tue", "Thu", "Sat"]`) — auto-detected from activity history day-of-week frequency. Use to pre-fill training days in the Create Plan workflow Step 2 instead of asking the athlete.
- **weekly_summary top-3 optimization**: `weekly_summary()` fetches power curves only from the top-3 TSS activities (not all N) via `ThreadPoolExecutor(max_workers=3)`. Result includes `week_peaks` (5s/1min/5min/20min max across the 3) and `power_profile` (Coggan classification) when weight is provided.
- **Indoor/outdoor context**: Derived from `detect_indoor(trainer, sport_type)` — `bool(trainer) or sport_type in ("VirtualRide", "VirtualRun")`. intervals.icu may return `trainer: null` for Zwift activities — `sport_type` fallback handles this.
- **Power profile categories**: Coggan-based W/kg thresholds at 5s, 1min, 5min, 20min. Used by `analyze_power_profile()` to classify rider type (sprinter, time_trialist, pursuiter, all_rounder) and identify strengths/weaknesses.

## FTP test detection

- **Detection methods are a list, not a single string**: `detect_ftp_test()` returns `detection_methods` (list) — multiple detection heuristics can match simultaneously. Each detected method emits TWO fields: the **value** (`estimated_ftp_20min` / `estimated_ftp_ramp`, rounded watts) AND the **formula string** (`estimated_ftp_formula_20min` / `estimated_ftp_formula_ramp`, e.g. `"20min_avg × 0.95"`). The formulas are per-method (not a shared `estimated_ftp_formula`). Workflow `analyze.md` has the full schema.
- **FTP test bounds**: 20-min heuristic triggers only when 80–150% of reference FTP (rejects anomalous data).

## Wellness / readiness internals

- **Baseline maturity (tiered)**: `wellness_summary()` returns `baseline_maturity` (insufficient / preliminary / consolidating / stable) + per-metric `baseline_sample_sizes`. Deviation flags (RHR/HRV/respiration + the SpO2 relative-yellow) auto-suppressed below `MIN_BASELINE_SIZE = 7`; absolute-threshold flags (Recovery/sleep/subjective + the SpO2 <90% red floor) fire regardless. Surface `baseline_note` verbatim in coaching output. Rationale in `references/training_zones.md` → Baseline maturity note. Legacy `partial_baseline` boolean still emitted (true only when history is empty).
- **Signal mode (non-WHOOP graceful degradation)**: `detect_signal_mode()` classifies the latest record into `signal_mode` — `full` (WHOOP Recovery present), `reduced` (HRV and/or RHR, no Recovery), `minimal` (only sleep hours / subjective fields), `insufficient` (nothing usable). `wellness_summary()` and `readiness_check()` both emit it, and the readiness verdict degrades per mode (4-band → 3-band → coarse). Don't assume the athlete uses WHOOP — a non-WHOOP athlete gets a `reduced`/`minimal` verdict with a banner, not an error.
- **Whoop fields from intervals.icu (what flows, what doesn't)**: Whoop syncs Recovery, HRV (rMSSD), RHR, sleep hours, sleep score, respiration, and SpO2 to intervals.icu. **Whoop strain is NOT synced** (dropped at the intervals.icu integration layer — not in `client.get_wellness()` output regardless of athlete settings). Don't propose features that depend on Whoop strain; use TSS for training load instead.
- **Whoop-exclusive wellness fields**: `WHOOP_EXCLUSIVE_FIELDS` in `wellness_summary()` lists fields that ONLY arrive via Whoop sync (no manual UI in intervals.icu): `resting_hr, hrv, sleep_score, readiness, respiration, spo2`. `sleep_hours` is intentionally excluded — intervals.icu lets athletes enter sleep manually, so a record with only `sleepSecs` populated is NOT a Whoop-synced day. When adding a wellness field, decide which polarity it has before touching `days_with_whoop_data` membership.
- **wellness_summary output schema**: Beyond `baseline` + `latest` + `flags`, wellness_summary returns `recovery_slope_3day` (today vs 3 days ago with `alarm: bool`), `subjective_stale_warning` (true when 3+ subjective fields all=1), `training_load` (CTL/ATL/TSB pulled from latest wellness record's server-side values), `days_with_whoop_data` (count of records with ≥1 Whoop-sourced metric — disambiguates from `days_with_data` which counts all returned dates), `signal_mode` (which readiness signals are present — see above), and `progression_signal` (HRV-above-band 3 days + CTL rising → green-lights a 5–10% TSS bump; None when criteria unmet). `readiness_check()` consumes these from wellness_summary rather than recomputing — single source of truth.
- **Mid-Week Check-In delegates to `--readiness-check`**: `workflows/advise.md` Mid-Week Check-In runs `intervals_icu_api.py --readiness-check`, not `--wellness 14`. The readiness-check tool returns the full wellness summary fields plus verdict_band (GREEN / YELLOW-HIGH / YELLOW-LOW / RED in `full` signal mode; a coarser 3-band set in `reduced`) + ceiling + sleep-score tiebreaker logic. Weekly Review (`workflows/plan.md`) still uses `--wellness 14` because it needs the per-day daily array for the weekly trend.
- **Shared readiness template**: the per-metric rendering (Recovery / Sleep / HRV / RHR / Respiration / SpO2 / TSB / Subjective) is now centralised in `references/readiness_template.md`. When adding a new wellness metric, update the canonical line skeleton + threshold legend in that file **once** — both workflows pick it up. Each workflow keeps only its workflow-specific framing inline (verdict/ceiling for Mid-Week, trend headers for Weekly Review).

## RPE collection

- **RPE collection**: Session RPE (1-10) collected after workout analysis; compared against IF for mismatch detection (fatigue signal, FTP underestimate). Stored in Obsidian frontmatter as `rpe`. RPE:Power mismatch analysis is noted in body text, not frontmatter.
