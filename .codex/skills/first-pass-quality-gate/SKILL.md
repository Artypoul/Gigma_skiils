---
name: first-pass-quality-gate
description: Use for Codex or Claude agent tasks that involve tools, multiple steps, code changes, documents, artifacts, PRs, production data, external writes, delegation, or any user-visible deliverable. It turns the first pass into an explicit Task Lock with gates for context, scope, risk, evidence, review, production authorization, and final status.
---

# First-Pass Quality Gate

## Required Use

Use this skill before the first tool call for any non-trivial task: file inspection, code change, artifact creation, PR work, production/external mutation, connector write, browser automation, document generation, or multi-step analysis.

Skip only for a direct answer that needs no tools, no current state, and no persistent artifact.

The hook recognizes conservative stable trivial prompts (for example, `2 + 2`, a greeting, or a timeless definition) and lets the agent answer them without a Task Lock only while no tool has run. Paths, current/latest facts, task verbs, and any tool call keep the normal clarification/Task Lock boundary.

Hook execution requires PowerShell 7 (`pwsh`) on `PATH`. If the runtime does not provide it, report mechanical enforcement as unavailable and do not claim that Task Lock hooks are active.

Run every controller action as its own one-line shell tool call. The hook recognizes the canonical root expression shown below without allowing chained commands.

In a plugin runtime, use the real plugin root. When the shell tool is POSIX Bash, invoke the same action through `pwsh`. Use `CLAUDE_PLUGIN_ROOT` instead of `PLUGIN_ROOT` in a Claude plugin runtime:

```bash
pwsh -NoProfile -File "$PLUGIN_ROOT/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome "<expected result>" -Scope "<absolute scope>" -WriteScope "<absolute writable scope>" -Mode local-change -Risk medium -CompletionPolicy deliver-current-state -Workflow none -WorkflowStage none -AllowedActions "read~~write~~execute~~validate" -DoneWhen "criterion 1~~criterion 2"
```

In a standalone `.codex/skills` mirror there is no plugin-root environment variable. Resolve the absolute directory containing this loaded `SKILL.md` from the skill catalog, and invoke its controller directly. Replace the placeholder with that existing directory; do not create an alias, symlink, copy, or alternate route:

```powershell
& "<absolute loaded skill directory>/scripts/quality-control.ps1" -Action StartTask -Outcome "<expected result>" -Scope "<absolute scope>" -WriteScope "<absolute writable scope>" -Mode local-change -Risk medium -CompletionPolicy deliver-current-state -Workflow none -WorkflowStage none -AllowedActions "read~~write~~execute~~validate" -DoneWhen "criterion 1~~criterion 2"
```

```bash
pwsh -NoProfile -File "<absolute loaded skill directory>/scripts/quality-control.ps1" -Action StartTask -Outcome "<expected result>" -Scope "<absolute scope>" -WriteScope "<absolute writable scope>" -Mode local-change -Risk medium -CompletionPolicy deliver-current-state -Workflow none -WorkflowStage none -AllowedActions "read~~write~~execute~~validate" -DoneWhen "criterion 1~~criterion 2"
```

The absolute path above resolves the mirror controller when compatible hooks have already initialized task state. A standalone mirror does not activate lifecycle hooks by itself; without those hooks, follow the protocol manually and report mechanical enforcement as unavailable instead of claiming that Task Lock state or pre-tool blocking is active.

## First-Pass Protocol

1. Ask Art one concise clarification question when a new task is missing the expected outcome, absolute scope, completion criteria, or a material product choice. If all of those are already explicit and higher-priority project rules permit skipping the question, use `-FullySpecified -SpecificationBasis "<why the current prompt is complete>"`; the controller stores only its hash for audit. If the message is an answer or continuation, continue.
2. Create a Task Lock before mutation. Use `-AllowDirty` only when Art explicitly authorized edits in a non-Git scope or an intentional dirty overlap:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome "<expected result>" -Scope "<absolute scope>" -WriteScope "<absolute writable scope>" -Mode local-change -Risk medium -CompletionPolicy deliver-current-state -Workflow none -WorkflowStage none -AllowedActions "read~~write~~execute~~validate" -DoneWhen "criterion 1~~criterion 2"
```

`execute` covers commands the classifier understands as scoped execution. An unknown shell command fails closed by default. Add `unscoped-shell` only when the user explicitly authorized a necessary known CLI, set `Risk high`, and state that its side effects cannot be mechanically contained by `WriteScope`; the controller conservatively records every such call as a content write and invalidates stale gates. Never use it for production, merge, deploy, force-push, money, or account/data mutation.

For an already complete new request, add the audited shortcut to that same command:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -FullySpecified -SpecificationBasis "Current prompt fixes outcome, scope, and DoneWhen with no unresolved product choice." -Outcome "<expected result>" -Scope "<absolute scope>" -WriteScope "<absolute writable scope>" -Mode local-change -Risk medium -CompletionPolicy deliver-current-state -Workflow none -WorkflowStage none -AllowedActions "read~~write~~execute~~validate" -DoneWhen "criterion 1~~criterion 2"
```

