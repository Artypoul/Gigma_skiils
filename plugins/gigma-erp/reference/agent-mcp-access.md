# Agent MCP access reference

Факты проверены по `itecho-erp-backend` `origin/master` после merge PR #271 `feature/agent-mcp-access` (`9108eaa3`, 2026-07-01).

## Модель

MCP-доступ не является отдельным backend-слоем. Внешний MCP-сервер хранит токен технического ERP-пользователя и ходит в обычный REST API:

```http
Authorization: Bearer <agent_token>
Accept: application/json
```

Агент хранится в `users`:

- `is_agent=true`;
- `agent_description` — назначение агента;
- `project_id`, `role_id`, `branch_id`, `department_id` — обычные ERP границы;
- direct permissions — через текущий Spatie/RBAC слой;
- tokens — стандартные Sanctum `personal_access_tokens`.

В Laravel нет нового `/api/mcp/*`, отдельной таблицы `agents` и отдельного auth provider.

## Permissions

Новые permissions с `guard_name=user`:

| Permission | Для чего |
|---|---|
| `view-agents` | Смотреть список и карточку агентов |
| `create-agents` | Создавать agent-user |
| `edit-agents` | Изменять и отключать agent-user |
| `manage-agent-tokens` | Выпускать, смотреть metadata и отзывать токены |

Ограничения:

- actor не может выдать агенту permission сильнее своих, если у actor нет `edit-permissions`;
- actor не может выдать агенту роль сильнее своей admin-границы;
- token нельзя выпустить для агента, которым actor не имеет права управлять;
- agent-user не может выпускать/отзывать токены другим агентам в MVP.

## Endpoints

Все endpoints живут в существующей группе `auth:user` и `banned`.

| Method | Path | Permission/policy | Назначение |
|---|---|---|---|
| GET | `/api/agents` | `view-agents` | Список агентов проекта |
| GET | `/api/tables/agents` | `view-agents` | Табличный список для UI |
| POST | `/api/agents` | `create-agents` | Создать agent-user |
| GET | `/api/agents/{agent}` | `view-agents` + project scope | Карточка агента |
| PATCH | `/api/agents/{agent}` | `edit-agents` + manage boundary | Обновить агента |
| DELETE | `/api/agents/{agent}` | `edit-agents` + manage boundary | Отключить агента и отозвать все токены |
| GET | `/api/agents/{agent}/tokens` | `manage-agent-tokens` + manage boundary | Список token metadata |
| POST | `/api/agents/{agent}/tokens` | `manage-agent-tokens` + manage boundary | Выпустить token |
| DELETE | `/api/agents/{agent}/tokens/{token}` | `manage-agent-tokens` + manage boundary | Отозвать token агента |

## Create agent payload

```json
{
  "name": "Order assistant",
  "login": "agent-orders",
  "role_id": 12,
  "branch_id": null,
  "department_id": null,
  "permissions": ["view-orders"],
  "agent_description": "External MCP server for order checks",
  "is_banned": false
}
```

Rules:

- `name` required, `string`, `min:1`, `max:255`;
- `login` required, unique in `users`, `min:3`, `max:255`;
- `role_id` required, must belong to actor project and be assignable by actor;
- `branch_id`/`department_id` nullable, must belong to actor project;
- `permissions.*` must exist with `guard_name=user` and be assignable by actor;
- `agent_description` nullable, max 5000;
- `is_banned` nullable boolean.

Response wrapper: `agent`.

Important response fields:

- `agent.id`;
- `agent.name`;
- `agent.login`;
- `agent.role`;
- `agent.branch`;
- `agent.department`;
- `agent.is_agent`;
- `agent.is_banned`;
- `agent.permissions`;
- `agent.last_activity_at`.

## Update agent payload

`PATCH /api/agents/{agent}` accepts the same fields as create, but all are optional except nullable-clears:

- omitted fields are preserved;
- `branch_id:null`, `department_id:null`, `permissions:[]` explicitly clear values;
- `name:null`, `login:null`, `role_id:null` are validation errors;
- setting `is_banned:true` revokes all existing tokens.

## Token lifecycle

Create token:

```json
{
  "name": "local-mcp-server",
  "expires_at": "2027-07-01T00:00:00Z"
}
```

Rules:

- `name` required, `min:3`, `max:100`;
- `expires_at` nullable date, after now, not later than one year;
- if omitted, backend creates token for one year;
- disabled agent cannot receive a new token.

Create response wrapper: `agent_token`.

```json
{
  "agent_token": {
    "id": 123,
    "name": "local-mcp-server",
    "value": "12|plain-token-visible-once",
    "created_at": "...",
    "last_used_at": null,
    "expires_at": "2027-07-01T00:00:00Z"
  }
}
```

`value` is returned only on create. `GET /api/agents/{agent}/tokens` returns metadata without `value`, `token` or hash.

## Forbidden flows

- `POST /api/login` and `POST /api/send_password` reject `is_agent=true`.
- Human user endpoints reject agent rows as human users:
  - `/api/users/{agent}`;
  - `/api/users/{agent}/integrations`;
  - `/api/users/{agent}/integrations/{integration}/parameters`;
  - `/api/users/{agent}/attach_menu`;
  - `/api/users/{agent}/create_menu_from_user_items`;
  - `/api/users/{agent}/history`.
- Human lists such as `/api/users`, `/api/managers`, `/api/responsible_users` hide agent users.

## MCP server integration checklist

1. Human owner/admin creates or selects agent-user.
2. Agent has minimal `role_id`, `branch_id`, `department_id` and direct permissions for the intended tools.
3. Human actor creates token once and stores plain value in MCP secret storage.
4. MCP tools map to regular ERP endpoints and always send `Authorization: Bearer <agent_token>`.
5. Every write tool should have its own confirmation/payload preview outside ERP.
6. Verify with `GET /api/user`, then one allowed endpoint and one forbidden endpoint.
7. If token leaks or scope changes, revoke token or `DELETE /api/agents/{agent}`.

## Backend files

- `routes/api.php`
- `app/Http/Controllers/AgentController.php`
- `app/Http/Controllers/AgentTokenController.php`
- `app/Services/AgentService.php`
- `app/Http/Requests/Agent/StoreRequest.php`
- `app/Http/Requests/Agent/UpdateRequest.php`
- `app/Http/Requests/Agent/StoreTokenRequest.php`
- `app/Http/Requests/Concerns/ValidatesAssignableAgentPermissions.php`
- `app/Http/Requests/Concerns/ValidatesHumanUsers.php`
- `app/Policies/UserPolicy.php`
- `app/Models/User.php`
- `database/migrations/2026_07_01_010000_add_agent_fields_to_users_table.php`
- `database/migrations/2026_07_01_010100_seed_agent_permissions.php`
- `tests/Feature/Agents/AgentAccessTest.php`

## Graphify hooks

Use Graphify as navigation only, then confirm in source:

```bash
graphify explain "AgentController"
graphify explain "AgentTokenController"
graphify explain "AgentService"
graphify explain "UserPolicy"
graphify explain "User"
graphify path "AgentTokenController" "UserPolicy"
```

For endpoint-to-code checks, start from `routes/api.php` and only then use Graphify to find adjacent controllers, requests, policies and tests.
