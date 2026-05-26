---
title: Refactor proposal — methodology, recurrence, sub-prompts
date: 2026-05-26
type: audit
audit_scope: [refactor-proposal, citation-currency, output-contract]
skill: cycling-fitness-coach
skill_version_start: 01b8e45
skill_version_end: 3b30820
rubric: internal-methodology-audit
status: actioned
findings_count: 8
findings_high: 2
findings_medium: 3
findings_low: 3
tags: [cycling, coaching, audit, refactor, methodology, citations]
---

# Refactor Proposal — 2026-05-26

Audit driven by user request: review the skill against a goal of producing a refactor proposal (not a rewrite) across eight aspects. Output produced in chat first, then ported to repo audits/ as the canonical record. P0 + P1 implementation began the same day; this artifact's `status:` flips to `actioned` once the P0+P1 commits land.

## §1 Audit table

| # | Aspect | Current state | Gap | Severity |
|---|--------|---------------|-----|----------|
| 1 | Frontmatter & trigger description | `name` + `description` only. Description rewritten 2026-05-23 (commit `8a90a81`) — opens with "Use when…" (writing-skills CSO compliant). Non-spec `compatibility:` dropped (`8e539d5`). | One ~600-char sentence enumerating ~14 trigger phrases. Long single-sentence is hard to scan and edit; risks regression each edit. No documented convention doc. | L |
| 2 | Workflow structure & checkpoints | 4 workflows (analyze 271 / plan 274 / advise 209 / generate 96 lines). `plan.md` has explicit numbered Steps 0–9 with **Step 2b Validation Gate** wiring Coaching Process Rule 1. | Checkpoint discipline uneven — `plan.md` is the only workflow with a labelled gate. Rule 1 fires implicitly in 3 of 4 workflows. | M |
| 3 | Output contract (paths, formats) | Contract spread across `plan_state_schema.md` (232 ln) + `obsidian_templates.md` (104 ln) + `setup.md` paths + CLAUDE.md gitignore enumeration. Recent commit `ad331b5` standardised workout-review filename convention. | No single "Artifacts produced" index. Inferable but not catalogued. | L |
| 4 | Methodology depth & citation rigour | Cited authorities: Seiler (2010), Stöggl & Sperlich (2014), Rønnestad, Coggan (implicit/power profile), Llanos-Lagos 2025, Beattie 2014, Quittmann 2025, Clark & Macdermid 2025, Lolli 2019, Impellizzeri 2020. Single "Citation currency — last verified 2026-05-20" on `block_templates.md`. | **No central bibliography.** Mujika **uncited across SKILL.md, workflows/, references/, CLAUDE.md** (verified by grep). San Millán **uncited** (Z2 framework central to polarized + base blocks, no in-doc anchor). Allen-Coggan never paired explicitly. Citation-currency pattern exists on one doc out of six methodology refs. | **H** |
| 5 | Tool integration (Zwift `.zwo`, intervals.icu API) | intervals.icu: split `intervals_icu/` package (W1 refactor), 4 CLI modes, signal-mode contract in `cli_reference.md`, `.fit` fallback (`fit_ingest.py`). Zwift: `generate_zwo.py` + `batch_generate_zwo.py` + `zwo_lint.py` (8 rules W1–W9). | Mature surface area but no API change log / lint rule changelog — versioning lives only in git. Retry/rate-limit behaviour in `api_client.py` not audited this cycle. | L |
| 6 | Sub-prompt reusability | `readiness_template.md` is the model — shared by `advise.md` + `plan.md`. Signal-mode contract canonicalised in `cli_reference.md` (`7fcabfa`). `rule_registry.md` catalogues standing rules. | 4 reference docs act as sub-prompts (block_templates Block Selection Logic section, weekly_adaptation, adaptation_rules, readiness_template) but have no explicit Inputs / Outputs / Invocation contract headers. Workflows say "read X.md" and the whole file gets loaded. | M |
| 7 | Token efficiency / context load | 4,190 total lines. Active focus area — 4 token-reduction phases shipped. SKILL.md slimmed to 116 ln (Phase 3+4, `610bb4a`). ToCs on files >300 ln. | Two refs still 400+: `block_templates.md` (458), `workout_analysis.md` (414). Workflows reference them as bare paths; section anchors would let load-on-demand land on the right section. | M |
| 8 | Audit recurrence logic | One "Citation currency" line on `block_templates.md`. One off-cycle Obsidian audit (writing-skills, 2026-05-23). 23-case `evals/trigger_eval.json` — but harness has documented limits. | **No quarterly ritual encoded.** No `audits/` log inside the skill repo (lived in Obsidian only, divorced from version control). No template defining what gets audited each quarter. **Broken pointer** at `rule_registry.md:3` to `audits/cycling-coach-w4-orphaning-design-2026-05-21.md` which doesn't exist. | **H** |

