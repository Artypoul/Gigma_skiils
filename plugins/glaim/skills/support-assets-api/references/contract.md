# GLAIM Support Assets API Contract

Verified against local code in:

- `app/modules/asset/presentation/router.py`
- `app/modules/asset/presentation/schemas.py`
- `app/modules/asset/domain/entities.py`
- `app/modules/asset/domain/validation.py`
- `app/modules/asset/infrastructure/repository.py`
- `app/core/config.py`
- `tests/test_assets.py`
- `docs/plan-support-assets-api.md`

## Base URL

- Production: `https://agentapi.gigma.ru/api/v2`

## Auth

All endpoints require:

```http
Authorization: Bearer <agent_token>
```

Control-plane endpoints additionally require:

```http
X-Control-Secret: <control_secret>
```

Optional audit header:

```http
X-Actor-Ref: owner-1
```

## Agent-safe endpoints

```http
GET  /assets/templates
GET  /assets
POST /assets/templates/{template_id}/generated-assets
```

Behavior:

- `GET /assets/templates`: approved, non-archived templates for the current app.
- `GET /assets`: published, non-archived, non-revoked assets joined through active bindings.
- `POST /assets/templates/{template_id}/generated-assets`: creates a `draft` asset with one version and `origin=agent_generated`.

## Control-plane endpoints

```http
POST /assets/templates
POST /assets/templates/{template_id}/approve
POST /assets/templates/{template_id}/archive

POST /assets
POST /assets/{asset_id}/versions
POST /assets/{asset_id}/approve
POST /assets/{asset_id}/publish
POST /assets/{asset_id}/archive
POST /assets/{asset_id}/revoke
POST /assets/{asset_id}/bindings
```

## Enums

`template_kind` and `asset_kind`

```text
image
document
message
```

`visibility`

```text
private
app_internal
public_sanitized
```

`scan_status`

```text
pending
passed
failed
not_required
```

`scope_type`

```text
app
profile
channel
source
```

## Request shapes

### Create template

```json
{
  "template_key": "support.happ.clipboard",
  "title": "HAPP: add subscription from clipboard",
  "description": "Template for the clipboard step",
  "template_kind": "image",
  "body": {
    "renderer": "support-card"
  },
  "policy": {
    "channels": ["chat"]
  }
}
```

### Create manual asset

```json
{
  "asset_key": "support.happ.clipboard.owner",
  "title": "HAPP: add subscription from clipboard",
  "description": "Owner-registered asset",
  "asset_kind": "image",
  "asset_template_id": "00000000-0000-0000-0000-000000000000",
  "visibility": "private"
}
```

### Create generated asset from template

```json
{
  "asset_key": "support.happ.clipboard.generated",
  "title": "HAPP: add subscription from clipboard",
  "description": "Generated support screenshot",
  "storage_uri": "asset://support/happ/clipboard.png",
  "mime_type": "image/png",
  "checksum_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "byte_size": 1200,
  "render_input": {
    "scenario": "happ_setup",
    "step": "clipboard"
  },
  "metadata": {
    "locale": "ru"
  },
  "visibility": "private",
  "scan_status": "passed"
}
```

### Add asset version

```json
{
  "storage_uri": "asset://support/happ/clipboard-v2.png",
  "mime_type": "image/png",
  "checksum_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "byte_size": 1300,
  "render_input": {
    "scenario": "happ_setup",
    "step": "clipboard"
  },
  "metadata": {
    "locale": "ru"
  },
  "scan_status": "passed"
}
```

### Create binding

```json
{
  "scope_type": "profile",
  "scope_ref": "<profile_id>"
}
```

Rules:

- for `app`, omit `scope_ref`;
- for `profile`, `channel`, and `source`, `scope_ref` is required.

## Validation constraints

- Key pattern: lowercase, starts with `[a-z0-9]`, then `[a-z0-9_.-]`, max 100 chars.
- `checksum_sha256`: exactly 64 lowercase hex chars.
- `mime_type`: validated string, max 128 chars.
- `byte_size`: `0..52428800`.
- JSON payload fields are capped at 20 KB encoded size.

## storage_uri rules

Accepted:

- `asset://...`
- allowlisted `https://...` prefixes from `ASSET_STORAGE_ALLOWED_PREFIXES`

Rejected:

- local file paths
- Windows drive paths
- loopback/private/link-local hosts
- user-info in URL
- secret-like query keys such as `token`, `signature`, `api_key`, `password`

If no allowlist is configured, only `asset://...` works.

## Lifecycle

Template:

```text
draft -> approved -> archived
```

Asset:

```text
draft -> approved -> published
published -> revoked
draft/approved/published -> archived
```

Publishing checks:

- asset status must be `approved`
- asset must have at least one version
- latest version `scan_status` must be `passed` or `not_required`

## Known operational limitation

There is currently no dedicated admin endpoint to list every draft asset/template for moderation. If the workflow creates drafts, save returned ids from create responses. A future follow-up can add `/api/v2/assets/manage/...` endpoints, but they are not present in the current code.
