# Development Handoff Contract

Use this reference when a software development task crosses agent turns, PR review cycles, merge, deploy, or dirty worktree states. Keep the handoff generic and evidence-based.

## Handoff Block

```text
HANDOFF
Workspace: <absolute repo path or repo name>
Task: <one sentence>
Branch: <current branch and tracking state>
PR: <url, number, state>
Base: <base branch and latest known commit>
State: planning | coding | review | waiting-merge | merged | deployed | blocked
Last evidence:
- git:
- tests:
- checks:
- reviews:
- deploy:
User constraints:
- <constraint that must steer the next agent>
Open blockers:
- <real blocker or "none known">
Next required action:
- <one concrete action>
Do not:
- <specific things the next agent must not do>
```

## Command Recipes

### Baseline Snapshot

```bash
git status --short --branch
git branch -vv
git log --oneline --decorate -5
git remote -v
```

If GitHub CLI is configured:

```bash
gh pr view --json url,state,mergedAt,headRefName,baseRefName,statusCheckRollup,reviewDecision
gh pr checks --watch --interval 10
```

For a known PR:

```bash
gh pr view <number> --json url,state,mergedAt,mergeCommit,headRefName,baseRefName,statusCheckRollup,reviewDecision
gh pr diff <number> --name-only
```

Read PR comment bodies only when needed for review/fix work. Do not paste raw bodies into chat or handoff output; summarize findings and redact secrets, tokens, credentials, private paths and long logs.

### Post-Merge

```bash
gh pr view <number> --json url,state,mergedAt,mergeCommit
git fetch --all --prune
git switch <base-branch>
git pull --ff-only
git status --short --branch
git log --oneline --decorate -5
```

If the worktree is dirty, do not switch or pull until the dirty files are classified.

### Fix Existing PR

```bash
git fetch --all --prune
gh pr view <number> --json url,state,headRefName,baseRefName,statusCheckRollup,reviewDecision
git switch <headRefName>
git status --short --branch
```

After patching:

```bash
git diff --check
git status --short
git add <only-current-task-files>
git commit -m "<message>"
git push
gh pr checks <number> --watch --interval 10
```

### Skill/Plugin Installability

When a skill or plugin is added, moved, renamed or removed, verify:

- plugin manifest exists for each supported runtime;
- marketplace entry exists for each supported runtime;
- plugin `version`, `description`, `skills`, interface metadata and default prompt are not placeholders;
- fallback mirror is regenerated from canonical plugin files;
- catalogue validation passes.

## Prod-Ready Checklist

Answer "ready" only when:

- current branch and PR state are known;
- local worktree does not mix unrelated changes into the task;
- CI/checks are completed or their unavailable state is explained;
- tests or equivalent validation were run and results are named;
- review comments were read after the last push;
- deploy health was checked when deploy is in scope;
- no secrets, tokens, private paths, or credentials were printed or committed;
- handoff names the next required action.

## Intent Map

| User phrase | Required behavior |
| --- | --- |
| `смерджил`, `merged` | Run post-merge protocol; verify PR state and checks. |
| `чини в PR`, `там же` | Reuse current PR branch; do not create a new PR. |
| `сделай монстр ревью` | Findings-first review, then fix P1/P2 if asked. |
| `продак реди?` | Run prod-ready check; answer from evidence. |
| `обнови ветки`, `origin?` | Fetch/prune and compare local vs remote without losing dirty work. |
| `деплой` | Follow deploy runbook/checks; do not drift into unrelated code. |
| `стоп`, `не туда` | Stop current workflow immediately. |

## Failure Patterns To Prevent

- Treating `merged` as a chat note instead of a post-merge trigger.
- Creating a new PR when the user asked to fix the existing PR.
- Declaring "ready" while a review/check is still queued.
- Reopening a product decision after the user explicitly froze it.
- Mixing unrelated dirty-tree changes into the current commit.
- Relying on memory instead of reading PR comments, checks, and branch state.
- Switching domains after the user narrowed scope.
- Reporting deploy success without checking workflow or health evidence.

## Output Style

For the user:

```text
Сделал post-merge protocol.
- PR: merged
- base branch: updated to <commit>
- checks: <status>
- dirty tree: <clean/dirty>
- next: <action>
```

For PR comments or long handoff notes, include the full `HANDOFF` block.
