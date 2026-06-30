---
name: setup-storefront
description: "Настроить витрину/сайт Gigma ERP под ключ: филиал + склад + приложение (App Token) + остатки + контентная привязка (страницы, меню, блоки), чтобы фронт видел товары, цены и контент. Используй когда нужно «настроить витрину», «поднять сайт/магазин/каталог», «сделать так, чтобы фронт видел товары и цены», «выдать App Token», «привязать контент к сайту»."
when_to_use: "поднять витрину/магазин/сайт для проекта, выдать App Token фронту, сделать каталог видимым, подготовить ERP к заказам, привязать страницы/меню/блоки к application"
allowed-tools: Bash Read Write Grep
---

# Настройка витрины Gigma ERP под ключ

Цель: чтобы публичный фронт по **App Token** видел каталог с ценами, контент сайта и мог оформлять заказы. Делается **owner-токеном через API** (без VPN). Полная карта эндпоинтов/контрактов/багов — `reference/erp-api.md`.

Цепочка: **филиал → склад → витрина (App Token) → остатки → контент → проверка каталога и контента**. Без склада+остатков товары в каталоге НЕ видны (каталог join'ит инвентарь). Без `application_id` страницы/меню/блоки не будут привязаны к нужному сайту.

## 0. Owner-токен

Bearer уровня `auth:user` (вид `2992|…`). Дают готовым ИЛИ получить: `POST /api/send_password {login}` → код (письмо или `passwords` в БД) → `POST /api/login {login,password,device}` → `user.access_token.value`. Проверка: `GET /api/user` должен вернуть `role.name=owner` и `project_id`.

> **Кириллицу в теле слать файлом**, не инлайном: шелл бьёт UTF-8 → «все поля required». Пиши JSON в файл, шли `curl --data-binary @file.json -H "Content-Type: application/json" -H "Accept: application/json"`.

## 1. Филиал (branch) — юр.лицо-контейнер

Витрина требует `branch_id`. Если филиалов нет (`GET /api/branches_list` пуст) — создать. Обязательны: `title,name,inn,phone_1,email,address,legal_address`. `inn` — просто `string|min:1`, можно заглушку (`"000000000000"`) — владелец впишет реальные перед приёмом оплаты.

```
POST /api/branches   {title,name,inn,phone_1,email,address,legal_address}  → branch.id
```

## 2. Склад (warehouse)

```
POST /api/warehouses  {name, address:"г <Город>", storage_unit_id, is_price_from_inventories, owned_by_us:true}
```
- **`address` ОБЯЗАТЕЛЬНО с префиксом «г »** (`"г Новосибирск"`) — иначе `city_id` NULL → 500 (грабля #2).
- `storage_unit_id` — из `GET /api/storage_units` (15=шт).
- **`is_price_from_inventories`**: `false` → каталог берёт цену из **карточки товара** (`nomenclature.price`) — простой вариант, цены правятся в номенклатуре. `true` → цена из остатка (`markupPrice` = цена+наценка на складе) — для модели «перепродажа с наценкой».

## 3. Витрина (application) — даёт App Token

```
POST /api/applications  {is_website:true, name, branch_id, warehouse_id:[<wid>], sales_strategy_id:2, wholesale:false}
```
Ответ содержит `token` (App Token), но **`is_token_active:false`** и склад привязывается НЕВЕРНО (грабля #1: `store` цепляет склад id=1). Поэтому сразу:

```
PUT /api/applications/{appId}  {warehouse_id:[<wid>], is_token_active:true}
```
После PUT проверь в ответе: `is_token_active:true` и `warehouses:[{id:<wid>}]` (твой склад, не id=1). `token` — это App Token для фронта (заголовок `Token`).

## 4. Остатки (inventory) — чтобы товары были видны

Для каждой позиции номенклатуры (`GET /api/nomenclatures?per_page=1000` → id, price):
```
POST /api/warehouses/{wid}/nomenclatures  {nomenclature_id, warehouse_id:<wid>, quantity:100000, price:<цена карточки>}
```
- **`price` слать обязательно** (колонка NOT NULL, грабля #3), даже при `is_price_from_inventories=false` — продублируй цену карточки.
- Большой `quantity` (виртуальный склад, если товар физически не лежит — закупается у поставщика).
- Услугам (`is_product=false`) остаток тоже нужен, если они должны проходить precalculate/заказ.
- Заливать циклом (Node `fetch`/bash). ~270 позиций ≈ минута.

## 5. Контент сайта — привязка к application

Все контентные write-запросы делают owner-токеном. Главный инвариант: в каждом объекте использовать **тот же `appId`**, который вернул шаг 3. Перед созданием показать владельцу список создаваемых страниц/пунктов/блоков; POST не идемпотентны и могут плодить дубли.

```http
GET  /api/page_types
GET  /api/block_types
POST /api/pages
POST /api/applications/{appId}/menu_items
POST /api/applications/{appId}/blocks
```

Минимальные рабочие тела:

```json
{
  "application_id": 39,
  "is_page": true,
  "page_type_id": 1,
  "slug": "delivery",
  "title": "Доставка",
  "meta_title": "Доставка",
  "description": "Условия доставки",
  "meta_description": "Условия доставки",
  "content": "<p>Текст страницы доставки.</p>",
  "tags": []
}
```

```json
{"name":"Доставка","slug":"delivery","parent_id":null,"avatar_id":null,"preview_id":null}
```

```json
{"block_type_id":1,"name":"Главный текст","identifier":"home-main-text","link":null,"avatar_id":null,"file_id":null,"text":"Текст блока","parent_id":null}
```

- `code` у страниц и блоков числовой; если не нужен внешний числовой код, не шли его — для страниц backend сгенерит сам. `slug` у страниц уникален; если страница уже есть — сначала найти её через `GET /api/tables/pages?application_id=<appId>&query=<slug>` и обновить `PUT /api/pages/{id}`.
- Пункты меню живут внутри application: `POST /api/applications/{appId}/menu_items`; `slug` должен совпадать с роутом фронта или slug страницы.
- Блоки живут внутри application: `POST /api/applications/{appId}/blocks`; `block_type_id` брать из `GET /api/block_types`. Для текста обычно `1`/`2`, для картинки нужен предварительный `POST /api/files` и `file_id`. Для стабильной фронтовой привязки задавай `identifier` и проверяй через `/api/counterparty/blocks/id/{identifier}`; `/blocks/{code}` используй только когда задан числовой `code`.
- Баннеры/слайды через API не создавать: публичный фронт читает `GET /api/counterparty/slides`, но программного create нет — это ручная настройка в UI Itecho.

## 6. Проверка (как будет ходить фронт)

```bash
curl -s -H "Token: <appToken>" -H "Accept: application/json" \
  "https://api.gigma.ru/api/counterparty/products?per_page=2"
curl -s -H "Token: <appToken>" "https://api.gigma.ru/api/counterparty/prices"
curl -s -H "Token: <appToken>" "https://api.gigma.ru/api/counterparty/menus/<menu-code>"
curl -s -H "Token: <appToken>" "https://api.gigma.ru/api/counterparty/blocks/id/<block-identifier>"
```
Должны вернуться товары с `price` и непустой `total`, `prices` → `{min_price,max_price}`. Для контента должен вернуться объект меню/блока нужного сайта. Если каталог пуст — нет остатков (шаг 4) или токен не активен (шаг 3). Если контент пуст — объект создан не на тот `application_id` или фронт запрашивает не тот `code`/`slug`.

## Грабли (кратко)

1. `store` витрины цепляет склад id=1 → привязывай склад через **PUT update**.
2. Адрес склада без «г <Город>» → 500 (`city_id` NULL).
3. Остаток без `price` → 500 (колонка NOT NULL вопреки nullable-валидации).
4. Кириллица инлайном в curl → тело не доходит → слать файлом `--data-binary @`.
5. `provider_code` (артикул) есть на карточке, но публичный каталог его НЕ отдаёт (`ShortProductResource`). Чтобы фронт связал цену с артикулом — добавить поле в ресурс ИЛИ выгрузить связку `артикул↔id↔price` owner-токеном (`GET /api/nomenclatures`).
6. Страницы/меню/блоки без правильного `application_id` создадутся, но фронт нужного сайта их не увидит.

Панель для проверки глазами: `https://cloud.gigma.ru/sites/{appId}` (витрина), `…/warehouses/list-warehouses/{wid}` (склад).
