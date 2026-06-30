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
| E-Commerce клиент внутри витрины | `Token: <application_token>` + `Authorization: Bearer <counterparty.access_token.value>` |
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

## Existing storefront preflight

Когда задача — подключить фронт к уже существующей витрине/Application, агент не должен создавать новую витрину.

1. Получить `appId`/App Token от владельца или найти owner-токеном:

```http
GET /api/applications
GET /api/applications/{appId}
Authorization: Bearer <user.access_token.value>
```

2. Проверить в ответе:

- `id` и `name` — это нужный сайт/витрина;
- `token` — тот App Token, который пойдёт во frontend config;
- `is_token_active` = `true`;
- `warehouses[]` содержит нужный склад;
- `branch_id` соответствует нужному юрлицу/проекту.

3. Проверить публичный контур ровно тем токеном, который будет на фронте:

```http
GET /api/counterparty/products?per_page=2
GET /api/counterparty/prices
GET /api/counterparty/categories
GET /api/counterparty/pages
GET /api/counterparty/slides
GET /api/counterparty/menus/<slug>
GET /api/counterparty/blocks/<code>
GET /api/counterparty/blocks/id/<identifier>
Token: <application_token>
Accept: application/json
```

Если каталог пустой, токен выключен, склад не привязан или контент не находится по `code`/`slug`, сначала исправить витрину через `setup-storefront`. Frontend не должен обходить это моками, alias routes или хардкодом контента.

Для контентных блоков главный публичный путь — `GET /api/counterparty/blocks/{code}`. В текущем backend поле `code` у блока числовое; например `blocks/1` и `blocks/2`. Путь `GET /api/counterparty/blocks/id/{identifier}` ищет поле `identifier`, а не database `id` и не `code`, поэтому `blocks/id/1` вернёт 404, если у блока `identifier` пустой.

## Процесс по кнопкам

### 0. Старт приложения / загрузка витрины

Когда пользователь открывает сайт или miniapp:

1. Взять App Token конкретной витрины.
2. Все публичные E-Commerce requests слать с header:

```http
Token: <application_token>
Accept: application/json
```

3. Загрузить данные для первого экрана:

| UI / экран | Method | Endpoint | Auth | Что сохранить |
|---|---|---|---|---|
| Меню/категории | GET | `/api/counterparty/categories` | `Token` | `categories[]` |
| Бренды/фильтры | GET | `/api/counterparty/brands` | `Token` | `brands[]` |
| Страны/фильтры, если нужны | GET | `/api/counterparty/countries` | `Token` | `countries[]` |
| Диапазон цен, если нужен | GET | `/api/counterparty/prices` | `Token` | `min_price`, `max_price` |
| Способы доставки | GET | `/api/counterparty/delivery_types` | `Token` | `deliveryTypes[]` |
| Способы оплаты | GET | `/api/counterparty/payment_types` | `Token` | `paymentTypes[]` |
| Страницы сайта | GET | `/api/counterparty/pages` | `Token` | `pages[]` |
| Слайды | GET | `/api/counterparty/slides` | `Token` | `slides[]` |
| Меню | GET | `/api/counterparty/menus/{slug}` | `Token` | menu tree |
| Контентный блок | GET | `/api/counterparty/blocks/{code}` | `Token` | `block` + `children[]` |

Не дергать справочники перед каждым кликом: загрузить один раз и кешировать в состоянии приложения.

Публичного endpoint'а "получить все блоки сайта" нет. Фронт должен знать нужные `code`/`identifier` из настройки витрины или получить их через owner API на этапе конфигурации. Не использовать `/blocks/id/{...}` для database id: это поиск по `identifier`.

### 1. Каталог

Когда пользователь открывает каталог, фильтрует или ищет:

```http
GET /api/counterparty/products?per_page=20&page=1&query=<text>&category_id[]=<id>&brand_id[]=<id>
Token: <application_token>
```

UI сохраняет:

- список товаров;
- pagination/meta, если backend вернул;
- `product.id` для карточки и корзины;
- `price` как строку/decimal-display, не как источник критичной математики.

Поддерживаемые фильтры текущего backend: `category_id[]`, `brand_id[]`, `country_id[]`, `query`, `price_from`, `price_to`, `order_by`, `tag_id[]`. Не добавлять `sale=true`: публичный request его не принимает.

### 2. Карточка товара

Когда пользователь нажал на товар:

```http
GET /api/counterparty/products/{product_id}
Token: <application_token>
```

UI показывает карточку и использует `product.id` для "Добавить в корзину".

### 3. Корзина без логина

Кнопка "Добавить в корзину" обычно не требует backend request: хранить локально:

```json
[
  { "id": 123, "quantity": 2 }
]
```

Перед оформлением или при изменении количества можно пересчитать:

```http
POST /api/counterparty/orders/precalculate
Token: <application_token>
Content-Type: application/json
```

```json
{
  "products": [
    { "id": 123, "quantity": 2 }
  ],
  "promo_code": "SALE10"
}
```

Если backend вернул `discount_error`, не падать: показать корзину без скидки и сообщение по промокоду.

### 4. Вход клиента

Вариант A: обычный звонок/пароль.

Кнопка "Получить код / звонок":

```http
POST /api/counterparty/send_password
Token: <application_token>
Content-Type: application/json
```

```json
{ "phone": "79991234567" }
```

Кнопка "Войти":

```http
POST /api/counterparty/login
Token: <application_token>
Content-Type: application/json
```

```json
{
  "phone": "79991234567",
  "password": "1111",
  "device": "web"
}
```

