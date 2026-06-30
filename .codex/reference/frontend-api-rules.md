# Frontend API rules for Gigma

Краткая выжимка из `Docs-gigma/static/erp-rules.txt` для подключения frontend/storefront/miniapp к Gigma API.

## Base URL

```
https://api.gigma.ru/api
```

Минимальные headers:

```
Accept: application/json
Content-Type: application/json
```

Для multipart upload `Content-Type` выставляет браузер/FormData.

## Auth types

| Сценарий | Header |
|---|---|
| Витрина/App Token | `Token: <application_token>` |
| E-Commerce клиент | `Authorization: Bearer <counterparty.access_token.value>` |
| ERP сотрудник | `Authorization: Bearer <user.access_token.value>` |

Sanctum token имеет вид `<id>|<secret>`. Хранить целиком.

## Client login

Обычный E-Commerce login:

```
POST /api/counterparty/login
{ "phone": "<phone-or-email>", "password": "<pwd>", "device": "<optional>" }
```

Поле `phone` может принимать email. После успеха сохранить `counterparty.access_token.value`.

Miniapp login:

```
POST /api/counterparty/miniapps/{provider}/contact_auth
Token: <application_token>
```

Не использовать public aliases вида `/api/miniapps/.../auth/...`.

## Storefront flow

1. Справочники: categories, brands, countries, delivery types, payment types.
2. Каталог: `GET /api/counterparty/products`.
3. Карточка: `GET /api/counterparty/products/{id}`.
4. Предрасчёт: `POST /api/counterparty/orders/precalculate`.
5. Заказ: `POST /api/counterparty/orders`.
6. Оплата: использовать `order.payment_link`, если backend вернул ссылку.

## Order contract reminders

- `POST /api/counterparty/orders` всегда требует `delivery_type_id` и `products[]`.
- Для delivery subtype/address смотреть live contract в Docs-gigma/OpenAPI.
- `phone` и `comment` не принимаются в заказе; телефон берётся из профиля counterparty.
- `POST /api/counterparty/orders` не идемпотентен.

## Errors

| Code | Что делать |
|---|---|
| 401 | Перелогинить клиента или сотрудника |
| 403 | Показать запрет доступа |
| 404 | Не гадать route; сверить Docs-gigma/OpenAPI |
| 422 | Разобрать `errors`, включая dotted keys `products.0.id` |
| 429 | Backoff, не спамить retry |

## Known traps

- Не путать `Token` и `Authorization`.
- Не использовать guessed aliases: `/api/payment_types`, `/api/units`, `/api/businesses`.
- Payment types для клиента: `GET /api/counterparty/payment_types`.
- Цена может прийти строкой.
- Delete может вернуть 204 без body.
- Create может вернуть 201, проверять весь диапазон `2xx`.
