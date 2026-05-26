# Audits

Version-controlled audit log for the cycling-fitness-coach skill. Each audit is a dated markdown file produced by a quarterly review or an ad-hoc rubric check.

**Protocol:** see `governance/audit_protocol.md` for cadence, scope, and frontmatter schema.

**Naming convention:** `cycling-coach-<topic>-YYYY-MM-DD.md`

| Topic slug | Used when |
|------------|-----------|
| `writing-skills` | Skill audited against `superpowers:writing-skills` rubric. |
| `methodology-currency` | Quarterly citation-currency refresh. |
| `eval-suite-refresh` | Trigger-eval audit / new probe additions. |
| `output-contract` | Walk-through of every emitted artifact's schema + gitignore status. |
| `refactor-proposal` | Multi-scope proposal that drives a refactor PR series (not a single-scope finding). |
| `program-summary` | Consolidated record of a multi-workstream improvement program (legacy slug; reserved for back-ports of pre-2026-05-26 Obsidian artifacts). |

A single audit can cover multiple scopes; the topic slug reflects the dominant one. The frontmatter `audit_scope:` array captures the full set.

## Index

| Date | Title | Status | Scope |
|------|-------|--------|-------|
| 2026-05-26 | [Refactor proposal — methodology, recurrence, sub-prompts](cycling-coach-refactor-proposal-2026-05-26.md) | actioned | refactor-proposal |
| 2026-05-23 | [Writing-skills rubric audit](cycling-coach-writing-skills-2026-05-23.md) | actioned | writing-skills |
| 2026-05-22 | [A+ program summary (W1–W8 consolidated record)](cycling-coach-a-plus-program-summary-2026-05-22.md) | complete | program-summary |

(Update on every new audit. Sort newest first.)

## How to add a new audit

1. Read `governance/audit_protocol.md` end-to-end.
2. Create a new file: `audits/cycling-coach-<topic>-YYYY-MM-DD.md`.
3. Copy the frontmatter schema from `audit_protocol.md` → Audit artifact format.
4. Body: §1 Audit table, §2 Action plan, §3 Out of scope, §4 Resolution (filled in after actioning).
5. Update this README's Index table.
6. Commit. (For methodology-currency audits, also bump the per-doc preamble dates.)
