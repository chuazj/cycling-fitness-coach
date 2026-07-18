---
title: 2026-Q3 quarterly audit — citation currency, methodology drift, eval refresh, output contract
date: 2026-07-18
type: audit
audit_scope: [citation-currency, eval-refresh, methodology-drift, output-contract]
skill: cycling-fitness-coach
skill_version_start: 37abdb7
skill_version_end: 05400e1
rubric: internal-methodology-audit
status: actioned
findings_count: 58
findings_high: 3
findings_medium: 20
findings_low: 35
tags: [cycling, coaching, audit]
---

# 2026-Q3 Quarterly Audit

First audit to run under the repo-tracked quarterly protocol (`governance/audit_protocol.md`). It began as an open-ended review request — "any bug fix / improvements needed?" — and landed inside the Q3 window, so it was run as the scheduled quarterly audit and extended to cover all four protocol scopes.

**Method.** Four parallel review agents, each scoped to one dimension: package code (`scripts/intervals_icu/`), generator/PMC scripts, doc-consistency, and coaching methodology. Every claim was then re-verified against the primary source before any fix was written — file and line read directly, scripts re-run, and for one finding the live intervals.icu API probed.

**Verification outcome: 53/53 claims held, zero walked back.** This is the notable result of the cycle. The standing rule to primary-source-check subagent claims exists because roughly 40% of review claims failed verification in the 2026-05-09 cycle. Holding at 53/53 here is a real change, and the one finding that *would* have been wrong was caught by that discipline rather than by the reviewers (see F-P1-MAXW below).

---

## §1 Audit table

Findings are grouped by severity. P0 = active crash or an incorrect athlete-facing prescription. P1 = wrong output or a contradiction an athlete would act on. P2 = accuracy, hardening, and drift.

### P0 — shipped in `e74cb0d`, `61a8cba`

| ID | Area | Gap | Action |
|----|------|-----|--------|
| F-P0-RPE | `scripts/rpe_trend.py` | Unguarded `float()` on Obsidian frontmatter. One malformed value (`if: 0.84 # felt hard`) killed the entire scan, and with it the prediction_tracker seed/reconcile path that depends on it. | try/except → stderr warning, skip the record, continue the scan. |
| F-P0-PRED | `scripts/prediction_tracker.py` | `predict` without `--session-date` wrote `reconcile_when: null`; every later `reconcile` then crashed. A silent write producing a delayed, unrelated-looking crash. | `--session-date` required and ISO-validated at predict; reconcile defensively guards the parse. |
| F-P0-BAND | `workflows/advise.md` | The Recovery-Prescription table treated Whoop Recovery 34–66 as one band, while `readiness.py` and `training_zones.md` subdivide it at 50. The table could prescribe Threshold on a morning the engine caps at sweet spot — two documented answers to the same question. | Row split into Moderate-high (50–66, YELLOW-HIGH) and Moderate-low (34–49, YELLOW-LOW, ceiling SS 88–94%), plus an addendum stating the engine ceiling always wins. |

### P1 — shipped in `e74cb0d`, `61a8cba`, `28f067e` (20 findings)

Representative, not exhaustive:

| ID | Area | Gap | Action |
|----|------|-----|--------|
| F-P1-MAXW | `scripts/intervals_icu/activity.py` | Reported max power was a 5s average, not a true max. **The reviewer's proposed fix was wrong** and was rejected on evidence: a live API probe showed `p_max` constant at 697 W across different rides — it is the athlete's *all-time* max, not per-activity. `icu_pm_p_max` matched the 1s stream maxima (172 W, 140 W). | Use `icu_pm_p_max`. Also corrected `references/intervals_icu_api.md`, whose misleading field description is what produced the bad suggestion. |
| F-P1-SLEEP | `scripts/intervals_icu/readiness.py` | The "sleep score ≥85 upgrades a short night" "upgrade" was a no-op, but the athlete-facing template stated the upgrade had happened. The skill was telling the athlete something it had not done. | Genuine green upgrade at 6–7 h + score ≥85, with the reasoning stated in the note. |
| F-P1-TZ | `scripts/fit_ingest.py` | FIT `start_time` is UTC but was emitted as `start_date_local`. Every pre-08:00 SGT ride was dated to the previous day. | Derive the UTC offset from the FIT activity message (`local_timestamp` − `timestamp`); emit a `start_time_utc_fallback` warning when the pair is unavailable. |
| F-P1-PII | `.gitignore`, `CLAUDE.md`, `governance/artifacts.md` | `prediction_report.json` was a documented output but not ignored — a PII file (forecasts, training-load history) in a repo with a live push remote. Uncommitted glob rules from a prior session were also still sitting in the working tree. | Globs committed, `/prediction_report*.json` added, CLAUDE.md and artifacts.md synced. The install path had live proof: untracked `wellness7.json` etc. sitting there. |
| F-P1-FTPW | `scripts/prediction_tracker.py` | `ftp_gain` reconcile matched records with no time bound, so an FTP test months off the predicted date still reconciled as a hit. | `FTP_RECONCILE_WINDOW_DAYS = 14`; out-of-window records skipped. |
| F-P1-TSB | 3 docs | TSB band boundaries had drifted apart across `readiness_template.md`, `plan_state_schema.md`, and `advise.md`. | All aligned to `readiness.py` as canonical: fresh ≥+5, neutral −10..+5, productive −30..−10, overreached <−30, detraining >+15. |

