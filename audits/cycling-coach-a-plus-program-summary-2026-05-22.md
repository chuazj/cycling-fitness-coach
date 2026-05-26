---
title: Cycling-Fitness-Coach Skill — A+ Program Summary
date: 2026-05-22
type: program-summary
audit_scope: [program-summary]
skill: cycling-fitness-coach
skill_version_start: 26f3333
skill_version_end: e6ce4f7
rubric: internal-program-review
status: complete
findings_count: 21
grade_start: "B+ (~85)"
grade_end: "A (92)"
tags: [cycling, coaching, audit, program-summary, roadmap]
---

# Cycling-Fitness-Coach Skill — A+ Program Summary

**Note:** this summary was originally written to the Obsidian vault on 2026-05-22 and is ported here on 2026-05-26 as part of the audit-protocol consolidation (refactor proposal §2 / C2, follow-up sweep). It is a pre-cutoff legacy artifact (repo `audits/` is canonical from 2026-05-26 onward per `references/artifacts.md`) — the port preserves it as a version-controlled historical record. Some W9 backlog items have since shipped in post-2026-05-22 commits (notably D3-N1 `show_avg` enforcement landed in commit `deaeb5c`); the body below is preserved verbatim and not back-edited.

**The single consolidated record of the A+ improvement program** (2026-05-20 →
2026-05-22). This document replaces the 16 working docs that previously lived in
`audits/` — the baseline audit, the 8-workstream roadmap, the per-workstream design
specs and implementation plans, the interim reviews, and the W8 re-audit. Their
substance is captured below; the skill repository itself holds the actual code and
docs.

---

## Outcome

**The skill went from `B+ (~85)` to `A (92)` — a confirmed +7**, verified by an
independent clean-context re-audit. Eight workstreams across three phases closed
every finding from the original audit, operationalized the skill's reference-doc
rules, added self-validation and reuse-hardening, and shut a health-data leak
vector. A+ was the aspiration; the program landed a strong, independently-confirmed
A with a small, well-scoped path to A+ (see *Future Enhancement — W9*).

| Milestone | Skill HEAD | Grade | Tests |
|-----------|-----------|-------|-------|
| Baseline audit | `26f3333` | B+ (~85) | 315 |
| Baseline same-day remediation | `f2e129e` | — | 315 |
| Phase 1 complete (W1–W3) | `1d82c20` | — | 446 |
| Phase 2 complete (W4–W7) | `255395a` | — | 588 |
| Pre-W8 gate remediation | `e6ce4f7` | — | 637 |
| **W8 re-audit — final** | `e6ce4f7` | **A (92)** | 637 |

---

## 1. Baseline — Audit of 2026-05-20

A sports-science and design peer review of the skill at `26f3333`, across four
domains. Verdict: **B+ (~85)** — "a mature, conscientiously sourced coaching skill;
the review brief simply hadn't caught up with it. The real work is refinement,
enforcement, and reuse-hardening."

| Domain | Grade | Headline gap |
|--------|-------|--------------|
| 1 — Training methodology | B+ (85) | No realistic-gain guardrail; no block-rotation rule |
| 2 — Wellness & recovery | A− (90) | Strongest domain; depth refinements only |
| 3 — ZWO generation | B (80) | Generator didn't enforce the skill's own anti-patterns |
| 4 — Tooling & integration | B+ (85) | A health-data leak vector (`readiness.json` un-ignored) |

**21 findings** were raised (D1-1…D4-4). A recurring structural critique ran
through them — the **orphaning pattern**: a recommendation that lives in a reference
doc and is never surfaced where the coach needs it (flagged at D1-3 ERG-variety and
D2-6 heat-adaptation). All 21 were remediated the same day (19 fixed, 1 scope-reduced,
1 — the `intervals_icu_api.py` monolith, D4-3 — deferred as the named re-grade gate),
taking the skill to `f2e129e`.

---

## 2. The Program — 8 Workstreams, 3 Phases

**Phase 1 — earn the A re-grade** (close the deferred gate + residual nits).
**Phase 2 — A+ structural work** (operationalise, self-validate, reuse-harden).
**Phase 3 — confirm the grade** (independent re-audit).

