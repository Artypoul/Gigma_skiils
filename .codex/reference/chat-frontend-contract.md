# GLAIM chat frontend contract

Источник правды: проект GLAIM, `docs/agent-bridge-design.md`,
`docs/plan-source-agent-chat-api.md`, `app/modules/chat/presentation/router.py`,
`app/modules/chat/presentation/schemas.py`, `tests/test_chat_endpoints.py`.

Все routes ниже идут под `/api/v2`. Source key в path должен совпадать с
`^[A-Za-z0-9_.-]+$`.

## Security model

Production схема:

```text
frontend / miniapp -> source backend / BFF -> GLAIM
```

`X-Source-Secret` является server-to-server секретом. Не отдавать его в браузер,
query string, client logs, crash reports или localStorage.

Control-plane token routes (`/source-tokens`) требуют:

```http
Authorization: Bearer <app-agent-token>
X-Control-Secret: <control-plane-secret>
```

Эти routes не относятся к пользовательскому чату и не вызываются из frontend.

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
Это граница диалога: формируй его на BFF из текущего пользователя, комнаты,
чата или внешнего conversation id. Один общий ref для разных пользователей
склеит их в одну session.

## Open or create session

```http
POST /api/v2/sources/{source}/chat/session
X-Source-Secret: <server-side-source-secret>
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
X-Source-Secret: <server-side-source-secret>
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
X-Source-Secret: <server-side-source-secret>
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
X-Source-Secret: <server-side-source-secret>
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
X-Source-Secret: <server-side-source-secret>
Accept: application/json
Content-Type: application/json
```

Body: same as stop.

Response `status` is `reset`; `session.session_id` points to the new reusable
session. Frontend must replace local `session_id`, clear local pending state and
start polling from the returned `next_after_id`.

## Error map

- `401 missing_source_secret`: BFF did not send `X-Source-Secret`.
- `401 invalid_source_token`: source secret does not match source/project/app.
- `403 session_not_owned` / `event_cursor_not_owned`: scope/session/cursor mismatch.
- `404 session_not_found` / `event_cursor_not_found`: stale local state.
- `422`: request validation, bad UUID, extra fields, empty message, malformed or oversized context, `workspace_missing`, `workspace_ambiguous`.

Validation responses intentionally do not echo raw input. Preserve that property
in BFF/frontend error handling.

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

- Source secret is absent from built frontend assets.
- Browser devtools network calls target BFF routes, not GLAIM source-chat routes, in production.
- BFF sends `X-Source-Secret` header, never query credentials.
- Retry of the same send is idempotent.
- Event polling uses `after_id` and does not duplicate rendered events.
- Markdown is rendered only for `format:"markdown"`.
- Stop and reset update UI state without exposing internal job details.
