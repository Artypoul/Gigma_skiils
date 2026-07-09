---
name: pr-finalize
description: "Finalize a frontend or web-app pull request once the implementation is ready. Use when the user asks to prepare a PR, verify checks, update required history or changelog docs, or assemble a clean Summary and Test plan before push or PR creation. Read repo rules first, run the strongest relevant checks the repo actually defines, and do not merge without explicit user approval."
---

# Pr Finalize

Use this only when the implementation is genuinely ready for PR work. This skill may run checks and prepare PR metadata, but it must not merge without explicit user approval.

## Preflight

1. Read repository rules first:
   - base branch
   - required docs such as history or changelog updates
   - CI or review gates
   - dirty worktree rules
2. Inspect git state, changed files, and current branch.
3. Read `package.json` or project docs to discover the strongest relevant verification commands the repository actually defines.

## Verification

Run the closest relevant checks that exist for the repo:

- `git diff --check`
- lint
- type-check
- unit tests
- build
- e2e or smoke tests when the affected flow is critical and the repo supports it

Do not silently downgrade from a stronger check to a weaker one unless the repository documents that fallback or the user explicitly accepts it.

If checks fail:

- stop
- report the failing command
- summarize the important error
- do not claim the PR is ready unless the user explicitly accepts the known risk

## History And Docs

If the repository requires release notes, `history.md`, changelog entries, migration notes, or rollout notes, update them before finalizing the PR. Summarize the real user or developer impact instead of narrating the coding process.

## PR Assembly

- stage only in-scope files
- respect the repository base branch rule, or use the default branch when the repo is silent
- if a PR already exists for the branch, return that URL instead of creating a duplicate
- use the repository's expected PR body format; when no format is documented, include at least:
  - `## Summary`
  - `## Test plan`

## Safety

- do not merge without explicit user approval
- do not force-push a protected or default branch
- do not hide incomplete verification
- do not fold unrelated cleanup into the PR at the last moment

## Final Report

Return:

- branch name
- checks run
- remaining blockers or accepted risks
- docs updated
- PR URL if one was created
