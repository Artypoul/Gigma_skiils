---
name: agent-session-execution
description: "Use for a multi-step task that needs explicit progress, safe action boundaries, waiting on real external work, or a clear completed/blocked state. Classify the action, track one active step, communicate material progress, and finish only with verified completion or a concrete blocker."
---

# Agent Session Execution

Use this skill to keep a long task coherent without inventing background work or asking for
permission to perform ordinary reversible steps.

## Session Flow

1. Classify the request: assessment-only, reversible local work, externally visible work, or
   destructive/irreversible work.
2. For work with several meaningful steps, keep a short task list with one active step. Update it
   as evidence changes; do not create a tracker for a trivial request.
3. Tell the user the immediate action before using tools, then give concise updates only when a
   result changes the next decision.
4. Perform reversible work that is in scope. Ask before external publication, destructive changes,
   or an unresolved product choice.
5. Use a monitor, scheduler, worktree, task tracker, or subagent only when that capability exists
   and the user or selected workflow authorizes it.
6. Treat a failed, denied, queued, or unknown tool result as evidence, not success. Do not retry an
   external side effect automatically when its outcome is unknown.
7. In the final response, restate material findings rather than relying on interim updates.

## Boundaries

- Repository-specific PR, worktree, and deploy rules belong to the project workflow skills.
- Do not claim that a task continues after the turn unless a real monitor or schedule was started.
- Read `references/session-state.md` when waiting, monitoring, or action authority is material.
