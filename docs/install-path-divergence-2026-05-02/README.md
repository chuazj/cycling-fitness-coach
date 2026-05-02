# Install-Path Divergence Backup — 2026-05-02

## What this is

A snapshot of work that existed only at the install path (`~/.claude/skills/cycling-fitness-coach/`) and was about to be overwritten by a sync to origin/master. Saved here for recovery / cherry-picking before the destructive sync.

## Context

The install path is a separate git working copy from this repo. Per CLAUDE.md it is supposed to be a one-way mirror of the working copy — but in practice some interactive sessions edited files directly at the install path without committing back. By 2026-05-02 the install path had:

- Drifted **7 commits behind** origin/master (last in-sync at commit `1387394`).
- Accumulated **uncommitted local edits** to 4 files (~217 lines added).
- A new **untracked** file (`references/adaptation_rules.md`, 231 lines).

The local edits diverge in content from the work that landed in origin/master via the working copy — they address overlapping topics (adaptation rules, training zones, periodization additions) but with different wording and structure. They are not duplicates.

The user (zijian@hotmail.sg) chose Option B during the 2026-05-02 sync conversation: back up first, then `git reset --hard origin/master` at the install path. The install path is now a clean mirror of origin, and these files are the recoverable copy of what was wiped.

## Files

| File | What it is |
|---|---|
| `local-modifications.patch` | Output of `git diff` at the install path — covers the 4 modified-but-uncommitted files (SKILL.md, references/periodization.md, references/training_zones.md, workflows/analyze.md) |
| `adaptation_rules.md.untracked` | Verbatim copy of the install-path-only `references/adaptation_rules.md` (untracked at install path; never touched origin) |

## How to recover

If any of this content turns out to be worth keeping:

1. Inspect the patch: `git apply --check docs/install-path-divergence-2026-05-02/local-modifications.patch` will tell you whether it still applies cleanly. (It probably won't, since the files have moved on — read the diff and cherry-pick by hand.)
2. Compare `adaptation_rules.md.untracked` against `references/adaptation_rules.md` in the working copy. Both address per-activity adaptation cascades but with different scope/format. Decide whether to merge or discard.
3. Anything still useful → propose as a normal edit to the working copy.

## When to delete this directory

Once a future audit cycle confirms nothing here is worth recovering, delete the entire `docs/install-path-divergence-2026-05-02/` directory and remove this entry from any open audit memory.
