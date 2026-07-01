# Референс API Gigma ERP (api.gigma.ru)

Факты проверены по коду `itecho-erp-backend` (Laravel 12) и боевыми вызовами. Канон правил — https://artypoul-docs-gigma-7b80.twc1.net/erp-rules.txt. Не выдумывать — сверять с кодом.

## Базовый URL и панель

- API: `https://api.gigma.ru/api` (доступен **без VPN**; VPN нужен только для прямого доступа к БД).
- Панель: `https://cloud.gigma.ru`. Витрина (Application) в панели называется **«site»** → `/sites/{id}`; склад → `/warehouses/list-warehouses/{id}`.

## Три слоя авторизации

| Слой | Как передаётся | Кто | Для чего |
|---|---|---|---|
| **Owner / сотрудник** | `Authorization: Bearer <userToken>` | `auth:user` | Админка: проекты, филиалы, склады, номенклатура, витрины, остатки |
| **App Token (витрина)** | заголовок `Token: <appToken>` | `token` (middleware) | Публичная витрина: каталог, цены, precalculate, contact_form, вход клиента |
| **Клиент** | `Authorization: Bearer <counterpartyToken>`; для заказов/карт/подписок вместе с `Token: <appToken>` | `auth:counterparty` | Личный кабинет и действия в контексте витрины |

Owner-токен получают как сотрудника проекта: `POST /api/send_password {login}` → код из письма owner/admin → `POST /api/login {login,password,device}` → `user.access_token.value` (вид `2992|…`). Чтение кода из БД/таблицы `passwords` — только break-glass с явным разрешением владельца, не обычная настройка агента.

Для MCP/AI-агента без owner-токена использовать self-service заявку: `POST /api/agent-access-requests` → письмо owner/admin → `status` polling → `consume` → `agent_token.value` (см. `agent-access-request.md`). Это предпочтительнее, чем просить owner password/OTP.

## Owner-эндпоинты (Bearer userToken, `auth:user`)

```
GET  /api/user                              профиль владельца (project_id, права)
GET  /api/branches_list                     филиалы
POST /api/branches                          создать филиал (юр.лицо)
GET  /api/sales_strategies                  стратегии продаж (1=продать остатки, 2=макс прибыль)
GET  /api/storage_units                     единицы (14=м², 15=шт, 16=п.м, 17=кг, 18=м)
GET  /api/warehouses                        склады
POST /api/warehouses                        создать склад
GET  /api/applications                      витрины
POST /api/applications                      создать витрину (генерит App Token)
PUT  /api/applications/{id}                 правка витрины (привязка склада, активация токена)
GET  /api/agents | /api/tables/agents       agent-users для внешних MCP-серверов
POST /api/agents                            создать agent-user (см. agent-mcp-access.md)
PATCH|DELETE /api/agents/{id}               обновить / отключить agent-user
GET|POST /api/agents/{id}/tokens            metadata / выпуск Sanctum token агента
DELETE /api/agents/{id}/tokens/{token}      отзыв token агента
POST /api/warehouses/{wid}/nomenclatures    добавить остаток (товар на склад)
GET  /api/nomenclatures?per_page=1000       номенклатура проекта
POST /api/nomenclatures/import              импорт каталога xlsx (см. скил load-nomenclature)
GET  /api/page_types | /api/block_types      справочники типов контента
POST /api/pages                             создать контент-страницу, обязательна привязка application_id
POST /api/applications/{id}/menu_items       создать пункт меню сайта
POST /api/applications/{id}/blocks           создать динамический блок сайта
```

## Public MCP agent access request

```
POST /api/agent-access-requests                    создать заявку на owner/admin email
GET  /api/agent-access-requests/{publicId}/review  HTML review page из письма
POST /api/agent-access-requests/{publicId}/review  детали заявки по approval_token
POST /api/agent-access-requests/{publicId}/approve owner/admin approve
POST /api/agent-access-requests/{publicId}/decline owner/admin decline
POST /api/agent-access-requests/{publicId}/status  статус по request_token
POST /api/agent-access-requests/{publicId}/consume одноразовая выдача agent_token.value
```

`request_token`, `approval_token`, `agent_token.value` не класть в query string, чат, PR body, shell history или клиентские логи.

## Публичная витрина (заголовок `Token`, App Token)

```
GET  /api/counterparty/products?page=N      каталог (пагинация; ShortProductResource)
GET  /api/counterparty/products/{id}        карточка товара
GET  /api/counterparty/prices               {min_price,max_price}
GET  /api/counterparty/categories | brands | delivery_types | payment_types
GET  /api/counterparty/menus/{slug?}        меню/навигация сайта; default slug = navpanel
GET  /api/counterparty/blocks/{code}        динамические блоки сайта
POST /api/counterparty/orders/precalculate  сумма корзины без заказа (throttle 30/мин)
POST /api/counterparty/contact_form         ЗАЯВКА-лид (аноним по ФИО+телефону)
POST /api/counterparty/send_password|login  вход клиента
POST /api/counterparty/callback_auth/init|status  вход по звонку
```

