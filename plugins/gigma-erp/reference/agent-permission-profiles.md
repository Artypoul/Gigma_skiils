# Agent permission profiles for self-service access requests

Факты проверены по `C:\Users\Art\Documents\GitHub\itecho-erp-backend` на 2026-07-07.

Источники:

- `routes/api.php`
- `database/seeders/PermissionSeeder.php`
- `database/migrations/2026_07_01_010100_seed_agent_permissions.php`
- `app/Policies/UserPolicy.php`
- `app/Services/AgentAccessRequestService.php`
- `docs/agent-mcp-tool-profiles.md`

## Source of truth

Runtime source of truth для production-запроса - `GET /api/permissions` с human
Bearer token. Именно этот endpoint показывает актуальные `permissions.name` в
текущей БД.

Этот reference нужен для zero-token сценария, когда human token еще нет, но
агенту надо безопасно составить self-service заявку. Его можно использовать как
поддерживаемый offline baseline для request composition, пока нет доступа к
`GET /api/permissions`.

Если `GET /api/permissions` уже доступен, он важнее этого файла.

## Known current permission names

Ниже - известные permission names, которые подтверждены текущим ERP кодом и
подходят для self-service request body.

### Core / org / people

```json
[
  "view-admins",
  "edit-admins",
  "view-users",
  "edit-users",
  "edit-roles",
  "edit-permissions",
  "edit-branches",
  "edit-departments"
]
```

### Business

```json
[
  "view-counterparties",
  "edit-counterparties",
  "view-communications",
  "edit-communications",
  "view-orders",
  "edit-orders",
  "view-tasks",
  "edit-tasks",
  "view-applications",
  "create-applications",
  "edit-applications"
]
```

### Agent lifecycle / token management

```json
[
  "view-agents",
  "create-agents",
  "edit-agents",
  "manage-agent-tokens"
]
```

## Known but not guaranteed without runtime confirmation

Текущий backend docs/policies также упоминают дополнительные permission names,
которые могут существовать не в каждой БД. Не включай их в zero-token заявку,
пока они не подтверждены через `GET /api/permissions`.

Примеры:

```json
[
  "create-users",
  "create-orders",
  "create-tasks",
  "create-counterparties",
  "create-communications",
  "view-branches",
  "view-shops",
  "view-warehouses",
  "view-nomenclatures",
  "view-categories",
  "create-nomenclatures",
  "edit-nomenclatures",
  "create-categories",
  "edit-categories",
  "create-warehouses",
  "edit-warehouses",
  "create-shops",
  "edit-shops"
]
```

## Safe presets

### `read_only_assistant`

Базовый всегда-разумный помощник: читать заказы, задачи, клиентов, коммуникации,
список пользователей и приложения, но ничего не менять.

```json
[
  "view-orders",
  "view-tasks",
  "view-counterparties",
  "view-communications",
  "view-users",
  "view-applications"
]
```

### `business_assistant`

Широкий business-access для обычного помощника без доступа к админам, ролям,
правам и токенам. Это рекомендуемый preset для фразы
"максимальные разумные полномочия помощника".

```json
[
  "view-orders",
  "edit-orders",
  "view-tasks",
  "edit-tasks",
  "view-counterparties",
  "edit-counterparties",
  "view-communications",
  "edit-communications",
  "view-users",
  "view-applications",
  "create-applications",
  "edit-applications"
]
```

### `trusted_operator`

Усиленный операторский профиль. Используй только если владелец прямо хочет
разрешить изменения орг-структуры проекта, а не только бизнес-данных.

```json
[
  "view-orders",
  "edit-orders",
  "view-tasks",
  "edit-tasks",
  "view-counterparties",
  "edit-counterparties",
  "view-communications",
  "edit-communications",
  "view-users",
  "view-applications",
  "create-applications",
  "edit-applications",
  "edit-branches",
  "edit-departments"
]
```

## Dangerous / system rights

Не давай их обычному always-on assistant token по умолчанию.

```json
[
  "edit-admins",
  "edit-users",
  "edit-roles",
  "edit-permissions",
  "view-agents",
  "create-agents",
  "edit-agents",
  "manage-agent-tokens"
]
```

Коротко по смыслу:

- `edit-admins` - может менять owner/admin-зону;
- `edit-users` - может менять обычных пользователей;
- `edit-roles` / `edit-permissions` - может расширять access model;
- `view/create/edit-agents` / `manage-agent-tokens` - agent lifecycle и выпуск токенов.

## Phrase mapping for zero-token agents

Если human token недоступен:

- "дай доступ помощнику" -> используй `read_only_assistant`;
- "дай помощнику максимальные разумные полномочия" -> используй `business_assistant`;
- "нужен доверенный оператор" -> используй `trusted_operator`, но явно скажи, что
  это уже write-capable профиль;
- "нужен доступ создавать/крутить других агентов или токены" -> не выдавай это как
  обычный assistant preset; проси явное human confirmation и отдельное решение.

## Fallback rules

1. Если permission name есть в этом файле, можно использовать его в zero-token
   self-service request.
2. Если permission name нет в этом файле и нет ответа `GET /api/permissions`,
   не выдумывай его.
3. Если задача формулируется абстрактно, но без явной просьбы о write-доступе,
   стартуй с `read_only_assistant`.
4. Если пользователь сам просит широкий помощнический доступ без админки и без
   token-management, используй `business_assistant`.
5. Если нужны dangerous/system rights, остановись и явно назови риск: это уже не
   обычный assistant access, а повышенный административный доступ.
