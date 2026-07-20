---
name: runtime-agent
description: "Implement, debug, or review a GLAIM runtime service, local agent courier, runner, or adapter that uses /api/v2/jobs/claim, /progress, /complete, /session-thread, or managed materials. Use when the task mentions agent lifecycle endpoints, Bearer agent token, claim_token, context_payload, material_manifest, material_access, glaim_managed_chat, job material fetch, runner-hub, Codex/Claude runtime execution, or an agent answering without reading profile/skills."
---

# GLAIM Runtime Agent

Use this skill for the agent-side execution channel. Do not use the frontend chat skill for this path: frontend calls source-chat routes with `X-Source-Secret`; runtime agents call job lifecycle routes with an agent Bearer token.

Read `../../reference/runtime-agent-contract.md` before implementing or reviewing runtime code. It is the compact source of truth for claim -> material fetch -> model -> progress/complete.

## Hard Contract

When `/api/v2/jobs/claim` returns `context_payload.mode == "glaim_managed_chat"`:

1. Do not call the model yet.
2. Read `context_payload.material_manifest.items`.
3. Fetch every `profile:*` ref before the model call.
4. Baseline behavior: fetch every `skill:*` ref before the model call. Optimize to a smaller deterministic subset only when there is tested selector logic; if uncertain, fetch all skills.
5. Fetch through `context_payload.material_access`, not through guessed routes.
6. Send `Authorization: Bearer <agent token>`.
7. Send `X-Claim-Token: <claim.claim_token>`.
8. Build the model context from fetched material `content`, not from manifest titles, summaries, or public search.
9. If any required material fetch fails, fail the job with `material_fetch_failed`; do not guess and do not answer from memory.

`material_manifest` is a catalog, not the skill text. Domain skills such as support or consultant skills are fetched materials; they cannot teach the runtime how to fetch themselves.

## Runtime Flow

1. Claim:
   - `POST /api/v2/jobs/claim`
   - read `id`, `claim_token`, `prompt`, and `context_payload`.
2. If `context_payload.mode != "glaim_managed_chat"`, use the current non-managed path.
3. If managed:
   - fetch required materials with `GET {material_access.path}?ref=<ref>`;
   - use the claim response `claim_token` as `X-Claim-Token`;
   - verify each returned `content_hash` matches the manifest item;
   - keep fetched `content` out of logs.
4. Compose the model input:
   - runtime/system instructions;
   - fetched profile material;
   - fetched skill materials;
   - `context_payload.content` containing the user message.
5. During execution, post progress with the same `X-Claim-Token`.
6. On completion, post `/complete` with:
   - same `X-Claim-Token`;
   - normal result or failure;
   - `data.fetched_material_refs`, `data.fetched_material_hashes`, and `data.material_fetch_count`.

## Failure Rules

- Missing `context_payload.material_access` in managed mode -> `material_fetch_failed`.
- Empty or malformed manifest in managed mode -> `material_fetch_failed`.
- Any profile fetch failure -> `material_fetch_failed`.
- Skill fetch failure in baseline-all mode -> `material_fetch_failed`.
- Material hash mismatch -> `material_fetch_failed`.
- Zero fetched materials for managed mode -> protocol violation; do not call the model.

Never fall back to public web search, guessed product facts, or manifest titles when managed materials fail.

## Review Checklist

- Runtime fetches materials before the first LLM/Codex/Claude call.
- Runtime always fetches `profile:*`.
- Runtime either fetches all `skill:*` refs or has deterministic, tested selector logic.
- Runtime uses `claim.claim_token` for `X-Claim-Token`.
- Runtime records fetched refs/hashes in progress or complete `data`, without logging material contents.
- Tests prove material fetch happened before model invocation.
- Production logs for a managed job show `GET /api/v2/jobs/{id}/materials` before `/complete`.

## Common Mistakes

- Treating `context_payload.content` as the full prompt context.
- Treating `material_manifest.items[].title` or `summary` as enough to answer.
- Putting material-fetch instructions only in a model prompt.
- Looking for this protocol inside domain skills. The runtime must know the GLAIM protocol before it can load those skills.
- Mixing frontend source-chat auth with agent lifecycle auth.