3. Confirm context after every new user message, resume, or compaction:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action ConfirmContext -ContextDisposition unchanged -ContextNote "<why the Task Lock still matches>"
```

If the message extends or replaces the requested outcome, create a fresh Task Lock with `-Continuation` instead of confirming unchanged context.

4. Run the smallest real validators that prove each DoneWhen criterion. Every passed item must use a successful non-management tool result produced after the latest write and name that tool exactly:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action AddEvidence -CriterionId C1 -Validator "contract-test" -EvidenceStatus passed -Subject "<file, URL, command, or artifact>" -ExpectedToolName Bash
```

5. For local/report work, pass acceptance then selfReview. For PR work, record separate `PrePublishWhen` criteria, pass publish then selfReview before `commit`/`push`/PR operations, and pass final acceptance plus required review before `ready`. A later content/external write resets these gates; VCS bookkeeping does not, while every new push reopens required review.
6. Finish with an explicit terminal status: ready, partial, blocked, or unknown. Do not present active work as complete.

## Modes

- `report-only`: read, inspect, and report. No edits or external writes.
- `local-change`: local file edits and local validation.
- `pr`: local edits plus normal branch commit/push and PR create/edit/comment/review when Art asked for PR work. Use `PrePublishWhen`; merge and force-push are not included.
- `production`: any live/external/entity mutation. Requires Entity Lock and explicit user confirmation.

## Production Rule

Never do production, merge, deploy, force-push, money, account, or non-PR external-entity mutations through raw shell commands. Normal PR lifecycle operations are dev workflow in `pr` mode; merge/deploy remain production. Register the exact typed production tool input and stable ID fields, then wait for Art's confirmation phrase in the latest prompt, for example:

```text
Подтверждаю выполнение в production.
```

Then run:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action SetEntityLock -EntityType "<type>" -StableId "<stable id>" -StableIdField "<input.id.path>" -ProjectId "<project>" -ProjectIdField "<input.project.path>" -Environment production -Intent write -WrapperToolName "<mcp_or_app_tool>" -ExpectedToolInputJson '<exact JSON arguments>' -ExpectedBeforeHash "<before>" -ChangeHash "<change>"
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action ConfirmContext -ContextDisposition unchanged -ContextNote "Exact entity and change remain unchanged."
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action AuthorizeProduction
```

Authorization is one-shot. A changed input, different stable ID, second call, failed/unknown outcome, or later user prompt requires a new lock/confirmation cycle; never auto-retry.

## Delegation Rule

Delegation requires explicit user authorization and `delegate` in `AllowedActions`. After the subagent returns, run an independent parent read/test, then record verification before any mutation or `ready` status:

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action AuthorizeDelegation -DelegationOutcome "<bounded outcome>" -DelegationScope "<bounded scope>"
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action VerifyDelegation -DelegationEvidence "<what the parent independently checked>"
```

## Workflow Compatibility

This skill is an enforcement envelope, not a replacement for project-local skills. Apply precedence as: user/safety authority, nearest project rules and project skills, selected workflow skill, then generic first-pass defaults. Never weaken a stricter gate.

For `$feature`, use phase Task Locks:

- `planning`: repository `Scope`, plan-only `WriteScope`, `Workflow feature`, `WorkflowStage planning`, pre-publish plan checks, and final evidence for the published planning PR/review.
- `implementation`: a fresh `StartTask -Continuation`, approved implementation `WriteScope`, `WorkflowStage implementation`, tests/diff checks before publication, and final evidence/review for the current code diff.

One global clarification answer satisfies `$feature` too; do not ask the same question twice. A report that a PR was merged never authorizes deploy by itself.

The quality controller is the canonical `$feature` enforcement path when this plugin is active: a successful push reopens the required review gate, and `ready` remains blocked until the current review passes. Do not register a second watch/turnstile pair for the same session; legacy global feature hooks are optional compatibility helpers, not a prerequisite for this plugin.

## Status Commands

```powershell
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action SetGate -Gate publish -GateStatus passed
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action SetGate -Gate selfReview -GateStatus passed
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action SetGate -Gate acceptance -GateStatus passed
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action SetStatus -FinalStatus ready
& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action ShowStatus
```

For partial, blocked, or unknown, include `-Reason`, at least one `-Limitations` item, and `-NextAction`. After a failed write, inspect current state and run `AcknowledgeWriteRecovery` before another mutation.

## References

- `references/task-lock-schema.md`: field contract for Task Lock and terminal state.
- `references/risk-and-evidence.md`: how to choose risk, validators, and evidence quality.
- `references/tool-enforcement-matrix.md`: which hooks and scripts enforce each improvement.