### P2 — shipped in `0752b85`, `d09d56c` (~28 findings)

Code hardening: non-dict ledger lines; `:` in batch ZWO filenames (Windows drive-relative and NTFS alternate-data-stream escapes); `--planned-tss` type validation; clean CLI errors from `generate_zwo.py`; `--list-recent 0`; FTP/weight prompting on modes that never read them.

Two P2s were more than hygiene. FIT lap `intensity` is an enum (`active`/`rest`/…), not a numeric IF — laps now map to WORK/RECOVERY instead of falling through a 75%-of-max heuristic. And Garmin smart recording breaks the 1 Hz assumption underneath NP/TSS, so files with samples < 80% of moving time now carry a `non_1hz_recording` warning instead of silently producing wrong numbers.

Docs: CLI reference accuracy (undocumented flags, corrected `zwo_lint` exit codes, canonical output filenames), IF-band and zone-heading alignment to the adaptation cascade, taper selection tiebreak, `--wellness 21` so one missed WHOOP night cannot silently disable the CV-trend flag, and KEYSTONE session tagging wired end-to-end (producer in `plan.md` Step 5, schema documentation, rule-registry row) — the consumer rule had been shipped with nothing producing its input.

---

## §2 Scope coverage

### Scope 1 — Citation currency (**actioned**, `5129a61`)

All three citations queued for Q3 by the 2026-05-26 refactor proposal are closed, each verified against the publisher or journal record:

| Authority | Result |
|-----------|--------|
| Mujika & Padilla (2003) | *Med Sci Sports Exerc* 35(7):1182–1187 — volume, issue, and page range confirmed exactly as cited. Inline cite added at `race_taper.md` → 2-Week Taper. Mujika (2010), *Scand J Med Sci Sports* 20(Suppl 2):24–31, also confirmed. |
| San Millán & Brooks (2018) | *Sports Med* 48(2):467–479 confirmed. **Scope caveat added**: cross-sectional trained-vs-untrained comparison, not a Z2 dose-response trial — it cannot support "X hours of Z2 per week". Mechanism anchored to Brooks (1986), *Fed Proc* 45:2924–2929, with the 2018 *Cell Metabolism* consolidation (27(4):757–785) added as the current review. |
| Allen-Coggan | Re-anchored to the 3rd edition (Allen, Coggan & McGregor, VeloPress 2019). **Edition delta assessed as non-material**: the 3rd ed. adds FRC, Pmax, mFTP, and the Power Duration Curve, but the Z1–Z7 boundaries and TSS/NP/IF definitions this skill actually uses are unchanged. Source footers added to `training_zones.md` and `plan_state_schema.md`. |

Currency log rolled forward — all seven authorities now **Next due 2026-Q4**. This is what stops Weekly Review Step 4b from surfacing "audit due" every week.

Two items are carried forward rather than closed, and are now explicit queue rows instead of buried "needs verification" notes: the exact Rønnestad (2020) VO2max paper behind the 30/15s default, and a re-read of Seiler & Tønnessen (2009) in *Sportscience* (online-only and editable post-publication).

### Scope 2 — Eval suite refresh (**actioned**, `05400e1`)

The Q3 doc batch added four SKILL.md dispatch rows (fueling, readiness/Whoop, menstrual-cycle, .fit upload) with no positive probe for any of them — new routing shipped untested. Added 5 positives, 23 → 28 queries (11 → 16 positive, 12 negative unchanged).

