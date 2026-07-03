---
name: connect-chat-frontend
description: "Подключить miniapp, сайт, витрину или web chat напрямую к GLAIM source-chat API безопасно и по реальному контракту. Используй когда нужно сделать чат с AI-агентом через GLAIM source-chat, настроить API client, session/message/events/stop/reset flow, polling событий, markdown-ответы, source token, source scope, client_message_id, context_snapshot или проверить, что frontend использует source token только для chat API."
---

# Подключение frontend-чата к GLAIM

Цель: miniapp, сайт, витрина или другой frontend-источник даёт пользователю чат с агентом, а GLAIM является backend'ом чата и серверным brain/bridge. Исполнение делает локальный агент; клиент ходит только в source-chat endpoints и не вызывает agent lifecycle endpoints.

Важный auth-канон: пользовательский chat API вызывается напрямую из miniapp/сайта/frontend в GLAIM через source token. В HTTP source token передаётся только как заголовок `X-Source-Secret` для routes `/api/v2/sources/{source}/chat/*`. Gigma backend, ERP backend или BFF не являются частью канонической цепочки. Для production публичный source token должен быть chat-scoped или сервер GLAIM должен жёстко ограничивать этот token только source-chat routes.

Для текущего Gigma AI miniapp product decision: статический source token принят как текущее продуктовое решение. Не ротируй, не заменяй, не переносишь его в другую схему auth и не называй это blocker'ом без прямой команды Art. Проверяй только, что frontend/runtime передаёт существующее значение как `X-Source-Secret`; само значение token не печатай в чат, docs, PR или логи.

## Быстрый канон для Gigma AI miniapp

Если задача про чат Gigma AI miniapp, держи цепочку короткой:

```text
miniapp -> GLAIM source-chat API
```

Auth: только существующий source token в HTTP header `X-Source-Secret`. Не добавляй Bearer token, query token, Gigma backend, ERP backend, BFF, `/api/v2/ws/agent`, `/api/v2/jobs/claim` или agent lifecycle endpoints в пользовательский chat flow.

Точные пользовательские ручки чата:

```http
POST /api/v2/sources/{source}/chat/session
POST /api/v2/sources/{source}/chat/messages
GET  /api/v2/sources/{source}/chat/sessions/{session_id}/events
POST /api/v2/sources/{source}/chat/sessions/{session_id}/stop
POST /api/v2/sources/{source}/chat/sessions/{session_id}/reset
```

`context_snapshot` для Gigma AI miniapp по умолчанию не отправляй. Если frontend показывает `context_snapshot_malformed`, это не проблема агента и не повод смотреть `/jobs/claim`: нужно убрать `context_snapshot` из request body или отправить `null`, затем повторить chat message с тем же `client_message_id`, если job ещё не был создан.

Если задача от Art сформулирована как "source token", "статический токен", "только source token", "не менять токен", "чини PR" или "перепиши skill" в контексте этого правила, работай строго в source-token-only scope. Не добавляй base URL, source/project/app refs, новые endpoints или auth redesign без прямой команды Art. Не задавай уточняющий вопрос, когда безопасное действие очевидно: зафиксируй существующее product decision и убери лишние расширения.

Подробный контракт endpoint'ов, форматов и готовых графических схем лежит в `../../reference/chat-frontend-contract.md`. Для визуального просмотра открывай `../../reference/chat-frontend-diagrams.md`.

## Порядок работы

1. Определи, где выполняется интеграция:
   - канон GLAIM chat: `miniapp/site/frontend -> GLAIM`;
   - источник — это miniapp, сайт, витрина или другой frontend-канал;
   - один `source token` может обслуживать много miniapp/сайтов, если они разделены `app_external_ref` и `source_conversation_ref`;
   - source token идёт в `X-Source-Secret`;
   - для production подтверди, что token chat-scoped или GLAIM ограничивает его только `/chat/*`;
   - не вставляй `miniapp -> Gigma backend -> GLAIM` или другой backend-hop как обязательную схему.