| WS | Workstream | Delivered | HEAD |
|----|-----------|-----------|------|
| **W1** | Refactor the monolith | The 1899-line `intervals_icu_api.py` → a 6-module `intervals_icu/` package (`api_client`/`metrics`/`activity`/`wellness`/`readiness`/`cli`) behind a ~16-line re-export façade; 4 large functions decomposed into ~34 helpers; 3 bugs fixed; CLI + import surface preserved. Closed the D4-3 re-grade gate. | `1d82c20` |
| **W2** | VO2max 30/15 citation refresh | Reworded the "30/15 is superior" claim — reframed as effective + time-efficient, with 2025 counter-evidence (Fleckenstein); added a citation-currency marker process. | `b20ae2e` |
| **W3** | Menstrual-cycle protocol | New `references/menstrual_cycle_training.md` — phase-aware guidance (correctly stated as unproven), symptom-based autoregulation, a RED-S hard gate; wired into `advise.md` + `plan.md`. Closed D2-4. | `6ba7714` |
| **W4** | Kill the orphaning pattern | New `references/rule_registry.md` catalogues 31 orphan-prone rules; the 12 fully-orphaned + 8 cheap sharpens wired into all 4 workflows as checklists + inline notes; a maintenance convention added so no future rule can orphan. **The single biggest A+ lever.** | `6adaa70` |
| **W5** | Predict→measure→calibrate loop | New `scripts/prediction_tracker.py` logs forecasts (RPE-at-IF, FTP-gain) to a gitignored ledger and reconciles them against actuals; forecasting models made explicit artifacts in `references/prediction_calibration.md`. A coach that learns from its own forecasts. | `d464248` |
| **W6** | ZWO generator hardening | NP-based TSS estimation replaced the avg-power estimate; new `scripts/zwo_lint.py` linter (15 checks); the ERG long-rep design rule encoded so the generator warns, not just the docs. Domain 3 → A-grade tooling. | `c57320e` |
| **W7** | Reuse-hardening | Non-WHOOP readiness: a 4-tier signal-mode ladder gives non-WHOOP athletes a real verdict instead of "INSUFFICIENT-DATA". Manual `.fit` fallback: new `scripts/fit_ingest.py` for activities not synced to intervals.icu. Closed D2-3 + D4-4. | `255395a` |
| **W8** | Independent re-audit | This program's Phase 3 — see §4. | `e6ce4f7` |

Test suite grew 315 → 588 across W1–W7, all green at every merge.

---

## 3. Pre-W8 Gate Review — and a Security Finding

Before the W8 re-audit, a 4-agent comprehensive review swept all Phase 1+2 work
(functionality / code / docs / packaging). It confirmed **all 8 audit gaps
demonstrably closed** and surfaced **1 Critical + 7 Important + 10 Minor**.

> **The Critical (C-1) — a public-repo PII leak.** The branch
> `backup/pre-history-rewrite-2026-05-02` was still pushed to the **public** GitHub
> repo and carried real athlete training data (`plans/` files — FTP progression,
> weight, dated workout logs). It fully negated a 2026-05-02 history rewrite that
> had scrubbed `master`. **Credentials were never exposed** — `.env` had no history
> on that branch — so no API-key rotation was needed. Root cause: a file-by-file
> `.gitignore` for `plans/`.

ZJ approved full remediation. All 18 findings were closed: the public branch was
deleted from origin, `.gitignore` switched to a robust `plans/*` directory exclude,
plus code parity/robustness fixes and a doc-consistency sweep. Skill `255395a →
e6ce4f7`; test suite 588 → 637. *Note: GitHub may still serve the deleted branch's
commits via direct-SHA URL for ~90 days; a free GitHub Support "Remove sensitive
data" request is the only guaranteed immediate purge — ZJ's call, the data is
training logs, not secrets.*

---

## 4. W8 — Independent Re-audit (Final Grades)

**Method.** To keep the re-audit non-self-referential, it was run by **5 fresh-context
agents** with no knowledge of the workstreams: 4 domain auditors (each independently
re-verified every baseline finding by reading the skill on disk) + 1 synthesis agent
that called the overall grade by judgment, not by averaging. Scope: sports-science
and design — code quality was the separate pre-W8 gate.

| Domain | Baseline | Re-audit | Δ |
|--------|----------|----------|---|
| 1 — Training methodology | B+ (85) | **A (93)** | +8 |
| 2 — Wellness & recovery | A− (90) | **A (93)** | +3 |
| 3 — ZWO generation | B (80) | **A− (89)** | +9 |
| 4 — Tooling & integration | B+ (85) | **A− (90)** | +5 |
| **Overall** | **B+ (~85)** | **A (92)** | **+7** |

