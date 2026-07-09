---
name: project-workflow-router
description: Load project context, then route multi-step or product-sensitive repository work to the right project skills. Use for implementation, code review, PR fixes/finalization, merge/deploy/handoff, frontend/UI, data/API, website copy, context repair, or skill-bundle design when more than one workflow may apply. Do not trigger for tiny self-contained questions, single-command checks, or simple context snapshots; use project-context-bootstrap alone for those.
---

# Project Workflow Router

Use this skill to decide which workflow chain to run. It is a router, not a replacement for the selected skills.

## Always Start

1. Use `project-context-bootstrap` first when it is available.
2. Read the project-local `AGENTS.md` and memory files before choosing a workflow.
3. Prefer local project skills over generic global skills.
4. If a named skill is available, read its `SKILL.md` before acting.
5. If the user asked for review, audit, check-up, консилиум, plan-only, or read-only work, end with a report. Do not edit, commit, push, create PRs, merge, or deploy.

## Route Matrix

| User/task signal | Skill chain |
| --- | --- |
| "сделай", "реализуй", "добавь", "измени" when the user is asking for code/product changes; multi-file feature, API/UI/data changes | `project-context-bootstrap` -> `feature` -> project plan/review skills -> implementation -> tests/checks -> code review/monster feedback -> finalization |
| "ревью", "чек ап", "ошибки агента", "посмотри PR" | `project-context-bootstrap` -> code-review stance -> local review skills -> findings-first report |
| "смерджил", "merged", "handoff", "чини в PR", "prod ready", deploy state | `project-context-bootstrap` -> `development-handoff` when available |
| Frontend/UI/forms/responsive/cabinet changes | `project-context-bootstrap` -> local `frontend-plan` or equivalent -> local `frontend-safety-check`/`affordance-review` |
| Auth/payment/subscription/webhook/user flow | `project-context-bootstrap` -> local flow/data review skills -> `feature` if implementation is needed |
| Website meanings, landing, offer, CTA, page copy | `project-context-bootstrap` -> project-specific context skill if present -> website/copy skill |
| GitHub review comments or failing checks | `project-context-bootstrap` -> GitHub comment/check skill when available -> fix same PR |
| PR creation/finalization | `project-context-bootstrap` -> local `pr-finalize` or equivalent |
| Unknown or product-sensitive choice | `project-context-bootstrap` -> ask one concrete product question before edits |

See `references/bundles.md` for reusable named bundles.

## Output

Before substantial work, state:

```text
SKILL ROUTE
Context:
Selected chain:
Why:
Mode: report-only | changes-requested
Blocked by:
Next:
```

Keep it short. Once the route is clear, execute the selected workflow instead of stopping at a plan.

## Safety

- Do not use this router to skip review gates.
- If project/global rules configure a review gate and the review skill/tool/check is unavailable, stale, or queued, report it as `Blocked by`, not as a normal fallback.
- Do not create a new PR if the user asked to fix the existing one.
- Do not broaden product scope silently; ask when several product choices are valid.
- Do not mark a task ready while CI/review/deploy evidence is unknown.
