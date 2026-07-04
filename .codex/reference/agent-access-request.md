# Agent access request reference

Факты проверены по `itecho-erp-backend` `origin/master` после merge PR #273 `feature/agent-access-requests` (`16038537`, 2026-07-02).

## Модель

Self-service доступ агента нужен, когда MCP/AI-агенту нужен ERP Bearer token, но у оператора нет owner Bearer token. Агент создаёт публичную заявку на email owner/admin. Backend отправляет письмо с review link; owner/admin подтверждает доступ; после этого агент один раз забирает `agent_token.value`.

Это не `/api/mcp/*` слой и не login flow агента. После consume создаётся обычный `users` agent-user с `is_agent=true`, ролью employee/employer и Sanctum token.

## Public endpoints

Endpoints публичные и без `Authorization`. `POST` endpoints принимают JSON body и имеют throttle; `GET /review` отдаёт HTML-страницу для owner/admin.

| Method | Path | Назначение |
|---|---|---|
| POST | `/api/agent-access-requests` | Создать заявку и отправить owner/admin письмо, если email подходит |
| GET | `/api/agent-access-requests/{publicId}/review` | HTML review page для owner/admin |
| POST | `/api/agent-access-requests/{publicId}/review` | Получить детали заявки по `approval_token` |
| POST | `/api/agent-access-requests/{publicId}/approve` | Owner/admin одобряет заявку |
| POST | `/api/agent-access-requests/{publicId}/decline` | Owner/admin отклоняет заявку |
| POST | `/api/agent-access-requests/{publicId}/status` | Агент проверяет статус по `request_token` |
| POST | `/api/agent-access-requests/{publicId}/consume` | Агент одноразово забирает `agent_token.value` |

## Create request

`permissions` в заявке — это обычные ERP permission names из таблицы `permissions` с `guard_name=user`, а не отдельный MCP-набор. Если human Bearer token уже есть, полный каталог можно прочитать через `GET /api/permissions`.

Готовые billing-наборы для заявки:

- billing read-only: `["view-orders"]`;
- billing operations по заказам: `["view-orders", "edit-orders"]`;
- billing read-only + application context: `["view-orders", "view-applications"]`;
- billing operations + application updates: `["view-orders", "edit-orders", "view-applications", "edit-applications"]`.

Отдельных permission names `view-payments`, `edit-payments`, `view-subscriptions`, `edit-subscriptions` в текущем ERP нет. Для billing webhook/admin действий действует отдельная owner/admin role boundary.

```http
POST /api/agent-access-requests
Accept: application/json
Content-Type: application/json

{
  "owner_email": "owner@example.com",
  "agent_name": "MCP Order Agent",
  "agent_login": "mcp-order-agent",
  "permissions": ["view-orders"],
  "purpose": "Read orders and prepare summaries"
}
```

Rules:

- `owner_email` required, RFC email, max 255; backend lowercases and trims it;
- `agent_name` required, string, min 1, max 255;
- `agent_login` nullable, string, min 3, max 255; if omitted, backend generates `<slug>-<public_id_prefix>`;
- `permissions` nullable array, max 100;
- `permissions.*` must exist in `permissions.name` with `guard_name=user`;
- `purpose` nullable string, max 5000.

Response:

```json
{
  "message": "Если такой администратор есть, мы отправили запрос.",
  "request": {
    "public_id": "uuid",
    "request_token": "plain-token-visible-once-for-agent",
    "expires_at": "2026-07-02T10:30:00+00:00"
  }
}
```

Security behavior:

- response is neutral even if owner email is unknown or not eligible;
- `approval_token` is never returned to the requester;
- `request_token` is plain only in create response, then only hash is stored;
- `owner_email`, request IP and user agent are stored as HMAC hashes; masked email is stored for display;
- if eligible owner/admin exists, backend sends `AgentAccessRequestMail`;
- mail cooldown: one approval email per owner per 10 minutes, but requests can still be created.

## Eligible owner/admin

Backend sends approval mail only if `owner_email` matches a non-banned, non-agent `users.login` with `project_id` and one of:

- role name `owner`;
- role name `admin`;
- permission `edit-admins`;
- permission `edit-permissions`.

Before approve and consume, backend rechecks that owner/admin is still eligible and still in the same project.

## Owner review and approve

Mail subject: `Запрос доступа MCP-агента`.

Mail link:

```text
/api/agent-access-requests/{public_id}/review#approval_token=<approval_token>
```

The HTML page moves `approval_token` from URL fragment into the body requests and removes it from browser URL history. Do not put `approval_token` in query string.

