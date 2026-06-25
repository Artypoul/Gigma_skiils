# Карта e-commerce-возможностей Gigma

Распиленный (по `erp-rules.txt`, `openapi.json` и операционным скилам `gigma-erp`) справочник для роли **консультант по интернет-магазинам**: что Gigma реально умеет для онлайн-продаж, как это включается и **чего обещать нельзя**. Не дублирует полный API-контракт — за точными телами запросов иди в канонические источники (внизу).

> Главное правило консультанта: **не выдумывать фичи**. Если возможности нет в этой таблице или она помечена ⚠ — не обещать клиенту. Сверяться с `erp-rules.txt`.

## Что такое Gigma для интернет-магазина

Gigma — **headless** платформа. Один бэкенд `https://api.gigma.ru/api`, два контура:

- **E-Commerce (витрина)** — публичный API клиента магазина, неймспейс `/api/counterparty/*`: каталог, корзина-расчёт, заказы, профиль, оплата, контент. Это то, что дёргает фронт-витрина.
- **ERP (бэк-офис)** — рабочее место владельца/сотрудников: номенклатура, склады, остатки, заказы-управление, CRM, роли, контент.

Витрина (фронт) — **отдельный сайт**, который ходит в этот API. Бэкенд её не рендерит. Типовая связка: статика/Next-фронт на хостинге + домен + **серверный рендер (SSR) только для оплаты** + headless Gigma как бэкенд. Всё изолировано по `project_id` (мультитенант).

Авторизация: `Authorization: Bearer <id>|<secret>` (Sanctum, разделитель `|` обязателен).
- Клиент магазина: `POST /api/counterparty/login` (`phone` принимает и email; пароль — звонком, последние 4 цифры номера).
- Сотрудник: `POST /api/login` (пароль из письма после `/api/send_password`).

## Потребность магазина → возможность Gigma

| Что нужно магазину | Есть | Как (endpoint / скил) | ⚠ Ограничение / ловушка |
|---|---|---|---|
| Каталог товаров и услуг | ✅ | `nomenclatures` (kind 2=товар, 1=услуга) + `categories` + `brands` + `tags`; витрина читает `GET /api/counterparty/products`, `/api/counterparty/categories`, `/api/counterparty/brands` | цена — **строка** `"1000.00"`, не число |
| Поиск по каталогу | ✅ | `GET /api/counterparty/products?query=…`; подсказки — `GET /api/counterparty/tags`; популярные запросы — `GET /api/counterparty/search/popular`; история — `GET /api/counterparty/search/history` | кириллицу в `query` URL-кодировать |
| Массовая загрузка прайса | ✅ | `POST /api/nomenclatures/import` — `multipart/form-data`, поле `file` (xls/xlsx/csv) → скил **load-nomenclature**; повторная загрузка обновляет позиции по артикулу, не плодит дубли (см. load-nomenclature) | рекомендуется xlsx: на CSV импорт сам определяет разделитель и путается на запятых внутри названий; пустые ячейки писать `None`, не `''`; единице измерения нужен `abbreviation` (детали загрузки — в load-nomenclature) |
| Остатки и склад | ✅ | `warehouses` + `inventories`; `POST /api/inventories` поштучно или `POST /api/inventories/upload` — файл (xls/csv/xml) **или** JSON-накладная (для 1С/поставщика) | `inventory.counterparty_id` — только для поставщика (тип 2); складу нужен `city_id` (см. create-tenant) |
| Корзина, расчёт суммы | ✅ | `POST /api/counterparty/orders/precalculate` (тело: `products[]` + опц. `promo_code`) | **не создаёт заказ**; лимит 30 запр/мин — кешировать на фронте |
| Оформление заказа клиентом | ✅ | `POST /api/counterparty/orders` (`delivery_type_id` + `products[]`; условно `shop_id`/`address`) | `phone`/`comment` **не принимаются** (телефон из профиля); POST не идемпотентен |
| Заказ без регистрации (гость) | ✅ | `POST /api/counterparty/contact_form` (имя/телефон + `products[]`) | `products.*.id` — это **id остатка** (`warehouse_nomenclatures`), не товара |
| Онлайн-оплата картой | ✅ | YooKassa: `payment_type_id=2` → бэк создаёт платёж и кладёт `payment_link`; webhook `POST /api/yookassa` → статус `22` (оплачен) | нужен YooKassa-кабинет клиента; creds хранятся **per-warehouse** (мультимагазин ок); на тесте `payment_link` может не работать |
| Оплата наличными / при получении | ✅ | `payment_type_id=1` | — |
| Способы доставки | ✅ | `delivery_types` + `subtypes` + `params`; самовывоз (type 1 → `shop_id`), доставка по адресу (type 2 → subtype 2 → `address`) | адрес — через Dadata `POST /api/counterparty/search_address` |
| Личный кабинет клиента | ✅ | `/api/counterparty` (профиль), избранное (`/api/counterparty/products/favourites`), история заказов (`/api/counterparty/orders`) | сброс пароля — звонком |
| Контент-страницы (о доставке, оплате, о нас) | ✅ | `POST /api/pages` (по `slug`) + `page_types` | — |
| Баннеры / слайдер на главной | ⚠ read-only в API | витрина читает `GET /api/counterparty/slides` | программного create слайдов нет — заводятся через UI Itecho |
| Меню и навигация витрины | ✅ | пункты — `POST /api/applications/{id}/menu_items`; витрина читает `GET /api/counterparty/menus/{code}` | сам ресурс `/api/menus` — GET-only (это меню сотрудника) |
| Динамические блоки (промо-секции) | ✅ | `POST /api/applications/{id}/blocks`; витрина читает `GET /api/counterparty/blocks/{code}` | — |
| Уведомления клиенту | ⚠ частично | `GET /api/counterparty/notifications` (опрашивать) | **вебхуков наружу НЕТ** — только polling каждые 30–60 сек |
| Скидки / промокоды | ✅ | `discounts` (`promo_code`, `magic_link`, `audience`, статистика) | ⚠ `POST /api/promotions` **баговый (500)** — использовать `discounts` |
| Несколько магазинов / юрлиц | ✅ | несколько `branches` и `warehouses`; YooKassa-creds свои на каждый склад | — |
| CRM: клиенты, история, заказы | ✅ | `counterparties` + `/history` + `/api/orders` | — |
| Роли и доступы сотрудников | ✅ | `roles` + `permissions` (Spatie; `edit-X` = create+update+delete) | чужой `project_id` → **403**, даже при наличии права |
| Статусы заказа | ✅ | `order_statuses`; ID статуса заказа (`order_status_id`) захардкожены: `2`=ждёт оплаты, `22`=оплачен, `6`=отменён | не путать с `payment_type_id` (1=нал, 2=карта); имена статусов разнятся по проектам — для логики брать ID, для показа — `GET /api/order_statuses` |