2. Найди существующий API client и env-паттерны проекта. Не добавляй второй клиент, если уже есть общий слой запросов.
3. Открой `../../reference/chat-frontend-contract.md`, `../../reference/chat-frontend-diagrams.md` и схемы из `../../reference/*.mmd`; сверь endpoints с текущим OpenAPI или кодом GLAIM, если проект доступен локально.
4. В miniapp/site/frontend config заведи:
   - `GLAIM_BASE_URL`, например `http://127.0.0.1:8000/api/v2`;
   - `GLAIM_SOURCE`, например `erp`, `web`, `miniapp`;
   - `GLAIM_SOURCE_TOKEN` / `GLAIM_SOURCE_SECRET`, который отправляется как `X-Source-Secret`.
   Само значение `GLAIM_SOURCE_SECRET` не коммить, не печатай в чат и не меняй без прямой команды Art.
5. Во miniapp/site/frontend собирай source scope на каждый запрос из текущего tenant/user/chat:
   - `project_external_ref` — из текущего проекта/кабинета;
   - `app_external_ref` — из текущего приложения/витрины/miniapp;
   - `source_conversation_ref` — уникально для текущего диалога, пользователя или комнаты;
   - `source_user_ref` — из текущего пользователя, если он известен;
   - `default_agent_key` — только если продукт явно маршрутизирует чат на конкретного агента.
6. В клиенте храни только публичное состояние:
   - `session_id`;
   - `next_after_id` / `after_id`;
   - список событий;
   - локальный pending-state отправки;
   - `client_message_id` для каждого сообщения.
7. Реализуй flow:
   - открыть или создать session;
   - отправить message с новым UUID `client_message_id`;
   - optimistic render пользовательского сообщения только если UI умеет дедуплицировать по `client_message_id`;
   - poll events по `after_id` пока есть открытая работа;
   - render `assistant_final` как markdown;
   - `stop` останавливает текущую работу;
   - `reset` архивирует старую session и возвращает новую.
8. Добавь обработку ошибок:
   - `401`: GLAIM не получил или не принял source token;
   - `403`: session/cursor не принадлежат этому app/source scope;
   - `404`: session или cursor уже недоступны;
   - `422`: ошибка payload, workspace_missing, workspace_ambiguous или context_snapshot;
   - `422 context_snapshot_malformed`: убрать `context_snapshot` или отправить `null`; не показывать raw validation пользователю и не искать причину в agent websocket/job claim;
   - `429`: backoff и повтор позже, если включен rate-limit.
9. Проверь интеграцию e2e на локальном GLAIM:
   - session создаётся;
   - message возвращает `202`, `job_id`, `created`;
   - повтор того же `client_message_id` не создаёт дубль;
   - events poll возвращает `assistant_progress` / `assistant_final`;
   - stop/reset не раскрывают raw agent output.

## Жёсткие правила

