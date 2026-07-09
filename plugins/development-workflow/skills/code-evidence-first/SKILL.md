---
name: code-evidence-first
description: "Clarify the expected deliverable before reading code when a code request is broad, ambiguous, or easy to misread. Use for prompts like 'look at this', 'fix this', 'review this', 'what is happening here', or any code task where it is not yet clear whether the user wants an explanation, root cause, route lookup, review, plan, or fix. Ask one short outcome-focused question first, then inspect the real code with rg and file reads before answering, reviewing, planning, or editing."
---

# Code Evidence First

Start from outcome clarity, then use source truth.

Use this as the stricter intake variant of `read-code-first`, not as its replacement.

## Workflow

1. Identify whether the user already named the expected result: explanation, fix, review, route lookup, root cause, PR-ready patch, deploy check, or another concrete deliverable.
2. If the expected result is broad, missing, or easy to misread, ask one short intake question before implementation. Center it on what the user wants to get from this turn.
3. If the user already gave a precise target, do not ask a duplicate question. Briefly lock the target in your reasoning and continue.
4. Translate the clarified request into likely artifacts: route, component, hook, slice, API client, config reader, test, build file, schema, or log parser.
5. Search first with `rg` or `rg --files`. Prefer exact symbols, paths, error texts, endpoint fragments, and config keys.
6. Open the minimum relevant files and read enough surrounding lines to understand control flow, data flow, ownership, and local patterns.
7. Read both the definition and at least one real usage when behavior depends on context.
8. Only then answer, plan, review, or edit.
9. If the code still does not answer the question, say what was checked, what remains unknown, and what next evidence is needed.

## Intake Question Rules

- Keep the intake short and concrete.
- Prefer one question; use two only when the second materially changes the work.
- Phrase the question around the deliverable, not around abstract process.
- Good examples:
  - "What do you want as the result: a quick answer, a fix in code, or a review?"
  - "Do you need the root cause, a PR fix, or just where this lives?"
  - "Is the priority to repair the behavior or first explain why it behaves this way?"
- Avoid vague prompts like "Tell me more".
- For tiny factual lookups where the user clearly asked for one fact, skip the intake question.

## Search Order

- For routes and navigation, search route constants, router maps, `navigate`, path fragments, and page entrypoints.
- For behavior questions, search the concrete symbol first, then callers, then nearby helpers and tests.
- For runtime, env, and deploy questions, inspect runtime config readers, env types, bootstrap files, and the exact calling code.
- For errors, search the exact error text, code, endpoint, or toast string first.
- For regressions, read adjacent tests before changing behavior when tests exist.
- For PR feedback or review, inspect both the touched file and the contract around it before judging.

## Rules

- Do not answer code questions from memory alone.
- Do not jump into implementation before the expected result is clear.
- Prefer file-backed answers over speculative explanations.
- For simple code facts, inspect the exact file anyway.
- If the user pasted a snippet but local source exists, inspect the surrounding source before concluding when feasible.
- Cite file paths and line references when they materially help the user.
- If the request is not about code, normal behavior is fine.

## Minimum Evidence

Before giving a code-dependent answer, inspect at least one of:

- the defining source file,
- the caller, route, or container that uses it,
- an adjacent test or config file when setup affects behavior,
- or the exact snippet or stack-trace location the user referenced when no wider code is available.
