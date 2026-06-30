---
name: connect-chat-frontend
description: "Подключить frontend, miniapp, web chat или BFF к GLAIM source-chat API безопасно и по реальному контракту. Используй когда нужно сделать чат с AI-агентом через GLAIM, настроить API client, session/message/events/stop/reset flow, polling событий, markdown-ответы, source secret, source scope, client_message_id, context_snapshot или проверить, что frontend не раскрывает agent/source/control токены."
---

# Подключение frontend-чата к GLAIM

Цель: frontend даёт пользователю чат с агентом, а GLAIM остаётся серверным brain/bridge. Исполнение делает локальный агент; браузерный клиент не ходит в agent lifecycle endpoints и не получает секреты.

Подробный контракт endpoint'ов и форматов лежит в `../../reference/chat-frontend-contract.md`. Открывай его перед реализацией или ревью интеграции.

## Порядок работы

1. Определи, где выполняется интеграция:
   - production frontend: `frontend -> свой backend/BFF -> GLAIM`;
   - ERP/miniapp backend: `miniapp -> ERP -> GLAIM`;
   - локальный прототип: прямой вызов GLAIM допустим только без реального production-секрета.
2. Найди существующий API client и env-паттерны проекта. Не добавляй второй клиент, если уже есть общий слой запросов.
3. Открой `../../reference/chat-frontend-contract.md` и сверь endpoints с текущим OpenAPI или кодом GLAIM, если проект доступен локально.
4. В backend/BFF заведи server-only env:
   - `GLAIM_BASE_URL`, например `http://127.0.0.1:8000/api/v2`;
   - `GLAIM_SOURCE`, например `erp`, `web`, `miniapp`;
   - `GLAIM_SOURCE_SECRET`.
5. В backend/BFF собирай source scope на каждый запрос из текущего tenant/user/chat:
   - `project_external_ref` — из текущего проекта/кабинета;
   - `app_external_ref` — из текущего приложения/витрины/miniapp;
   - `source_conversation_ref` — уникально для текущего диалога, пользователя или комнаты;
   - `source_user_ref` — из текущего пользователя, если он известен;
   - `default_agent_key` — только если продукт явно маршрутизирует чат на конкретного агента.
6. Во frontend храни только публичное состояние:
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
   - `401`: backend неверно настроил/потерял source secret;
   - `403`: session/cursor не принадлежат этому app/source scope;
   - `404`: session или cursor уже недоступны;
   - `422`: ошибка payload, workspace_missing, workspace_ambiguous или context_snapshot;
   - `429`: backoff и повтор позже, если включен rate-limit.
9. Проверь интеграцию e2e на локальном GLAIM:
   - session создаётся;
   - message возвращает `202`, `job_id`, `created`;
   - повтор того же `client_message_id` не создаёт дубль;
   - events poll возвращает `assistant_progress` / `assistant_final`;
   - stop/reset не раскрывают raw agent output.

## Жёсткие правила

- Не клади `X-Source-Secret`, agent token, `X-Control-Secret`, workspace path, `agent_key`, `thread_id`, internal `project_id/app_id/channel_binding_id` в браузерный bundle, localStorage, query string или клиентские логи.
- Не передавай secret в query string. GLAIM намеренно принимает source secret только в header `X-Source-Secret`.
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

Если GLAIM отвечает `context_snapshot_too_large` или `context_snapshot_malformed`, фронт должен предложить обновить чат/контекст и не показывать raw validation payload.

## Проверки перед сдачей

- Source secret живёт только server-side.
- `source_conversation_ref` строится per user/chat/room и не хранится как один общий env.
- У всех запросов к GLAIM есть `Accept: application/json`.
- `client_message_id` генерируется один раз на пользовательскую отправку и переиспользуется при retry той же отправки.
- Повтор message retry не создаёт дубль в UI.
- Markdown render ограничен безопасным renderer'ом.
- UI обрабатывает пустую историю, долгую работу, stop, reset, offline/retry.
- Тесты или ручная проверка покрывают session -> message -> events -> final/error.