## Чего НЕ делать / не обещать (известные ограничения, §19 erp-rules)

- **Нет исходящих вебхуков** на смену статуса заказа/контрагента → только polling (30–60 сек).
- **Нет bulk-операций**: 50 товаров = 50 запросов. Rate-limit ~60/мин, на импортах ≤1 запрос/сек, ≤5 параллельно. На массовых операциях закладывать время (`N × ~1с`).
- **ERP `POST /api/orders/{id}/nomenclatures`** баг 500 → заказы оформлять через витринный `POST /api/counterparty/orders` (резерв создаётся внутри транзакции).
- **ERP `DELETE /api/orders/{id}`** баг 500 → отмена через `PUT /api/orders/{id}` со статусом `6`.
- **`POST /api/promotions`** баг 500 → использовать `discounts`.
- **`POST /api/sales_strategies`** — только через UI Itecho, не через API.
- **`POST /api/tags`** — отдельного create нет; теги создаются включением в `tag_id[]` родителя (номенклатуры/категории).
- **`POST /api/calls`** — баг 500, не задокументирован (вопрос к бэк-команде).
- **Слайды/баннеры** — в API только чтение; заводятся через UI Itecho.
- **Нет idempotency-key, нет версионирования URL** (`/api/v1` отсутствует).
- На **5xx при POST/PUT** первая гипотеза — «неполное тело», не «сервер упал».

## Канонические источники (всегда сверяться с ними, не с памятью)

- **Правила для агента** (единственный источник правды): https://artypoul-docs-gigma-7b80.twc1.net/erp-rules.txt — auth, форматы, тела (§18), баги (§19), сценарии (§17).
- **OpenAPI** (179+ операций, точные контракты): https://artypoul-docs-gigma-7b80.twc1.net/openapi.json
- **Swagger UI** (Try It): https://artypoul-docs-gigma-7b80.twc1.net/api-docs/
- Индекс / полный корпус: `/llms.txt`, `/llms-full.txt` по тому же хосту.
- Операционные скилы-«руки»: плагин **`gigma-erp`** (create-tenant, load-nomenclature) — должен быть установлен рядом.
