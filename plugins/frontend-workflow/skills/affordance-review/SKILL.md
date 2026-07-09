---
name: affordance-review
description: "Review frontend refactors, forms, lists, drag and drop, conditional sections, async hydration, or streaming UI for interaction affordance and hidden regressions. Use before or after splitting forms, moving sections, changing keyboard or pointer behavior, reworking async state, or when the user asks for a UI regression review beyond visual styling alone."
---

# Affordance Review

Review by default. Patch only when the user explicitly asks for fixes.

## Affordance Matrix

Check every relevant item. Mark it `OK`, `risk`, or `missing`.

### 1. Keyboard Activation

- interactive regions are reachable by keyboard when they should be
- Enter and Space behavior is wired intentionally
- nested controls do not cause accidental parent activation

### 2. Pointer Affordance

- clickable zones are actually clickable, not only visually suggestive
- drag and drop, file triggers, image actions, and cards still have a usable pointer target

### 3. Cleanup And Teardown

- object URLs are revoked
- timers are cleared
- subscriptions, streams, and `AbortController` instances are canceled
- reset paths clear every related state slot, not only the visible one

### 4. Async Hydration

- the UI distinguishes loading, success, and error honestly
- save or submit is not enabled from a half-hydrated state
- settled state depends on real success or error signals, not only on `!isLoading`

### 5. Parent And Child Ownership

- if a parent owns the active tab, section, or segment, child reset and validation flows still return control correctly
- child forms do not keep stale hidden state that the parent can no longer see or clear

### 6. CSS Consumer Audit

- renamed or removed class stems are checked in selectors and markup consumers
- hiding or moving one block did not silently strand the styles that another state still depends on

### 7. Layout Invariants

- hiding one child in a flex or grid layout does not break spacing or alignment
- `display: none` or conditional rendering does not leave `space-between`, grid tracks, or `nth-child` selectors pointing at the wrong structure

### 8. Hidden Or Split Forms

For conditional or split forms, verify all five sub-contracts:

- render
- state
- validate
- submit
- visible error reporting

Treat hidden-field validation with no visible feedback as a real bug.

## Form Save Scope

- debounce, abort, and ordering live in the parent orchestrator, not in low-level leaf inputs
- leaf inputs should emit `onChange` synchronously in the same tick
- do not assume request libraries will coalesce rapid saves for you
- when sequencing matters, require explicit abort or `await` logic at the owner level

## Output

Return either:

- a concise matrix with `OK`, `risk`, or `missing` plus file areas, or
- a findings-first `P0` to `P2` report when real regressions exist

Always call out silent failures, especially hidden validation or cleanup bugs. If the change touched layout or styles, mention desktop, tablet, and mobile verification as part of the review.
