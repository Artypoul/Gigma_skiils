---
name: cabinet-screen-ux-pass
description: Refine an existing cabinet or admin screen without breaking the current flow. Use when the user asks to make a page more informative, clearer, or visually stronger, to move deep settings inside the main management surface, or to improve presentation while preserving routes, business logic, and the current block structure unless a structural change is explicitly requested.
---

# Cabinet Screen Ux Pass

## Overview

Inspect the real screen implementation first, then present a short concrete plan before editing. Increase clarity, information density, and visual hierarchy without inventing new backend data or silently changing the screen's structure.

## Workflow

1. Read the actual route and the screen components before proposing anything.
2. Separate three layers in your head:
   - structure: which blocks and routes exist
   - presentation: hierarchy, spacing, badges, density, actions
   - data: which real fields the page already has
3. Before any edit, give a short plan with:
   - what will change
   - what will stay untouched
   - how you will verify the result
4. If the user says `только оформление`, `структуру не менять`, or similar, treat that as a hard constraint.
5. Prefer improving the meaning of existing blocks over adding new ones.
6. When the user asks to bring deep settings inside, move them into the main management surface before proposing a new route, tab, or separate page.
7. After edits, run the narrowest useful check and verify the intended route visually when possible.

## Design Rules

- Reuse the product's existing cabinet patterns before inventing a new one.
- Make the screen answer three questions quickly:
  - what exists now
  - what status it is in
  - what the next action is
- Prefer one strong primary block and supportive secondary blocks over many equal-weight boxes.
- Use badges, meta rows, and short support text to raise informativeness.
- Prefer real status text over decorative filler.
- For mobile, keep the same tasks as desktop, but compress them into title + one supporting line when needed.
- If a route is auth-gated, say so when visual verification is blocked instead of pretending you checked the final state.

## Scope Guardrails

- Do not change business logic, routes, or backend contracts unless the user explicitly asks.
- Do not hardcode fake “advanced settings” data just to make the screen feel richer.
- Do not confuse landing pages with cabinet screens; verify the exact route first.
- Do not hide a structural change inside a “visual tweak”.

## Response Shape

When replying before edits, keep the plan short and concrete. A good default is:

1. what you inspected
2. what you will change
3. what you will not change
4. how you will verify
