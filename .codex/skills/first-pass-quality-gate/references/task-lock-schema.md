# Task Lock Schema

The Task Lock is the first-pass contract. It should be created before mutation and kept current until the final answer.

Required fields:

- `outcome`: one sentence describing the concrete result Art expects.
- `scopePaths`: absolute paths or stable external scopes the agent may touch.
- `outOfScope`: explicit boundaries, especially production, money, security, unrelated refactors, and duplicates.
- `mode`: `report-only`, `local-change`, `pr`, or `production`.
- `risk`: `low`, `medium`, or `high`.
- `completionPolicy`: `deliver-current-state` or `wait-for-required-gates`.
- `workflowId`: `none` or the required workflow/skill chain.
- `workflowStage`: current phase such as `planning`, `implementation`, or `none`.
- `writeScopePaths`: writable subset of `scopePaths`; use it to keep a planning phase plan-only.
- `allowedActions`: an enforced allowlist of `read`, `write`, `execute`, `unscoped-shell`, `validate`, `commit`, `push`, `pr`, `production`, and `delegate`. `unscoped-shell` is never a default, requires `risk: high`, records that command side effects cannot be contained by `writeScopePaths`, and is conservatively tracked as a content write.
- `prePublishWhen`: `P1`, `P2`, etc.; evidence required before PR publication operations.
- `doneWhen`: acceptance criteria; each becomes `C1`, `C2`, etc.

Terminal status:

- `ready`: all required gates passed and each DoneWhen item has passed evidence.
- `partial`: useful work is done, but at least one limitation remains.
- `blocked`: progress requires Art, external state, credentials, unavailable tools, or a real decision.
- `unknown`: outcome cannot be determined from available evidence.

After compaction or new user input, the context gate returns to pending. Record `unchanged` or `status-only` plus a note with `ConfirmContext`; for an extension/replacement, create a fresh Task Lock with `-Continuation`.

A content or external write resets publish, acceptance, self-review, and required review. `git add`, a normal commit/push, and PR lifecycle bookkeeping preserve already verified file evidence; every successful push reopens required review. Evidence used for `ready` must be observed after the latest content/external write. Outside Git, local writes fail closed unless Art explicitly authorized `-AllowDirty`.

For a multi-phase workflow, create a fresh Task Lock with `-Continuation` when the phase changes. `$feature` uses at least `planning` and `implementation`; the planning `writeScopePaths` must not include production code.