После успеха сохранить:

```text
counterparty.access_token.value
```

Дальше клиентские requests делятся на два типа:

```http
Authorization: Bearer <counterparty.access_token.value>
Accept: application/json
```

Так ходят профиль и logout. А действия, которые остаются в контексте конкретной витрины (заказы, избранное, saved payment methods, subscriptions), требуют оба заголовка:

```http
Token: <application_token>
Authorization: Bearer <counterparty.access_token.value>
Accept: application/json
```

Вариант B: miniapp signed contact.

```http
POST /api/counterparty/miniapps/{provider}/contact_auth
Token: <application_token>
Content-Type: application/json
```

```json
{
  "phone": "+79139277802",
  "auth_date": 1780000000,
  "hash": "<64 hex>",
  "init_data": "auth_date=...&user=...&hash=...",
  "device": "max-miniapp"
}
```

После успеха также сохранить `counterparty.access_token.value`.

### 5. Профиль и личный кабинет

После логина:

| UI / кнопка | Method | Endpoint | Auth |
|---|---|---|---|
| Профиль | GET | `/api/counterparty` | Bearer |
| Выйти | POST | `/api/counterparty/logout` | Bearer |
| Мои заказы | GET | `/api/counterparty/orders` | Token + Bearer |
| Детали заказа | GET | `/api/counterparty/orders/{order_id}` | Token + Bearer |
| Уведомления, если включены | GET | `/api/counterparty/notifications` | Token |

Logout body:

```json
{ "from_all_devices": false }
```

### 6. Избранное

| UI / кнопка | Method | Endpoint | Body | Auth |
|---|---|---|---|---|
| Добавить в избранное | POST | `/api/counterparty/products/favourites` | `{ "product_id": 123 }` | Token + Bearer |
| Список избранного | GET | `/api/counterparty/products/favourites` | - | Token + Bearer |
| Удалить из избранного | DELETE | `/api/counterparty/products/favourites/{id}` | - | Token + Bearer |

Если пользователь не залогинен, UI должен предложить вход, а не слать Bearer-запрос без токена.

### 7. Оформление заказа

Кнопка "Оформить заказ":

```http
POST /api/counterparty/orders
Token: <application_token>
Authorization: Bearer <counterparty.access_token.value>
Content-Type: application/json
```

Минимальное тело:

```json
{
  "delivery_type_id": 2,
  "products": [
    { "id": 123, "quantity": 2 }
  ],
  "payment_type_id": 2,
  "promo_code": "SALE10"
}
```

Для доставки до адреса могут понадобиться:

```json
{
  "delivery_subtype_id": 2,
  "address": "Новосибирск, ..."
}
```

Для самовывоза может понадобиться:

```json
{
  "shop_id": 1
}
```

Важно:

- `phone` не слать;
- `comment` не слать, если backend contract явно не изменён;
- заказ не идемпотентен: при сетевой ошибке сначала проверить список/детали заказа, потом решать повтор.

### 8. Оплата

Если `POST /api/counterparty/orders` вернул `order.payment_link`:

1. Открыть/redirect на `payment_link`.
2. После возврата с оплаты polling:

```http
GET /api/counterparty/orders/{order_id}
Token: <application_token>
Authorization: Bearer <counterparty.access_token.value>
```

Интервал polling: не чаще 5 секунд.

Ожидаемые статусы зависят от справочника `order_statuses`; исторически оплачен = `22`, отменён = `6`, но для UI лучше показывать `status.name` из ответа.

## Endpoint map

| Назначение | Method | Endpoint | Header |
|---|---|---|---|
| App categories | GET | `/api/counterparty/categories` | `Token` |
| App brands | GET | `/api/counterparty/brands` | `Token` |
| App countries | GET | `/api/counterparty/countries` | `Token` |
| Delivery types | GET | `/api/counterparty/delivery_types` | `Token` |
| Payment types | GET | `/api/counterparty/payment_types` | `Token` |
| Products list | GET | `/api/counterparty/products` | `Token` |
| Product card | GET | `/api/counterparty/products/{id}` | `Token` |
| Pages | GET | `/api/counterparty/pages`, `/api/counterparty/pages/{slug}` | `Token` |
| Slides | GET | `/api/counterparty/slides` | `Token` |
| Menu | GET | `/api/counterparty/menus/{slug?}` | `Token` |
| Block by code | GET | `/api/counterparty/blocks/{code}` | `Token` |
| Block by identifier | GET | `/api/counterparty/blocks/id/{identifier}` | `Token` |
| Cart precalculate | POST | `/api/counterparty/orders/precalculate` | `Token` |
| Send password | POST | `/api/counterparty/send_password` | `Token` |
| Login | POST | `/api/counterparty/login` | `Token` |
| Miniapp login | POST | `/api/counterparty/miniapps/{provider}/contact_auth` | `Token` |
| Current counterparty | GET | `/api/counterparty` | Bearer |
| Create order | POST | `/api/counterparty/orders` | Token + Bearer |
| Orders list | GET | `/api/counterparty/orders` | Token + Bearer |
| Order details | GET | `/api/counterparty/orders/{id}` | Token + Bearer |
| Logout | POST | `/api/counterparty/logout` | Bearer |
| Favourites | GET/POST/DELETE | `/api/counterparty/products/favourites...` | Token + Bearer |
| Saved payment methods | GET/DELETE | `/api/counterparty/payment-methods...` | Token + Bearer |
| Subscriptions | GET/POST/PATCH | `/api/counterparty/subscriptions...` | Token + Bearer |

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
