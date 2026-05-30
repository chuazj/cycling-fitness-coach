---
title: Comprehensive 3-Dimension Review — implementation, methodology, code
date: 2026-05-30
type: audit
audit_scope: [methodology-drift, output-contract, citation-currency]
skill: cycling-fitness-coach
skill_version_start: b448557
skill_version_end: b448557
rubric: internal-comprehensive-review (3-dimension, parallel-agent + primary-source verification)
status: actioned
findings_count: 18
findings_high: 0
findings_medium: 6
findings_low: 12
tags: [cycling, coaching, audit, comprehensive-review]
---

# Comprehensive 3-Dimension Review — 2026-05-30

**Method.** Three parallel domain auditors (skill implementation / training methodology / Python code quality),
each instructed to cite exact `file:line` + quote and to label HYPOTHESIS vs VERIFIED. Every load-bearing
finding was then primary-source-verified by the synthesizer before inclusion (per the standing
"verify subagent claims" feedback rule). Test suite run live: **646 pass, 0 fail** (`python -m unittest discover tests -v`).

**Headline.** No P0, no P1 safety/PII issues. The skill is mature (last graded A/92). The findings cluster into
two real correctness items (a silent FTP default; an unbounded FTP-raise path), a set of doc-integrity nits
(test-count drift, two dangling cross-refs), and a backlog of *enforcement* hardening (schema-versioning,
eFTP/TSS reconciliation) that converts "documented + surfaced" into "documented + surfaced + enforced" — the
exact leg the A→A+ program (W9) identified as still open.

---

## Prioritized action list

### P1 — correctness / data-integrity (fix soon)

| ID | Dim | Finding | Fix locus |
|----|-----|---------|-----------|
| P1-1 | Code | `batch_generate_zwo.py` silently defaults `--ftp 200` (no warning) and never runs `check_erg_design` | `batch_generate_zwo.py:138,150` |
| P1-2 | Method | FTP-raise path authorizes "apply new FTP estimate" with **no upper sanity bound**, contradicting `adaptation_rules.md` | `weekly_adaptation.md:94` |
| P1-3 | Impl | `governance/artifacts.md` has two dangling cross-refs to non-existent anchors (`→ Ledger schema`, `→ Model artifacts`) | `artifacts.md:27-28` |
| P1-4 | Impl | Test-count drift: two **canonical** docs say 637; actual is 646 | `cli_reference.md:7`, `README.md:305` |

### P2 — enforcement-hardening & polish

