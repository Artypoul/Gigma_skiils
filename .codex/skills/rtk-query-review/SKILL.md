---
name: rtk-query-review
description: "Review RTK Query changes for cache tags, invalidation, response transforms, optimistic updates, request sequencing, auth and reauth flow, duplicate transport layers, and type safety. Use after edits to API slices, base query setup, auth, caching, or when the user asks for RTK Query review or a diagnosis of stale or duplicated data behavior."
---

# Rtk Query Review

Review by default. Do not patch code unless the user explicitly asks for fixes.

## Workflow

1. Inspect the base API slice, store integration, touched `*.api.*` files, at least one caller, and nearby tests.
2. Map the changed surface:
   - query endpoints
   - mutation endpoints
   - auth or reauth path
   - cache update path
   - manual selectors or helper utilities
3. Produce a findings-first report. Use `P0`, `P1`, and `P2` with file and line evidence when possible.

## What To Check

### 1. Tag Taxonomy

- `tagTypes` cover the affected entities
- `providesTags` and `invalidatesTags` line up across list, detail, and mutation endpoints
- mutations do not leave obvious stale cache paths behind

### 2. Query And Mutation Contracts

- endpoint args are stable and serializable
- `transformResponse` and `transformErrorResponse` preserve the real runtime shape
- manual cache updates match the same keys that readers consume
- pagination, filters, and list/detail cache keys do not drift apart silently

### 3. Ordering, Cancellation, And Duplication

- when request order matters, callers use explicit sequencing such as `await unwrap()` or abort logic
- quick consecutive `trigger()` calls are not treated as if RTK Query will coalesce them
- duplicate transports are avoided when the repo already has one API layer for the same concern

### 4. Auth And Reauth

- base query or wrapper logic handles auth refresh consistently
- RTK Query and any parallel Axios/fetch layer do not fight each other on 401 or 403 behavior
- endpoint code does not bypass the established auth path without reason

### 5. Type Safety

- avoid `response: any` or broad `any` spreads when a raw payload type or `unknown` plus narrowing is possible
- selectors and callers do not assume nullable data is always present
- optimistic update code does not hide broken shapes behind casts

### 6. Optimistic And Manual Cache Flows

- optimistic updates have rollback or invalidation coverage
- manual cache writes match the eventual server truth
- retries and duplicate submissions do not create inconsistent local state

## Output Format

For each finding, include:

- severity
- file and approximate line
- the concrete risk
- one short fix direction

If you find no issues, say so clearly and mention any test gaps or residual risk.
