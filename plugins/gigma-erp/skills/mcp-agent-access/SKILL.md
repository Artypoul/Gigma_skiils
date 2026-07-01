---
name: mcp-agent-access
description: "Создать, проверить или подключить MCP/AI-агента к Gigma ERP через agent-user и Sanctum Bearer token. Используй когда нужно выдать токен MCP-серверу, проверить /api/agents, права view/create/edit-agents или manage-agent-tokens, отключить агента, отозвать токен или связать MCP tool calls с обычным ERP REST API."
allowed-tools: Bash Read Grep
---

# MCP agent access в Gigma ERP

Цель: подключить внешний MCP-сервер к Gigma ERP через технического `User` с `is_agent=true` и обычный `Authorization: Bearer <agent_token>`.

Источник деталей: `../../reference/agent-mcp-access.md`. Если нужно менять backend-код, дополнительно используй Graphify hooks ниже и сверяй исходники.

## Главная модель

- Агент — это строка в `users`, не отдельный auth provider.
- MCP-сервер живёт снаружи ERP и вызывает обычные REST API.
- `/api/mcp/*` в Laravel не возвращать и не придумывать.
- Токен агента — Sanctum token формата `<id>|<secret>`, как у `auth:user`.
- Права агента = роль + direct permissions внутри текущего `project_id`/`branch_id`.

## Перед любым write

1. Получить owner/human Bearer token, не App Token витрины.
2. Проверить `GET /api/user`: actor не должен быть agent-user, проект верный.
3. Согласовать с владельцем:
   - имя и `login` агента;
   - `role_id`, `branch_id`, `department_id`;
   - список `permissions`;
   - имя токена и срок жизни;
   - где MCP-сервер безопасно сохранит plain token.
4. Перед `POST/PATCH/DELETE` явно показать payload и дождаться подтверждения.

## Runbook

1. Проверить доступность agent API:

```http
GET /api/agents
Authorization: Bearer <owner_token>
Accept: application/json
```

`404` обычно значит, что backend ещё без PR #271; `403` значит, что actor не имеет agent permissions.

2. Создать агента:

```http
POST /api/agents
Authorization: Bearer <owner_token>
Accept: application/json
Content-Type: application/json

{
  "name": "Local MCP Server",
  "login": "local-mcp-server",
  "role_id": 12,
  "branch_id": null,
  "department_id": null,
  "permissions": ["view-orders"],
  "agent_description": "External MCP server for read-only ERP checks"
}
```

3. Выпустить токен:

```http
POST /api/agents/{agent}/tokens
Authorization: Bearer <owner_token>
Accept: application/json
Content-Type: application/json

{
  "name": "local-mcp-server",
  "expires_at": "2027-07-01T00:00:00Z"
}
```

Plain token приходит только в `agent_token.value` при создании. Не печатай его в чат целиком, не коммить в файлы, не клади в PR body.

4. Проверить токен агента:

```http
GET /api/user
Authorization: Bearer <agent_token>
Accept: application/json
```

Затем проверить один обычный ERP endpoint, который соответствует выданным permissions. Если нужен другой endpoint — сначала выдай минимальное право, не расширяй роль "на всякий случай".

5. Отключение:

- `DELETE /api/agents/{agent}` — soft-disable (`is_banned=true`) и отзыв всех токенов.
- `DELETE /api/agents/{agent}/tokens/{token}` — отзыв одного токена.

## Жёсткие запреты

- Не использовать `/api/login` или `/api/send_password` для agent-user: password flow для агентов запрещён.
- Не выдавать агенту права сильнее прав текущего human actor.
- Не выпускать токен для агента, чьи роль/permissions сильнее текущего actor.
- Не делать MCP-token владельцем проекта без явного решения владельца.
- Не давать MCP прямой доступ к БД, shell, файлам сервера или внешней сети через ERP.
- Не смешивать `Token: <application_token>` витрины и `Authorization: Bearer <agent_token>`.

## Dependency Map

```yaml
references:
  - ../../reference/agent-mcp-access.md
owner_endpoints:
  - method: GET
    path: /api/agents
    backend: App\Http\Controllers\AgentController::index
  - method: POST
    path: /api/agents
    backend: App\Http\Controllers\AgentController::store
  - method: PATCH
    path: /api/agents/{agent}
    backend: App\Http\Controllers\AgentController::update
  - method: DELETE
    path: /api/agents/{agent}
    backend: App\Http\Controllers\AgentController::destroy
  - method: GET
    path: /api/agents/{agent}/tokens
    backend: App\Http\Controllers\AgentTokenController::index
  - method: POST
    path: /api/agents/{agent}/tokens
    backend: App\Http\Controllers\AgentTokenController::store
  - method: DELETE
    path: /api/agents/{agent}/tokens/{token}
    backend: App\Http\Controllers\AgentTokenController::destroy
regular_erp_check:
  - method: GET
    path: /api/user
    backend: App\Http\Controllers\UserController::authorized
backend_functions:
  - App\Services\AgentService::create
  - App\Services\AgentService::createToken
  - App\Policies\UserPolicy::manageAgentTokens
  - App\Http\Requests\Concerns\ValidatesAssignableAgentPermissions
related_skills:
  - connect-frontend-api
  - setup-storefront
risk_level: high
default_mode: confirm_required
```

## Graphify Hooks

Если проверяешь backend-изменение или спорный контракт, используй Graphify только как навигацию и затем открой исходники:

```bash
graphify explain "AgentController"
graphify explain "AgentTokenController"
graphify explain "AgentService"
graphify explain "UserPolicy"
graphify path "AgentTokenController" "UserPolicy"
```

Исходники для сверки: `routes/api.php`, `app/Http/Controllers/AgentController.php`, `app/Http/Controllers/AgentTokenController.php`, `app/Services/AgentService.php`, `app/Policies/UserPolicy.php`, `tests/Feature/Agents/AgentAccessTest.php`.

## Проверка перед сдачей

- Agent API отвечает по owner Bearer token.
- Созданный agent имеет `is_agent:true`, нужный `project_id`, роль и минимальные permissions.
- `agent_token.value` показан только один раз и не сохранён в репо.
- `GET /api/user` с agent token возвращает этого агента.
- Endpoint без нужного permission возвращает `403`.
- Отключённый агент или отозванный token больше не проходят `GET /api/user`.
