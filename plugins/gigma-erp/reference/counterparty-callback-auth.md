# Counterparty callback auth

Детальный reference для входа клиента в storefront/app через `callback_auth` в Gigma ERP.

## Когда читать

- Нужно добавить вход по звонку в сайт, витрину или приложение.
- Нужно проверить fallback к `miniapp-auth` или обычному `send_password/login`.
- Нужно понять точный контракт `init`/`status`/`exchange`, а не общий auth слой.
- Нужно, чтобы свой backend проверял выданный токен через introspection.

## Канонические endpoint'ы

Все три endpoint'а живут в counterparty-контуре и требуют App Token:

```http
POST /api/counterparty/callback_auth/init
POST /api/counterparty/callback_auth/status
POST /api/counterparty/callback_auth/exchange
Token: <application_token>
Accept: application/json
Content-Type: application/json
```

Новый публичный alias route не добавлять. Все три отвечают с `Cache-Control: no-store`.

Отдельно, вне App Token, живёт server-to-server проверка токена:

```http
POST /api/counterparty/auth/introspect
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
```

## client_nonce

`client_nonce` — клиентский секрет одной попытки входа: 32-128 символов base64url (`A-Za-z0-9-_`), криптослучайные. Он обязателен во всех трёх запросах.

- Сервер хранит только `HMAC-SHA256(nonce)` и использует его как единственное доказательство, что `status` и `exchange` делает владелец браузера, начавший `init`.
- Один nonce = одна попытка. Повторный `init` с тем же nonce -> `409`.
- Новая попытка входа -> новый nonce.

## Режимы интеграции

### Server-wrapper, preferred

Использовать, если у приложения есть свой серверный слой или оно само ставит auth cookies.

Рекомендуемый публичный контракт приложения:

- browser -> ваш `POST /login/callback-auth/init`
- ваш сервер генерирует `client_nonce` и вызывает Gigma `POST /api/counterparty/callback_auth/init`
- ваш сервер сохраняет `session_token` и `client_nonce` в `httpOnly` cookie или серверной сессии
- browser получает только `callback_number` и `expires_at`
- browser -> ваш `POST /login/callback-auth/status`
- при `verified` ваш сервер сам вызывает Gigma `exchange`, ставит финальную auth cookie и очищает callback-session

В этом режиме browser не должен видеть ни `session_token`, ни `client_nonce`.

### Direct storefront, narrow fallback

Использовать только если frontend ходит в Gigma напрямую и отдельного backend/BFF нет.

В этом режиме browser сам вызывает `init`, `status` и `exchange`, но `session_token` и `client_nonce` держит только в памяти текущей вкладки. Не восстанавливать их из `localStorage`, `sessionStorage`, URL или обычных cookies.

## Request / response

### 1. Init

```http
POST /api/counterparty/callback_auth/init
Token: <application_token>
Content-Type: application/json
```

```json
{
  "phone": "+7 (900) 123-45-67",
  "client_nonce": "R2xvYmFsTm9uY2VFeGFtcGxlMTIzNDU2Nzg5MA"
}
```

Backend нормализует телефон к `7XXXXXXXXXX` и принимает только этот итоговый формат. Невалидный payload -> `422`.

Успешный ответ:

```json
{
  "session_token": "<opaque session token>",
  "callback_number": "79001000011",
  "expires_at": "2026-07-29T01:23:45+00:00"
}
```

Важно:

- `access_token` на шаге `init` не возвращается;
- pending-сессия не переиспользуется: повтор с тем же nonce -> `409 callback_auth_session_already_started`, другой nonce поверх активного challenge того же телефона -> `409 callback_auth_challenge_already_active`;
- ретрай разрешён после cooldown (по умолчанию 15 секунд);
- при исчерпанном бюджете -> `429 callback_auth_rate_limited` с `Retry-After`, UCaller не вызывается;
- при недоступности UCaller -> `503`, сессия не создаётся.

### 2. Status

