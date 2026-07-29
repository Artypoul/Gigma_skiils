---
name: counterparty-callback-auth
description: "Спроектировать или проверить авторизацию приложения, витрины, сайта или fallback-miniapp через counterparty callback auth в Gigma ERP. Используй когда нужно добавить вход клиента по звонку через `/api/counterparty/callback_auth/init`, `/status` и `/exchange`, разобрать `client_nonce`, `session_token`, выдачу `access_token`, App Token header, UCaller callback flow, server-to-server проверку токена через `/api/counterparty/auth/introspect`, rate limits или отличия от `send_password/login` и `miniapp-auth`."
---

# Counterparty callback auth в Gigma ERP

Цель: получить `counterparty` Sanctum token для клиента витрины через трёхшаговый callback flow `init` -> `status` -> `exchange` и не перепутать его с обычным `send_password/login` или signed-contact miniapp auth.

Если у приложения есть свой сервер, BFF или SSR-контур, предпочитать server-wrapper: браузер общается со своими endpoint'ами, а не держит сырые `session_token` и `client_nonce`.

## Порядок работы

1. Открыть `../../reference/counterparty-callback-auth.md`.
2. Для общей картины auth-слоёв и заголовков сверить `../../reference/erp-api.md`.
3. Если задача про frontend витрины, дополнительно открыть раздел "Вход клиента" в `../../reference/frontend-api-rules.md`: там описаны `send_password/login` и правило "оба заголовка", а сам callback flow — только здесь.
4. Если задача про backend-код, сначала проверить канонический контур:
   - `CallbackAuthController` с методами `init`, `status`, `exchange`
   - `CallbackAuthService`
   - `CallbackAuthHasher` и модель `AuthCallbackSession`
   - `InitCallbackAuthRequest`, `StatusCallbackAuthRequest`, `ExchangeCallbackAuthRequest`
   - middleware `token` и `counterparty.auth.no_store`
   - rate limiters `callback_init_ip`, `callback_init`, `callback_status`, `callback_exchange`
5. Если задача про server-to-server проверку выданного токена, дополнительно смотреть `CounterpartyAuthIntrospectionController`, `CounterpartyAuthIntrospectionService`, middleware `counterparty.auth.client`.

## Канонический flow

0. Сгенерировать `client_nonce`: 32-128 криптослучайных символов base64url (`A-Za-z0-9-_`). Один nonce = одна попытка входа. Сервер хранит только его HMAC и использует как единственное доказательство, что `status` и `exchange` делает тот же клиент, который сделал `init`.

1. Стартовать callback-сессию:

```http
POST /api/counterparty/callback_auth/init
Token: <application_token>
Content-Type: application/json

{ "phone": "79991234567", "client_nonce": "<32..128 base64url>" }
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

{ "session_token": "<session_token>", "client_nonce": "<client_nonce>" }
```

Ответ всегда содержит только метаданные: `status`, `expires_at`, `server_time`, `remaining_seconds`. Токена в нём нет никогда.

3. Интерпретировать ответ по состоянию:

- `pending` -> оставаться в polling и показывать `remaining_seconds`
- `verified` -> один раз вызвать `exchange`
- `expired` -> предложить перезапуск `init` с новым `client_nonce`
- `404` -> считать сессию чужой, устаревшей или недоступной и начинать заново с новым `client_nonce`

4. Обменять подтверждённую сессию на Bearer:

```http
POST /api/counterparty/callback_auth/exchange
Token: <application_token>
Content-Type: application/json

{ "session_token": "<session_token>", "client_nonce": "<client_nonce>" }
```

Успех: `{ "access_token": "<Sanctum plain token>" }`. Отказы:

- `409 callback_auth_not_verified` -> звонок ещё не подтверждён, вернуться в polling
- `410 callback_auth_expired` -> сессия протухла, начинать заново
- `410 callback_auth_exchange_window_closed` -> прошло больше 60 секунд с первой выдачи токена
- `404` -> не тот `session_token`, `client_nonce` или приложение

5. После успешного обмена:

- сохранить `access_token`;
- гидрировать профиль через `GET /api/counterparty` с `Authorization: Bearer <access_token>`;
- для заказов, избранного, сохранённых карт, подписок и уведомлений слать оба заголовка: `Token` + `Authorization`.

## Режимы интеграции

### 1. Server-wrapper, preferred

Использовать, если приложение умеет ставить свои cookies или уже имеет серверный слой: SvelteKit, Next.js, Nuxt, mobile backend, BFF.

