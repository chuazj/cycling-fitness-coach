---
title: Open-backlog verification — W9 enforcement items + 2026-05-30 deferred set
date: 2026-06-01
type: audit
audit_scope: [methodology-drift, output-contract, citation-currency]
skill: cycling-fitness-coach
skill_version_start: c2ce55e
skill_version_end: eae1ed9
rubric: internal-backlog-verification (16-agent verify fan-out + adversarial required/optional classification, all claims primary-source-verified to file:line)
status: actioned
findings_count: 10
findings_high: 0
findings_medium: 1
findings_low: 9
tags: [cycling, coaching, audit, backlog-verification, w9]
---

# Open-backlog verification — 2026-06-01

**Question that triggered it.** "Are there outstanding gaps / improvements that are not fixed *and* required?" — i.e. after the 2026-05-22 A+ program, the 2026-05-26 refactor, and the 2026-05-30 comprehensive review, what is *genuinely still open*, and is any of it **required** (correctness / safety / data-integrity / broken-guarantee) vs merely enhancement / polish / preventive.

**Method.** A 16-agent verification workflow (not open-ended discovery — three audits in ten days make fresh true-positives low-probability and confabulation-risk high). Five cluster-verifiers triaged the 11-item W9 enforcement backlog + the 5/30 deferred set against **current committed files** (file:line + quote, not inferred from which prior audit mentioned an item); one resolution-drift verifier confirmed the 5/30 review's 18 claimed fixes actually landed; one hard-gated discovery agent looked only for guarantee-breaking defects (returned none beyond the cluster set). Every OPEN/PARTIAL candidate was then adversarially re-classified by an independent agent instructed to *refute* both "still open" and "required". Test suite run live: **661 → 663 pass, 0 fail** after the one actioned fix.

**Headline.** **No P0/P1. The required column is empty.** All 10 carried-forward open items adversarially classified `required: false`. One sat on the required/optional boundary — **F1 (D2-N3)**, a readiness doc-vs-code contradiction that changed an emitted verdict — and was fixed and shipped this pass (`9017dca`). A follow-up consistency+polish batch (`eae1ed9`) then closed **F2, F3, F6, F7, F9** (6 of 10 actioned in total). The 4 that remain — **F4, F5, F8, F10** — are enhancement / preventive: F10 is queued for the 2026-Q3 citation-currency audit; F4/F5/F8 are deferrable, with the strength/mobility pillar the preference-aligned next investment.

---

## §1 Audit table

