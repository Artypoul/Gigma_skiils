---
name: request-agent-access
description: "Запросить или получить доступ MCP/AI-агента к Gigma ERP через self-service заявку на почту owner/admin, без owner Bearer token: новый агент или новый ПК без токена, /api/agent-access-requests, письмо владельцу, approval_token, status polling, consume и одноразовая выдача agent_token. Используй когда нужно подключить агента по email владельца, попросить владельца одобрить доступ, проверить статус заявки, забрать токен агента после approve или объяснить пошаговый flow получения MCP-доступа."
---

# Request agent access в Gigma ERP

Цель: внешний MCP/AI-агент получает свой `agent_token` через публичную заявку владельцу проекта. Owner/admin подтверждает доступ из письма; агент не получает owner token и не логинится как человек.

Источник деталей: `../../reference/agent-access-request.md`.
Права и безопасные пресеты для zero-token сценария: `../../reference/agent-permission-profiles.md`.
Если после заявки нужно проектировать MCP tools по ERP API, затем используй `mcp-agent-access`.

## Главная модель

- Агент сам создаёт заявку через `POST /api/agent-access-requests`.
- Backend отправляет письмо на `owner_email`, если это eligible owner/admin.
- Owner/admin открывает review link, проверяет права и делает approve/decline.
- Агент polling'ом проверяет `status` по `request_token`.
- После `approved` агент один раз вызывает `consume` и получает `agent_token.value`.
- `agent_token.value` показывается только один раз; после consume повторный вызов не возвращает token value.

## Как выбрать permissions для заявки

- Не существует отдельного "списка прав для MCP": в заявке используются обычные ERP permissions из таблицы `permissions` с `guard_name=user`.
- Если у человека уже есть human Bearer token, канонический полный список имён читать через `GET /api/permissions`.
- Если human token недоступен, не зависай на вопросе "назовите exact rights": используй поддерживаемый offline reference `agent-permission-profiles.md`.
- Специальные agent-management permissions:
  - `view-agents`;
  - `create-agents`;
  - `edit-agents`;
  - `manage-agent-tokens`.
- Для обычных MCP tool'ов запрашивать только бизнес-права под реальные endpoint'ы. Для zero-token сценария используй готовые пресеты:
  - `read_only_assistant` - всегда-разумный стартовый read-only доступ;
  - `business_assistant` - широкий business-access без админских/system прав;
  - `trusted_operator` - более сильный write-capable профиль только по явной просьбе владельца.
- Фраза "максимальные разумные полномочия помощника" по умолчанию означает `business_assistant`, а не admin/system access.
- Не включай `edit-admins`, `edit-permissions`, `manage-agent-tokens`, `view-agents`, `create-agents`, `edit-agents`, `edit-users`, `edit-roles` в обычный assistant preset.
- Если нужное право не подтверждено ни `GET /api/permissions`, ни `agent-permission-profiles.md`, не выдумывай его.

## Перед стартом

1. Уточнить у владельца или пользователя:
   - ERP API base URL, по умолчанию `https://api.gigma.ru`;
   - owner/admin email проекта;
   - имя агента;
   - `agent_login`, если нужен стабильный логин;
   - либо конкретный список `permissions`, либо название готового профиля (`read_only_assistant`, `business_assistant`, `trusted_operator`);
   - цель доступа (`purpose`);
   - где MCP-сервер сохранит plain token.
2. Не просить owner Bearer token, пароль, OTP из письма или доступ к БД для обычного сценария.
3. Если права описаны расплывчато:
   - "просто помощник" -> `read_only_assistant`;
   - "максимальные разумные полномочия помощника" -> `business_assistant`;
   - "доверенный оператор" -> `trusted_operator`, но явно сказать, что это write-capable профиль.
4. Если пользователь просит agent lifecycle или security/system access, не маскируй это под assistant profile: назови риск и проси отдельное подтверждение.

## Zero-token quickstart

Используй этот блок, когда агент на новом ПК говорит "у меня нет MCP-доступа", "нет agent token" или "как подключиться к MCP". Смысл: сначала получить `agent_token`, потом уже строить MCP tools через `mcp-agent-access`.

1. Собрать минимальные входные данные:
   - `ERP_API_BASE_URL` (`https://api.gigma.ru`, если пользователь не дал другой);
   - `owner_email`;
   - `agent_name`, например `Art PC MCP Agent`;
   - стабильный `agent_login`, например `art-pc-mcp-agent`;
   - `permissions`: либо точный подтверждённый список, либо готовый preset из `agent-permission-profiles.md`;
   - `purpose`, зачем агенту доступ;
   - локальный путь для секрета, например `%USERPROFILE%\.gigma\mcp-agent.env`.