## Клиент (Bearer counterpartyToken, `auth:counterparty`)

```
GET    /api/counterparty/                    профиль; PUT правка; DELETE
GET    /api/counterparty/orders              история; POST создать заказ; GET /{order}; нужен Token + Bearer
GET    /api/counterparty/payment-methods     сохранённые карты; DELETE /{id}; нужен Token + Bearer
.../subscriptions...                         подписки; нужен Token + Bearer
```

## Контракты денег/заказа (критично)

- **`OrderPricingService::calculate`** считает цену по списку `products:[{id,quantity}]`. Для **КАЖДОЙ** позиции ищет `Inventory` (остаток) на складах витрины; нет остатка → **422 `CODE_INVENTORY_NOT_FOUND`**. Это касается и услуг (работ) — им тоже нужен остаток, чтобы пройти precalculate/order.
- **Количество — целое ≥1** (`integer|min:1`). Дробные не пройдут; округлять `ceil`.
- **Цена** строки = `nomenclature.price` (если у склада `is_price_from_inventories=false`) ЛИБО `warehouseNomenclature.markupPrice` (если `true` — остаток со своей ценой+наценкой). Клиент свою цену слать не может.
- **Упаковка**: `quantity_pack = intdiv(quantity, pieces_per_pack)`, fallback pack=1. При `wholesale=true` количество должно быть кратно упаковке и ≥ упаковки (`CODE_WHOLESALE_*`).
- **`contact_form`** (заявка): требует `first_name`,`last_name`,`phone`(numeric 10-12),`products`; считает цену (нужен склад), проверяет наличие (`quantity>inventory.quantity` → 422), создаёт `Counterparty(CLIENT)`, **резервирует остаток на 24ч**, `delivery_type_id=2` захардкожен (тип должен существовать); при `payment_type_id=IS_BANK_CARD` → YooKassa `payment_link`+статус `IS_PAYMENT_WAITING`, иначе `IS_CREATED`.

## Модель данных

- **Nomenclature** (карточка товара/услуги): `provider_code` (=артикул поставщика, напр. Леруа), `price` (цена продажи), `cost_price` (себестоимость), `markup`, `discount`, `pieces_per_pack`, `is_product` (услуга = false), `type/kind`, `category_id`. Услуги и товары — в одной таблице.
- **Inventory = таблица `warehouse_nomenclatures`** (в панели «inventories»): остаток = `nomenclature_id` + `warehouse_id` + `quantity` + `price` + `vat`. Артикула тут НЕТ — он на карточке. **`price` — NOT NULL** в БД (хотя Request говорит nullable → пустой даёт 500).
- **Application (витрина)**: `token` (App Token, `Str::random(32)`), `is_token_active`, `wholesale`, `branch_id`, привязанные склады, `sales_strategy_id`. В каталоге видны ТОЛЬКО товары, у которых есть остаток на складе витрины.
- **Warehouse**: `is_price_from_inventories` (источник цены), `city_id` (**NOT NULL**), привязан к складам через витрину.
- **Page/MenuItem/Block (контент сайта)**: контент привязывается к `application_id`/`applications/{id}`. Агент должен создавать страницы, пункты меню и блоки на тот же `Application`, чей App Token отдаётся фронту.
- **Agent-user для MCP**: технический `User` с `is_agent=true`, обычными role/permissions и Sanctum Bearer token. Внешний MCP-сервер ходит в обычный ERP REST API; отдельного `/api/mcp/*` слоя нет. Подробно: `agent-mcp-access.md`; self-service через почту owner/admin — `agent-access-request.md`.

## Известные баги/грабли ERP (обходить)

1. **`ApplicationController::store` неверно привязывает склад**: `$warehouseId = isset($data['warehouse_id']) ?? null;` → всегда `true` → `sync(true)` цепляет склад **id=1**. Обход: привязывать склад через **`PUT /applications/{id}`** (метод `update` делает sync правильно).
2. **Склад: `city_id` NOT NULL**, а город парсится из адреса примитивно — ищется кусок, начинающийся с **«г »**. Адрес без `г <Город>` (напр. «уточняется», «Новосибирск») → 500. Давать `"address":"г Новосибирск"`.
3. **`warehouse_nomenclatures.price` NOT NULL** без дефолта, но Request помечает `price` как nullable → пустой price даёт 500 (QueryException), а не 422. Всегда слать `price` при добавлении остатка.
4. **Кириллица в JSON через шелл** часто бьётся → тело не доходит (валидация «все поля required»). Писать JSON в UTF-8 файл и слать `curl --data-binary @file.json`.
5. **Контент без правильного `application_id`** создаётся, но фронт нужного сайта его не увидит. Всегда проверять `GET /api/tables/pages?application_id=<appId>` и публичные `GET /api/counterparty/menus/{slug}` / `blocks/{code}` с App Token. Для страниц `query=<slug>` не использовать как lookup по slug: backend ищет `query` только по `title`/`description`/`content`.
6. **Слайды/баннеры** публично читаются через `GET /api/counterparty/slides`, но программного create в API нет — заводятся через UI Itecho.
