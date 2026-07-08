---
name: support-assets-api
description: "Спроектировать, подключить или проверить GLAIM Support Assets API по реальному контракту: asset templates, generated assets, manual assets, versions, approve/publish/archive/revoke flow и asset bindings. Используй когда нужно создать support asset template, сгенерировать draft asset по шаблону, завести или опубликовать image/document/message asset, привязать ассет к app/profile/channel/source, проверить headers Authorization/X-Control-Secret/X-Actor-Ref, storage_uri, scan_status, publish constraints или понять, почему ассет не появляется в GET /assets."
---

# Support Assets API

## Overview

Use this skill for the new GLAIM support-assets contour under `/api/v2/assets`. Work only from the real contract: local code in `glaim`, verified request schemas, domain validation, and tests.

Read `references/contract.md` when you need exact payload fields, enum values, code paths, or verified failure modes.

## Pick the lane

Choose one lane first:

- Agent-safe lane: `GET /assets/templates`, `GET /assets`, `POST /assets/templates/{template_id}/generated-assets`.
- Control-plane lane: template create/approve/archive, asset create/version/approve/publish/archive/revoke, and bindings.

Do not mix the lanes casually. Agent-safe calls use only `Authorization: Bearer <agent_token>`. Control-plane calls additionally require `X-Control-Secret` and may include `X-Actor-Ref` for audit.

Never expose `X-Control-Secret` to frontend code, public miniapps, browser bundles, or user-facing chat flows.

## Workflow

1. Confirm the base URL and environment.
   - Production base URL is `https://agentapi.gigma.ru/api/v2`.
   - If the local `glaim` repo is available, verify the contract against code before editing docs or clients.
2. Confirm the caller type.
   - Agent/courier/runtime generation only: use the agent-safe lane.
   - Owner/admin/moderation/setup: use the control-plane lane.
3. Choose the object lifecycle.
   - Template lifecycle: `draft -> approved -> archived`.
   - Asset lifecycle: `draft -> approved -> published`, with `archive` or `revoke` later.
4. Keep track of returned ids.
   - Save `template_id` and `asset_id` from create responses.
   - There is currently no separate admin list endpoint for all drafts, so losing the id creates avoidable friction.
5. Verify why the asset is or is not visible.
   - `GET /assets/templates` shows only approved, non-archived templates for the current app.
   - `GET /assets` shows only published, non-archived, non-revoked assets that are visible through bindings.

## Canonical flows

### Agent-generated asset from a template

1. List approved templates with `GET /assets/templates`.
2. Pick the correct `template_id`.
3. Call `POST /assets/templates/{template_id}/generated-assets`.
4. Expect a new asset in `draft` status and `origin=agent_generated`.
5. Save the returned `asset_id`.
6. Hand the asset off to owner/admin for `approve` and `publish`.

### Owner-admin publication flow

1. Create or locate the template.
2. Approve the template if agents should generate from it.
3. Either:
   - let the agent generate a draft asset from the template, or
   - create a manual asset with `POST /assets`, then add a version with `POST /assets/{asset_id}/versions`.
4. Approve the asset.
5. Publish the asset.
6. Bind the published asset to the correct scope with `POST /assets/{asset_id}/bindings`.

## Binding rules

- `scope_type` can be only `app`, `profile`, `channel`, or `source`.
- For `app`, send no `scope_ref`.
- For `profile`, `channel`, and `source`, `scope_ref` is required.
- `profile` bindings must belong to the same app; do not fake ownership checks in docs or client code.
- Bindings are meaningful only after the asset is published. Draft and approved-but-unpublished assets do not appear in agent-safe `GET /assets`.

## Validation and safety rules

- Keys must be stable lowercase identifiers with dots, dashes, or underscores.
- Valid `asset_kind` and `template_kind`: `image`, `document`, `message`.
- Valid `visibility`: `private`, `app_internal`, `public_sanitized`.
- Valid `scan_status`: `pending`, `passed`, `failed`, `not_required`.
- `storage_uri` is safest as `asset://...`.
- External `https://...` storage works only if it matches `ASSET_STORAGE_ALLOWED_PREFIXES`.
- Reject local file paths, loopback/private hosts, user-info in URLs, and secret-like query keys.
- Publishing is valid only when:
  - asset status is `approved`;
  - the asset has at least one version;
  - the latest version `scan_status` is `passed` or `not_required`.

## Troubleshooting

- `401 missing_control_plane_secret`: control-plane endpoint was called without the required secret.
- `storage_uri_host_not_allowed`: external storage prefix is not allowlisted, or only `asset://` is allowed.
- `storage_uri_secret_query`: URL query includes token/signature-like keys.
- `template_not_approved`: agent tried to generate from a draft or archived template.
- `asset_status_not_approved`: publish was attempted too early.
- `asset_version_missing`: publish was attempted before any version existed.
- `asset_scan_not_passed`: publish was attempted with `pending` or `failed` latest scan.
- `scope_ref_required`: a non-`app` binding missed `scope_ref`.
- Asset is missing from `GET /assets`: check publish state, archive/revoke state, and binding existence.

## Hard rules

- Do not tell frontend code to call control-plane endpoints directly.
- Do not use source tokens, chat tokens, or miniapp secrets for this API; this contour is Bearer-agent based.
- Do not assume there is an admin draft-list API today.
- Do not invent `/assets/manage/...` as an already-available route. Mention it only as a possible follow-up PR.
- Do not publish generated assets automatically from the agent lane.

## Check before finishing

- The selected endpoint lane matches the caller capabilities.
- Headers are correct for that lane.
- `storage_uri`, `checksum_sha256`, `mime_type`, and `byte_size` respect the contract.
- The asset lifecycle step is legal for the current status.
- The binding scope matches the real usage area.