2. Создать заявку через `POST /api/agent-access-requests`. Сохранить `public_id` и `request_token` локально. В чат вывести только `public_id`, `expires_at` и статус "ждём approve"; `request_token` не выводить.
3. Сказать пользователю: owner/admin должен открыть письмо "Запрос доступа MCP-агента" и одобрить доступ. Не просить owner token.
4. Polling статуса делать каждые 10-30 секунд до `approved`, `declined`, `expired` или 30 минут.
5. После `approved` вызвать `consume` один раз. `agent_token.value` сразу записать в secret storage MCP-сервера; в stdout/чат/PR body не печатать.
6. Проверить `GET /api/user` с новым `Authorization: Bearer <agent_token>`. Если вернулся ожидаемый `login` агента и нужные permissions, доступ получен.
7. Перейти к `mcp-agent-access`: описать exact allowlist `method + path` для каждого MCP tool и проверить positive/negative access.

Рекомендуемые zero-token defaults:

- если пользователь не уточнил профиль, но просит обычный доступ помощника -> `read_only_assistant`;
- если просит "максимальные разумные полномочия помощника" -> `business_assistant`;
- если просит операторский write-capable доступ -> `trusted_operator`, но не добавляй system rights.

Безопасный PowerShell-скелет для нового ПК:

```powershell
$baseUrl = $env:ERP_API_BASE_URL
if (-not $baseUrl) { $baseUrl = "https://api.gigma.ru" }

$payload = @{
  owner_email = "<owner-email>"
  agent_name = "Art PC MCP Agent"
  agent_login = "art-pc-mcp-agent"
  permissions = @(
    "view-orders",
    "view-tasks",
    "view-counterparties",
    "view-communications",
    "view-users",
    "view-applications"
  )
  purpose = "MCP agent access for read-only ERP assistant"
} | ConvertTo-Json -Depth 5

$created = Invoke-RestMethod `
  -Method Post `
  -Uri "$baseUrl/api/agent-access-requests" `
  -Headers @{ Accept = "application/json" } `
  -ContentType "application/json" `
  -Body $payload

$stateDir = Join-Path $env:USERPROFILE ".gigma"
New-Item -ItemType Directory -Force $stateDir | Out-Null
@{
  public_id = $created.request.public_id
  request_token = $created.request.request_token
  expires_at = $created.request.expires_at
} | ConvertTo-Json -Depth 5 | Set-Content -NoNewline -Encoding utf8 -LiteralPath (Join-Path $stateDir "agent-access-request.json")

[pscustomobject]@{
  public_id = $created.request.public_id
  expires_at = $created.request.expires_at
  next = "wait_owner_approve"
}
```

Polling + consume после заявки:

```powershell
$baseUrl = $env:ERP_API_BASE_URL
if (-not $baseUrl) { $baseUrl = "https://api.gigma.ru" }
$state = Get-Content -Raw -LiteralPath "$env:USERPROFILE\.gigma\agent-access-request.json" | ConvertFrom-Json

do {
  $status = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/api/agent-access-requests/$($state.public_id)/status" `
    -Headers @{ Accept = "application/json" } `
    -ContentType "application/json" `
    -Body (@{ request_token = $state.request_token } | ConvertTo-Json)

  [pscustomobject]@{
    status = $status.status
    expires_at = $status.expires_at
  }

  if ($status.status -eq "pending") { Start-Sleep -Seconds 15 }
} while ($status.status -eq "pending")

if ($status.status -eq "approved") {
  $consume = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/api/agent-access-requests/$($state.public_id)/consume" `
    -Headers @{ Accept = "application/json" } `
    -ContentType "application/json" `
    -Body (@{ request_token = $state.request_token } | ConvertTo-Json)

  $agentToken = $consume.agent_token.value
  "GIGMA_MCP_AGENT_TOKEN=$agentToken" |
    Set-Content -NoNewline -Encoding utf8 -LiteralPath "$env:USERPROFILE\.gigma\mcp-agent.env"

  $verified = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/api/user" `
    -Headers @{
      Accept = "application/json"
      Authorization = "Bearer $agentToken"
    }

  [pscustomobject]@{
    status = $consume.status
    agent_login = $consume.agent.login
    verified_login = $verified.user.login
    token_saved = "$env:USERPROFILE\.gigma\mcp-agent.env"
  }
} else {
  [pscustomobject]@{
    status = $status.status
    next = "create_new_request_or_ask_owner"
  }
}
```

Если используешь эти команды как агент, не выводи `$created`, `$state`, `$consume` целиком: там есть секреты.

## Runbook

1. Создать заявку:

```http
POST /api/agent-access-requests
Accept: application/json
Content-Type: application/json

