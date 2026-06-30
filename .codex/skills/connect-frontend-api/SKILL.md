---
name: connect-frontend-api
description: "Подключить frontend, storefront, miniapp или сайт к Gigma ERP / E-Commerce API. Используй когда нужно настроить API client, base URL, headers, App Token, counterparty auth, каталог, корзину, оформление заказа, оплату, обработку 401/422/429 или сверить фронтовую интеграцию с Docs-gigma."
allowed-tools: Bash Read Grep
---

# Подключение frontend к Gigma API

Цель: frontend должен ходить в Gigma API по каноническим endpoint'ам, не придумывать aliases и корректно разделять App Token, Bearer token ERP-пользователя и Bearer token counterparty.

Источник правды: `Docs-gigma/static/erp-rules.txt` и онлайн-дока `https://artypoul-docs-gigma-7b80.twc1.net/`. Краткая выжимка для агента — `reference/frontend-api-rules.md`.

## Порядок работы

1. Открыть `reference/frontend-api-rules.md`.
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
   - клиентский кабинет/заказ по `Authorization: Bearer <counterparty.access_token.value>`;
   - ERP admin по `Authorization: Bearer <user.access_token.value>`.
5. Сначала проверить happy path в браузере/тесте: каталог → карточка → precalculate → order.

## Жёсткие правила

- Не добавлять frontend aliases к API routes. Если Docs-gigma говорит `/api/counterparty/...`, ходить именно туда.
- Не путать `Token` и `Authorization`.
- Не хранить `Authorization` без `|` в Sanctum token: токен имеет вид `<id>|<secret>`.
- Не слать `phone`/`comment` в `POST /api/counterparty/orders`: телефон берётся из профиля counterparty.
- Не повторять `POST /api/counterparty/orders` без проверки результата: создание заказа не идемпотентно.
- Денежные поля из API приходят строками; отображать как деньги, не полагаться на float для критичных расчётов.
- 422 может приходить по dotted-path ключам вроде `products.0.id`; UI должен показывать ошибку рядом с конкретной строкой корзины.

## Минимальный E-Commerce flow

1. Получить/ввести клиента:
   - callback auth / miniapp auth / login по звонку;
   - сохранить `counterparty.access_token.value`.
2. Загрузить справочники один раз:
   - categories, brands, countries, delivery types, payment types.
3. Каталог:
   - `GET /api/counterparty/products?...`
   - карточка: `GET /api/counterparty/products/{id}`.
4. Корзина:
   - `POST /api/counterparty/orders/precalculate`.
5. Заказ:
   - `POST /api/counterparty/orders`.
6. Оплата:
   - если в ответе есть `order.payment_link`, редиректить пользователя;
   - polling заказа делать не чаще 5 секунд.

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
- Для App Token используется header `Token`, для user/counterparty — `Authorization: Bearer`.
- E2E покрывает минимум один товар и один заказ до создания/оплаты.
- UI обрабатывает `401`, `403`, `404`, `422`, `429`.
