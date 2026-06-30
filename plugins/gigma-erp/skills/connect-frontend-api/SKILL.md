---
name: connect-frontend-api
description: "Подключить frontend, storefront, miniapp или сайт к Gigma ERP / E-Commerce API, в том числе к уже существующей витрине/Application по App Token. Используй когда нужно настроить API client, base URL, headers, App Token, counterparty auth, каталог, корзину, оформление заказа, оплату, обработку 401/422/429 или сверить фронтовую интеграцию с Docs-gigma."
allowed-tools: Bash Read Grep
---

# Подключение frontend к Gigma API

Цель: frontend должен ходить в Gigma API по каноническим endpoint'ам, не придумывать aliases и корректно разделять App Token, Bearer token ERP-пользователя и Bearer token counterparty.

Источник правды: `Docs-gigma/static/erp-rules.txt` и онлайн-дока `https://artypoul-docs-gigma-7b80.twc1.net/`. Краткая выжимка для агента — `reference/frontend-api-rules.md`.

## Порядок работы

1. Открыть `reference/frontend-api-rules.md`.
   - Обязательно использовать разделы "Процесс по кнопкам" и "Endpoint map".
   - Если фронт нужно подключить к уже существующей витрине, сначала пройти раздел "Existing storefront preflight".
2. Если нужен точный контракт endpoint'а, читать OpenAPI/Docs-gigma, а не угадывать путь:
   - `https://artypoul-docs-gigma-7b80.twc1.net/openapi.json`
   - `https://artypoul-docs-gigma-7b80.twc1.net/llms-full.txt`
3. В коде frontend завести один API client с:
   - base URL `https://api.gigma.ru/api`;
   - `Accept: application/json`;
   - `Content-Type: application/json` для JSON POST/PUT/PATCH;
   - timeout и единый error parser.
4. Выбрать auth flow:
   - публичный каталог/витрина по `Token: <application_token>`;
   - профиль клиента по `Authorization: Bearer <counterparty.access_token.value>`;
   - клиентские действия внутри витрины (заказы, избранное, карты, подписки) по двум заголовкам: `Token: <application_token>` + `Authorization: Bearer <counterparty.access_token.value>`;
   - ERP admin по `Authorization: Bearer <user.access_token.value>`.
5. Сначала проверить happy path в браузере/тесте: старт приложения → каталог → карточка → вход → precalculate → order → payment link.

## Уже существующая витрина

Если пользователь говорит "привязать фронт к существующей витрине/сайту/App Token", **не создавать новую application**. Сначала получить от владельца или найти owner-токеном:

```http
GET /api/applications
GET /api/applications/{appId}
```

Проверить: `id`, `name`, `token`, `is_token_active:true`, склады в `warehouses[]`, нужный `branch_id`. Затем публично проверить тем же App Token: `GET /api/counterparty/products`, `prices`, нужные `menus/{code}`/`blocks/{code}`. Если токен выключен, склад не тот или каталог/контент пустой — это задача `setup-storefront`, а не фронтовой фикс.

## Жёсткие правила

- Не добавлять frontend aliases к API routes. Если Docs-gigma говорит `/api/counterparty/...`, ходить именно туда.
- Не создавать новую витрину/Application при задаче "подключить к существующей": использовать подтверждённый `appId` и его App Token.
- Не путать `Token` и `Authorization`.
- Не хранить `Authorization` без `|` в Sanctum token: токен имеет вид `<id>|<secret>`.
- Не слать `phone`/`comment` в `POST /api/counterparty/orders`: телефон берётся из профиля counterparty.
- Не повторять `POST /api/counterparty/orders` без проверки результата: создание заказа не идемпотентно.
- Денежные поля из API приходят строками; отображать как деньги, не полагаться на float для критичных расчётов.
- 422 может приходить по dotted-path ключам вроде `products.0.id`; UI должен показывать ошибку рядом с конкретной строкой корзины.

## Минимальный E-Commerce flow

Подробная версия с UI-действиями и endpoint'ами лежит в `reference/frontend-api-rules.md`.

Коротко: старт приложения по App Token → справочники → каталог → карточка → auth клиента → precalculate → order → payment link → polling заказа.

## Miniapp auth

Для miniapp frontend использовать skill `miniapp-auth`. Главное:

```
POST /api/counterparty/miniapps/{provider}/contact_auth
Header: Token: <application_token>
```

Не использовать `/api/miniapps/.../auth/...`.

## Проверки перед сдачей

- API client не содержит hardcoded mock base URL.
- В requests есть `Accept: application/json`.
- Для App Token используется header `Token`, для user/counterparty — `Authorization: Bearer`; для заказов/избранного/карт/подписок клиента нужны оба заголовка.
- E2E покрывает минимум один товар и один заказ до создания/оплаты.
- UI обрабатывает `401`, `403`, `404`, `422`, `429`.