{
  "owner_email": "owner@example.com",
  "agent_name": "MCP Order Agent",
  "agent_login": "mcp-order-agent",
  "permissions": [
    "view-orders",
    "view-tasks",
    "view-counterparties",
    "view-communications",
    "view-users",
    "view-applications"
  ],
  "purpose": "Read-only ERP assistant"
}
```

Если пользователь попросил "максимальные разумные полномочия помощника", safe request body по умолчанию такой:

```json
{
  "owner_email": "owner@example.com",
  "agent_name": "Business Assistant",
  "agent_login": "business-assistant",
  "permissions": [
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
  ],
  "purpose": "Broad business assistant access without admin or token-management rights"
}
```

Это рекомендуемый preset, пока не появился runtime ответ `GET /api/permissions`.

Сохранить из ответа `request.public_id`, `request.request_token`, `request.expires_at`. Не печатать `request_token` в чат целиком.

2. Ждать owner approve:

```http
POST /api/agent-access-requests/{public_id}/status
Accept: application/json
Content-Type: application/json

{
  "request_token": "<request_token>"
}
```

Polling: каждые 10-30 секунд до `approved`, `declined`, `expired` или таймаута. Заявка живёт 30 минут.

3. После `approved` забрать token:

```http
POST /api/agent-access-requests/{public_id}/consume
Accept: application/json
Content-Type: application/json

{
  "request_token": "<request_token>"
}
```

Сразу сохранить `agent_token.value` в секретное хранилище MCP-сервера. В чат, PR body, логи и файлы репозитория token не писать.

4. Проверить token:

```http
GET /api/user
Authorization: Bearer <agent_token>
Accept: application/json
```

Затем проверить каждый MCP tool: один разрешённый endpoint должен пройти, похожий запрещённый должен дать `403` или ожидаемый deny.

5. Если `status` вернул `expired`, `declined` или `consume` вернул `already_consumed`, не пытаться угадать токен. Создать новую заявку или попросить владельца сделать token rotation через admin flow.

## Owner review

Owner/admin получает письмо "Запрос доступа MCP-агента" со ссылкой:

```text
/api/agent-access-requests/{public_id}/review#approval_token=...
```

`approval_token` должен идти только во fragment/body, не в query string. Backend отклоняет `approval_token` в query для approve/decline/review.

Owner может одобрить все запрошенные permissions или более узкий subset. Backend не разрешит approve прав шире запрошенных или шире прав owner/admin.

## Жёсткие запреты

- Не использовать `/api/send_password` и `/api/login` для agent-user: агенты не логинятся password flow.
- Не добывать owner token через БД/таблицу `passwords` для обычного доступа агента.
- Не передавать `request_token`, `approval_token` или `agent_token.value` в query string, PR body, issue comments, shell history или клиентские логи.
- Не создавать generic REST/curl proxy MCP tool; каждый tool должен иметь explicit allowlist `method + path`.
- Не запрашивать owner/admin permissions для агента по умолчанию.
- Не маскировать `edit-admins`, `edit-permissions`, `manage-agent-tokens`, `view-agents`, `create-agents`, `edit-agents`, `edit-users` или `edit-roles` как "обычный доступ помощника".
- Не делать повторный consume как способ "посмотреть token ещё раз": value повторно не вернётся, нужен новый approve или token rotation.

## Проверка перед сдачей

- `POST /api/agent-access-requests` вернул `public_id`, `request_token`, `expires_at`.
- Если human token отсутствовал, permissions выбраны либо из `agent-permission-profiles.md`, либо из уже подтверждённого runtime списка, а не придуманы на ходу.
- Owner получил письмо или пользователь подтвердил, что письмо не пришло из-за неизвестного/неподходящего owner email.
- `status` перешёл в `approved`, `declined` или `expired`; нет бесконечного polling.
- `consume` вызван только после `approved`.
- `agent_token.value` сохранён только в secret storage и не попал в репозиторий/чат.
- `GET /api/user` с agent token возвращает созданного агента.
- MCP tools используют allowlist и не имеют generic ERP proxy.
