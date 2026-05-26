---
title: Writing-skills rubric audit
date: 2026-05-23
type: audit
audit_scope: [writing-skills]
skill: cycling-fitness-coach
skill_version_start: 94688c9
skill_version_end: 8e539d5
rubric: superpowers:writing-skills
status: actioned
findings_count: 8
findings_high: 1
findings_medium: 1
findings_low: 6
tags: [cycling, coaching, audit, writing-skills]
---

# Writing-Skills Rubric Audit — 2026-05-23

**Note:** this audit was originally written to the Obsidian vault on 2026-05-23 and is ported here on 2026-05-26 as part of the C2 audit-protocol rollout (refactor proposal §2 / P0). The Obsidian copy may diverge; this repo copy is the canonical version-controlled record.

Audited against the `superpowers:writing-skills` rubric covering trigger quality, functionality/structure, and token efficiency.

## §1 Audit table

| ID | Area | Current state (2026-05-23) | Gap | Severity |
|----|------|----------------------------|-----|----------|
| F1 | Frontmatter — description shape | Description led with "Analyzes intervals.icu rides … generates Zwift .zwo workouts … creates periodized plans …" — a workflow summary, not a trigger condition. | CSO violation per writing-skills. Risks Claude following the description (which describes *what the skill does*) instead of loading the SKILL.md body (which defines *Coaching Process Rules*). Could short-circuit Validate-Before-Prescribing and Establish-Zones-First gates. | **H** |
| F2 | Frontmatter — opener convention | Description did not open with "Use when…". | Misses the writing-skills CSO opener. Auto-fixes if F1 is actioned. | M |
| F3 | Frontmatter — trigger coverage | Concurrent strength/lifting intent (e.g., "leg day tomorrow and sweet spot the day after") not covered. `durability_strength.md` handles it but the description doesn't route through. | Trigger gap on a real coaching intent. | L |
| F4 | Frontmatter — non-spec keys | `compatibility:` field present (listed Python 3.9+, requests, intervals.icu key, Obsidian, fitparse). | agentskills.io spec defines only `name` and `description` — `compatibility:` was silently ignored by loaders. Requirements belong in README, not frontmatter. | L |
| F5 | Reference docs — ToC threshold | Three refs (`adaptation_rules.md`, `plan_state_schema.md`, `zwo_format.md`) in 200–275 line band, approaching the 300-line ToC threshold. | Pre-emptive — not yet a violation. Convention: add ToC when next touching the file. | L |
| F6 | Workflow file consolidation | `workflows/advise.md` houses 3 intents (Training Advice, Mid-Week Check-In, Race Peaking). | Routing in SKILL.md is correct and functionally fine. Split is only a candidate if any intent doubles in size. | L |
| F7 | Response Guidelines paragraph | Acronym-expansion guidance in SKILL.md → Response Guidelines #5. | Long paragraph; could move to a reference doc. Decision: keep — applies to every coaching response, body-level placement is correct. | L |
| F8 | Reference Files table descriptions | Each ref's table row has a short tagline. | After Phase 3 compression (610bb4a), descriptions are short routing hints. No further trim warranted. | L |

## §2 Action plan (at time of audit)

For F1–F4, sequence:

1. Baseline eval (run_eval.py on current description).
2. Add F3 probe to eval set first.
3. RED-test F3 fix only if probe fails.
4. RED-test F1 GREEN sketch via `--description` override.
5. Commit F3 probe; commit F1+F2+F3 description rewrite; commit F4 frontmatter cleanup.
6. Sync install path.

Sequence followed (with eval-harness caveat — see §4).

## §3 Out of scope

- **F5:** deferred to next-touch of each file. ToC convention triggers naturally on the next material edit.
- **F6:** no action — routing is correct.
- **F7:** no action — body-level placement is correct.
- **F8:** no action — already minimal post-Phase-3.

## §4 Resolution

Actioned in master:

| Finding | Commit | Note |
|---------|--------|------|
| F3 probe | `86dacdd` | Probe added to `evals/trigger_eval.json`. Probe fired RED on baseline → strength/lifting phrase added in F1's GREEN. |
| F1 + F2 + F3 | `8a90a81` | Description rewritten to "Use when…" opener; F3 strength phrase folded in. |
| F4 | `8e539d5` | `compatibility:` removed from frontmatter; requirements documented in README.md. |

**Eval-harness caveat — shipped on rubric grounds, not GREEN bar.** `run_eval.py` is non-viable for measuring this skill once installed (real-skill shadowing + first-tool-must-be-Skill/Read). Documented in `CLAUDE.md` → "Eval harness limitations". Iron-Law RED→GREEN discipline only applies when the eval is a viable measurement instrument; for installed user-level skills it isn't. Full trace: commits `86dacdd → 8a90a81 → 8e539d5`.

**Install path sync confirmed:** `~/.claude/skills/cycling-fitness-coach` HEAD == working-copy HEAD at the time of resolution.
