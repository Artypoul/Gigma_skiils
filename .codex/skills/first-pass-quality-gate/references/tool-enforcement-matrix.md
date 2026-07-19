# Tool Enforcement Matrix

| Improvement target | Instrumentation | Enforced by |
| --- | --- | --- |
| No tool use before task boundary | Clarification gate and Task Lock | `UserPromptSubmit`, `PreToolUse`, `Stop`, `StartTask` |
| First pass stays on scope | Absolute `scopePaths`, enforced `allowedActions`, parsed patch targets, fail-closed non-Git dirty policy | `PreToolUse`, `PermissionRequest`, `PostToolUse` |
| Project skills remain authoritative | Workflow id/stage, phase Task Locks, narrower write scope, explicit precedence | `StartTask`, `PreToolUse`, skill instructions |
| New user input is reconciled | Context reset plus recorded disposition/note; changed scope requires a fresh Task Lock | `UserPromptSubmit`, `ConfirmContext`, `PreToolUse` |
| Compaction does not erase intent | State snapshot and restore message | `PreCompact`, `PostCompact` |
| Evidence is real and fresh | Exact expected tool, successful result, post-final-write timestamp | `PostToolUse`, `AddEvidence`, `SetGate` |
| PR flow does not deadlock | Pre-publish criteria/gate; `git add`/commit/push/PR are distinct from content writes; push reopens review | `Get-ToolClassification`, `PreToolUse`, `PostToolUse` |
| `$feature` does not need duplicate hooks | Workflow stage and write scope are enforced in the controller; current-review readiness is checked from the same state | `StartTask`, `PostToolUse`, `SetStatus`, `Stop` |
| No false-ready final | Terminal status and readiness problems | `SetStatus`, `Stop` |
| Production identity is stable | Wrapper name, canonical exact-input hash, stable/project ID field hashes | `SetEntityLock`, `PreToolUse` |
| Production requires Art | Latest-prompt, one-shot confirmation; replay and auto-retry blocked | `UserPromptSubmit`, `AuthorizeProduction`, `PreToolUse`, `PostToolUse` |
| Delegation is bounded | User authorization, strict handoff labels, independent parent verification | `AuthorizeDelegation`, `SubagentStart`, `SubagentStop`, `VerifyDelegation` |
| Failed writes do not cascade | Mutation pause until a successful read/validator recovery check | `PostToolUse`, `AcknowledgeWriteRecovery`, `PreToolUse` |
| Auditability without raw prompts | Hashed prompt/session/entity/tool identifiers in telemetry | local state, telemetry JSONL |

Hosted tools and specialized paths that bypass local hooks remain outside the mechanical boundary. The skill and project rules are required there; do not describe hooks as complete enforcement.