**Confirmed:**
- All 21 baseline findings closed or meaningfully advanced; all 8 workstreams landed.
- **The orphaning pattern is *structurally* resolved** — `rule_registry.md` plus its
  maintenance convention is a real mechanism, not a one-off patch; it has already
  absorbed 4 post-W4 rules on its own.
- The repo is independently re-verified clean — no health data, no secrets,
  `.gitignore` robust-by-default.
- **11 new findings: 1 Medium, 1 Low–Medium, 9 Low. No Critical, no High, no
  regressions.**

**Why A and not A+.** Of the baseline's three-part prescription, *refinement* and
*reuse-hardening* are fully delivered; **enforcement** is the leg still open. The
pattern across all 11 new findings: rules are now correctly **surfaced** (as prose
or checklists) but not yet uniformly **enforced in code**.

### New findings (the W9 backlog)

| ID | Domain | Severity | One-line |
|----|--------|----------|----------|
| D2-N1 | Wellness | Medium | No automated multi-week performance-decrement detector (NFOR/OTS rides on coach memory) |
| D1-N2 | Method | Low–Medium | A decision-tree branch still derives an FTP from an unpaced training 20-min peak |
| D1-N1 | Method | Low | Block tables print "+10%"; the 5–8% ramp ceiling lives only in prose |
| D1-N3 | Method | Low | Block-rotation rule is asymmetric (fires only for FTP Builder blocks) |
| D2-N2 | Wellness | Low | Menstrual logging documented but not surfaced in script output |
| D2-N3 | Wellness | Low | HRV CV-trend is informational-only, no independent escalation path |
| D3-N1 | ZWO | Low | Linter checks an FTP test has a `<FreeRide>` but not `show_avg` |
| D3-N2 | ZWO | Low | Batch generation path is silent on ERG-design warnings |
| D3-N3 | ZWO | Low | `batch_generate_zwo.py` defaults `--ftp 200` silently |
| D4-N1 | Tooling | Low | `.env` location described three ways across docs |
| D4-N2 | Tooling | Low | `wellness.py` (662 LOC) is the largest remaining module |

---

## 5. Future Enhancement — W9 Enforcement-Hardening *(reference, not scheduled)*

**Not part of the closed program — recorded here as the scoped path from A (92) to
A+.** W9 would convert "documented and surfaced" into "documented, surfaced, and
enforced." Estimated ~1 focused session; the D2-N1 detector is the bulk of it.

1. **D2-N1 (Medium — highest value).** Build a multi-week performance-decrement
   detector so FOR/NFOR/OTS escalation is script-backed, not coach-memory — e.g.
   flag "20-min peak down ≥3% across 3 consecutive weeks at matched volume."
2. **D3-N1.** Have `zwo_lint.py` check `show_avg` on FTP-test workouts, not just
   FreeRide presence — finish the FTP-test enforcement the workflow already mandates.
3. **D3-N3** (and optionally **D3-N2**). Route `batch_generate_zwo.py` through the
   existing `resolve_ftp_arg` helper — default `--ftp` to None and warn, instead of
   silently defaulting 200; optionally run `check_erg_design` on batch output.
4. **D1-N1, D2-N2.** Pull caveats out of prose into the artifacts they govern —
   print the realistic-gain ceiling in the block tables; surface menstrual logging
   in script output.
5. **D1-N2.** Tighten the loose decision-tree branch — an unpaced training 20-min
   peak should "flag retest", never derive a threshold via ×0.95.
6. **D4-N1.** State the `.env` location once, canonically.
7. **Preventive.** Watch `periodization.md` size (804 lines — the next bloat point);
   consider splitting block templates from adaptation logic before it grows further.

Items 1–3 are the substantive A+ work; 4–6 are polish; 7 is preventive.

---

## Appendix — Skill State at Program Close

- **Repository:** `github.com/chuazj/cycling-fitness-coach` (public), HEAD `e6ce4f7`.
- **Working copy:** `~/OneDrive/code/claude_skill/Cycling/cycling-fitness-coach/`
  (edit here); install path `~/.claude/skills/cycling-fitness-coach/` (ff-synced).
- **Test suite:** 637 tests, all green.
- **Structure:** 13 reference docs, 4 workflows, 9 scripts + the 6-module
  `intervals_icu/` package, `SKILL.md` / `README.md` / `CLAUDE.md`.

---
*Program summary generated 2026-05-22 · consolidates the former `audits/` working
set · skill at `e6ce4f7`, graded A (92).*
