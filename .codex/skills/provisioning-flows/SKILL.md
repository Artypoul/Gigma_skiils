---
name: provisioning-flows
description: "Design, implement, review, or explain safe creation and synchronization of external entities: get-or-create, upsert, JIT provisioning, event-driven creation, entitlement assignment, and desired-state reconciliation. Use when a task asks how to create a user, subscription, server, group, order, or any external record only if it is missing; how to avoid duplicates; or how a payment/subscription should grant access."
---

# Provisioning flows

Use this skill to design an entity lifecycle across systems. Keep entity creation separate from access entitlement.

## Workflow

1. Name the entity, source system, target system, and immutable external key. Do not use a mutable contact field, such as a phone number or email address, as the primary identity key.
2. Choose one creation model:
   - manual or pre-provisioned;
   - JIT / get-or-create on first use;
   - creation after a confirmed event;
   - upsert during synchronization;
   - desired-state reconciliation.
3. Specify exactly what proves absence. Create only after a canonical lookup endpoint returns a confirmed `404` or equivalent authoritative “not found” result; a possibly stale list response is not sufficient.
4. Specify idempotency: unique external key, lock or idempotency key, and how concurrent requests converge on one record.
5. Specify failure behaviour. Network failures, timeouts, `401`, and `5xx` are unknown outcomes, not proof that an entity is absent.
6. Specify the entitlement source separately. Prefer a confirmed, scoped subscription or explicit policy record; do not infer paid access from a payment-history row alone.
7. Add reconciliation so the target system is repaired from the source of truth after delayed events or partial failures.
8. Verify the happy path, retry path, duplicate request, missing entity, expired entitlement, and a cancelled-but-still-paid entitlement when applicable.

## Decision rules

- Use **get-or-create** when the entity is needed only on demand. Read first; create only after definite absence.
- Use **upsert** when the source regularly provides the entity’s current fields and the target should mirror them.
- Use **event-driven creation** only when the event has a verifiable identity and replay-safe handling.
- Use **reconciliation** when events can be late, duplicated, lost, or processed partially.
- Keep a paid entitlement valid through the paid period even if auto-renewal was cancelled.
- Never let a temporary upstream error create a duplicate entity or grant paid access.
- Treat contact details as secondary lookup attributes. Store and use the source system's immutable ID for matching and idempotency.

## Output for a design or implementation task

State, in plain language:

- source of truth;
- stable identity key;
- create/update/read rules;
- idempotency and concurrency rule;
- entitlement rule and end-of-access rule;
- retry and reconciliation rule;
- evidence or tests that prove the flow.

For a simple non-technical explanation, read [references/plain-language-guide.md](references/plain-language-guide.md).
