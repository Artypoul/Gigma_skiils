# GLAIM chat frontend contract

Источник правды: проект GLAIM, `docs/agent-bridge-design.md`,
`docs/plan-source-agent-chat-api.md`, `app/modules/chat/presentation/router.py`,
`app/modules/chat/presentation/schemas.py`,
`app/modules/chat/application/use_cases.py`, `app/shared/presentation/auth.py`,
`tests/test_chat_endpoints.py`.

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

Для Gigma AI miniapp статический source token сейчас является осознанным
product decision. Не ротировать, не заменять и не переносить его в другой
auth-flow без прямой команды Art. Проверка должна доказывать только, что
существующий runtime secret отправляется как `X-Source-Secret`; само значение
token в docs, PR, логах и чатах не раскрывать.
Этот блок описывает только source token decision и не задаёт base URL,
source/project/app refs или новые endpoints.

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

## Thread switching and history

For user-facing miniapp chat, a "thread" is source-owned and is represented by
`source_conversation_ref`. It is not the local executor `thread_id`; executor
thread binding is an agent-only channel and must not be used by frontend code.

Product-ready switching flow:

1. The miniapp owns the thread list and stores each thread's
   `source_conversation_ref`, title/preview/unread state, cached `session_id` and
   cached `next_after_id`.
2. If the product lets users route chat to different agents, also store the
   thread's stable `default_agent_key`; local UI state is keyed by
   `source_conversation_ref + default_agent_key`.
3. When the user opens a thread, call `POST /api/v2/sources/{source}/chat/session`
   with that thread's `source_conversation_ref` and, when applicable,
   `default_agent_key`.
4. Replace local active state with returned `session.session_id`, render returned
   `events`, and store returned `next_after_id`.
5. Continue polling `GET /api/v2/sources/{source}/chat/sessions/{session_id}/events`
   with the same source scope and `after_id=next_after_id` until the page is
   empty or the cursor is unchanged; only then is local history caught up.
6. For live updates, keep polling with the last `next_after_id`.
7. When the user switches thread, stop polling the previous active thread and
   repeat the session/events flow with the new `source_conversation_ref` and
   `default_agent_key`.

Current source-chat API does expose session history endpoints inside the current
verified `source_conversation_ref`:

- `GET /api/v2/sources/{source}/chat/sessions`
- `GET /api/v2/sources/{source}/chat/sessions/{session_id}`
- `GET /api/v2/sources/{source}/chat/sessions/{session_id}/messages`

Use those real endpoints when the product needs server-side session history or
transcript pages for the active source conversation. Do not invent aliases such
as `GET /chat/threads` or `GET /chat/history`.

`reset` is not a thread switch. It archives the current session and creates a
new session for the same `source_conversation_ref`. To create a new UI thread,
the miniapp creates a new `source_conversation_ref` and opens `/chat/session`.

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

Response `events` is the initial visible history for the selected
`source_conversation_ref`; `next_after_id` is the cursor to continue polling.
It can be only the first page, so frontend should keep calling `/events` with
the latest `next_after_id` until it receives an empty page or unchanged cursor.
Frontend should deduplicate rendered history by `event.id`.

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
  "client_message_id": "00000000-0000-0000-0000-000000000999"
}
```

`context_snapshot` опционален. Для Gigma AI miniapp безопасный default — не
добавлять это поле, пока у frontend нет проверенного адаптера под формат GLAIM.
Если контекст нужен, добавляй его в тот же message body, а не отправляй
отдельным объектом:

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

## List sessions inside one source conversation

```http
GET /api/v2/sources/{source}/chat/sessions
X-Source-Secret: <source-token>
Accept: application/json
```

Query:

```text
project_external_ref=project-ext-1
app_external_ref=app-ext-1
source_conversation_ref=miniapp:user:1:application:2
include_archived=false
limit=50
cursor=<optional-session-id>
```

This is not a global "all threads for the whole app" endpoint. It lists sessions
only for the already verified `project/app/source_conversation_ref` scope.

Response:

```json
{
  "sessions": [
    {
      "session_id": "00000000-0000-0000-0000-000000000111",
      "status": "active",
      "title": "Проверка товаров",
      "last_message_preview": "Проверь товары",
      "active_job_id": null,
      "is_generating": false,
      "message_count": 4,
      "created_at": "2026-06-26T00:00:00Z",
      "updated_at": "2026-06-26T00:10:00Z",
      "archived_at": null
    }
  ],
  "next_cursor": null
}
```

## Session detail and rename

```http
GET   /api/v2/sources/{source}/chat/sessions/{session_id}
PATCH /api/v2/sources/{source}/chat/sessions/{session_id}
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Common GET query:

```text
project_external_ref=project-ext-1
app_external_ref=app-ext-1
source_conversation_ref=miniapp:user:1:application:2
```

PATCH body:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2",
  "title": "Новый заголовок"
}
```

The session title must not be blank; blank input fails with `422 session_title_empty`.

## Archive session

```http
POST /api/v2/sources/{source}/chat/sessions/{session_id}/archive
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

Response `status` is `archived`; current open work for that session is stopped
server-side.

## List transcript messages

```http
GET /api/v2/sources/{source}/chat/sessions/{session_id}/messages
X-Source-Secret: <source-token>
Accept: application/json
```

Query:

```text
project_external_ref=project-ext-1
app_external_ref=app-ext-1
source_conversation_ref=miniapp:user:1:application:2
include_archived=false
limit=100
cursor=<optional-message-id>
```

Response:

```json
{
  "messages": [
    {
      "id": "message-id",
      "role": "user",
      "status": "final",
      "content": "Проверь товары",
      "format": "text",
      "client_message_id": "00000000-0000-0000-0000-000000000999",
      "parent_message_id": null,
      "branch_root_message_id": null,
      "replaces_message_id": null,
      "version": 1,
      "created_at": "2026-06-26T00:00:00Z",
      "updated_at": "2026-06-26T00:00:00Z",
      "archived_at": null
    }
  ],
  "next_cursor": null
}
```

Use `/messages` when the UI needs transcript pages, edit/retry/regenerate lineage
or sidebar previews that are more stable than reconstructing everything from
operational `events` alone.

## Message actions

```http
POST /api/v2/sources/{source}/chat/messages/{message_id}/retry
POST /api/v2/sources/{source}/chat/messages/{message_id}/regenerate
POST /api/v2/sources/{source}/chat/messages/{message_id}/edit
X-Source-Secret: <source-token>
Accept: application/json
Content-Type: application/json
```

