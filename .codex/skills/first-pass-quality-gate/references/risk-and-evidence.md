# Risk And Evidence

Risk is about blast radius, reversibility, and ambiguity.

- `low`: read-only analysis, narrow local edits, no external side effect.
- `medium`: shared code, user-visible artifacts, PR changes, browser automation, generated documents.
- `high`: production, money, identity, migrations, deploys, credentials, irreversible or externally visible writes.

Evidence must be bound to an observed successful non-management tool result, name the expected tool exactly, and be newer than the final write. Do not mark a criterion passed because the agent "looked" or "feels confident".

For PR mode, distinguish pre-publish evidence (`P*`) from final DoneWhen evidence (`C*`). Pre-publish proves the current files are safe to commit/push/open for review. Final evidence may then prove that the PR exists, CI/review completed, and the current diff has no blockers.

Good evidence examples:

- Syntax/parser result for scripts and configs.
- Contract test output for hooks and guard behavior.
- Validator output for JSON, Markdown, document, image, PDF, or spreadsheet artifacts.
- Source-backed report with exact files, lines, commits, thread ids, or URLs.
- Production result only when the typed wrapper returns a stable id/status matching the Entity Lock.
- Delegated result only after the parent independently reads/tests it and records `VerifyDelegation`.

Weak evidence that must not pass acceptance by itself:

- Unrendered visual artifact without screenshot/render check.
- "Probably works" after editing.
- Tool unavailable without recording `partial`, `blocked`, or `unknown`.
- A subagent final answer that the parent has not verified.
- A validator result produced before the latest write.
