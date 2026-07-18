# Quarterly Audit Protocol

This file defines the recurring audit ritual that keeps the skill's methodology current and its eval coverage honest. Audits run quarterly. Each audit produces a dated artifact in `audits/`, version-controlled with the skill.

> **Why this exists.** Audit work has happened (W4 orphan-prevention, 2026-05-23 writing-skills audit, multiple token-reduction phases). Until now those artifacts lived in Obsidian — divorced from version control, hard to diff against. Co-locating audits with the skill makes each one a first-class artifact that the next quarterly audit can compare against.

## Table of contents

- [Cadence](#cadence) — quarterly schedule, first audit due, surfacing mechanism
- [Scope per audit](#scope-per-audit) — four scopes that get reviewed each cycle
- [Triggering mechanism](#triggering-mechanism) — how the audit-due signal actually surfaces
- [Audit artifact format](#audit-artifact-format) — frontmatter schema + body conventions
- [Currently-queued actions](#currently-queued-actions) — gaps known to be open, with target quarter
- [Retention & PII](#retention--pii) — what stays, what's gitignored

---

## Cadence

| Quarter | Window | First scheduled |
|---------|--------|-----------------|
| Q1 | January (any week) | 2027-Q1 |
| Q2 | April (any week) | 2027-Q2 |
| Q3 | July (any week) | **2026-Q3** ← first repo-tracked audit |
| Q4 | October (any week) | 2026-Q4 |

**Why quarterly:** evidence half-life in the cited domains (block periodization, interval formats, fuelling, recovery markers) is on the order of 6–18 months. Quarterly cadence is the slowest review interval that still catches a meaningful new RCT or meta-analysis before it propagates into a coaching recommendation downstream.

**Audit window:** any week within the named month. Not date-pinned — the Weekly Review surfacing mechanism (below) catches the due date and surfaces the audit as a coaching item until it's actioned.

---

## Scope per audit

Each quarterly audit covers four scopes. Each scope produces a section in the audit artifact.

### Scope 1 — Citation currency

For each authority in `governance/bibliography.md`:

- Re-read primary source citation. Confirm volume/page/year if previously flagged **needs verification**.
- Check for newer edition (books) or follow-on paper (RCTs).
- If a follow-on paper contradicts or qualifies the cited claim, surface as a **methodology-drift finding** (Scope 3).
- Update `Last verified` date in the bibliography's Currency log.

Per-domain methodology docs also carry a "Citation currency" preamble (`block_templates.md`, `weekly_adaptation.md`, `race_taper.md`, `durability_strength.md`, `fueling.md`, `menstrual_cycle_training.md`, `training_zones.md`). Refresh each doc's preamble date.

### Scope 2 — Eval suite refresh

Read `evals/trigger_eval.json`. For each query:

- Is the query still representative of how the athlete actually phrases the intent? Rewrite if not.
- Has any new workflow (added since the last audit) introduced a positive case not yet covered? Add it.
- Has any new false-positive risk emerged (new domain-adjacent skill installed; new conversational pattern)? Add a negative probe.

Run the eval if the harness is operational — note CLAUDE.md "Eval harness limitations" — and record the result in the audit artifact. If the harness is non-viable, document why and proceed on rubric grounds (see prior writing-skills audit for the precedent).

### Scope 3 — Methodology drift

For each methodology reference doc:

- Has new peer-reviewed evidence emerged that supports, qualifies, or refutes a cited claim?
- Has a claim that was practitioner consensus moved to peer-reviewed support (or vice versa)? Update the **Evidence tier** in `bibliography.md` (`governance/bibliography.md` → Evidence-level conventions).
- Has any in-doc claim quietly drifted from its citation? (E.g., the doc says "X% gain expected" but the cited paper says Y% — flag for correction.)

### Scope 4 — Output contract audit

Read `governance/artifacts.md` (the canonical artifact index). For each emitted file:

- Does the schema still match what the consuming workflow expects?
- Has a script started emitting a field the schema doesn't document, or stopped emitting a field the schema requires?
- Is the gitignore still correct? (PII regressions — a script started writing to a path that isn't ignored.) Cross-check against `artifacts.md` → Gitignore policy summary.

---

## Triggering mechanism

A quarterly cadence doesn't happen by virtue of being documented. The audit-due signal surfaces through **Weekly Review**.

**Where it fires:** `workflows/plan.md` → Weekly Review step where wellness/readiness is rendered. At the same step, check the Currency log in `governance/bibliography.md`:

```
For each row in bibliography.md → Currency log:
  if current_date >= next_due_quarter:
    surface as a "Skill maintenance" item in the Weekly Review output
    coach the athlete on the impact (none — skill-internal task)
    propose a session-end action: open audit_protocol.md and run a quarterly audit
```

The surfacing is **once per week** until the audit lands and the Currency log dates roll forward. This converts "remember to audit" into a passive prompt that the next Weekly Review will produce on its own.

**Why not setup.md or a startup hook?** `setup.md` is only read at the start of sessions that need to invoke a script or write notes — not every session. Weekly Review is the closest thing to a guaranteed regular cadence. Surfacing at Weekly Review also pairs naturally with the user's existing review ritual.

**Wire-up status:** **Wired** as of 2026-05-26 in `workflows/plan.md` → Weekly Review Step 4b (Skill maintenance check). The Step 5 output template includes a conditional `### Skill maintenance` sub-section that appears only when a Currency-log row's `Next due` has passed. Verified: the first surfacing will fire in any Weekly Review run after 2026-07-01 (first 2026-Q3 due date), and continue weekly until an audit lands and the Currency log dates roll forward.

---

## Audit artifact format

Each audit lands as a markdown file at `audits/cycling-coach-<topic>-YYYY-MM-DD.md`. Topic slug is kebab-case and describes the audit scope (`writing-skills`, `methodology-currency`, `eval-suite-refresh`, `output-contract`, `refactor-proposal`). A single audit can cover multiple scopes; topic slug reflects the dominant one.

### Frontmatter schema

```yaml
---
title: <Human readable title>
date: YYYY-MM-DD
type: audit
audit_scope: [citation-currency, eval-refresh, methodology-drift, output-contract]  # one or more
skill: cycling-fitness-coach
skill_version_start: <commit hash at audit start>
skill_version_end: <commit hash at audit end, after any actioned findings ship>
rubric: <rubric used, e.g., superpowers:writing-skills, internal-methodology-audit>
status: open | actioned | closed-without-action
findings_count: <int>
findings_high: <int>
findings_medium: <int>
findings_low: <int>
tags: [cycling, coaching, audit]
---
```

### Body conventions

- **§1 Audit table** — one row per finding: ID (F1, F2, …), area, current state, gap, severity (H/M/L), proposed action.
- **§2 Action plan** — for each H/M finding, concrete next step (RED→GREEN sequence if eval-testable, file edits + acceptance criterion otherwise).
- **§3 Out of scope** — list findings deliberately not actioned this audit, with reasoning. Prevents next-quarter audit from re-discovering them.
- **§4 Resolution** — appended after findings are actioned. Per-finding row: commit hash + one-line note. Updates `status:` frontmatter to `actioned`.

Use Obsidian-compatible markdown (frontmatter at top, no exotic plugin syntax). Audits should render cleanly in both the repo (GitHub) and the Obsidian vault.

---

## Currently-queued actions

These are gaps identified in the 2026-05-26 refactor proposal and committed to address in the next audit cycle. They are **queued**, not deferred-forever — the next audit (2026-Q3) re-surfaces them as concrete deliverables, not as new findings.

| Gap | Target quarter | Deliverable |
|-----|---------------:|-------------|
| Mujika not cited in `references/race_taper.md` | 2026-Q3 | Add inline cite at the taper-structure paragraph anchoring to `bibliography.md#mujika-inigo`. Verify Mujika & Padilla (2003) volume/pages. |
| San Millán not cited in `references/training_zones.md` (Z2 / mitochondrial framing) | 2026-Q3 | Add inline cite at the Z2 paragraph with **POPULAR-MEDIA** evidence tier flag; anchor underlying mechanism to Brooks (1986, lactate shuttle). |
| Allen-Coggan not anchored in `references/training_zones.md` or `references/plan_state_schema.md` | 2026-Q3 | Add footer cite to each; verify against 3rd edition (2019), update bibliography if the 2nd→3rd transition changed the cited framework. |
| ~~Methodology citation-currency preambles on 6 docs (C4)~~ | ~~2026-Q3~~ | **Shipped 2026-05-26**: preambles on all 6 methodology reference docs. |
| ~~Sub-prompt contract headers on 4 docs (C3)~~ | ~~2026-Q3~~ | **Shipped 2026-05-26**: contract headers present on 4 reference docs (verified 2026-07-18). |
| ~~Workflow checkpoint consistency (C5)~~ | ~~2026-Q4~~ | **Shipped 2026-05-26**: validation-gate tables added to `analyze.md`, `advise.md`, `generate.md`. |
| ~~Section anchors for large refs (C6)~~ | ~~2026-Q4~~ | **Shipped 2026-05-26**: "Stable section anchors" inventory added to `block_templates.md` and `workout_analysis.md`; §N-style cross-refs in `plan.md` rewritten to named-item pointers. |
| ~~Output artifact index `governance/artifacts.md` (C7)~~ | ~~2026-Q4~~ | **Shipped 2026-05-26**. Now required reading for Scope 4 (output contract audit). |
| ~~Weekly Review audit-due surfacing wire-up~~ | ~~2026-Q3~~ | **Shipped 2026-05-26**: `workflows/plan.md` → Weekly Review Step 4b + Step 5 `### Skill maintenance` sub-section. |

---

## Retention & PII

**Retention:** all audits retained indefinitely in `audits/`. Historical audits are useful diff targets — the value compounds with each quarter.

**PII policy:**
- Audits **about the skill itself** (this file's primary case — methodology, eval, output contract) contain no PII. Commit normally.
- Audits **incorporating athlete data** (e.g., a calibration audit that reasons about specific FTP test history) — gitignore the athlete-data section per-audit, OR redact before committing. Use a `## Athlete data (gitignored)` collapsible section if needed.
- See `CLAUDE.md` → "The entire `plans/` directory is gitignored" for the standing PII rule; audits inherit the same logic for athlete-specific subsections.

**Versioning:** audit's `skill_version_start` and `skill_version_end` frontmatter fields pin the audit to specific commit hashes. A future re-audit can `git diff <start>..<end>` to see exactly what shipped from the audit.