```http
POST /api/counterparty/callback_auth/status
Token: <application_token>
Content-Type: application/json
```

```json
{
  "session_token": "<opaque session token>",
  "client_nonce": "<тот же client_nonce>"
}
```

Ответ всегда одной формы, токена в нём нет никогда.

#### Pending

```json
{
  "status": "pending",
  "expires_at": "2026-07-29T01:23:45+00:00",
  "server_time": "2026-07-29T01:20:10+00:00",
  "remaining_seconds": 215
}
```

#### Verified

```json
{
  "status": "verified",
  "expires_at": "2026-07-29T01:22:10+00:00",
  "server_time": "2026-07-29T01:20:30+00:00",
  "remaining_seconds": 100
}
```

Здесь `expires_at` — дедлайн на `exchange` (120 секунд от подтверждения звонка), а не исходный TTL сессии.

#### Expired

```json
{
  "status": "expired",
  "expires_at": "2026-07-29T01:23:45+00:00",
  "server_time": "2026-07-29T01:25:01+00:00",
  "remaining_seconds": 0
}
```

### 3. Exchange

```http
POST /api/counterparty/callback_auth/exchange
Token: <application_token>
Content-Type: application/json
```

```json
{
  "session_token": "<opaque session token>",
  "client_nonce": "<тот же client_nonce>"
}
```

Успешный ответ:

```json
{
  "access_token": "12|plainSanctumToken"
}
```

Отказы:

- `409 callback_auth_not_verified` — звонок ещё не подтверждён;
- `410 callback_auth_expired` — сессия протухла;
- `410 callback_auth_exchange_window_closed` — прошло больше 60 секунд с первой выдачи;
- `404` — неизвестный `session_token`, чужой `client_nonce`, чужой проект или чужое приложение.

## Поведение и ограничения

- TTL callback-сессии: 5 минут от `init`.
- После `verified` на `exchange` есть 120 секунд, даже если исходные 5 минут истекли.
- Повторный `exchange` идемпотентен 60 секунд от первой выдачи: прежний Sanctum-токен отзывается, выдаётся новый. Это retry при потерянном ответе, а не способ получить второй живой токен.
- `session_token` и `client_nonce` хранятся только как HMAC-SHA256 (pepper `services.callback_auth.pepper`, fallback `APP_KEY`).
- Сессия привязана к `project_id` и `application_id`; запрос из другого проекта или под App Token другого приложения даёт `404`.
- IP в авторизации сессии не участвует: переход Wi-Fi -> LTE вход не ломает.
- `Counterparty` создаётся на `exchange`, а не на `init`.
- Выданный Bearer имеет явную ability `counterparty:access` (не wildcard), TTL по умолчанию 1440 минут и привязку к `application_id`; на эндпоинтах группы `counterparty.application` он работает только вместе с App Token того же приложения.
- Verified-сессия после дедлайна больше не выдаёт токен и становится `expired`.
- Старые сессии подчищает `php artisan callback-auth:prune-sessions`.

## Session token lifecycle

- Не класть `session_token` и `client_nonce` в URL, query string, analytics, client logs, `localStorage` или `sessionStorage`, если есть server-wrapper.
- В server-wrapper режиме хранить их только в `httpOnly` cookie или server-side session storage.
- В direct-storefront режиме держать их только в runtime state текущей вкладки и очищать после `exchange`, `expired`, `409`, `410`, `404` или ручного retry.
- Новая попытка входа = новый `client_nonce` и новая callback-session; старую очищать на своей стороне.

## Rate limits и анти-спам

Route-лимиты:

- `callback_init_ip`: 400/час на IP.
- `callback_init`: 6/час на `HMAC(client_nonce)`; при отсутствующем или невалидном nonce — 60/час на IP.
- `callback_status`: 240/мин на IP и 120/мин на сессию.
- `callback_exchange`: 60/мин на IP и 10/мин на сессию.