Retry/regenerate body:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2",
  "client_action_id": "00000000-0000-0000-0000-000000000777",
  "source_user_ref": "user-1",
  "context_snapshot": null
}
```

Edit body adds a new `message` field:

```json
{
  "project_external_ref": "project-ext-1",
  "app_external_ref": "app-ext-1",
  "source_conversation_ref": "miniapp:user:1:application:2",
  "client_action_id": "00000000-0000-0000-0000-000000000778",
  "message": "Уточни остатки по складу",
  "source_user_ref": "user-1",
  "context_snapshot": null
}
```

Each action returns `202` and the same `ChatMessageResponseSchema` shape as
`POST /chat/messages`. `client_action_id` is idempotency for the action itself;
generate a fresh UUID per retry/regenerate/edit user action.

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
Use the same `project_external_ref`, `app_external_ref` and
`source_conversation_ref` that were used to open the active session. A stale
`session_id` from another thread can return `403 session_not_owned` or
`404 session_not_found`; reopen `/chat/session` for the active
`source_conversation_ref` and replace local state.

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
start polling from the returned `next_after_id`. Reset keeps the same
`source_conversation_ref`; it does not select a different miniapp thread.

## WebSocket transports

There are two public websocket entry points.

### Events-only websocket

```http
POST /api/v2/sources/{source}/chat/sessions/{session_id}/events/ws-ticket
WS   /api/v2/sources/{source}/chat/sessions/{session_id}/events/ws
```

Use this when frontend needs live `chat.events` for one active session. The
socket authorizes either by:

- `X-Source-Secret` request header, or
- one-time ticket from `/events/ws-ticket`.

Server sends `connection.ready`, then `chat.events`, and may send `chat.error`.

### Rich chat websocket

```http
POST /api/v2/sources/{source}/chat/ws-ticket
WS   /api/v2/sources/{source}/chat/ws
```

Use this when the product wants one richer socket for session history, message
actions and live sync. The socket accepts either `X-Source-Secret` header or a
ticket from `/chat/ws-ticket`.

Supported client commands on this websocket:

- `ping`
- `sync`
- `session.open`
- `session.list`
- `session.get`
- `session.update`
- `session.archive`
- `session.stop`
- `session.reset`
- `message.list`
- `message.send`
- `message.retry`
- `message.regenerate`
- `message.edit`

Server response envelopes include:

- `connection.ready`
- `session.state`
- `sessions.page`
- `messages.page`
- `message.accepted`
- `chat.events`
- `chat.error`
- `pong`

Do not pass source token in query string for websocket auth; use the header or
issued ticket.

## Error map

- `401 missing_source_secret`: client did not send `X-Source-Secret`.
- `401 invalid_source_token`: source secret does not match source/project/app.
- `401 invalid_ws_ticket`: websocket ticket is invalid, expired or mismatched.
- `403 source_token_scope_denied`: chat-scoped token or websocket scope does not allow this conversation or mutable fields.
- `403 session_not_owned` / `event_cursor_not_owned`: scope/session/cursor mismatch.
- `403 message_not_owned`: message action was attempted outside the verified source scope.
- `404 session_not_found` / `event_cursor_not_found`: stale local state.
- `404 message_not_found`: message action points to a message not visible in this source scope.
- `422 context_snapshot_malformed`: `context_snapshot` есть в body, но не проходит backend-формат. Убери поле или отправь `null`; такой запрос отсекается до создания job.
- `422 session_title_empty`: rename request contains blank title.
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
- Retry/regenerate/edit use real `/chat/messages/{message_id}/...` routes with fresh `client_action_id`.
- Event polling uses `after_id` and does not duplicate rendered events.
- Thread switching is implemented by changing active `source_conversation_ref`
  and, for multi-agent UI, active `default_agent_key`; then reopening
  `/chat/session`, not by using executor `thread_id`.
- If the product uses server-side history, it uses the real `/chat/sessions`,
  `/chat/sessions/{session_id}` and `/chat/sessions/{session_id}/messages`
  routes inside the current `source_conversation_ref` scope.
- History catch-up continues from `session.events` through `/events?after_id=...`
  until an empty page or stable cursor before switching to live polling.
- No fake aliases such as `GET /chat/threads` or `GET /chat/history` are added.
- If websocket transport is used, it authenticates via `X-Source-Secret` header
  or issued ticket, not via query-string secret.
- Markdown is rendered only for `format:"markdown"`.
- Stop and reset update UI state without exposing internal job details.

## Minimal e2e smoke

Use the same `baseUrl`, `{source}`, `project_external_ref`,
`app_external_ref`, `source_conversation_ref` and `X-Source-Secret` that the
frontend runtime uses. Do not invent a production host or rotate the Gigma AI
miniapp static source token while running this smoke.

1. Create/open session with common scope.
2. Send message with `session_id`, `message` and a new `client_message_id`.
3. Poll events with the same scope and returned `next_after_id`.
4. Confirm that public events are visible: `user_message` and then
   `assistant_progress`, `assistant_final` or public `error`.
5. Retry the same message request with the same `client_message_id`; expect the
   same job and no duplicate UI message.

For Gigma AI miniapp, omit `context_snapshot` in the default smoke. If
`context_snapshot_malformed` appears, fix the message body first; `/jobs/claim`
and `/ws/agent` are not user-chat debugging endpoints.
