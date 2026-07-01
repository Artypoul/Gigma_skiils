---
name: request-agent-access
description: "Запросить или получить доступ MCP/AI-агента к Gigma ERP через self-service заявку на почту owner/admin, без owner Bearer token: /api/agent-access-requests, письмо владельцу, approval_token, status polling, consume и одноразовая выдача agent_token. Используй когда нужно подключить агента по email владельца, попросить владельца одобрить доступ, проверить статус заявки или забрать токен агента после approve."
---

# Request agent access в Gigma ERP

Цель: внешний MCP/AI-агент получает свой `agent_token` через публичную заявку владельцу проекта. Owner/admin подтверждает доступ из письма; агент не получает owner token и не логинится как человек.

Источник деталей: `../../reference/agent-access-request.md`. Если после заявки нужно проектировать MCP tools по ERP API, затем используй `mcp-agent-access`.

## Главная модель

- Агент сам создаёт заявку через `POST /api/agent-access-requests`.
- Backend отправляет письмо на `owner_email`, если это eligible owner/admin.
- Owner/admin открывает review link, проверяет права и делает approve/decline.
- Агент polling'ом проверяет `status` по `request_token`.
- После `approved` агент один раз вызывает `consume` и получает `agent_token.value`.
- `agent_token.value` показывается только один раз; после consume повторный вызов не возвращает token value.

## Перед стартом

1. Уточнить у владельца или пользователя:
   - owner/admin email проекта;
   - имя агента;
   - `agent_login`, если нужен стабильный логин;
   - минимальный список `permissions`;
   - цель доступа (`purpose`);
   - где MCP-сервер сохранит plain token.
2. Не просить owner Bearer token, пароль, OTP из письма или доступ к БД для обычного сценария.
3. Если права непонятны, просить минимальный read-only набор и расширять отдельной заявкой.

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
  "permissions": ["view-orders"],
  "purpose": "Read orders and prepare summaries"
}
```

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
- Не делать повторный consume как способ "посмотреть token ещё раз": value повторно не вернётся, нужен новый approve или token rotation.

## Проверка перед сдачей

- `POST /api/agent-access-requests` вернул `public_id`, `request_token`, `expires_at`.
- Owner получил письмо или пользователь подтвердил, что письмо не пришло из-за неизвестного/неподходящего owner email.
- `status` перешёл в `approved`, `declined` или `expired`; нет бесконечного polling.
- `consume` вызван только после `approved`.
- `agent_token.value` сохранён только в secret storage и не попал в репозиторий/чат.
- `GET /api/user` с agent token возвращает созданного агента.
- MCP tools используют allowlist и не имеют generic ERP proxy.