Схема:

- браузер -> ваш `POST /login/callback-auth/init`
- ваш сервер сам генерирует `client_nonce` и вызывает `POST /api/counterparty/callback_auth/init`
- ваш сервер сохраняет `session_token` и `client_nonce` только в `httpOnly` cookie или серверной сессии
- браузер получает только `callback_number`, `expires_at` и локальный UI-state
- браузер -> ваш `POST /login/callback-auth/status`
- при `verified` ваш сервер сам вызывает Gigma `exchange`, ставит финальную auth cookie и очищает callback-session

### 2. Direct storefront, narrow fallback

Использовать только если frontend действительно ходит в Gigma напрямую и отдельного серверного слоя нет.

Схема:

- браузер сам вызывает Gigma `init`, `status` и `exchange` с App Token
- `session_token` и `client_nonce` живут только в памяти текущей вкладки
- после `exchange` frontend сохраняет только итоговый `access_token`

## Server-to-server introspection

Отдельный контур для вашего backend'а (чат, бот, интеграция), которому нужно проверить чужой `access_token` контрагента:

```http
POST /api/counterparty/auth/introspect
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

token=<counterparty access token>&audience=<audience клиента>
```

- Credentials выпускает владелец ERP командами `counterparty-auth-client:issue`, `:list`, `:rotate`, `:disable`; secret показывается один раз.
- `Content-Type` строго `application/x-www-form-urlencoded`, иначе `415`. `token` или `audience` в query string -> `422`.
- Живой токен: `{"active": true, "principal_handle": "...", "project": {"id": N}, "application": {"id": N, "name": "..."}, "scopes": ["chat:access"], "expires_at": "..."}`.
- Любой отказ по существу -> `{"active": false}`. Неверные credentials -> `401`, чужой `audience` -> `403`.
- `principal_handle` — служебный UUID контрагента, а не его id; связывать своего пользователя нужно именно с ним.
- Все ответы, включая отказы, идут с `Cache-Control: no-store`.
- Ошибки `4xx/5xx` пишутся в `activity_logs` с `type=counterparty_auth_introspection` и полем `outcome`; сам токен и текст исключения туда не попадают.

## Жёсткие правила

- Не добавлять alias routes вроде `/api/app/callback-auth` или `/api/miniapps/.../callback_auth`, если задача живёт в counterparty-контуре.
- Не ожидать `access_token` от `status`: токен выдаёт только `exchange`.
- Не ожидать `CounterpartyResource` из `status` или `exchange`: этот flow возвращает токен, а не объект `counterparty`.
- Не ожидать поля `already_consumed`: в контракте callback auth его нет.
- Не использовать `session_token` как замену `access_token` и не хранить его как долгоживущую сессию.
- Не терять `client_nonce`: без него `status` и `exchange` дадут `422`, а с чужим — `404`.
- Не переиспользовать один `client_nonce` между попытками входа: повторный `init` с тем же nonce даёт `409` и не раскрывает `session_token`.
- Не класть `session_token` и `client_nonce` в `localStorage`, `sessionStorage`, URL, query params или non-`httpOnly` cookie, если у приложения есть свой серверный слой.
- Не возвращать сырые `session_token` и `client_nonce` из своих публичных app-endpoint'ов, если можно хранить их серверно и поллить через local endpoint.
- Не терять `Token: <application_token>` ни на одном из трёх запросов.
- Не привязывать вход к IP: IP больше не участвует в авторизации сессии, переход Wi-Fi -> LTE вход не ломает.
- Не вызывать `init` в цикле: пока активен challenge, повтор даёт `409`; ретрай разрешён после cooldown (по умолчанию 15 секунд).
- Не логировать `session_token`, `client_nonce`, `access_token` и полный `callback_number` в query string, browser analytics, чат или клиентские логи.
- Не смешивать этот flow с `miniapp-auth`: у них разные endpoint'ы и разный контракт ответа.
- Не ходить в `auth/introspect` с App Token или Bearer клиента: там принимаются только Basic client credentials.

## Frontend-ориентиры