Each new probe sits deliberately next to an existing negative so the pair tests a boundary rather than an easy case. The sharpest is readiness: "Whoop recovery 38% with threshold scheduled" and "HRV dropped to 42 from ~60" must trigger, while the existing "resting HR jumped 58 → 72, do I need a doctor?" must not. Training-decision framing routes to the coach; medical-advice framing must not.

**Not scored.** Per CLAUDE.md → "Eval harness limitations", `run_eval.py` cannot measure this skill once installed (real-skill shadowing, plus the harness counting any first tool call other than Skill/Read as a no-trigger). Added on rubric grounds, consistent with the standing precedent from the writing-skills audit.

### Scope 3 — Methodology drift (**actioned**, `61a8cba`, `d09d56c`)

Fifteen quote-level methodology claims were re-verified against their source docs before any edit. The drift found was internal — the skill contradicting itself — rather than the literature having moved:

- Session IF bands had drifted from the adaptation cascade (sweet spot, threshold, VO2max, over-under all realigned).
- The Recovery-band split at 50 existed in the engine and in `training_zones.md` but not in the prescription table (see F-P0-BAND).
- Race-day TSB target appeared as two different bands; unified to +5..+15 per Mujika & Padilla.
- HR-shortfall and RPE-escalation rules lacked the "2+ consecutive sessions" qualifier the cascade assumes.
- The +5% aggressive ramp could stack past the +10%/week ceiling; now explicitly capped.

One external note recorded so the next audit does not re-discover it as new: the 2018 *Sports Med* paper drew published comment (Monferrer-Marín et al., 2022, with authors' reply) contesting aspects of the metabolic-flexibility assessment method. It does not touch any claim this skill makes — the skill cites the trained-vs-untrained contrast, not the disputed protocol.

### Scope 4 — Output contract (**actioned**, `28f067e`, `d09d56c`)

Walked `governance/artifacts.md` against what the scripts actually emit. One real PII regression (F-P1-PII) and one schema-citation error: `artifacts.md` cited a weekly-summary output filename that the CLI reference did not document, now canonically `summary.json`. Ignore rules were converted to root-anchored globs so ad-hoc suffixed variants (`wellness7.json`) are caught while test fixtures under `tests/fixtures/` stay unaffected.

---

## §3 Out of scope

Deliberately not actioned. Listed so the Q4 audit does not re-discover them:

- **`fitparse` not installed locally.** Two `.fit` tests skip and the .fit fallback path is dead on this machine. Explicitly dropped by the athlete this cycle — it is an environment task, not a skill defect, and the code path is unit-tested regardless.
- **Stale `.git/worktrees/w6base`.** Cannot be pruned (OneDrive holds a lock); prints a `Permission denied` line on every commit. Commits succeed. Cosmetic — retry when OneDrive releases it.
- **Rønnestad (2020) and Seiler & Tønnessen (2009) verification.** Carried to Q4 as explicit queue rows in `audit_protocol.md`.
- **Eval scoring.** Blocked by harness limitations, not by this skill. Revisit only if the harness gains a mode that tolerates installed user-level skills.

---

## §4 Resolution

All findings actioned. Six commits, all pushed to `origin/master` and ff-merged into the install path.

| Commit | Contents |
|--------|----------|
| `28f067e` | PII/hygiene — gitignore globs committed, `prediction_report` covered, CLAUDE.md + artifacts.md synced |
| `e74cb0d` | P0/P1 code — crash guards, sleep upgrade, FIT local time, true max power (tests 666 → 680) |
| `61a8cba` | P0-3 + P1 coaching docs — one prescription per athlete state |
| `0752b85` | P2 code — input hardening, FIT lap enum, non-1 Hz warning (tests 680 → 691) |
| `d09d56c` | P2 docs — CLI reference accuracy, methodology alignment, KEYSTONE wiring |
| `5129a61` | Q3 citation queue closed; currency log rolled to 2026-Q4 |
| `05400e1` | Eval Scope 2 — 5 positives for the new dispatch rows (23 → 28) |

**Test suite: 691 passing, 2 skipped** (the skips are `fitparse`, per §3). Every code change was written test-first with the failing test observed first.

**Next audit: 2026-Q4** (October window). Weekly Review Step 4b will surface it once the currency-log dates pass.
