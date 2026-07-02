# GLAIM chat frontend contract

Источник правды: проект GLAIM, `docs/agent-bridge-design.md`,
`docs/plan-source-agent-chat-api.md`, `app/modules/chat/presentation/router.py`,
`app/modules/chat/presentation/schemas.py`, `tests/test_chat_endpoints.py`.

Все routes ниже идут под `/api/v2`. Source key в path должен совпадать с
`^[A-Za-z0-9_.-]+$`.

## Visual references

- `chat-frontend-diagrams.md` — страница с готовыми PNG-превью всех схем.
- `chat-frontend-flow.mmd/.svg/.png` — каноническая архитектура: miniapp/site/frontend ходит в GLAIM source-chat API, локальный агент только исполняет job.
- `chat-auth-boundaries.mmd/.svg/.png` — source-token-only границы: frontend ходит только в chat routes.
- `chat-runtime-sequence.mmd/.svg/.png` — последовательность session -> message -> queue -> agent -> events.
- `chat-ui-state-machine.mmd/.svg/.png` — минимальная state machine для ChatGPT-like UI.

## Security model

Основная схема сохранена отдельно в `chat-frontend-flow.mmd`,
`chat-frontend-flow.svg` и `chat-frontend-flow.png`.

Production канон:

```text
miniapp / site / web chat / other frontend source -> GLAIM source-chat API
```

Gigma backend, ERP backend или BFF не являются частью канонической цепочки.
Агент не должен вставлять `miniapp -> Gigma backend -> GLAIM` или другой
backend-hop как обязательную схему подключения чата.

Пользовательский chat API авторизуется source token'ом через
заголовок:

```http
X-Source-Secret: <source-token>
```

Miniapp/site/frontend вызывает GLAIM напрямую с `X-Source-Secret`. В таком
режиме source token становится клиентским credential'ом чата: не коммитить его в
repo, не передавать в query string, не логировать и использовать только для
source-chat routes.

Production-доступ из публичного клиента разрешён только если source token
chat-scoped или GLAIM жёстко ограничивает этот token только
`/sources/{source}/chat/*`. Если текущий source token может открывать другие
`/sources/{source}/*` routes, сначала нужно выделить chat-scoped source token
или ограничить доступ на стороне GLAIM.

Gigma AI miniapp production preset:

```text
GLAIM_BASE_URL=https://agentapi.gigma.ru/api/v2
source=miniapp
project_external_ref=gigma-ai
project_name=Gigma AI
app_external_ref=gigma-ai
app_name=Gigma AI
```

Для Gigma AI miniapp статический source token сейчас является осознанным
product decision. Не ротировать, не заменять и не переносить его в другой
auth-flow без прямой команды Art. Проверка должна доказывать, что существующий
runtime secret отправляется только как `X-Source-Secret` и проходит backend auth;
само значение token в docs, PR, логах и чатах не раскрывать.

Этот frontend contract описывает только пользовательский chat path. Выпуск,
ротация и отзыв source token не являются частью frontend-чата и не должны
появляться на схеме подключения чата.

## Common scope

Каждый source-chat вызов должен нести один и тот же scope:

```json
{
  "project_external_ref": "project-ext-1",
  "project_name": "Project name",
  "app_external_ref": "app-ext-1",
  "app_name": "App name",
  "source_conversation_ref": "miniapp:user:1:application:2",
  "source_user_ref": "user-1",
  "default_agent_key": "agent-1"
}
```

Минимально обязательны:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2"
}
```

GLAIM сам upsert'ит `projects`, `apps`, `channel_bindings` по этому scope.

Не хранить `source_conversation_ref` как один глобальный env для всего frontend.
Это граница диалога: формируй его во frontend/miniapp из текущего пользователя,
комнаты, чата или внешнего conversation id. Один общий ref для разных
пользователей склеит их в одну session.

## Open or create session

```http
POST /api/v2/sources/{source}/chat/session
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Body: common scope.

Response:

```json
{
  "session": {
    "session_id": "00000000-0000-0000-0000-000000000111",
    "status": "new",
    "last_activity_at": "2026-06-26T00:00:00Z",
    "created_at": "2026-06-26T00:00:00Z",
    "updated_at": "2026-06-26T00:00:00Z"
  },
  "events": [],
  "next_after_id": null
}
```

`workspace_missing` или `workspace_ambiguous` приходят как `422`: сначала нужно
настроить активный agent workspace для этого app/source.

## Send message