| ID | (orig) | Area | Current state | Gap | Sev | Proposed action |
|----|--------|------|---------------|-----|-----|-----------------|
| **F1** | D2-N3 | Readiness gating | `readiness.py` `_synthesize_verdict` let an isolated rising HRV CV-trend yellow flag cap an otherwise-green athlete at YELLOW-LOW / Sweet Spot. CLAUDE.md gating spec + `training_zones.md:116` + `wellness.py:260` + `advise.md:102` all call CV-trend **informational** ("review weekly TSS"). | Doc-vs-code (and doc-vs-doc: `advise.md:56` endorsed gating) contradiction; emitted verdict contradicted the authoritative spec. Conservative direction (trains easier) → not a safety hazard. | **M** | Exclude `HRV_CV` from the gating set (still surfaces in Active-flags); align the lone outlier doc row. **ACTIONED — see §4.** |
| F2 | D1-N2 | Weekly-summary script | `activity.py:458` computes `suggested_ftp = round(max_20min_peak * 0.95)` from the week's best 20-min peak (an unpaced training peak) and emits `ftp_update_suggested` when >3% over current FTP. | `weekly_adaptation.md:94` (fixed 5/30) says never derive FTP from an unpaced peak; the script still computes that exact number. Gated (>3%) + labeled + surfaced retest-framed (`analyze.md:278-282` "Consider scheduling an FTP test to confirm") — never auto-applied. Registry self-flags `partial`. | L | Rename key (`retest_flag_peak` / add `requires_confirming_test: true`) or attach an inline caveat string; +1 test. Closes the script↔doc seam without removing the early-warning. |
| F3 | D1-N1 | Block tables | `block_templates.md` block tables print bare `+10%` TSS steps; the 5-8% ramp ceiling (`:208`) and 2-4% realistic per-block FTP-gain (`:80`) live in adjacent prose. | Ceiling doesn't travel with the table a planner reads first. `:208` already frames +10% as "a ceiling, not a default"; `rule_registry.md:28` wires the realistic-gain guardrail. | L | One-line footnote under each block table referencing Weekly Ramp Rate. |
| F4 | D1-N3 | Block rotation | `block_templates.md:471` stimulus-rotation fires only for 2+ consecutive sweet-spot-dominant / FTP-Builder blocks. | No symmetric branch (2+ consecutive VO2max / Polarized → return toward FTP). Plausibly by design — `:445` prescribes repeated VO2max for crit season; athlete's actual monotony risk is sweet-spot-side. | L | If pursued: generalize to any 2-3 same-shaped blocks **with goal-aware guards** (exempt intended crit cycles). |
| F5 | D2-N1 | Performance monitoring | Multi-week peak-power decrement (NFOR/OTS early-warning) is prose-only (`weekly_adaptation.md:100-102`). `pmc_calculator.py:267` does single week-over-week delta only; `sparkline.py` visualizes the multi-week series. | No script flags a sustained 3+-week decline. A+ program's "highest-value" W9 item — but **re-surfaces already-collected data**, which ZJ's standing preference ranks low-value. | L | Optional pure-function flagging a 3+-week non-positive slope on the existing sparkline series. Low priority per re-surfacing preference. |
| F6 | D2-N2 | Menstrual logging | Menstrual handling is prose-only (`menstrual_cycle_training.md`, `advise.md:204`, `plan.md:18`); no script emits a cycle/bleeding field. Soft conflation at `menstrual_cycle_training.md:97`. | Absence, not wrong output. No hard guarantee of a menstrual field in script JSON. Phase-periodization correctly stays absent (McNulty 2020). Re-surfacing class. | L | Tighten the `:97` wording; optional `_build_daily` field is low priority per re-surfacing preference. |
| F7 | D4-N1 | `.env` docs | `setup.md:19` + `intervals_icu_api.md:11` say "project root"; `README.md:51` says "skill directory". | A+ ask ("state .env location once, canonically") not done. Both phrasings = same physical dir; `load_env` probes 3 candidates → nobody misdirected. | L | Pick one canonical phrase (e.g. "the skill root — the dir containing SKILL.md"); point others at `setup.md`. |
| F8 | D4-N2 | Module size | `wellness.py` grew 662 → **685 LOC**, largest in the `intervals_icu/` package (note: `generate_zwo.py` 698 is larger across `scripts/`). | Preventive only — works, fully tested. No defect. | L | Extract per-gate flag logic to a helpers submodule if it keeps growing; rescope any "largest module" wording to the package. |
| F9 | CL-2 | Test-count sync | `661/663` hardcoded as a literal in 3 canonical docs (`CLAUDE.md:151`, `README.md:305`, `cli_reference.md:7`); no `.github/`, Makefile, pytest.ini, or count-assert test. | Drifted 637→646→648→661 historically; mechanism to stop the *next* drift was never built. Currently in-sync. | L | Optional: a test asserting `unittest discover` collects an exact expected count, or a grep-vs-live-output check. |
| F10 | CL-4 | Bibliography | `bibliography.md` carries 8 **needs-verification** provenance flags (Allen & Coggan ed., Mujika 2010, Rønnestad 2020, Seiler & Tønnessen 2009, Beattie 2014, Clark & Macdermid 2025, Quittmann 2025). | Provenance (edition/volume/page) unconfirmed; self-disclosed at `bibliography.md:8`. No wrong cited *number* reaches a prescription; load-bearing values trace to non-flagged sources. | L | **Already queued for 2026-Q3** citation-currency audit (see `audit_protocol.md` → Currently-queued actions). |

---

## §2 Action plan

Only F1 (the single Medium) was actioned this pass; F2-F10 are Low and out of scope (§3).

### F1 / D2-N3 — make HRV CV-trend truly informational (athlete-chosen contract)

