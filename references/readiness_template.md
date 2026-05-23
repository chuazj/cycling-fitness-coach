# Readiness Output Template

Canonical rendering rules for the wellness/readiness output block shared by the Mid-Week Check-In (`workflows/advise.md`) and Weekly Review (`workflows/plan.md`).

**Why this file exists:** both workflows render the same set of WHOOP-sourced metrics (Recovery / Sleep / HRV / RHR / Respiration / SpO2 / TSB / Subjective). When a new wellness metric is added, the per-metric rendering line and its threshold legend must be updated **once here**, not in two workflow files.

The two workflows differ in *framing* (Mid-Week shows a single-day verdict + ceiling; Weekly Review shows a trend) and in the *script output schema* they consume (`--readiness-check` vs `--wellness 14`). Each workflow keeps its workflow-specific header section; both use this file for the per-metric body.

---

## Per-metric line skeleton (canonical)

Map your script-output field paths to the placeholders below. Mid-Week uses the `--readiness-check` structure (`recovery.score`, `hrv.today`, …). Weekly Review uses `--wellness 14` (latest day from the daily array).

### Recovery
```
- Recovery: {score} → {band}  {if slope_3day.alarm: ⚠ slope {three_days_ago}→{today} ({delta:+}pt over 3 days)}
```
- Whoop bands: **red <34, yellow 34-66, green ≥67**. (Mid-Week subdivides yellow at 50: YELLOW-HIGH 50-66, YELLOW-LOW 34-49.)
- Fires regardless of baseline depth — absolute thresholds.

### Sleep
```
- Sleep: {hours}h, score {score}/100 → {status}  {if note present: ({note})}
```
- Targets: ≥7h pass; 6–7h tiebroken by `sleep_score` (≥85 upgrade, <70 downgrade); <6h red.
- Weekly Review framing: render avg-over-week instead of latest, e.g. `avg {X}h over week`.

### HRV (rMSSD)
```
- HRV: {today}ms vs {n}d baseline {baseline}ms ({delta:+}ms){if band_mean_7d and band_sd_7d: | 7d band μ{band_mean_7d}±{band_sd_7d*0.5} (Plews/Buchheit)}{if cv_pct: | CV {cv_pct}%}
```
- *Yellow* below 7-day band single day; *red* below band 2 consecutive days. *Suppressed if n<7.* CV-trend needs ≥14 days.
- If `cv_trend.rising` is true, append on next line:
  `  └─ ⚠ CV trend: {prior_cv_pct}% → {recent_cv_pct}% ({delta_pp:+}pp over 14d) — widening variability, early autonomic-strain signal`

### RHR
```
- RHR: {today}bpm vs {n}d baseline {baseline}bpm ({delta:+}bpm)
```
- *Yellow at +5 bpm, red at +10 bpm.* Suppressed if n<7.

### Respiration
```
- Respiration: {today:.1f}/min vs {n}d baseline {baseline:.1f}/min ({delta:+}/min)
```
- *Yellow at +1.0/min (early illness), red at +2.0/min (likely active illness).* Suppressed if n<7. Render only if `respiration.today` is non-null.

### SpO2
```
- SpO2: {today}% {OK/WARN/FAIL tag — WARN if ≥2pp below baseline, FAIL if <90%}
```
- *Yellow ≥2pp below 14-day baseline (needs ≥7d history); red <90% absolute floor.*
- If WARN/FAIL, apply the **Apple Watch cross-check** before holding the flag — see `workflows/advise.md` → SpO2 cross-check (Mid-Week section only; Weekly Review just notes the flag and references advise.md).
- Render only if `spo2.today` is non-null.

### TSB context
```
- TSB context: {tsb:+} (CTL {ctl} / ATL {atl}) — {fresh/neutral/productive/overreached}
```
- Status mapping: TSB > +10 fresh; -10 to +10 neutral; -20 to -10 productive; < -20 overreached.

### Subjective fields
Render the Subjective row only when at least one of `fatigue`/`soreness`/`stress`/`mood` is non-null. Join only the non-null fields:
```
- Subjective: fatigue={X}, mood={Y}  {if subjective.stale_warning: ⚠ all filled=1, athlete may not be updating manually}
```
If all four are null, omit the row entirely.

### Active flags
```
**Active flags:** {list flags by severity, or "None — all clear"}
```

### Progression signal (positive)
Render only if `progression_signal` is non-null:
```
**Progression signal (positive):** {rule} — green-lights +5-10% TSS on the next quality session if athlete is in build phase. Mostly dormant in maintenance.
```

---

## Shared interpretation footnotes

These notes are part of the canonical block — render them after the metric lines in both workflows.

**Recovery lag interpretation:** Whoop Recovery is computed from last night's sleep, which primarily processed *yesterday's* training. A yellow/red Recovery this morning usually reflects yesterday's hard session — read it alongside yesterday's training, not today's plan. See `references/training_zones.md` → Recovery Score (Whoop / Wearable) for the full caveat.

**Reading priority:** Recovery score (when present) is the single best summary signal — Whoop folds baseline-calibrated HRV+RHR+sleep+respiration into it. Use the individual metric lines as drill-down explanations of *why* Recovery is what it is. If Recovery is absent (athlete not on a wearable that pushes it), fall back to HRV+RHR+sleep — but with sample-size confidence in mind.

**Baseline-maturity caveat:** When `baseline_maturity` is "preliminary" or "insufficient", deviation-based flags (RHR/HRV/respiration/SpO2-relative) are auto-suppressed below n=7 history. Fall back to Recovery + sleep + subjective fields for fatigue calls in that case. Surface the `baseline_note` verbatim if present.

**Data freshness:** If the latest wellness record is more than 0 days old, lead the section with: **⚠ Latest wellness record is {N} day(s) old — readings below are not today's. Treat as historical, not current state.** (Mid-Week uses `data_age_days`; Weekly Review uses `latest_date_age_days`.)

**Rule priority on flags:** If yellow/red flags are present, weight the adaptation recommendation toward recovery (Rule Priority 1-2 in `references/weekly_adaptation.md` → Rule Priority).

---

## Workflow-specific framing (NOT shared — kept inline in each workflow)

Each workflow wraps the metric body above with its own framing:

- **Mid-Week Check-In (`workflows/advise.md`)** — prefixes with `**Verdict:** {verdict_band} — {verdict text}` + `**Ceiling:** {ceiling}`. Includes the SpO2 cross-check sub-table. Closes with: *"If verdict is YELLOW-LOW or RED, apply the verdict's ceiling to the planned session before showing the session."*
- **Weekly Review (`workflows/plan.md`)** — prefixes with `**Overall:** {green/yellow/red — from overall_status}` + `**Baseline maturity:** {baseline_maturity} (n={smallest sample size})`. Sleep line shows weekly average instead of latest. No verdict band (weekly trend, not single-day call).

When adding a new metric: update **this file's per-metric skeleton** once, plus the per-workflow framing if the new metric needs a special treatment in only one workflow.
