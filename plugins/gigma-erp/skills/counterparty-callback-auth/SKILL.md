---
name: counterparty-callback-auth
description: "Спроектировать или проверить авторизацию приложения, витрины, сайта или fallback-miniapp через counterparty callback auth в Gigma ERP. Используй когда нужно добавить вход клиента по звонку через `/api/counterparty/callback_auth/init` и `/status`, разобрать `session_token`, `callback_number`, одноразовую выдачу `access_token`, App Token header, UCaller callback flow, rate limits или отличия от `send_password/login` и `miniapp-auth`."
---

# Counterparty callback auth в Gigma ERP

Цель: получить `counterparty` Sanctum token для клиента витрины через двухшаговый callback flow и не перепутать его с обычным `send_password/login` или signed-contact miniapp auth.

## Порядок работы

1. Открыть `../../reference/counterparty-callback-auth.md`.
2. Для общей картины auth-слоёв и заголовков сверить `../../reference/erp-api.md`.
3. Если задача про frontend витрины, дополнительно открыть раздел "Вход клиента" в `../../reference/frontend-api-rules.md`.
4. Если задача про backend-код, сначала проверить канонический контур:
   - `CallbackAuthController`
   - `CallbackAuthService`
   - `InitCallbackAuthRequest`
   - `StatusCallbackAuthRequest`
   - middleware `token`
   - rate limiters `callback_init_ip`, `callback_init`, `callback_status`

## Канонический flow

1. Стартовать callback-сессию:

```http
POST /api/counterparty/callback_auth/init
Token: <application_token>
Content-Type: application/json

{ "phone": "79991234567" }
```

Ожидать в ответе только:

- `session_token`
- `callback_number`
- `expires_at`

2. Показать номер для звонка и запустить polling статуса:

```http
POST /api/counterparty/callback_auth/status
Token: <application_token>
Content-Type: application/json

{ "session_token": "<session_token>" }
```

3. Интерпретировать ответ по состоянию:

- `pending` -> оставаться в polling и показывать `remaining_seconds`
- `verified` при первом чтении -> получить `access_token`
- `verified` при повторном чтении -> получить `already_consumed: true`
- `expired` -> предложить перезапуск `init`
- `404` -> считать сессию чужой, устаревшей или недоступной и начинать заново

4. После успешной верификации:

- сохранить `access_token`;
- гидрировать профиль через `GET /api/counterparty` с `Authorization: Bearer <access_token>`;
- для заказов, избранного, сохранённых карт и подписок слать оба заголовка: `Token` + `Authorization`.

## Жёсткие правила

- Не добавлять alias routes вроде `/api/app/callback-auth` или `/api/miniapps/.../callback_auth`, если задача живёт в counterparty-контуре.
- Не ожидать `CounterpartyResource` из `status`: этот flow возвращает токен, а не объект `counterparty`.
- Не использовать `session_token` как замену `access_token` и не хранить его как долгоживущую сессию.
- Не терять `Token: <application_token>` ни на `init`, ни на `status`.
- Не поллить `status` с другого client IP, если backend уже привязал сессию к исходному IP.
- Не вызывать `init` на каждый refresh: pending-сессия для того же телефона, проекта и IP переиспользуется.
- Не логировать `session_token`, `access_token` и полный `callback_number` в query string, browser analytics, чат или клиентские логи.
- Не смешивать этот flow с `miniapp-auth`: у них разные endpoint'ы и разный контракт ответа.

## Frontend-ориентиры

- Передавать телефон в пользовательском формате можно, но backend нормализует его к `7XXXXXXXXXX`; невалидный телефон даёт `422`.
- Показывать `callback_number`, `expires_at` и обратный отсчёт.
- Поллить `status` раз в 3-5 секунд; лимит `60/min` по IP делает слишком частый polling бессмысленным.
- На `already_consumed` не крутить polling бесконечно: сессия уже использована.
- После `verified` отдельно подтянуть профиль клиента; не ждать его в том же ответе.

## Инварианты backend

- TTL callback-сессии = 5 минут.
- `init` ограничен двумя лимитами: `200/hour` по IP и `3/hour` по нормализованному телефону внутри проекта.
- Сервис дополнительно режет сценарий с 5 активными pending-сессиями на один телефон в проекте.
- Pending-сессия переиспользуется только для того же телефона, проекта и client IP.
- `access_token` выдаётся только один раз на сессию.
- UCaller webhook подтверждает сессию только по тройке `callId` + нормализованный телефон + `confirmationNumber`.

## Проверки перед сдачей

- Happy path `init` создаёт или находит `Counterparty` внутри проекта витрины.
- Happy path `status` отдаёт токен один раз и помечает `access_token_consumed_at`.
- `pending` и `expired` корректно обрабатываются на UI.
- Чужой проект, другой client IP и неизвестный `session_token` приводят к `404`.
- Нет `Token` header -> `401`.
- После логина storefront-действия используют оба заголовка, а не один Bearer.
