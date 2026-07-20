# GLAIM runtime agent contract

This contract is for the agent-side runtime service: local courier, runner-hub,
Codex/Claude adapter, SSH runner, or any process that claims jobs and produces
progress/complete events.

It is not the frontend source-chat contract. Frontend clients use
`/api/v2/sources/{source}/chat/*` and `X-Source-Secret`. Runtime agents use
`/api/v2/jobs/*` and `Authorization: Bearer <agent_token>`.

## Claim response fields

`POST /api/v2/jobs/claim` returns the runtime work item.

Required fields for the material protocol:

```text
id                job id
claim_token       one-time/claim-scoped token for this owned job
prompt            user task
context_payload   optional runtime context from GLAIM
```

When `context_payload.mode == "glaim_managed_chat"`, the prompt does not contain
full profile or skill bodies. It contains a catalog and a material endpoint:

```text
context_payload.material_manifest.items[]
context_payload.material_access
```

`material_manifest` is not enough to answer. It is only a list of refs and
hashes that the runtime must fetch before calling the model.

## Mandatory managed-material flow

For every claimed job:

1. Read `claim.context_payload`.
2. If `context_payload.mode != "glaim_managed_chat"`, continue with the normal
   non-managed path.
3. If `context_payload.mode == "glaim_managed_chat"`, stop before any model
   call.
4. Read `context_payload.material_manifest.items`.
5. Fetch all `profile:*` refs.
6. Baseline: fetch all `skill:*` refs.
7. Only optimize skill selection after adding deterministic selector tests; if
   the selector is uncertain, fetch all skill refs.
8. Build the model context from fetched material `content`.
9. Call the model only after material fetch succeeds.
10. Post progress/complete with the same `X-Claim-Token`.

## Material fetch request

Use the endpoint from `context_payload.material_access`:

```http
GET /api/v2/jobs/{job_id}/materials?ref={material_ref}
Authorization: Bearer <agent_token>
X-Claim-Token: <claim.claim_token>
Accept: application/json
```

Do not invent a route. Do not use source-chat token. Do not omit
`X-Claim-Token`: it is the value returned by the same `/jobs/claim` response.

Expected response:

```json
{
  "ref": "skill:vps-support:vps-service-facts",
  "kind": "skill",
  "title": "Карта фактов сервиса Твой ВПС",
  "content": "...full material body...",
  "content_hash": "sha256..."
}
```

The backend verifies ownership and material hash, but the runtime should still
compare returned `content_hash` to the matching manifest item before using the
content.

## Model context assembly

Recommended order:

```text
[RUNTIME SYSTEM INSTRUCTIONS]
...

[GLAIM FETCHED PROFILE]
ref: profile:...
title: ...
content:
...

[GLAIM FETCHED SKILL]
ref: skill:...
title: ...
content:
...

[GLAIM CLAIM CONTENT]
context_payload.content
```

Never log full fetched material content. It may contain private profile memory,
instructions, or business context. It is safe to log refs and hashes.

## Failure behavior

Fail before model invocation with `material_fetch_failed` when:

- managed mode has no `material_access`;
- manifest is missing or malformed;
- no profile material can be fetched;
- a required skill material cannot be fetched;
- returned `content_hash` differs from manifest hash;
- zero materials were fetched for a managed job.

Completion failure shape:

```http
POST /api/v2/jobs/{job_id}/complete
Authorization: Bearer <agent_token>
X-Claim-Token: <claim.claim_token>
Content-Type: application/json

{
  "status": "failed",
  "error": "material_fetch_failed",
  "data": {
    "error_code": "material_fetch_failed",
    "failed_ref": "skill:...",
    "fetched_material_refs": ["profile:..."],
    "fetched_material_hashes": {"profile:...": "sha256..."},
    "material_fetch_count": 1
  }
}
```

Do not answer from memory, public search, or manifest titles after a material
fetch failure.

## Success telemetry

On successful managed jobs, include material evidence without content:

```json
{
  "data": {
    "fetched_material_refs": [
      "profile:...",
      "skill:vps-support:vps-service-facts"
    ],
    "fetched_material_hashes": {
      "profile:...": "sha256...",
      "skill:vps-support:vps-service-facts": "sha256..."
    },
    "material_fetch_count": 2
  }
}
```

This lets reviewers prove that the runtime used the GLAIM materials instead of
guessing.

## Pseudocode

```python
claim = post_claim(agent_token)
payload = claim.get("context_payload") or {}

if payload.get("mode") == "glaim_managed_chat":
    manifest = payload["material_manifest"]
    access = payload["material_access"]
    items = manifest["items"]

    profile_refs = [i["ref"] for i in items if i["kind"] == "profile"]
    skill_refs = [i["ref"] for i in items if i["kind"] == "skill"]
    required_refs = profile_refs + skill_refs

    if not profile_refs:
        fail_job("material_fetch_failed")

    materials = []
    for ref in required_refs:
        material = get_material(
            path=access["path"],
            ref=ref,
            bearer_token=agent_token,
            claim_token=claim["claim_token"],
        )
        assert_hash_matches_manifest(material, items)
        materials.append(material)

    if not materials:
        fail_job("material_fetch_failed")

    model_context = build_context(payload["content"], materials)
else:
    model_context = payload.get("content") or claim["prompt"]

result = call_model(model_context)
complete_job(result, claim_token=claim["claim_token"], fetched_materials=materials)
```

## Tests to require

- Managed claim with one profile and two skills results in three material GETs
  before the first model call.
- Missing `X-Claim-Token` on material GET fails the test.
- Material fetch failure prevents model invocation and completes/marks failed
  with `material_fetch_failed`.
- The model input contains fetched material content and does not rely on
  `material_manifest.title` or `summary`.
- Completion/progress data includes fetched refs and hashes, not material
  content.
