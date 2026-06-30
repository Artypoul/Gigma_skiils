---
name: miniapp-auth
description: "Спроектировать или проверить авторизацию miniapp в Gigma ERP. Используй когда нужно добавить вход для миниэпса, MAX/Telegram miniapp auth, counterparty access_token, signed contact payload, callback-auth fallback или проверить, где должен жить miniapp auth route."
allowed-tools: Bash Read Grep
---

# Miniapp auth в Gigma ERP

Цель: miniapp должен получить обычный `Counterparty` Sanctum token (`counterparty.access_token.value`) и дальше работать как E-Commerce клиент.

## Перед кодом

1. Сначала найти канонический контур через Graphify и исходники:
   - route/controller/service рядом с `counterparty/callback_auth`;
   - `Token` middleware для App Token;
   - `CounterpartyService::generateAccessToken()`;
   - `CounterpartyResource`.
2. Не добавлять публичные alias routes под текущий фронт. Если авторизация клиента живёт в counterparty-контуре, URL должен быть только там.
3. Сверить, что фронт готов слать `Token` header приложения. Это не `Authorization: Bearer`.

## Канонический route

```
POST /api/counterparty/miniapps/{provider}/contact_auth
Header: Token: <application_token>
```

Рабочий provider сейчас: `max`.

Нельзя поднимать дубль вида `/api/miniapps/.../auth/...` без отдельного решения владельца.

## Контракт ответа

Успешный ответ должен совпадать с обычным counterparty login:

```json
{
  "counterparty": {
    "id": 123,
    "phone_1": "79139277802",
    "access_token": {
      "value": "12|plainSanctumToken"
    }
  }
}
```

## MAX signed contact

Запрос от фронта:

```json
{
  "phone": "+79139277802",
  "auth_date": 1780000000,
  "hash": "<64 hex>",
  "init_data": "auth_date=...&user=...&hash=...",
  "device": "max-miniapp"
}
```

Проверки:

- `init_data` валидируется по WebAppData-схеме provider token.
- `auth_date` не из будущего и не старше настроенного TTL.
- `hash` contact payload проверяется до выдачи токена.
- Подпись проверять по исходному `phone`; нормализованный телефон использовать для поиска/создания `Counterparty`.
- `project_id` брать только из `Application`, найденного по `Token` header.

## Telegram

Не выдавать counterparty token по произвольному `phone`, если Telegram не даёт подписанный proof владения телефоном. Без такого proof:

```
422 miniapp_contact_auth_not_supported
```

Для Telegram использовать callback auth или отдельную будущую привязку Telegram user id к counterparty.

## Данные и таблицы

- Не создавать таблицы provider bindings, пока продукт явно не требует связку `provider_user_id -> counterparty`.
- Не вводить новые термины, если хватает `Application`, `Counterparty`, `Token`, `CounterpartyResource`.
- Историю регистрации писать тем же паттерном, что callback-auth.

## Тесты

Минимальный набор:

- happy path MAX: создаёт/находит `Counterparty` и возвращает `counterparty.access_token.value`;
- project scope: один телефон в разных `project_id` не смешивается;
- invalid hash -> 401;
- provider token missing -> 503;
- Telegram unsigned phone -> 422;
- нет `Token` header -> 401.

Перед PR: `route:list --path=miniapps` должен показывать только канонический counterparty route.
