# Counterparty callback auth

Детальный reference для входа клиента в storefront/app через `callback_auth` в Gigma ERP.

## Когда читать

- Нужно добавить вход по звонку в сайт, витрину или приложение.
- Нужно проверить fallback к `miniapp-auth` или обычному `send_password/login`.
- Нужно понять точный контракт `init`/`status`, а не общий auth слой.

## Канонические endpoint'ы

Оба endpoint'а живут в counterparty-контуре и требуют App Token:

```http
POST /api/counterparty/callback_auth/init
POST /api/counterparty/callback_auth/status
Token: <application_token>
Accept: application/json
Content-Type: application/json
```

Новый публичный alias route не добавлять.

## Request / response

### 1. Init

```http
POST /api/counterparty/callback_auth/init
Token: <application_token>
Content-Type: application/json
```

```json
{
  "phone": "+7 (900) 123-45-67"
}
```

Backend нормализует телефон к `7XXXXXXXXXX` и принимает только этот итоговый формат. Невалидный payload -> `422`.

Успешный ответ:

```json
{
  "session_token": "<opaque session token>",
  "callback_number": "79001000011",
  "expires_at": "2026-07-03T01:23:45+00:00"
}
```

Важно:

- `access_token` на шаге `init` не возвращается;
- для того же телефона, проекта и client IP pending-сессия переиспользуется;
- UCaller не должен вызываться повторно, если backend вернул старую pending-сессию.

### 2. Status

```http
POST /api/counterparty/callback_auth/status
Token: <application_token>
Content-Type: application/json
```

```json
{
  "session_token": "<opaque session token>"
}
```

#### Pending

```json
{
  "status": "pending",
  "expires_at": "2026-07-03T01:23:45+00:00",
  "server_time": "2026-07-03T01:20:10+00:00",
  "remaining_seconds": 215
}
```

#### Verified, first consume

```json
{
  "status": "verified",
  "access_token": "12|plainSanctumToken"
}
```

#### Verified, second consume

```json
{
  "status": "verified",
  "already_consumed": true
}
```

#### Expired

```json
{
  "status": "expired",
  "expires_at": "2026-07-03T01:23:45+00:00",
  "server_time": "2026-07-03T01:25:01+00:00",
  "remaining_seconds": 0
}
```

## Поведение и ограничения

- TTL callback-сессии: 5 минут.
- `access_token` можно получить только один раз на сессию.
- Сессия привязана к `project_id` Application и может быть скрыта как `404`, если запрос пришёл из другого проекта.
- Если `client_ip` был сохранён на `init`, polling `status` с другого IP тоже даст `404`.
- Verified-сессия после expiry больше не выдаёт токен и становится `expired`.

## Rate limits и анти-спам

- `callback_init_ip`: `200/hour` на IP.
- `callback_init`: `3/hour` на нормализованный телефон внутри проекта.
- `callback_status`: `60/min` на IP.
- Внутри сервиса есть дополнительный барьер: максимум 5 активных pending-сессий на телефон внутри проекта.

Практический совет для frontend: polling `status` раз в 3-5 секунд укладывается в лимит и не создаёт лишний шум.

## После успешной верификации

1. Сохранить `access_token`.
2. Гидрировать профиль:

```http
GET /api/counterparty
Authorization: Bearer <access_token>
Accept: application/json
```

3. Для storefront-операций клиента слать оба заголовка:

```http
Token: <application_token>
Authorization: Bearer <access_token>
```

Это нужно для заказов, избранного, сохранённых карт и подписок.

## Отличия от соседних auth flow

| Flow | Endpoint | Что приходит в ответе | Когда использовать |
|---|---|---|---|
| Обычный клиентский логин | `/api/counterparty/send_password` + `/login` | `counterparty.access_token.value` после `login` | Когда доступен код/пароль |
| Miniapp signed contact | `/api/counterparty/miniapps/{provider}/contact_auth` | `counterparty` resource c `access_token.value` | Когда provider даёт подписанный proof |
| Callback auth | `/api/counterparty/callback_auth/init` + `/status` | `session_token/callback_number`, затем отдельный `access_token` | Когда нужен вход по звонку или fallback |

Не ожидать miniapp-подобный `counterparty` response из `callback_auth/status`.

## UCaller webhook

UCaller webhook сам по себе не логинит frontend. Он только переводит pending-сессию в `verified`, если совпали:

- `callId`
- нормализованный `clientNumber`
- `confirmationNumber`
- session status = `pending`
- session not expired

Frontend всё равно должен забрать токен отдельным `POST /api/counterparty/callback_auth/status`.
