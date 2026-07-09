---
name: read-code-first
description: "Read the actual code before answering any code-dependent request. Use for bug reports, route or file lookups, code review, feature work, refactors, stack traces, architecture questions, config or env questions, or any task where the answer should come from source files rather than memory. First inspect relevant files, symbols, callers, tests, or config with rg and file reads, then answer, review, plan, or edit."
---

# Read Code First

Inspect source truth before answering.

## Workflow

1. If the request is broad or ambiguous enough that the expected deliverable is unclear, ask one short question about the result or switch to the stricter `code-evidence-first` flow.
2. If the user already named the exact result, do not ask a duplicate question. Briefly lock the target in your own reasoning and continue.
3. Translate the request into likely artifacts: route, component, hook, class, function, API slice, config reader, test, build file, schema, or log parser.
4. Search first with `rg` or `rg --files`. Prefer exact symbols, paths, route fragments, error codes, and config keys over broad reads.
5. Open the minimum relevant files and read enough surrounding lines to understand control flow, data flow, and ownership.
6. Read both the definition and at least one real usage when behavior depends on context.
7. Only then answer, plan, review, or edit.
8. If the code still does not answer the question, say what was checked and what remains unknown.

## Clarify The Result

- Keep the clarification short and outcome-focused.
- Use the stricter `code-evidence-first` skill when ambiguity is material enough to change the work.
- Prefer one concrete question such as "What do you want as the result: a quick answer, a fix, or a review?"
- Avoid vague prompts like "Tell me more".
- For tiny factual lookups where the expected output is obvious, skip the clarification.

## Search Order

- For routes and navigation, search route constants, router maps, `navigate`, and page paths.
- For behavior questions, search the concrete symbol first, then its callers, then adjacent helpers.
- For runtime, env, and deploy questions, inspect config readers, env type files, runtime bootstrap, and the calling code.
- For errors and stack traces, search the exact message, code, or endpoint string first.
- For regressions, read adjacent tests before changing behavior when tests exist.
- For unfamiliar subsystems, prefer primary files over summaries or history notes.

## Rules

- Do not answer code questions from memory alone.
- Do not skip the outcome clarification when the request can reasonably mean different kinds of work.
- Prefer file-backed answers over speculative explanations.
- For simple code facts, inspect the exact file anyway.
- If the user pasted a snippet but a local codebase exists, inspect the surrounding source before concluding when feasible.
- Cite file paths and line references when they materially help the user.
- If the request is not about code, normal behavior is fine.

## Minimum Evidence

Before giving a code-dependent answer, inspect at least one of:

- the defining source file,
- the caller, route, or container that uses it,
- an adjacent test or config file when setup affects behavior,
- or the exact snippet or stack-trace location the user referenced when no wider code is available.
