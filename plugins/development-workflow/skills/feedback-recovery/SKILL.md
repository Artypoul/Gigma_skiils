---
name: feedback-recovery
description: "Recover after wrong-direction user feedback in coding, design-transfer, review, or skill work. Use when the user says `не то`, `не туда`, `stop`, `wrong`, `off-spec`, `not from the design`, `not pixel-perfect`, `nothing changed`, `you are lying`, or similar, and the agent must stop, re-read the latest request, lock the source of truth, inspect git/workspace evidence, and ship only the smallest verified correction."
---

# Feedback Recovery

Treat this skill as a recovery protocol for the current agent. Your job is not to defend the old path. Your job is to stop drift, re-anchor to the active source of truth, and produce one verified correction.

## Agent Posture

When this skill triggers:

- assume the previous implementation path may be wrong;
- treat the newest user message as higher priority than your memory of the thread;
- do not explain at length why the old decision seemed reasonable;
- do not widen scope in order to "improve" the complained-about area;
- prefer one small proved fix over a larger redesign.

## Immediate Response

Do this immediately when the user says the result is wrong:

1. Stop the current implementation path.
2. Do not keep refactoring, broadening scope, or stacking new ideas on top of the complained-about change.
3. Acknowledge the concrete mismatch in one or two plain sentences.
4. Re-read the latest user message and treat it as the active task.
5. If the work lives in a git repo, inspect current evidence before editing:

```bash
git status --short --branch
git diff --stat
git log --oneline --decorate -5
```

If the user said `stop`, `pause`, `оставь`, or the equivalent, stop immediately and do not continue the workflow.

## Lock The Source Of Truth

Before touching files again, decide which artifact actually wins.

Use this order unless the user explicitly overrides it:

1. the latest user instruction in the current turn;
2. the exact screenshot, crop, or failing behavior the user pointed at;
3. the named design/source artifact: Figma, donor, PR comment, contract doc, or live reference;
4. the current local implementation.

If two sources conflict and the winner is not obvious, ask one concrete question before editing.

Write a tiny recovery map for yourself:

```text
scope | judged state | winning source | exact delta | next verification
```

Do not silently blend Figma, donor, screenshots, and local code. If you intentionally borrow behavior from one source and visuals from another, state that explicitly.

## Diagnose The Failure

Classify the complaint before coding:

- layout or spacing;
- asset or provenance;
- behavior or affordance;
- copy/content;
- workflow/process;
- git/branch/PR state.

Then identify whether the miss came from:

- wrong source of truth;
- approximation instead of evidence;
- missing breakpoint check;
- dead interaction;
- compensating hack that moved the bug elsewhere;
- overclaiming `done` before verification;
- too many unrelated local changes in one pass.

State the diagnosis briefly. Do not argue with the complaint.

## Recovery Rules

Make the smallest reversible correction that resolves the complained-about delta.

Rules:

- prefer local fixes over page-wide or app-wide compensating hacks;
- do not "balance" one visual bug by moving unrelated blocks;
- do not keep unrelated edits in the same recovery pass;
- do not claim `fixed`, `done`, `ready`, or `pixel-perfect` before rerunning the affected checks;
- if the wrong change was already pushed, offer the real choice: revert the bad commit or fix forward on the same branch.

When the failure came from a broad dirty worktree, isolate the current-task files before continuing. If isolation is impossible, report that blocker explicitly.

## Verify Before Claiming Recovery

Choose verification that matches the complaint:

- visual issue: compare the complained-about width plus at least one adjacent breakpoint;
- behavior issue: prove the state actually changes, not just the markup;
- asset issue: prove provenance or file identity, not visual similarity alone;
- PR/review issue: re-read comments, CI state, and latest branch evidence after the patch;
- copy/content issue: compare exact strings against the approved source.

If the proof is incomplete, use an honest status such as `needs-polish`, `local-fix-only`, `manual-check-needed`, or `blocked`.

## Final Recovery Report

End with five short facts:

- exact mistake fixed;
- winning source of truth;
- files changed;
- verification performed;
- whether the fix is local only or already pushed.

Do not end with vague reassurance. State the current risk plainly.
