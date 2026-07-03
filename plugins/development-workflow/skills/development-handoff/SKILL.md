---
name: development-handoff
description: "Manage development handoff between Codex agents: post-merge protocol, same-PR fixes, monster review gates, prod-ready checks, deploy checks, dirty worktree safety and continuation from evidence. Use when the user says merged/смерджил, fix in PR/чини в PR, monster review/монстр ревью, prod ready/продак реди, update branches/обнови ветки, deploy/деплой, handoff/передай смену, or when continuing an interrupted development task."
---

# Development Handoff

Use this skill to keep a development task coherent across agents, PR reviews, merge, deploy and interruptions. A handoff is not a memory dump; it is the next agent's operating state.

Golden rule: inspect repository and PR evidence before acting from memory.

## Quick Snapshot

When inside a git repository, run the bundled read-only helper first:

Resolve bundled script paths relative to this `SKILL.md`.

```bash
python scripts/handoff_snapshot.py --repo <repo-path>
```

Default helper output redacts absolute local paths and remote URLs. Use `--show-paths` only for local diagnostics and do not paste that output into chat, docs or PR comments.

If a PR number or URL is known:

```bash
python scripts/handoff_snapshot.py --repo <repo-path> --pr 123
```

If the helper is unavailable, gather the same facts manually:

```bash
git status --short --branch
git branch -vv
git log --oneline --decorate -5
gh pr view --json url,state,mergedAt,headRefName,baseRefName,statusCheckRollup,reviewDecision
```

Read `references/handoff-contract.md` when you need the full template, exact command recipes, prod-ready checklist, or skill/plugin installability checks.

## Interpret User Commands

Treat short user phrases as process triggers:

- `смерджил`, `merged`, `залил` -> run post-merge protocol.
- `чини в PR`, `чини там же`, `не вижу правки в PR` -> reuse the existing PR branch.
- `монстр ревью`, `monster review`, `сделай ревью` -> run findings-first review and track fixes.
- `продак реди?`, `prod ready?` -> answer only after the prod-ready evidence gate.
- `обнови ветки`, `origin?` -> fetch/prune and compare local vs remote without losing dirty work.
- `деплой` -> follow deploy checks; do not drift into unrelated work.
- `стоп`, `не туда`, `не меняй` -> stop immediately.

Do not ask for clarification when the safe next protocol is obvious.

## Post-Merge Protocol

When the user says the PR was merged:

1. Verify PR state with `gh pr view <id> --json state,mergedAt,mergeCommit,url`.
2. Run `git fetch --all --prune`.
3. Check dirty worktree before switching branches.
4. Switch to the base branch and run `git pull --ff-only` only when safe.
5. Check `git status --short --branch` and latest commits.
6. Check GitHub Actions or required workflows for the merge commit.
7. If the task involved deploy, check deploy workflow and runtime health using the repository runbook.
8. Return a short handoff: merged item, updated branch, checks, remaining blockers, next action.

Queued or unavailable checks are not green.

## Fix Existing PR Protocol

When the user asks to fix a PR:

1. Identify the current PR and branch from git/gh evidence.
2. If the PR is open, patch that branch. Do not create a new PR.
3. Read review comments, checks and failing logs before editing.
4. Fix the cause and adjacent same-pattern issues.
5. Stage only files belonging to the current task.
6. Push to the same branch.
7. Re-check CI and review comments after the push.

If the PR is already merged or closed, explain that state and only then decide whether a follow-up PR is needed.

## Review Gate

For monster review or serious review:

1. Start with findings ordered by severity.
2. Ground each finding in file/line evidence.
3. Include risk and one-sentence fix.
4. If P1/P2 findings are real and the user asked to fix, fix them in the same PR.
5. Re-run relevant checks and re-read review comments after push.

Do not call a PR ready while a real P1/P2 remains open.

## Prod-Ready Gate

Before answering "ready":

- repo, branch, PR and base branch are known;
- local dirty tree does not contaminate the task;
- tests or equivalent checks were run and named;
- CI/review state is known after the last push;
- deploy workflow/health is checked when deploy is in scope;
- no secrets, tokens, private paths or credentials were printed or committed;
- handoff includes the next required action.

If any item is unknown, answer "not ready yet" or "ready with this explicit risk".

## Dirty Worktree

When there are local changes:

1. Classify them as current-task, pre-existing, generated, or unknown.
2. Never reset, checkout, clean, move, or overwrite unrelated changes without direct permission.
3. Stage only current-task files.
4. If dirty files block branch update or PR continuation, report the exact blocker.
5. Mention left-over dirty files in the final handoff.

## Product And Scope Constraints

Explicit user decisions steer the workflow until changed:

- "only <scope>" means stay inside that scope.
- "this product decision is fixed" means do not redesign it unless asked.
- "same PR" means no new PR.
- "do not ask" means act from evidence when risk is low.

If a user constraint conflicts with security, money, production data, destructive git operations, or deploy safety, pause and explain the risk.

## Skill/Plugin Work

When changing reusable skills or plugins:

1. Confirm ownership: generic workflow skills belong in a generic workflow plugin, not in a domain plugin.
2. Add or update both machine manifests required by the catalogue.
3. Update marketplace discovery entries when a plugin is added, moved or removed.
4. Run the mirror sync script.
5. Validate the skill and the catalogue.
6. Do not store private chat transcripts, secrets or product-specific incident text in the skill.

## Final Handoff

End meaningful work with this compact block:

```text
HANDOFF
Workspace: <repo name or redacted local path>
Branch:
PR:
State:
Last evidence:
User constraints:
Open blockers:
Next required action:
Do not:
```

Keep chat output short; put long audit trails in PR comments or PR body.
