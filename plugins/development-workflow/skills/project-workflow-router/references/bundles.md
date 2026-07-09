# Reusable Skill Bundles

Use these bundles as named starting points. Load the real skill files that exist in the current session/project. Optional missing skills may use a named fallback; configured review gates, CI checks, PR evidence, or deploy gates that are unavailable/stale/queued are blockers, not normal fallbacks.

## context-first

Use for any new thread or resumed project work.

Chain:
`project-context-bootstrap` -> read local `AGENTS.md`/memory/history -> git/PR snapshot -> next safe action.

## feature-ready

Use for meaningful implementation.

Chain:
`project-context-bootstrap` -> `feature` -> local planning skill -> plan review gate -> implementation -> tests/checks -> code review/monster feedback -> local finalization skill.

Ready only after both plan review and post-code review gates are clear or explicitly waived by Art.

## agent-error-check

Use when Art asks to check another agent's work.

Chain:
`project-context-bootstrap` -> thread/PR/git evidence -> findings-first review -> handoff block.

Report-only unless Art explicitly asks to fix.

## pr-fix

Use when fixing an existing PR.

Chain:
`project-context-bootstrap` -> `development-handoff` or GitHub review-comment skill -> patch same branch -> checks -> update PR.

If review comments/checks cannot be read, stop and report the missing evidence before patching.

## frontend-change

Use for UI, forms, responsive, desktop/mobile split.

Chain:
`project-context-bootstrap` -> local `frontend-plan` -> local `affordance-review` when controls/forms are involved -> implementation -> `frontend-safety-check`.

For review/check-up requests, stop after the report. Implement only when Art asks to change code.

## data-flow-change

Use for auth, payment, subscription, webhooks, profile, or load/action changes.

Chain:
`project-context-bootstrap` -> local `flow-debug-checklist` -> local `data-load-review` -> `feature` if implementation is needed.

For payment, auth, webhook, or production-data flows, treat missing contract evidence as blocking.

## website-copy

Use for landing, offer, positioning, CTA, FAQ, SEO, or page copy.

Chain:
`project-context-bootstrap` -> project-specific product context skill if present -> website workflow/router/copy skill -> conversion review/polish.

## merge-deploy-handoff

Use after merged PRs or deploy requests.

Chain:
`project-context-bootstrap` -> `development-handoff` -> verify PR merge/checks -> update base branch -> deploy/runbook only when requested or project rules require it.