Review details:

```http
POST /api/agent-access-requests/{public_id}/review
Accept: application/json
Content-Type: application/json

{
  "approval_token": "<approval_token>"
}
```

Response includes:

- `status`;
- `request.public_id`;
- `request.agent_name`;
- `request.agent_login`;
- default role (`employee`, fallback legacy `employer`);
- `request.requested_permissions`;
- `request.approved_permissions`;
- `request.purpose`;
- `request.expires_at`.

Approve:

```http
POST /api/agent-access-requests/{public_id}/approve
Accept: application/json
Content-Type: application/json

{
  "approval_token": "<approval_token>",
  "permissions": ["view-orders"]
}
```

`permissions` is optional. If omitted, backend tries to approve all requested permissions. Owner/admin can approve a narrower subset, but cannot approve:

- permissions not requested by the agent;
- permissions broader than owner/admin can assign.

Role is not chosen by requester. Backend uses project role named `employee`; if missing, legacy `employer`; if neither exists, approve fails with validation error on `role_id`.

Decline:

```http
POST /api/agent-access-requests/{public_id}/decline
Accept: application/json
Content-Type: application/json

{
  "approval_token": "<approval_token>"
}
```

## Status polling

```http
POST /api/agent-access-requests/{public_id}/status
Accept: application/json
Content-Type: application/json

{
  "request_token": "<request_token>"
}
```

Response:

```json
{
  "status": "pending",
  "expires_at": "...",
  "server_time": "..."
}
```

Statuses:

| Status | Meaning | Next step |
|---|---|---|
| `pending` | Owner has not approved/declined yet | Continue polling until TTL or user-facing timeout |
| `approved` | Owner approved | Call consume once |
| `declined` | Owner declined | Stop; do not retry automatically |
| `expired` | TTL passed | Stop; create a fresh request only with user/owner intent |
| `consumed` | Token was already issued | Do not expect token value again |

Request TTL: 30 minutes. Suggested polling: every 10-30 seconds, bounded by `expires_at`.

## Consume

```http
POST /api/agent-access-requests/{public_id}/consume
Accept: application/json
Content-Type: application/json

{
  "request_token": "<request_token>"
}
```

Success response:

```json
{
  "status": "consumed",
  "agent": {
    "id": 123,
    "name": "MCP Order Agent",
    "login": "mcp-order-agent"
  },
  "agent_token": {
    "id": 456,
    "name": "mcp-self-service",
    "value": "456|plain-token-visible-once",
    "expires_at": "2027-07-02T10:30:00+00:00"
  }
}
```

Token details:

- created by `AgentService::createToken`;
- token name is `mcp-self-service`;
- expiry is one year from consume;
- value is returned only once;
- repeated consume after successful issue returns `already_consumed:true` and does not include `agent_token.value`.

Failure cases:

- `409` if request is not approved;
- `409` if expired;
- `409` if `agent_login` is already taken;
- `403` if owner/admin lost eligibility before consume;
- `409` if owner/admin moved to another project after request creation;
- `404`-style not found if `request_token`/`approval_token` is wrong.

## Secrets and logging

Never put these in query string, PR body, chat, shell history or client logs:

- `request_token`;
- `approval_token`;
- `agent_token.value`;
- owner OTP/password;
- owner Bearer token.

Backend validation explicitly rejects `approval_token`/`request_token` in query for review/approve/decline/status/consume. Validation logs redact sensitive keys.

## Relation to mcp-agent-access

Use this self-service flow when there is no owner Bearer token and owner can approve by email. After `consume`, switch to `mcp-agent-access` guidance for:

- designing MCP tool allowlists;
- validating `GET /api/user` with agent token;
- checking allowed and denied ERP endpoints;
- revoking or rotating tokens.

Use direct `mcp-agent-access` owner endpoints only when a least-privileged human Bearer token is already available.

## Backend files

Paths below are in external repo `itecho-erp-backend`.

- `routes/api.php`
- `app/Http/Controllers/AgentAccessRequestController.php`
- `app/Services/AgentAccessRequestService.php`
- `app/Models/AgentAccessRequest.php`
- `app/Mail/AgentAccessRequestMail.php`
- `app/Http/Requests/AgentAccess/*`
- `resources/views/emails/agent_access_request.blade.php`
- `resources/views/agent_access_requests/review.blade.php`
- `database/migrations/2026_07_01_070000_create_agent_access_requests_table.php`
- `tests/Feature/Agents/AgentAccessRequestTest.php`