## §2 Refactor proposal (summary)

Seven changes proposed, prioritised P0–P2. Full rationale (with sports-science citation + skill-creator methodology citation per change) in chat transcript and in the P0 deliverables themselves.

| # | Change | Priority | Files affected |
|---|--------|---------:|----------------|
| C1 | Central bibliography `references/bibliography.md` | **P0** | + `references/bibliography.md` |
| C2 | Audit protocol + repo `audits/` dir + fix broken pointer | **P0** | + `references/audit_protocol.md`, + `audits/README.md`, + ported writing-skills audit, ~ `references/rule_registry.md:3` |
| C3 | Sub-prompt contracts on 4 sub-prompt-style refs | **P1** | ~ `readiness_template.md`, `block_templates.md`, `weekly_adaptation.md`, `adaptation_rules.md` |
| C4 | Citation currency cadence on every methodology doc | **P1** | ~ `weekly_adaptation.md`, `race_taper.md`, `durability_strength.md`, `fueling.md`, `menstrual_cycle_training.md`, `training_zones.md` |
| C5 | Workflow checkpoint consistency | P2 | ~ `analyze.md`, `advise.md`, `generate.md` |
| C6 | Section anchors for large reference docs | P2 | ~ `block_templates.md`, `workout_analysis.md` + workflow cross-refs |
| C7 | Output artifact index `references/artifacts.md` | P2 | + `references/artifacts.md` |

**Frontmatter convention doc dropped** — this skill stands alone (per-user clarification 2026-05-26).

## §3 Out of scope

- Frontmatter convention alignment with other skill families. Standalone skill; no cross-skill convention target.
- Description sentence A/B/C variants. Variants drafted in proposal but not actioned this cycle — current description (`8a90a81`) is CSO-compliant; variant testing deferred until a real regression appears.
- `api_client.py` retry/rate-limit audit. Not the subject of this proposal; queue for a future audit if integration reliability becomes a finding.

## §4 Resolution

P0 + P1 actioned on 2026-05-26 (skill versions `01b8e45` → `3b30820`).

| Change | Commit | Note |
|--------|--------|------|
| C1 — bibliography | `59d56f4` | 208 ln; 7 framework authorities + 6 auxiliary; ASCII-only anchors; currency log; evidence-tier conventions. |
| C2 — audit protocol + audits/ + writing-skills port + rule_registry pointer fix | `9880245` | Quarterly cadence with Weekly Review surfacing mechanism; 3 audit artifacts ported/created (README, 2026-05-23 writing-skills, this file); rule_registry.md:3 self-contained. |
| C4 — citation cadence preambles (6 docs) | `3b30820` | New preambles on weekly_adaptation, race_taper, fueling, training_zones; existing preambles on block_templates, durability_strength, menstrual_cycle_training extended with bibliography anchors. |
| C3 — sub-prompt contracts (4 docs) | `3b30820` | Additive Inputs / Outputs / Invocation headers on readiness_template, adaptation_rules, weekly_adaptation, block_templates → Block Selection Logic. |
| SKILL.md + CLAUDE.md router sync | `3b30820` | Reference Files table and Architecture tree updated for new ref files + audits/ dir. |

**Tests:** `python -m unittest discover tests` → 646 OK (no regressions). No script code paths touched.

**Not yet shipped (deliberate scope cut):**

- Push to origin (`git push origin master`) and install-path sync — held for user confirmation per system / CLAUDE.md guidance on visible / shared actions.
- P2 changes — C5 (workflow checkpoint consistency), C6 (section anchors), C7 (output artifact index) — queued in `references/audit_protocol.md` → Currently-queued actions for the 2026-Q3 / 2026-Q4 audits.
- Weekly Review audit-due surfacing wire-up — proposed mechanism documented in audit_protocol.md but not yet wired into `workflows/plan.md`. Queued as a follow-up.