Сервисные бюджеты `init` внутри проекта (конфигурируются через `CALLBACK_AUTH_INIT_*`):

- 120/мин на проект;
- 60/мин на проект + IP;
- cooldown 15 секунд на телефон;
- 4/мин и 30/день на телефон.

Исчерпание любого -> `429 callback_auth_rate_limited` с `Retry-After`; провайдер при этом не вызывается.

Практический совет для frontend: polling `status` раз в 3-5 секунд укладывается в лимит и не создаёт лишний шум.

## После успешной верификации

1. Забрать `access_token` через `exchange`.
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

Это нужно для заказов, избранного, сохранённых карт, подписок и уведомлений.

Если приложение использует server-wrapper, именно сервер должен:

1. Вызвать Gigma `exchange` и забрать `access_token`.
2. Поставить свою финальную auth cookie.
3. Очистить callback-session cookie.
4. Вернуть browser уже безопасный redirect/result без `session_token` и `client_nonce`.

## Server-to-server introspection

Для чужого backend'а (чат, бот, интеграция), которому нужно проверить токен контрагента.

```http
POST /api/counterparty/auth/introspect
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

token=<counterparty access token>&audience=<audience клиента>
```

- Credentials выпускает владелец ERP: `counterparty-auth-client:issue`, `:list`, `:rotate`, `:disable`. Secret показывается один раз.
- `Content-Type` строго `application/x-www-form-urlencoded`, иначе `415`. `token` или `audience` в query string -> `422`.
- Живой токен:

```json
{
  "active": true,
  "principal_handle": "0f1c1f8e-...",
  "project": { "id": 12 },
  "application": { "id": 34, "name": "Site A" },
  "scopes": ["chat:access"],
  "expires_at": "2026-07-30T01:23:45+00:00"
}
```

- Любой отказ по существу (чужое приложение, протухший или неизвестный токен, отключённый клиент) -> `{"active": false}`.
- Неверные credentials -> `401`, чужой `audience` -> `403`, превышение лимита -> `429`.
- Лимиты: 60/мин на IP и 300/мин на `client_id`.
- `principal_handle` — служебный UUID контрагента, а не его id; свою запись пользователя связывать именно с ним.
- Все ответы, включая отказы, идут с `Cache-Control: no-store`.
- Ошибки `4xx/5xx` пишутся в `activity_logs` с `type=counterparty_auth_introspection`, `status=error` и полем `outcome`; сам токен туда не попадает.

## Отличия от соседних auth flow

| Flow | Endpoint | Что приходит в ответе | Когда использовать |
|---|---|---|---|
| Обычный клиентский логин | `/api/counterparty/send_password` + `/login` | `counterparty.access_token.value` после `login` | Когда доступен код/пароль |
| Miniapp signed contact | `/api/counterparty/miniapps/{provider}/contact_auth` | `counterparty` resource c `access_token.value` | Когда provider даёт подписанный proof |
| Callback auth | `/api/counterparty/callback_auth/init` + `/status` + `/exchange` | `session_token`/`callback_number`, затем метаданные, затем `access_token` | Когда нужен вход по звонку или fallback |
| Introspection | `/api/counterparty/auth/introspect` | `{"active": ...}` без выдачи новых токенов | Когда свой backend проверяет уже выданный токен |

Не ожидать miniapp-подобный `counterparty` response ни из `status`, ни из `exchange`.

## UCaller webhook

UCaller webhook сам по себе не логинит frontend и не является единственным источником правды. Он находит pending-сессию по совпадению:

- `callId`
- нормализованный `clientNumber`
- `confirmationNumber`
- session status = `pending`
- session not expired

Но перевод сессии в `verified` дополнительно требует подтверждения от провайдера (`getInfo`, `call_status = 1`). Тот же reconcile выполняют `status` и `exchange`, поэтому потерянный webhook вход не ломает.

Frontend всё равно должен забрать токен отдельным `POST /api/counterparty/callback_auth/exchange`.