- Передавать телефон в пользовательском формате можно, но backend нормализует его к `7XXXXXXXXXX`; невалидный телефон даёт `422`.
- Показывать `callback_number`, `expires_at` и обратный отсчёт, синхронизируя таймер по `server_time` и `remaining_seconds`.
- Поллить `status` раз в 3-5 секунд: бюджет 120 запросов в минуту на сессию, чаще смысла нет.
- Как только `status` стал `verified`, сразу вызывать `exchange`: на обмен есть отдельное окно 120 секунд от подтверждения звонка.
- Повторный `exchange` безопасен только 60 секунд от первой выдачи токена. Это retry при потерянном ответе, а не способ "взять токен ещё раз".
- В server-wrapper режиме polling должен идти через ваш local endpoint без передачи raw `session_token` и `client_nonce` из браузера.
- В direct-storefront режиме `session_token` и `client_nonce` допустимы только в оперативной памяти вкладки; после reload их не восстанавливать из browser storage.
- `409 callback_auth_not_verified` — состояние восстановимое: вернуться в polling `status`, сохранив `session_token` и `client_nonce`. Polling не крутить на `410`, `404` и терминальных `409` (`callback_auth_session_already_started`, `callback_auth_challenge_already_active`) — там начинать заново с новым `client_nonce`.
- После `exchange` отдельно подтянуть профиль клиента; не ждать его в том же ответе.
- Обрабатывать `429 callback_auth_rate_limited` и уважать заголовок `Retry-After`.

## Инварианты backend

- TTL callback-сессии = 5 минут от `init`.
- После `verified` на `exchange` даётся 120 секунд, даже если исходные 5 минут уже истекли.
- Повторный `exchange` идемпотентен 60 секунд от первой выдачи: прежний Sanctum-токен отзывается, выдаётся новый; после окна — `410`.
- `session_token` и `client_nonce` хранятся в БД только как HMAC-SHA256 (pepper `services.callback_auth.pepper`, fallback `APP_KEY`). Plaintext-секретов в таблице нет.
- Сессия привязана к `project_id` + `application_id` + `client_nonce_hash`. IP в авторизации не участвует.
- На пару `project + phone` допускается один активный UCaller-challenge: тот же nonce -> `409 callback_auth_session_already_started`, другой nonce поверх активного challenge -> `409 callback_auth_challenge_already_active`. Блокировка снимается по cooldown (`CALLBACK_AUTH_INIT_PHONE_COOLDOWN_SECONDS`, по умолчанию 15 секунд).
- Route-лимиты: `callback_init_ip` 400/час по IP; `callback_init` 6/час по HMAC(`client_nonce`); `callback_status` 240/мин по IP и 120/мин по сессии; `callback_exchange` 60/мин по IP и 10/мин по сессии.
- Сервисные бюджеты `init` внутри проекта: 120/мин на проект, 60/мин на проект+IP, cooldown 15 секунд, 4/мин и 30/день на телефон. Исчерпание -> `429 callback_auth_rate_limited` с `Retry-After`, UCaller при этом не вызывается.
- Недоступность UCaller -> `503`, сессия не создаётся.
- `Counterparty` создаётся не на `init`, а на `exchange`.
- Bearer выпускается с явной ability `counterparty:access` (wildcard запрещён), TTL по умолчанию 1440 минут, с проставленным `application_id`.
- Из-за middleware `counterparty.application` этот Bearer работает только вместе с App Token того же приложения; чужой App Token даёт `404`.
- UCaller webhook сам по себе не логинит: он находит сессию по `callId` + нормализованный телефон + `confirmationNumber`, а перевод в `verified` требует подтверждения провайдером (`getInfo`, `call_status = 1`). Тот же reconcile делают `status` и `exchange`, поэтому потеря webhook вход не ломает.
- Все три эндпоинта отвечают с `Cache-Control: no-store`.
- Старые сессии подчищает `php artisan callback-auth:prune-sessions`.

## Проверки перед сдачей

- `init` без `client_nonce` или с коротким nonce -> `422`.
- Повторный `init` с тем же nonce -> `409`, `session_token` в ответе не раскрывается.
- `status` не содержит `access_token` ни в одном состоянии.
- `exchange` на `verified` отдаёт токен, проставляет `access_token_delivered_at` и `access_token_id` и создаёт или находит `Counterparty` внутри проекта витрины.
- Повтор `exchange` в течение 60 секунд отзывает предыдущий Sanctum-токен и выдаёт новый; после окна -> `410`.
- `pending` и `expired` корректно обрабатываются на UI, включая `429` с `Retry-After`.
- Чужой проект, чужое приложение, чужой `client_nonce` и неизвестный `session_token` приводят к `404`.
- Смена IP между `init` и `status`/`exchange` вход не ломает.
- Нет `Token` header -> `401`.
- Ответы всех трёх эндпоинтов содержат `Cache-Control: no-store`.
- После логина storefront-действия используют оба заголовка, а не один Bearer.
