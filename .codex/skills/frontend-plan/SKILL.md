---
name: frontend-plan
description: "Plan a frontend or web-app change before coding. Use for feature work, refactors, route or page changes, UI rewrites, state or API integrations, or when the user asks what to do next on a frontend task. Read the repository rules, recent context, and relevant code first, then return a scoped plan with touched areas, contracts to preserve, risks, verification, and explicit non-goals."
---

# Frontend Plan

Plan first. Do not edit code unless the user explicitly changes the task from planning to implementation.

## Workflow

1. Read the project rules and live context first: `AGENTS.md`, `CLAUDE.md`, `history.md` or `HISTORY.md`, `README.md`, nearby docs, and `package.json` when present.
2. Inspect current git context when it matters:
   - `git status --short --branch`
   - recent commits
   - open PR or review state if this is follow-up work
3. Search the codebase with `rg` before proposing structure. Find the existing route, page, component, hook, API layer, store slice, style consumer, and tests that already own the behavior.
4. Identify the contracts the change must preserve:
   - route and entrypoint ownership
   - data flow and API/client ownership
   - loading, error, and empty states
   - accessibility and keyboard behavior
   - responsive layout constraints
   - tests, analytics, auth, persistence, or compatibility concerns when present
5. If the requested outcome is still broad or ambiguous, ask one short question about the result before finalizing the plan.
6. Return a plan that stays inside the active scope. Do not smuggle in unrelated cleanup.

## What To Look For

- Existing component boundaries before inventing new ones
- Current state owner: local state, Redux, RTK Query, URL state, form library, or context
- Existing API helpers before proposing a new transport path
- Existing styling patterns before inventing a new CSS system
- Existing tests or fixtures that should move with the change
- Existing review comments or accepted product decisions that lock the approach

## Plan Format

Use a compact block like:

```markdown
## FP — <short title>

**Scope:** one concrete task; no unrelated refactor

**Outcome:** what the user should get after implementation

**What to touch:** routes / pages / components / store / API / tests / styles

**Contracts to preserve:** routing, data flow, a11y, responsive, compatibility

**Risks and forks:** what could go wrong or what needs a decision

**Not doing:** what stays out of scope

**Verification:** lint, type-check, unit, e2e, responsive, manual flow

**After coding:** which follow-up skills matter (`rtk-query-review`, `affordance-review`, `pr-finalize`)
```

## Rules

- Plan only by default.
- Prefer repository patterns over idealized rewrites.
- If an API or runtime contract is unclear, name the exact thing that needs confirmation.
- Mention responsive checks whenever UI layout changes.
- Mention follow-up review skills when state, forms, accessibility, or RTK Query are involved.
