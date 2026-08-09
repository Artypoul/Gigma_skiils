# Tool Enforcement Matrix

Enforcement has two tiers (policy 0.4.x). **Advisory mode** — no Task Lock (or state missing/terminal): tools run with a one-time warning, `production-shell`/`external-write` are hard-denied, unclassified shell escalates to `ask`, and rows below marked "strict" are NOT mechanically enforced. **Strict mode** — an active Task Lock exists: the full matrix applies. A state file that exists but cannot be read fails closed.


| Improvement target | Instrumentation | Enforced by |
| --- | --- | --- |
| Task boundary (advisory before a lock) | Without a Task Lock tools are allowed with a one-time advisory warning; production/external writes stay denied; unclassified shell escalates to `ask`; one soft stop-block fires if tools ran before the clarification step | `UserPromptSubmit`, `PreToolUse`, `Stop`, `StartTask` |
| First pass stays on scope | OS-aware absolute `scopePaths`, enforced `allowedActions`, parsed source/move targets, reparse-component rejection, fail-closed non-Git dirty policy | `PreToolUse`, `PermissionRequest`, `PostToolUse` |
| Task Lock bootstrap cannot deadlock or run a look-alike | Canonical one-line plugin-root invocation for PowerShell and POSIX `pwsh`; absolute/relative look-alikes, chained commands and extra subexpressions rejected | `Test-IsQualityControlCommand`, `PreToolUse` |
| Shell/API mutations do not masquerade as reads | One command per shell call (strict), safe Git/GitHub/kubectl/curl allowlists, unknown-shell fail-closed classification in strict mode and `ask` escalation in advisory mode, high-risk explicit `unscoped-shell` always tracked as a content write, scoped explicit-file staging (including exact `--chmod`) plus staged-index commit check, destructive push/local Git denial, curl and `gh api` mutation rules | `Get-ToolClassification`, `Get-RequiredAction`, `Get-GitAddFiles`, `Get-StagedFiles`, `StartTask`, `PreToolUse`, `PostToolUse` |
| Project skills remain authoritative | Workflow id/stage, phase Task Locks, narrower write scope, explicit precedence | `StartTask`, `PreToolUse`, skill instructions |
| New user input is reconciled | Context reset plus recorded disposition/note; changed scope requires a fresh Task Lock | `UserPromptSubmit`, `ConfirmContext`, `PreToolUse` |
| Compaction does not erase intent | State snapshot and restore message | `PreCompact`, `PostCompact` |
| Evidence is real and fresh | Exact expected tool, successful result, post-final-write timestamp | `PostToolUse`, `AddEvidence`, `SetGate` |
| PR flow does not deadlock or cross branches | Pre-publish criteria/gate; scoped stage/commit; explicit current-branch normal push; push reopens review | `Get-ToolClassification`, `Get-StagedFiles`, `Test-IsSafeGitPushCommand`, `PreToolUse`, `PostToolUse` |
| `$feature` does not need duplicate hooks | Strict mode only: workflow stage and write scope are enforced in the controller; current-review readiness is checked from the same state. In advisory mode `$feature` discipline is textual | `StartTask`, `PostToolUse`, `SetStatus`, `Stop` |
| No false-ready final | Strict mode only: terminal status and readiness problems are enforced at `Stop`. Advisory mode does not block completion | `SetStatus`, `Stop` |
| Production identity is stable | Wrapper name, canonical exact-input hash, stable/project ID field hashes | `SetEntityLock`, `PreToolUse` |
| Production requires Art | Latest-prompt positive confirmation with explicit negation guard; replay and auto-retry blocked | `UserPromptSubmit`, `AuthorizeProduction`, `PreToolUse`, `PostToolUse` |
| Delegation is bounded | Latest-prompt turn-bound user authorization, strict handoff labels, independent parent verification | `UserPromptSubmit`, `AuthorizeDelegation`, `SubagentStart`, `SubagentStop`, `VerifyDelegation` |
| Failed writes do not cascade | Mutation pause until a successful read/validator recovery check | `PostToolUse`, `AcknowledgeWriteRecovery`, `PreToolUse` |
| Auditability without raw prompts | Hashed prompt/session/entity/tool identifiers in telemetry | local state, telemetry JSONL |

Hosted tools and specialized paths that bypass local hooks remain outside the mechanical boundary. The skill and project rules are required there; do not describe hooks as complete enforcement.
