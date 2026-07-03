# Plan: Development Handoff Skill

## Goal

Add a reusable development handoff skill that helps an agent continue work from evidence instead of stale chat memory. The skill should encode the repeated failures seen in recent agent work: wrong domain ownership, missing plugin installability updates, stale PR state, and weak review-to-fix tracking.

The skill text must stay generic: do not mention a specific product or project name in `SKILL.md`. Repository-specific names may appear only where required by plugin/marketplace metadata.

## Scope

- Add a new generic plugin, `development-workflow`, instead of putting the skill into a product/domain plugin.
- Add one skill: `development-handoff`.
- Add `agents/openai.yaml` for the skill.
- Update Codex and Claude marketplace entries so the plugin is installable.
- Sync `.codex/skills/` from `plugins/` after implementation.
- Validate the catalogue and the new skill.

## Out of Scope

- No changes to existing domain skill behavior.
- No backend, frontend, API, database, deploy, or production logic changes.
- No import of private chat transcripts into the repository.
- No generic rewrite of existing plugins or manifests.

## Data and Storage

DB does not change.

No secrets, tokens, chat logs, or production data are stored. The skill only stores reusable process instructions.

## Reuse Check

Existing related material:

| Existing file | Decision |
| --- | --- |
| `AGENTS.md` | Reuse repo rules for plugin canon, `.codex` mirror, validation, and PR review cycle. |
| `validate_plugin.py` | Reuse as required catalogue validation. |
| `sync-codex.sh` | Reuse to rebuild `.codex` mirror from canonical plugin files. |
| Existing domain plugins | Do not place this skill there; the handoff workflow is cross-domain. |
| Existing `feature` workflow | Reuse for doc-first implementation and PR review discipline. |

## Skill Behavior

The skill should make an agent produce and verify a handoff snapshot before continuing work:

- identify repo, branch, PR, base branch, latest commit, and dirty files;
- check whether the PR is open, closed, or merged before saying "same PR";
- identify domain ownership before creating, moving, or renaming skills;
- if a skill is added, moved, renamed, or removed, require plugin version bump, marketplace discovery text, `.codex` sync, and validation;
- track review findings as `finding -> fix -> verification -> re-review`;
- keep handoff concise and evidence-based;
- stop and ask only when the next action would be destructive or product-sensitive.

## Review Risks

- A generic handoff skill could become too broad. Keep it focused on continuation and PR/skill-work safety.
- Adding a new plugin expands the marketplace. This is intentional because the skill is not owned by a product/domain plugin.
- If the skill mentions a specific project/product, it becomes less reusable and violates the request.

## Verification

Run:

```bash
python C:\Users\Art\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\development-workflow\skills\development-handoff
python validate_plugin.py
git diff --check
```

After PR creation or push, check:

```bash
gh pr view <number> --json state,headRefName,headRefOid,statusCheckRollup,comments,reviews,latestReviews,mergeStateStatus
```

## Planning Review

Manual planning review roles:

| Role | Check |
| --- | --- |
| Skill architecture | Generic plugin is the right ownership boundary; no domain plugin pollution. |
| Process safety | Handoff gates cover stale PR state, dirty worktree, review fixes, and installability. |
| Marketplace/installability | New plugin is discoverable in both marketplaces and passes mirror validation. |

Current result: no blocker in the plan. Implementation can proceed after the planning-only PR review gate is satisfied.