| ID | Dim | Finding |
|----|-----|---------|
| P2-1 | Code/Impl | Calibration ledger + plan-state have no `schema_version` / migration path (W9 #1, #11). Add `## Ledger schema` + `## Model artifacts` sections (also closes P1-3). |
| P2-2 | Method | eFTP/measured-FTP divergence documented but never wired as a reconciliation trigger (W9 #10). |
| P2-3 | Code | No automated check that generated `.zwo` TSS matches plan TSS (W9 #8). |
| P2-4 | Code | API outage/5xx guidance present only in `analyze.md`; absent from `plan.md`/`advise.md`/`generate.md`. |
| P2-5 | Impl | `--compact` flag undocumented in `cli_reference.md` (which claims completeness). |
| P2-6 | Method | Mujika (taper) + San Millán (Z2) catalogued but uncited at point-of-use (already queued 2026-Q3). |
| P2-7 | Code | `_get()` retry loop lacks a defensive terminal `raise` (fragile, not a live bug). |
| P2-8 | Code | `extract_id` gives a generic error on Strava URLs — add an actionable "use fit_ingest.py" hint. |
| P2-9 | Method | HR zone table silently collapses power Z5–Z7 into one band — add a one-line note. |
| P2-10 | Method | Polarized block states "~0% Z3 / drift if >5%" as a hard target; soften to "minimal Z3" to match Seiler. |
| P2-11 | Method | Taper TSB target band (+5 to +20) sits at the fresh/aggressive end; +5 to +15 is the conservative central estimate. |
| P2-12 | Impl | SKILL.md frontmatter uses single-line description; `ntnx-architect`/`ntnx-thanos` use `>-` block scalar (cosmetic). |

### Already RESOLVED (verified — do not re-open)

- W9 #3 wellness cold-start (`wellness.py:17` `MIN_BASELINE_SIZE=7` + 4-tier maturity ladder)
- W9 #6 menstrual overlay — **correct-by-design**: screening question is wired (`plan.md:18`, `advise.md:202-213`); phase-based plan restructuring is deliberately *absent* because the science (McNulty 2020) makes it inappropriate
- W9 #9 heat-adaptation abort criteria (`durability_strength.md:92-99`)
- W9 D3-N1 linter `show_avg` check (`zwo_lint.py:242-249` + tests)

---

## Dimension 1 — Skill implementation

### D1-a `governance/artifacts.md` dangling cross-refs (P1-3) — VERIFIED
**Current state.** `artifacts.md:27` cites the ledger schema as `references/prediction_calibration.md → Ledger schema`; `:28` cites `→ Model artifacts`. Verified headings in `prediction_calibration.md`: *The loop / The two models / IF -> RPE expectation / FTP-gain rate / Recalibration triggers / Calibration is propose-and-confirm*. **Neither "Ledger schema" nor "Model artifacts" exists.**
**Gap.** A reader following the canonical artifact index to learn the ledger schema lands on a doc that never defines one.
**Recommendation.** Add the two sections to `prediction_calibration.md` (see P2-1) — this repairs the refs *and* closes the schema-version gap in one edit. If deferring P2-1, at minimum repoint `artifacts.md` to existing anchors.

### D1-b Test-count drift in canonical docs (P1-4) — VERIFIED
**Current state.** `cli_reference.md:7` "(637 tests across 8 files…)" and `README.md:305` "637 tests across 8 files…". Live run = **646**. `CLAUDE.md:151` already correct (646). Commit `b448557` fixed CLAUDE.md but missed these two.
**Gap.** The two contributor-facing "canonical" docs are stale; this is the 2nd drift.
**Recommendation.**
```diff
- cli_reference.md:7  …(637 tests across 8 files, runs in ~0.1s …)
+ cli_reference.md:7  …(646 tests across 8 files, runs in ~0.1s …)
- README.md:305       637 tests across 8 files: pure function unit tests, …
+ README.md:305       646 tests across 8 files: pure function unit tests, …
```
Leave `audits/cycling-coach-a-plus-program-summary-2026-05-22.md` at 637 (historical snapshot, correctly verbatim). Consider a single-source token or CI check to stop the recurrence.

### D1-c Plan-state has no schema-version field (W9 #1 → P2-1) — VERIFIED OPEN
`plan_state_schema.md` documents every section + a `## Validation Rules` block but no version marker; the W7-added `## FTP Test History` section confirms the schema evolves in place. Add a `Schema Version` row to Athlete Profile with a read-old-tolerate/write-new rule. Doc-only (no script reads `active_plan.md`; only Claude does).

### D1-d `--compact` undocumented (P2-5) / SKILL.md frontmatter style (P2-12)
`cli.py:59` defines `--compact`; `cli_reference.md` (claims "every script") omits it — add a one-liner. Frontmatter divergence is cosmetic; convert to `>-` block scalar only if suite consistency is wanted.

### What's already strong (D1)
- **Validation-gate tables (C5)** are real and rule-bound across all 4 workflows.
- **rule_registry.md** orphan-prevention is a genuine, self-sustaining mechanism (absorbed 4 post-W4 rules).
- **readiness_template.md** is genuinely DRY — single-sourced, both workflows delegate, no re-inlining.
- **Signal-mode contract** single-sourced in `cli_reference.md:99-110`; workflows defer rather than restate.
- Workflow CLI invocations match the actual argparse surface (no phantom flags).

---

## Dimension 2 — Scientific training methodology

### D2-a FTP-raise has no upper sanity bound (P1-2) — VERIFIED
**Current state.** `weekly_adaptation.md:94`: "**ACTION** suggest mid-block FTP retest **or apply new FTP estimate (20min peak × 0.95)**" — fired off a >3% lower trigger, no upper cap. Contrast `adaptation_rules.md:151`: "Flag FTP retest window… **Do NOT silently raise FTP.**" `metrics.py:174-176` sanity-bounds FTP *detection* (80–150%) but not the *applied raise*.
**Gap.** A noisy 20-min peak (surge, meter spike, mislabeled all-out) can drive an implausible FTP jump; the two coaching paths are inconsistent.
**Recommendation.** Align `weekly_adaptation.md:94` to the conservative path — make it "suggest mid-block FTP retest" only; cap any *applied* single-step increase at ~+6–8% (consistent with `block_templates.md:80`: 2–4%/block intermediate, 4–6% novice). Larger → require a dedicated field test. Authority: Allen & Coggan threshold-testing methodology + the skill's own per-block gain rate.

### D2-b eFTP divergence not operationalized (W9 #10 → P2-2) — VERIFIED OPEN
`block_templates.md:398,408,410` describe eFTP as a free cross-check ("if eFTP runs persistently above set FTP…"), but `eFTP` appears nowhere in `weekly_adaptation.md` / `adaptation_rules.md` / workflows / scripts. The cross-check is inert guidance.
**Recommendation.** Add a Weekly-Review check: "eFTP > set FTP by >~5% for 2+ weeks → flag retest / propose eFTP as working threshold." Register in `rule_registry.md` with a surface point. P2, not P1 — missing convenience cross-check, not a hazard.

### D2-c Authority orphans — Mujika & San Millán (P2-6) — VERIFIED, self-disclosed
`bibliography.md:80,122` already flag both as "Currently cited at: NONE." `race_taper.md` taper structure and `training_zones.md` Z2 mitochondrial framing are scientifically correct but un-anchored at point of use. Already queued 2026-Q3. Add inline `→ bibliography.md#mujika-inigo` and `→ bibliography.md#san-millan-inigo` (with POPULAR-MEDIA caveat → Brooks for mechanism). **No misattributions found** anywhere.

### D2-d Minor methodology polish (P2-9/10/11)
- HR zone table (`training_zones.md:64-70`) collapses power Z5–Z7 into one "anaerobic+" band — defensible (HR saturates above threshold) but unstated; add a one-line note.
- Polarized "~0% Z3 / drift if >5%" (`block_templates.md:138,177`) is locally dogmatic; Seiler's model is a distribution, not a prohibition — soften to "minimal Z3." Contained: doc labels polarized-superiority only SUPPORTED, and `training_zones.md:51` leads with the load-matched null result.
- Taper TSB +5→+20 (`race_taper.md:5,23`) at the fresh end; +5→+15 is the conservative central estimate (Mujika & Padilla 2003). The `:60` over-taper guardrail already mitigates.

### What's scientifically sound (D2)
- **Coggan 7-zone model** doc↔code agree (`training_zones.md:9-17` ↔ `metrics.py:11-12`).
- **TSS/NP/IF/PMC math textbook-correct**: `metrics.py:69-81` TSS = dur·IF²/3600·100; `pmc_calculator.py:40-41,72-74` CTL=42d/ATL=7d/TSB=CTL−ATL. The `1/n` discrete EWA is a deliberate, documented match to intervals.icu (vs continuous `1−e^(−1/τ)`).
- **VO2max prescriptions** physiologically sound; the Rønnestad 30/15s claim is handled *exemplarily* — canonical 8.7% figure cited with PMID, **plus** the 2020 elite null-result and 2025 contradicting running study, correctly downgraded to CONTESTED.
- **Intensity-distribution selection non-dogmatic** — leads with the 2024-25 load-matched null result before recommending pyramidal-default / polarized-alternative with a ≥6h/wk gate.
- **Ramp-rate hygiene correct** (`block_templates.md:206-208`: +10% = aggressive ceiling, classic 5–8%/wk, ACWR>1.3 tie-in).
- **Menstrual/RED-S doc is excellent** — McNulty 2020 trivial-effect lead, phase-periodization labeled UNPROVEN, RED-S hard medical gate (Mountjoy 2023).
- **FOR→NFOR→OTS tiering correct**; RPE-at-constant-IF as the earliest overreaching signal.
- **ACWR presented with its own refutation** (Lolli 2019, Impellizzeri 2020).

---

## Dimension 3 — Code quality

### D3-a `batch_generate_zwo.py` silent 200W default + no ERG check (P1-1) — VERIFIED
**Current state.** `batch_generate_zwo.py:138` `p.add_argument("--ftp", type=int, default=200, …)`; `:150-151` bounds-check only fires for an explicit out-of-range value. Omitting `--ftp` ⇒ silent 200W, **no warning**. Every sibling (`generate_zwo.py:658`, `zwo_lint.py`, `fit_ingest.py`, `cli.py`) warns loudly via `resolve_ftp_arg`. `batch_generate()` also never calls `check_erg_design()`.
**Gap.** A coach generating a week of `.zwo` files with no `--ftp` gets TSS/IF computed against 200W (wrong for athlete @188W) with no signal — the exact "silently invent a default" failure the `--use-athlete-profile` design prevents. = W9 D3-N3.
**Recommendation.**
```diff
- p.add_argument("--ftp", type=int, default=200, help="FTP for stats calculation (default: 200)")
+ p.add_argument("--ftp", type=int, default=None,
+                help="FTP for stats calculation (50-500). Defaults to 200 with a warning.")
```
```diff
- if not (50 <= args.ftp <= 500):
-     p.error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")
+ from generate_zwo import resolve_ftp_arg
+ args.ftp = resolve_ftp_arg(args.ftp, p,
+     "WARNING: --ftp not supplied — using 200W for batch stats. TSS/IF will be "
+     "wrong unless 200W is the athlete's actual FTP.")
```
Plus collect `check_erg_design(workout)` per entry and print to stderr in `main()`. Add a test mirroring `test_cli.py:196-290`.

### D3-b No `.zwo` TSS vs plan TSS reconciliation (W9 #8 → P2-3) — VERIFIED OPEN
`calculate_workout_stats` computes `estimated_tss`; `batch_generate` sums `total_estimated_tss`; nothing compares against the *planned* TSS the workflow targeted. Add optional `--planned-tss`; warn when `abs(modeled-planned)/planned > 0.10`. Caveat: exclude/annotate ftptest (`estimated_tss=None`) and FreeRide/MaxEffort (placeholder-power) rather than treating as 0.

### D3-c Calibration ledger no schema version (W9 #11 → P2-1) — VERIFIED OPEN
`prediction_tracker.py` records (`:380-392`), `DEFAULT_MODEL` (`:49-53`), and the calibration JSON block carry no `schema_version`; `load_ledger`/`load_calibration` do no version branching. Add `"schema_version": 1` + on-load branch (warn/refuse/migrate). Pairs with the `## Ledger schema` / `## Model artifacts` doc sections (closes P1-3 too).

### D3-d Outage guidance only in analyze.md (P2-4) — VERIFIED
Code layer is robust (`api_client._get` retries 429/5xx with backoff). Workflow guidance exists only at `analyze.md:238`; `plan.md`/`advise.md`/`generate.md` have none. Add the same one-liner to the other three.

### D3-e Strava URLs (answers the brief's "Strava URL extraction") — VERIFIED informational
This skill is **intervals.icu-only**. `extract_id` (`metrics.py:211-223`) is robust — trailing slash, query string, http/https, bare ID, sub-paths all handled; Strava URLs are **correctly rejected** with `ValueError`. The brief's "Strava URL extraction" was a misnomer. Optional polish (P2-8): detect `strava.com` and raise an actionable "export the .fit and use fit_ingest.py" message.

### D3-f Defensive retry-raise (P2-7) — HYPOTHESIS (not reachable today)
`api_client._get` (`:25-54`) relies on every terminal branch returning/raising inside the loop; no post-loop net. Traced all branches — not reachable today (all attempt-2 paths raise). Add `raise RuntimeError(f"{endpoint}: retry loop exited without a response")` after the loop as future-proofing.

### What's already strong (D3)
- **Whoop/intervals.icu normalization is the best-engineered area** — every camelCase→snake_case map verified incl. `spO2→spo2` (`wellness.py:49`); truthiness-vs-`is not None` discipline correct (0 valid for readiness/respiration/spo2; impossible for RHR/HRV/sleep); `history = daily[:-1]` excludes today; n≥7 maturity guards.
- **Network error handling robust + tested** — distinct 401/404/5xx/timeout messages, exp backoff, non-JSON guard; 10 dedicated tests.
- **Concurrent fetch degrades gracefully** — per-future try/except → `data_warnings` + structured `fetch_errors`.
- **Atomic ledger write** — `mkstemp`+`os.replace`, cleanup-on-failure; malformed lines skipped with line numbers.
- **generate_zwo dataclasses self-validate** — power range, Warmup/Cooldown ramp direction, IntervalsT auto-duration + textevent refusal; round-trip XML byte-identical.
- **zwo_lint reuses generate_zwo internals** — lint thresholds can't drift from generator thresholds.
- **FTP/weight bounds enforced at every input boundary** except the one batch gap (P1-1); `--use-athlete-profile` prompts on TTY / hard-errors on non-TTY (verified live).

---

## Open questions / assumptions

1. **Eval not run.** Per `CLAUDE.md` → "Eval harness limitations", the skill-creator harness can't validate this installed skill's triggers (real-skill shadowing + first-tool-must-be-Skill/Read). All trigger/description comments are rubric-grounds HYPOTHESES, not measurements.
2. **W9 numbering.** The brief's #1–#11 were mapped to the repo's audit IDs (D1-N1…D4-N2) by description, not a canonical numbered list. Substance is unambiguous; exact numbering is best-effort.
3. **Primary-literature values.** "Correct value" assertions for zone boundaries, CTL/ATL constants, ramp %, taper TSB, carb g/h are stated from domain knowledge cross-checked against the skill's own bibliography — not re-derived from primary papers this pass. Several bibliography entries carry their own "needs verification" flags (queued 2026-Q3).
4. **W9 #6 (menstrual) reclassified RESOLVED/correct-by-design** on the assumption that "wired into plan generation" is satisfied by the screening question; deeper phase-periodized generation would be scientifically wrong (McNulty 2020).
5. **`.env` loader untested.** `load_env` quote-aware parsing (`api_client.py:106-129`) has no dedicated unit test; logic looks sound but is uncovered — possible coverage gap, not a defect.

---
---

## Resolution (P1 batch — 2026-05-30)

All four P1 findings actioned in the working copy. Tests **646 → 648** green (P1-1 added 2 net new tests; TDD RED→GREEN). Not yet committed/pushed at time of writing.

| ID | Resolution | Files |
|----|-----------|-------|
| P1-1 | `--ftp` defaults to `None` and routes through `resolve_ftp_arg` (loud stderr warning on 200W fallback, parity with siblings); `check_erg_design` now run per workout, surfaced in result `erg_warnings` + stderr. TDD: RED tests `test_default_ftp_is_none`, `test_erg_warnings_surfaced_for_micro_reps`, `test_no_erg_warnings_for_sub_threshold_reps`; existing `test_default_ftp` renamed. Verified end-to-end (omit → warns; `--ftp 188` → silent; `--ftp 999` → parser.error). | `scripts/batch_generate_zwo.py`, `tests/test_pure_functions.py`, `tests/test_cli.py` |
| P1-2 | Removed the unguarded "apply new FTP estimate (20min × 0.95)" auto-action at `weekly_adaptation.md` → Performance Indicators — now retest-only, aligned with `adaptation_rules.md` → Upside actions. Added an **Implausible-jump guardrail** (>~8% single-step jump = suspect → confirm with a dedicated test) to `block_templates.md` → Mid-Plan FTP Update; registered in `rule_registry.md` and wired into `analyze.md` Step 6 + `plan.md` Step 5b. | `references/weekly_adaptation.md`, `references/block_templates.md`, `references/rule_registry.md`, `workflows/analyze.md`, `workflows/plan.md` |
| P1-3 | Added `## Ledger schema` and `## Model artifacts` sections to `prediction_calibration.md` (field-level schema for the JSONL ledger + the calibration model), resolving the two dangling `artifacts.md:27-28` cross-refs (`→ Ledger schema`, `→ Model artifacts`). The `schema_version` *field* itself remains queued as P2-1. | `references/prediction_calibration.md` |
| P1-4 | Test count `637 → 648` in `cli_reference.md` and `README.md`; `646 → 648` in `CLAUDE.md`. Historical `a-plus-program-summary` left at 637 (pinned snapshot). | `references/cli_reference.md`, `README.md`, `CLAUDE.md` |

**Deferred at P1 time:** all P2 items — now actioned below.

---

## Resolution (P2 batch — 2026-05-30)

P2 backlog actioned in the working copy. Tests **648 → 661** green (P2-1 +5, P2-3 +7, P2-8 +1; TDD RED→GREEN; full suite `Ran 661 tests … OK`). P2-12 deliberately skipped (cosmetic; a 2026-05-26 decision dropped ntnx-* frontmatter-style alignment).

| ID | Resolution | Files |
|----|-----------|-------|
| P2-1 | `schema_version` (=1) on `DEFAULT_MODEL`, every new ledger record, and forward-tolerant loaders (`load_ledger`/`load_calibration` warn on a *newer* version, tolerate absent/older — read-old-tolerate / write-new). Serializers unchanged (round-trip tests preserved). | `scripts/prediction_tracker.py`, `tests/test_prediction_tracker.py` |
| P2-2 | eFTP > set-FTP by >~5% for 2+ wks → retest trigger added to `weekly_adaptation.md` → Performance Indicators, registered in `rule_registry.md`, surfaced in `plan.md` Weekly Review Step 4. | `references/weekly_adaptation.md`, `references/rule_registry.md`, `workflows/plan.md` |
| P2-3 | `check_planned_tss()` compares modeled vs per-workout optional `planned_tss`; warns when deviation > 10%; skips ftptest / FreeRide / MaxEffort; surfaced in result dict + stderr. (Per-workout JSON field chosen over a single `--planned-tss` flag — carries per-day targets.) | `scripts/batch_generate_zwo.py`, `tests/test_pure_functions.py` |
| P2-4 | API-outage one-liner added to `plan.md` / `advise.md` / `generate.md` (parity with `analyze.md` → Error Handling). | `workflows/plan.md`, `workflows/advise.md`, `workflows/generate.md` |
| P2-5 | `--compact` documented in `cli_reference.md`. | `references/cli_reference.md` |
| P2-6 | Mujika cited at point of use in `race_taper.md`; San Millán (POPULAR-MEDIA → Brooks) in `training_zones.md` Z2 + preamble; bibliography "Currently cited at" + Currency log rows updated. | `references/training_zones.md`, `governance/bibliography.md` |
| P2-7 | Defensive terminal `raise` after the `_get` retry loop (unreachable by construction — no test, matches the audit's "future-proofing" framing). | `scripts/intervals_icu/api_client.py` |
| P2-8 | `extract_id` raises an actionable "export .fit → `fit_ingest.py`" error on Strava URLs. | `scripts/intervals_icu/metrics.py` |
| P2-9 | HR-zone-collapse note (power Z5–Z7 all map to HR Z5; use power above threshold) added under the HR zone table. | `references/training_zones.md` |
| P2-10 | Polarized "~0% Z3" softened to "minimal Z3" (distribution target, not prohibition); the >5% drift guardrail retained. | `references/training_zones.md`, `references/block_templates.md` |
| P2-11 | Race-day TSB band tightened +5→+20 to +5→+15 (conservative central estimate, Mujika & Padilla 2003). | `references/race_taper.md` |
| P2-12 | **Skipped** — cosmetic SKILL.md frontmatter block-scalar style; a 2026-05-26 decision dropped ntnx-* style alignment, so changing it would reverse that for no functional gain. | — |

Test count refreshed **648 → 661** across `cli_reference.md`, `README.md`, `CLAUDE.md`. Not yet committed/pushed/synced at time of writing.

*Generated 2026-05-30 · 3 parallel auditors + primary-source verification · skill at `b448557`, P1 + P2 batches actioned · tests 661 green.*
