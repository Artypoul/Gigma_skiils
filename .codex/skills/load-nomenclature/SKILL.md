---
name: load-nomenclature
description: Массово залить справочник номенклатуры (товары/услуги, каталог) в проект Gigma ERP через штатный импорт xlsx. Используй когда нужно «создать справочники», «загрузить каталог/прайс», «импортировать товары», «завести номенклатуру».
when_to_use: загрузка каталога/прайса, импорт товаров и услуг, наполнение справочников проекта
allowed-tools: Bash Read Write Grep
---

# Загрузка справочника номенклатуры (импорт каталога)

Заливает позиции в `nomenclatures` под `project_id` авторизованного сотрудника **через Eloquent** (не в обход — касты/триггеры применяются). Ключ — артикул: повторный залив **обновляет** цену, а не плодит дубли.

## 1. Готовим файл — ТОЛЬКО `.xlsx`

CSV не использовать: импорт авто-определяет разделитель (`config/excel.php → imports.csv.delimiter = null`) и путается на запятых внутри названий. Делай xlsx через `openpyxl`.

Колонки (заголовки — как в экспорте ЕРП; формат заголовков `slug`):
`Артикул, Штрих-код, Категория, Название, Описание, Спецификация, Единицы хранения, Страна, Импорт, Тип, Вид, Торговая марка` + опц. `Себестоимость, Цена, Тип налога, Теги`.

Значения справочников:
- **Тип** и **Вид**: использовать уже засеяные имена — `Товар` / `Услуга` (иначе создадутся новые типы/виды).
- **Тип налога**: `Без НДС` / `10%` / `20%` (только lookup, не создаётся).
- **Категория**, **Торговая марка**, **Теги** — авто-создаются (требуется только `name`), это безопасно.

## 2. Две главные грабли (на них падает импорт)

1. **Пустые ячейки = `None`, НЕ `''`.** Пустая строка `''` валит integer-колонки (`1366 Incorrect integer value: '' for column 'barcode'`). В openpyxl пиши `None` для пустых.
2. **Единицы измерения.** `storage_units` требует `abbreviation` (NOT NULL без дефолта). Импорт создаёт единицу только по `name` → падает `1364 Field 'abbreviation' doesn't have a default value`. Варианты:
   - оставить **«Единицы хранения» пустыми** (`storage_unit_id = null`, проставить позже), **или**
   - заранее завести нужные единицы в `storage_units` с аббревиатурами (`шт→шт, м²→м², кг→кг, м→м`), тогда импорт их найдёт.

Генерация xlsx (пример):
```python
import json, openpyxl
rows = json.load(open('catalog.json', encoding='utf-8'))
wb = openpyxl.Workbook(); ws = wb.active
headers = list(rows[0].keys()); ws.append(headers)
for r in rows:
    ws.append([(None if (r[h] == '' or r[h] is None) else r[h]) for h in headers])
wb.save('catalog.xlsx')
```

## 3. Получаем токен сотрудника проekта

Импорт требует `auth:user`. Токен — через одноразовый код:
```
POST /api/send_password   { "login": "<email сотрудника проекта>" }   # генерит код, шлёт письмом
POST /api/login           { "login": "<email>", "password": "<код>", "device": "import" }
```
Токен в ответе: `user.access_token.value` (вид `2983|....`). Срок жизни кода — **5 минут**.

**Если письмо не доходит** (после переезда почта капризна): код дополнительно пишется в БД **открытым текстом** — `SELECT password FROM passwords WHERE login='<email>' ORDER BY id DESC LIMIT 1` (таблица `passwords`). Берёшь оттуда и логинишься.

## 4. Импорт

```bash
curl -s -X POST "https://api.gigma.ru/api/nomenclatures/import" \
  -H "Authorization: Bearer <TOKEN>" -H "Accept: application/json" \
  -F "file=@catalog.xlsx"
```
Ответ: `{ created, updated, skipped, errors }`. Если `skipped>0` — смотри `errors[0].message` (там SQL-ошибка), чини файл, повторяй (по артикулу — идемпотентно).

## 5. Проверка

```sql
SELECT COUNT(*) FROM nomenclatures WHERE project_id=<PID>;
SELECT provider_code, name, price FROM nomenclatures WHERE project_id=<PID> ORDER BY id LIMIT 5;
```

Доступ к БД — см. скил `create-tenant` (VPN `31.77.160.204` → priscilla `161.104.46.126`, `gen_user`, пароль из `.env`).