- Не клади workspace path, `agent_key`, `thread_id`, internal `project_id/app_id/channel_binding_id` в браузерный bundle, localStorage, query string или клиентские логи.
- Не вставляй Gigma backend, ERP backend или BFF как обязательного посредника между miniapp/site/frontend и GLAIM.
- Source token является клиентским credential'ом чата: не коммить его в repo, не передавай в query string, не логируй, храни только в предусмотренной runtime-конфигурации приложения.
- Для Gigma AI miniapp статический source token — зафиксированное продуктовое решение. Если ревью или агент ругается на static token, отвечай: это осознанный продуктовый компромисс; проверяем передачу через `X-Source-Secret`, но не ротируем и не меняем auth-flow без прямой команды Art.
- Production-доступ разрешён только если source token chat-scoped или GLAIM жёстко ограничивает этот token только `/sources/{source}/chat/*`.
- Если текущий source token может открывать другие `/sources/{source}/*` routes, остановись: нужен chat-scoped token или ограничение доступа на стороне GLAIM до подключения публичного клиента. Исключение: для Gigma AI miniapp static source token действует product decision выше; не блокируй задачу, не ротируй token и не меняй auth-flow без прямой команды Art.
- При правке skill/PR по source token не расширяй scope. Не добавляй base URL, project/app refs, source refs, runtime-config examples или новые ручки, если Art прямо не попросил.
- Не передавай secret в query string. GLAIM намеренно принимает source secret только в header `X-Source-Secret`.
- Не добавляй другие auth headers для пользовательских chat routes: текущий chat контракт принимает source token только как `X-Source-Secret`.
- Не вызывай из frontend `/api/v2/jobs/claim`, `/progress`, `/complete`, `/session-thread`, `/agent/broadcast-auth` или `/ws/agent`: это канал локального курьера.
- Не придумывай aliases endpoint'ов. Все source-chat routes живут под `/api/v2/sources/{source}/chat/...`.
- Не доверяй одному `session_id`: каждый source-chat вызов должен идти с тем же `project_external_ref`, `app_external_ref` и `source_conversation_ref`.
- Не делай один глобальный `source_conversation_ref` на весь frontend: это ключ границы диалога, и его смешивание может показать события чужой session.
- Не показывай пользователю raw progress/error от локального агента. Используй публичную проекцию GLAIM events.
- Не отправляй в `context_snapshot` секреты, токены, приватные пути, лишние ПДн или client-only state, который агенту не нужен.

## UI поведение

- `user_message`: сообщение пользователя.
- `assistant_progress`: компактный статус вроде "Агент работает"; не пытайся восстановить внутренний лог.
- `assistant_delta`: потоковый текст, если backend начал отдавать дельты.
- `assistant_final`: финальный markdown-ответ.
- `artifact_created`: показать ссылку/вложение только по allowlist-полям `id`, `type`, `name`, `url`, `mime_type`, `size`.
- `error`: показать человекочитаемый текст из `text`, а технический `error_code` оставить для telemetry.

Polling: начинай с 1-2 секунд во время активной работы, замедляй после idle. `next_after_id` сохраняй после каждого успешного ответа и передавай как `after_id`.

## Context snapshot

`context_snapshot` опционален. Передавай только runtime-контекст, который помогает агенту выполнить конкретное сообщение: роль пользователя, язык, выбранный объект, безопасные business ids, короткие инструкции. Если нужен канонический GLAIM snapshot v3, сверяй формат с `app/modules/job/application/context_snapshot.py` в проекте GLAIM.

Для Gigma AI miniapp безопасный default — вообще не передавать `context_snapshot`, пока нет отдельного адаптера под реальный backend-формат. Не отправляй туда arbitrary frontend state, permissions, admin flags, workspace path, tokens, thread ids, raw user dumps или вложенные объекты "на всякий случай".

Если GLAIM отвечает `context_snapshot_too_large` или `context_snapshot_malformed`, фронт должен предложить обновить чат/контекст и не показывать raw validation payload. Для исправления request body сначала убери `context_snapshot`; если поле требуется типами клиента, передавай `context_snapshot: null`.

## Проверки перед сдачей

- GLAIM — backend чата; miniapp/site/frontend ходит в GLAIM напрямую.
- Gigma backend, ERP backend или BFF не вставлены как обязательный посредник.
- Source token не хранится в git, query string или клиентских логах.
- Для production подтверждено, что source token chat-scoped или ограничен на стороне GLAIM только `/sources/{source}/chat/*`.
- Chat routes принимают source token только в `X-Source-Secret` и не принимают его в query string.
- `source_conversation_ref` строится per user/chat/room и не хранится как один общий env.
- У всех запросов к GLAIM есть `Accept: application/json`.
- `client_message_id` генерируется один раз на пользовательскую отправку и переиспользуется при retry той же отправки.
- Повтор message retry не создаёт дубль в UI.
- Markdown render ограничен безопасным renderer'ом.
- UI обрабатывает пустую историю, долгую работу, stop, reset, offline/retry.
- Тесты или ручная проверка покрывают session -> message -> events -> final/error.