```http
POST /api/v2/sources/{source}/chat/messages
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Body:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2",
  "source_user_ref": "user-1",
  "session_id": "00000000-0000-0000-0000-000000000111",
  "message": "Проверь товары",
  "client_message_id": "00000000-0000-0000-0000-000000000999",
  "context_snapshot": {
    "mode": "customer_support_chat",
    "language": "ru"
  }
}
```

Response status: `202`.

```json
{
  "job_id": "00000000-0000-0000-0000-000000000222",
  "run_id": "00000000-0000-0000-0000-000000000888",
  "session_id": "00000000-0000-0000-0000-000000000111",
  "status": "queued",
  "created": true,
  "events": [
    {
      "id": "00000000-0000-0000-0000-000000000333",
      "job_id": "00000000-0000-0000-0000-000000000222",
      "type": "user_message",
      "created_at": "2026-06-26T00:00:00Z",
      "text": "Проверь товары",
      "data": {
        "client_message_id": "00000000-0000-0000-0000-000000000999"
      },
      "format": "text",
      "artifact": null
    }
  ],
  "next_after_id": "00000000-0000-0000-0000-000000000333"
}
```

Idempotency: GLAIM строит ключ
`chat:session:{session_id}:message:{client_message_id}`. Retry той же отправки
с тем же UUID возвращает тот же job и `created:false`.

## Poll events

```http
GET /api/v2/sources/{source}/chat/sessions/{session_id}/events
X-Source-Secret: <source-token>
Accept: application/json
```

Query:

```text
project_external_ref=project-ext-1
app_external_ref=app-ext-1
source_conversation_ref=miniapp:user:1:application:2
after_id=<last_next_after_id>
limit=100
```

`limit` range: `1..200`. `after_id` is optional UUID.

Response:

```json
{
  "events": [
    {
      "id": "event-id",
      "job_id": "job-id",
      "type": "assistant_final",
      "created_at": "2026-06-26T00:00:00Z",
      "text": "**Готово**",
      "data": {},
      "format": "markdown",
      "artifact": null
    }
  ],
  "next_after_id": "event-id"
}
```

Public event types:

- `user_message`
- `assistant_progress`
- `assistant_delta`
- `assistant_final`
- `error`
- `artifact_created`

Hidden/internal event types such as `stderr`, `heartbeat`, raw `stdout` and
internal progress are not exposed as raw text.

## Stop session

```http
POST /api/v2/sources/{source}/chat/sessions/{session_id}/stop
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Body:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2"
}
```

Response `status` is `stopped` when open work was stopped, or `no_active_job`
when there was nothing active.

## Reset session

```http
POST /api/v2/sources/{source}/chat/sessions/{session_id}/reset
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Body: same as stop.

Response `status` is `reset`; `session.session_id` points to the new reusable
session. Frontend must replace local `session_id`, clear local pending state and
start polling from the returned `next_after_id`.

## Error map

- `401 missing_source_secret`: client did not send `X-Source-Secret`.
- `401 invalid_source_token`: source secret does not match source/project/app.
- `403 session_not_owned` / `event_cursor_not_owned`: scope/session/cursor mismatch.
- `404 session_not_found` / `event_cursor_not_found`: stale local state.
- `422`: request validation, bad UUID, extra fields, empty message, malformed or oversized context, `workspace_missing`, `workspace_ambiguous`.

Validation responses intentionally do not echo raw input. Preserve that property
in frontend/adapter error handling.

## Frontend state machine

Recommended minimum:

```text
booting -> ready -> sending -> waiting_agent -> ready
                       |             |
                       v             v
                    failed        stopped/reset
```

Keep `client_message_id` with the pending message until the send result is known.
On network retry, reuse the same UUID for the same user action. On a new user
action, generate a new UUID.

## Verification checklist

- GLAIM is the chat backend; miniapp/site/frontend calls GLAIM directly.
- No Gigma backend, ERP backend or BFF hop is inserted as the mandatory chat path.
- Browser devtools network calls target GLAIM `/api/v2/sources/{source}/chat/*` routes.
- Client sends `X-Source-Secret` header, never query credentials.
- Source token is absent from git, query string and client logs.
- For Gigma AI miniapp, the existing static source token remains unchanged unless Art explicitly asks for rotation or a new auth-flow.
- Production source token is chat-scoped or server-restricted to `/sources/{source}/chat/*`.
- Retry of the same send is idempotent.
- Event polling uses `after_id` and does not duplicate rendered events.
- Markdown is rendered only for `format:"markdown"`.
- Stop and reset update UI state without exposing internal job details.
