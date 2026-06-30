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
GET /api/counterparty/menus/<menu-code>
GET /api/counterparty/blocks/<block-code>
Token: <application_token>
Accept: application/json
```

Если каталог пустой, токен выключен, склад не привязан или контент не находится по `code`/`slug`, сначала исправить витрину через `setup-storefront`. Frontend не должен обходить это моками, alias routes или хардкодом контента.

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
| Способы оплаты | GET | `/api/counterparty/payment_types` | `Token` или counterparty Bearer | `paymentTypes[]` |

Не дергать справочники перед каждым кликом: загрузить один раз и кешировать в состоянии приложения.

### 1. Каталог

Когда пользователь открывает каталог, фильтрует или ищет:

```http
GET /api/counterparty/products?per_page=20&page=1&query=<text>&category_id[]=<id>&brand_id[]=<id>&sale=true
Token: <application_token>
```

UI сохраняет:

- список товаров;
- pagination/meta, если backend вернул;
- `product.id` для карточки и корзины;
- `price` как строку/decimal-display, не как источник критичной математики.

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

Дальше клиентские requests идут с:

```http
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
| Профиль | GET | `/api/counterparty` | counterparty Bearer |
| Выйти | POST | `/api/counterparty/logout` | counterparty Bearer |
| Мои заказы | GET | `/api/counterparty/orders` | counterparty Bearer |
| Детали заказа | GET | `/api/counterparty/orders/{order_id}` | counterparty Bearer |
| Уведомления, если включены | GET | `/api/counterparty/notifications` | counterparty Bearer |

Logout body:

```json
{ "from_all_devices": false }
```

### 6. Избранное

| UI / кнопка | Method | Endpoint | Body | Auth |
|---|---|---|---|---|
| Добавить в избранное | POST | `/api/counterparty/products/favourites` | `{ "product_id": 123 }` | counterparty Bearer |
| Список избранного | GET | `/api/counterparty/products/favourites` | - | counterparty Bearer |
| Удалить из избранного | DELETE | `/api/counterparty/products/favourites/{id}` | - | counterparty Bearer |

Если пользователь не залогинен, UI должен предложить вход, а не слать Bearer-запрос без токена.

### 7. Оформление заказа

Кнопка "Оформить заказ":

```http
POST /api/counterparty/orders
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
| Payment types | GET | `/api/counterparty/payment_types` | `Token` или Bearer |
| Products list | GET | `/api/counterparty/products` | `Token` |
| Product card | GET | `/api/counterparty/products/{id}` | `Token` |
| Cart precalculate | POST | `/api/counterparty/orders/precalculate` | `Token` |
| Send password | POST | `/api/counterparty/send_password` | `Token` |
| Login | POST | `/api/counterparty/login` | `Token` |
| Miniapp login | POST | `/api/counterparty/miniapps/{provider}/contact_auth` | `Token` |
| Current counterparty | GET | `/api/counterparty` | Bearer |
| Create order | POST | `/api/counterparty/orders` | Bearer |
| Orders list | GET | `/api/counterparty/orders` | Bearer |
| Order details | GET | `/api/counterparty/orders/{id}` | Bearer |
| Logout | POST | `/api/counterparty/logout` | Bearer |

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
