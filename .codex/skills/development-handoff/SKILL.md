---
name: development-handoff
description: "Create and verify a development handoff before continuing agent work. Use when resuming an interrupted coding session, fixing review comments, continuing a PR, handling a merged/closed PR, moving or creating skills/plugins, or preparing a concise handoff for another agent."
---

# Development Handoff

Use this skill to turn a messy continuation into a verified state snapshot. Prefer facts from Git, local files, CI, and PR metadata over chat memory.

## First Checks

1. Read local repo instructions before acting: `AGENTS.md`, `CLAUDE.md`, skill/plugin docs, and nearby workflow files when present.
2. Check Git state:
   - `git status --short --branch`
   - `git log --oneline --decorate -5`
   - `git diff --stat`
3. If a PR is mentioned, verify it before saying "same PR":
   - `gh pr view <number> --json state,headRefName,headRefOid,baseRefName,statusCheckRollup,comments,reviews,latestReviews,mergeStateStatus`
   - If `state` is `MERGED` or `CLOSED`, do not claim the fix can land in that PR. Create or propose a follow-up PR from the current base branch.
4. If the working tree has changes you did not make, do not overwrite them. Either work with them after reading the diff, or use a clean worktree from the target base branch.

## Handoff Snapshot

Prepare this compact block before continuing or handing off:

```md
## Handoff Snapshot

Intent:
Repo:
Branch:
Base branch:
PR:
PR state:
Latest local commit:
Latest remote/base commit:
Dirty files:
User constraints:
Do not touch:
Review findings:
Fixes already made:
Checks passed:
Known blockers:
Next required action:
Definition of done:
```

Keep it factual. Do not paste private chat logs, secrets, tokens, or long transcripts.

## Skill and Plugin Work

When adding, moving, renaming, or removing a skill:

1. Decide ownership before editing. A domain-specific skill belongs in that domain plugin; a cross-cutting workflow belongs in a generic workflow plugin.
2. Search existing skills first with `rg --files` and `rg "<term>"` to avoid duplicates.
3. Keep the canonical files under `plugins/`. Treat `.codex/skills/` and `.codex/reference/` as generated mirrors when the repo says so.
4. Update every affected discovery surface:
   - skill `SKILL.md` frontmatter;
   - `agents/openai.yaml` when present;
   - plugin `.codex-plugin/plugin.json`;
   - plugin `.claude-plugin/plugin.json` when the repo supports Claude plugins;
   - root marketplace files for Codex and Claude when adding a plugin or changing discovery wording.
5. Bump plugin versions for every plugin whose installed skill set or discovery text changes. This prevents versioned plugin caches from serving stale skills.
6. Run the repo sync command if the repo has a generated skill mirror, for example `bash sync-codex.sh`.
7. Validate the changed skill and the full catalogue.

## Review Fixes

Track review work as evidence:

```md
| Finding | Severity | Fix | Verification | Re-review |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
```

- Treat real `P1`, `P2`, and `P3` findings as unfinished until fixed or explicitly rejected with evidence.
- After fixing review findings, run a fresh re-review on the current diff. Do not rely on a review that saw an older plan, older code, or pre-fix state.
- If an external review tool is unavailable, say that directly and run a local role-based review on the current diff.

## Safe Continuation Rules

- If chat history conflicts with GitHub or Git state, trust checked GitHub/Git state and mention the mismatch.
- If a PR was merged during the handoff, create a new follow-up branch from the current base branch.
- If a branch contains unrelated local changes, avoid cleaning them unless the user explicitly asks. Prefer a fresh worktree.
- Before production-sensitive, money-sensitive, security-sensitive, or destructive actions, stop and ask for confirmation.
- Keep user-facing status short: what changed, why it matters, what was verified, and what remains.

## Completion Checklist

- Repo instructions read.
- Branch/PR/base state verified.
- Dirty files understood or isolated in a clean worktree.
- Domain ownership checked before skill/plugin placement.
- Plugin version and marketplace discovery updated when installability changed.
- Mirror sync completed when required.
- Skill and catalogue validation passed.
- Review findings fixed and re-reviewed on the latest diff.
