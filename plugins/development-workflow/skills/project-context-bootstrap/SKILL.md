---
name: project-context-bootstrap
description: Build a compact read-only repository context snapshot before code changes, code review, PR/merge/deploy work, debugging, handoff, resumed agent work, or checking another agent's changes. Trigger when the next action depends on project rules, product decisions, memory/history, current git/PR state, or local skill availability; for tiny self-contained tasks, keep the snapshot internal and report only blockers.
---

# Project Context Bootstrap

Use this skill as the first pass in any repository when project truth matters. Its job is to turn scattered files, git state, and prior decisions into one compact operating snapshot.

## Rules

- Read first, edit later.
- Prefer project-local rules over global habits.
- Treat missing context as a risk, not as permission to guess.
- Do not paste secrets, raw `.env` values, private remote URLs, or long logs into chat.
- Do not change files for read-only, review, audit, check-up, консилиум, or "посмотри/оцени" tasks.
- Do not create `project-memory.md` or any other context file unless the user explicitly asks to initialize project context.

## Find The Project Root

Before reading context, resolve the project root:

```bash
git rev-parse --show-toplevel
```

If git root is unavailable, use the current working directory as a fallback and mark `Missing context: repo root unknown`. In monorepos or nested workspaces, also check for the nearest applicable `AGENTS.md` between the current directory and the root.

## Context Order

From the resolved project root, read files that exist:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `project-memory.md`
4. `history.md` or `HISTORY.md`
5. `README.md` and nearby architecture docs such as `docs/architecture.md`, `docs/context.md`, `docs/business-logic.md`
6. Project-local skill indexes when relevant: list `.codex/skills`, `.agents/skills`, and `.claude/skills/README.md`; read only the `SKILL.md` files for skills selected by the task or router.

Read `AGENTS.md`, `project-memory.md`, and the top of `history.md` carefully enough to capture current decisions and blockers. If another file is large, use `rg` for targeted lookups and state what was not fully read.

## Git Snapshot

When inside a git repo, collect:

```bash
git status --short --branch
git log --oneline --decorate -5
git branch -vv
```

For review, handoff, PR fix, PR finalization, merge, deploy, or "ready?" work, PR/check/review evidence is mandatory. If GitHub CLI is unavailable or the user requested offline/local-only work, mark PR evidence as unknown/blocking instead of guessing.

```bash
gh pr view --json url,state,headRefName,baseRefName,statusCheckRollup,reviewDecision
```

For dirty worktrees, classify files as current-task, pre-existing, generated, or unknown. Never reset or clean unrelated files. Before edits, if any target file is already dirty and its origin is unknown or pre-existing, stop and ask Art how to proceed.

Redact private remotes, tokens, secrets in logs/history, raw PR output, and copied snippets.

## Output

Return a short block:

```text
CONTEXT SNAPSHOT
Project:
Product/current truth:
Branch/PR:
Dirty tree:
Relevant rules:
Active decisions:
Open blockers:
Missing context:
Next safe action:
Do not:
```

For small tasks, keep this internal and mention only blockers. For handoff, review, PR, merge, deploy, or agent-error checks, show the block.

## Initializing Context

Only when the user asks to create project memory, add a `project-memory.md` using `references/project-memory-template.md`. Keep it short: current truth, active decisions, open blockers, next step. Do not copy chat transcripts into it.
