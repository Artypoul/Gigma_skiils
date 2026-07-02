---
name: mcp-agent-access
description: "Создать, проверить или подключить MCP/AI-агента к Gigma ERP через agent-user и Sanctum Bearer token. Используй когда нужно выдать токен MCP-серверу, получить MCP-доступ для нового агента, проверить /api/agents, права view/create/edit-agents или manage-agent-tokens, отключить агента, отозвать токен или связать MCP tool calls с обычным ERP REST API. Если agent token ещё нет, сначала используй request-agent-access."
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

1. Получить заранее выданный least-privileged human Bearer token с agent permissions, не App Token витрины. Если такого token нет, используй `request-agent-access`: self-service заявка уйдёт owner/admin на почту, а агент после approve заберёт свой `agent_token`. Не добывать owner token через БД/таблицу `passwords` для обычной настройки MCP; это только break-glass с явным разрешением владельца.
2. Проверить `GET /api/user`: actor не должен быть agent-user, проект верный.
3. Согласовать с владельцем:
   - имя и `login` агента;
   - `role_id`, `branch_id`, `department_id`;
   - список `permissions`;
   - имя токена и срок жизни;
   - какие exact method+path будут доступны каждому MCP tool;
   - где MCP-сервер безопасно сохранит plain token.
4. Перед `POST/PATCH/DELETE` явно показать payload и дождаться подтверждения.

## Если токена ещё нет

Не начинать с `/api/agents` и не просить owner Bearer token. Для нового агента или нового ПК сначала выполнить self-service flow из `request-agent-access`:

1. Собрать `ERP_API_BASE_URL`, `owner_email`, `agent_name`, `agent_login`, минимальные `permissions`, `purpose` и путь для локального secret storage.
2. Создать `POST /api/agent-access-requests`.
3. Сохранить `public_id` и `request_token` локально, не выводя `request_token`.
4. Дождаться approve письма владельцем через status polling.
5. Один раз вызвать `consume`, сохранить `agent_token.value`.
6. Проверить `GET /api/user` с `Authorization: Bearer <agent_token>`.
7. Вернуться к этому скилу и описать MCP tools как allowlist конкретных `method + path`.

Граница ответственности: `request-agent-access` получает `agent_token`; этот скил настраивает/проверяет права и endpoint allowlist для MCP. Если пользователь спрашивает "как агенту получить доступ к MCP", обязательно дать обе части в таком порядке.

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

Plain token приходит только в `agent_token.value` при создании. Не печатай его в чат целиком, не коммить в файлы, не клади в PR body, не сохраняй в shell history.

4. Проверить токен агента:

```http
GET /api/user
Authorization: Bearer <agent_token>
Accept: application/json
```

Затем проверить каждый ERP endpoint, который будет открыт MCP tool'ом: positive check для разрешённого method+path и negative check для похожего запрещённого действия. Если нужен другой endpoint — сначала выдай минимальное право, не расширяй роль "на всякий случай".

5. Отключение:

- `DELETE /api/agents/{agent}` — soft-disable (`is_banned=true`) и отзыв всех токенов.
- `DELETE /api/agents/{agent}/tokens/{token}` — отзыв одного токена, где `{token}` = `agent_token.id` / `personal_access_tokens.id`, а не `agent_token.value`.

## Жёсткие запреты

- Не использовать `/api/login` или `/api/send_password` для agent-user: password flow для агентов запрещён.
- Не просить owner Bearer token, если достаточно self-service approve через `request-agent-access`.
- Не строить generic REST/curl proxy tool вроде "вызови любой ERP endpoint". Каждый MCP tool должен иметь allowlist конкретных `method + path` и свою проверку прав.
- Не выдавать агенту права сильнее прав текущего human actor.
- Не выпускать токен для агента, чьи роль/permissions сильнее текущего actor.
- Не делать MCP-token owner/admin по умолчанию. Break-glass owner/admin agent допустим только с явным письменным решением владельца, коротким TTL, endpoint allowlist, no generic tools и планом немедленной ротации.
- Не давать MCP прямой доступ к БД, shell, файлам сервера или внешней сети через ERP.
- Не смешивать `Token: <application_token>` витрины и `Authorization: Bearer <agent_token>`.
- Не логировать `Authorization` headers, OTP, owner token или `agent_token.value`.

## Dependency Map

```yaml
references:
  - ../../reference/agent-mcp-access.md
owner_endpoints:
  - method: GET
    path: /api/agents
    backend: App\Http\Controllers\AgentController::index
  - method: GET
    path: /api/tables/agents
    backend: App\Http\Controllers\AgentController::tableIndex
  - method: POST
    path: /api/agents
    backend: App\Http\Controllers\AgentController::store
  - method: GET
    path: /api/agents/{agent}
    backend: App\Http\Controllers\AgentController::show
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

Если проверяешь backend-изменение или спорный контракт, сначала убедись, что Graphify построен по свежему `itecho-erp-backend` `origin/master`. Если `graphify explain` не находит agent nodes, обнови граф в backend repo или переходи source-first по файлам ниже. Graphify использовать только как навигацию и затем открывать исходники:

```bash
graphify explain "AgentController"
graphify explain "AgentTokenController"
graphify explain "AgentService"
graphify explain "UserPolicy"
graphify path "AgentTokenController" "UserPolicy"
```

Исходники для сверки в repo `itecho-erp-backend`: `routes/api.php`, `app/Http/Controllers/AgentController.php`, `app/Http/Controllers/AgentTokenController.php`, `app/Services/AgentService.php`, `app/Policies/UserPolicy.php`, `tests/Feature/Agents/AgentAccessTest.php`.

## Проверка перед сдачей

- Agent API отвечает по owner Bearer token.
- Созданный agent имеет `is_agent:true`, нужный `project_id`, роль и минимальные permissions.
- `agent_token.value` показан только один раз и не сохранён в репо.
- `GET /api/user` с agent token возвращает этого агента.
- Каждый MCP tool имеет explicit allowlist `method + path`; generic REST proxy отсутствует.
- Разрешённый endpoint проходит, похожий endpoint без нужного permission возвращает `403` или ожидаемый deny.
- Отключённый агент или отозванный token больше не проходят `GET /api/user`.