Presented two reconciliation options; athlete chose **"make it truly informational"** (align code to the authoritative CLAUDE.md spec) over "make it officially gate" (flip the docs). Rationale: the documented action is a **weekly-TSS review**, not a same-day cap; the acute gates (recovery / sleep / HRV-vs-band / RHR / respiration / SpO2) already protect today's session; CV-trend is a slow 14-day-history trend that belongs in the weekly review, where `overall_status` already carries it.

RED → GREEN:
1. **RED** — added `test_synthesize_verdict_hrv_cv_flag_excluded_from_gating` (isolated CV-trend → expect GREEN); failed on old code (`YELLOW-LOW != GREEN`). Added a guard test (`..._does_not_suppress_real_gating`) confirming a real RHR yellow alongside CV-trend still gates.
2. **GREEN** — `readiness.py` `_synthesize_verdict`: `gating_flags = [f for f in flags if f.get("signal") not in ("recovery", "HRV_CV")]` (+ docstring rationale). The flag still lands in `flags` → still renders in Active-flags; it still rolls into the *weekly* `overall_status` (`plan.md:205`), the correct home for "review weekly TSS".
3. **Doc** — removed the CV-trend clause from the `advise.md:56` Moderate fatigue row (the lone outlier) and added an informational note matching the already-correct gating table at `:102`.
4. Acceptance: full suite **663 green** at both working copy and install path; no other doc implies same-day CV-trend gating (skill-wide grep confirmed).

Scope check confirmed `overall_status` is consumed only by the **weekly review** (`plan.md:205`, "weekly trend, not single-day call") and carried as an informational passthrough in the readiness output (`readiness.py:429`) — neither gates a session, so `--wellness` was correctly left untouched.

---

## §3 Out of scope (deliberately not actioned — do not re-discover)

**F4, F5, F8, F10 (the 4 not actioned this pass; all Low / not required).** Each adversarially confirmed `required: false` — no correctness, safety, data-integrity, or broken-guarantee defect. Deferred reasoning per row in §1. (F2, F3, F6, F7, F9 were actioned in the consistency+polish batch — see §4.) Cross-cutting notes for the next audit:

- **Re-surfacing class deprioritized by standing preference.** F5 (D2-N1) — and the optional *code* form of F6 (D2-N2 menstrual fields in `_build_daily`, distinct from the wording fix that shipped) — both re-surface data already collected (peak series / intervals.icu logging). Per the athlete's standing preference — new training-stimulus enhancements (strength, mobility) outrank data-re-surfacing tools — these are explicitly low-value. The **strength/mobility pillar** (a weekly lifting slot, deferred pending Block 3 restart) is the preference-aligned enhancement, not these.
- **F10 is already queued**, not a new finding — fold into the 2026-Q3 citation-currency pass; this audit only confirmed the 8 flags persist and remain non-load-bearing.
- **F4 is plausibly by-design** (the sweet-spot-only rotation trigger covers the athlete's actual monotony risk; a symmetric branch could misfire on intended crit-season VO2max cycles) and **F8 is preventive** (a 685-LOC module that works, fully tested) — neither is scheduled.

**Verified CLOSED (15) — do not re-open.** Confirmed landed in committed files this pass, so the next audit can skip re-deriving them:

- 2026-05-30 review, all P1 (P1-1 batch `--ftp` None + `resolve_ftp_arg` + per-workout `check_erg_design`; P1-2 FTP-raise retest-only + >~8% implausible-jump guardrail wired in `analyze.md`/`plan.md`/`rule_registry.md`; P1-3 `prediction_calibration.md` Ledger-schema + Model-artifacts sections resolving the `artifacts.md` dangling refs; P1-4 test count) and all P2 (P2-1 `schema_version` + forward-tolerant loaders; P2-3 `check_planned_tss`; P2-6 Mujika/San Millán cited at point of use; P2-2/4/5/7/8/9/10/11). P2-12 deliberately skipped (cosmetic).
- W9 enforcement items that **did** ship: D3-N1 linter `show_avg` check (+3 tests), D3-N2 batch ERG-warnings surfaced, D3-N3 batch `--ftp` no longer silent-200.
- Cross-reference integrity: 44 referenced files exist; all 17 `.md#anchor` refs resolve; 171 prose pointers all land in the correct file (no dangling/misdirecting ref) — including the project-CLAUDE.md pointers to `block_templates.md` / `durability_strength.md` / `prediction_calibration.md`.
- Wellness/readiness gate constants all match the documented spec (MIN_BASELINE 7, HRV μ±0.5σ, RHR +5/+10, respiration +1/+2, SpO2 −2pp / <90% floor, recovery 34/50/67, 3-day slope −10).
- `.env` loader has a dedicated unit test (`TestLoadEnv`); eval-harness trigger-validation limit is an accepted external-tool constraint (CLAUDE.md:34-41).

---

## §4 Resolution

| ID | Resolution | Commit | Files |
|----|-----------|--------|-------|
| F1 / D2-N3 | `HRV_CV` excluded from `_synthesize_verdict` gating set (informational-only, per athlete-chosen contract); docstring rationale added; `advise.md:56` Moderate row de-listed CV-trend + informational note added; +2 regression tests (661 → 663 green); test count bumped in 3 canonical docs. Verified live at install path. | `9017dca` | `scripts/intervals_icu/readiness.py`, `workflows/advise.md`, `tests/test_internal_helpers.py`, `CLAUDE.md`, `README.md`, `references/cli_reference.md` |

### Resolution (consistency+polish batch — 2026-06-01, `eae1ed9`)

| ID | Resolution | Files |
|----|-----------|-------|
| F2 / D1-N2 | `_ftp_update_suggestion` now flags the 20-min-peak FTP suggestion **retest-only** — adds `requires_confirming_test: True` + a caveat `note` ("unpaced training peak — schedule a dedicated FTP test before changing FTP"), docstring marks `suggested_ftp` a RETEST FLAG, and `analyze.md` Step 3 renders the ⚠ "do not apply directly". Aligns the script with `weekly_adaptation.md`. +2 tests. | `scripts/intervals_icu/activity.py`, `workflows/analyze.md`, `tests/test_internal_helpers.py` |
| F3 / D1-N1 | Ramp-ceiling footnote added under all 4 block tables (FTP Builder / VO2max / Endurance / Polarized): "+10% is a ceiling, not a default — ramp 5–8%/week if CTL <30 / inconsistent history / any yellow flag → **Weekly Ramp Rate**"; FTP Builder note also carries the 2–4%/block realistic-gain caveat. | `references/block_templates.md` |
| F6 / D2-N2 | Tightened the §8 wording: the `--wellness`/`--readiness-check` modes pull only generic subjective fields and do **not** emit a menstrual/bleeding field; read the log in the intervals.icu UI. (Optional code-surfacing form remains deferred — re-surfacing class.) | `references/menstrual_cycle_training.md` |
| F7 / D4-N1 | Canonicalized the `.env` location to one phrase — "the skill root (the directory containing `SKILL.md`)" — across `setup.md`, `intervals_icu_api.md`, `README.md` (was "project root" ×2 vs "skill directory"). | `references/setup.md`, `references/intervals_icu_api.md`, `README.md` |
| F9 / CL-2 | Added a doc-count guard test: derives the live test/file counts from a fresh `discover().countTestCases()` + `glob("test_*.py")` and asserts each of the 3 canonical docs' "N tests across M files" marker matches — no 4th hardcoded number; adding a test without updating the docs now fails the suite. Count rolled 663 → 666. | `tests/test_internal_helpers.py`, `CLAUDE.md`, `README.md`, `references/cli_reference.md` |

`status: actioned`. **6 of 10 actioned** (F1 + F2/F3/F6/F7/F9). F4 / F5 / F8 remain open as deferrable Low/optional backlog (no scheduled action); F10 → 2026-Q3 citation-currency audit. `git diff c2ce55e..eae1ed9` shows exactly what shipped from this audit. Tests 666 green.

*Generated 2026-06-01 · 16-agent verification fan-out + adversarial required/optional classification · skill `c2ce55e` → `eae1ed9`, F1 + consistency batch actioned · tests 666 green.*
