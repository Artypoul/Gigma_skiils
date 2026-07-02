---
name: receive-order-paid-webhook
description: "Интегрировать внешний backend/сервис с Gigma ERP order.paid webhook: принять POST об оплате заказа, проверить X-Signature HMAC, timestamp и event_id, настроить ORDER_PAID_WEBHOOK_SECRET, идемпотентность и безопасные ответы. Используй когда нужно реализовать или проверить получатель payment/order-paid webhook от Gigma ERP."
allowed-tools: Read Grep Bash
---

# Receive Gigma `order.paid` Webhook

## Overview

Используй этот скил, когда внешний backend, сайт, miniapp backend, подписочный сервис или другая интеграция должна принимать событие `order.paid` из Gigma ERP. Цель: принять только настоящий webhook, не обработать дубль как новый платёж и не утечь секретами/PII в логи.

Если работа идёт в `itecho-erp-backend`, не добавляй туда глобальный `ORDER_PAID_WEBHOOK_SECRET`: в ERP секрет хранится у конкретного `application_webhook`. На принимающем сервисе можно хранить тот же секрет в env `ORDER_PAID_WEBHOOK_SECRET`.

## Contract

Gigma ERP отправляет `POST` на публичный HTTPS URL webhook.

Headers:

- `Content-Type: application/json`
- `X-Webhook-Event: order.paid`
- `X-Webhook-Event-Id: order.paid:{order_id}:{payment_id|p_id|free}`
- `X-Webhook-Delivery-Id: {delivery_id}`
- `X-Webhook-Timestamp: {unix_seconds}`
- `X-Signature: sha256={hex_hmac}`

Signature:

```text
expected = "sha256=" + HMAC_SHA256(
  key = ORDER_PAID_WEBHOOK_SECRET,
  message = X-Webhook-Timestamp + "." + raw_request_body
)
```

Payload shape:

```json
{
  "event": "order.paid",
  "event_id": "order.paid:123:p_456",
  "occurred_at": "2026-07-03T10:00:00.000000Z",
  "order": {
    "id": 123,
    "final_price": "990.00",
    "paid_at": "2026-07-03T10:00:00.000000Z",
    "products": [
      { "id": 10, "name": "Product", "quantity": 1 }
    ]
  },
  "counterparty": {
    "id": 55,
    "phone_1": "+79990000000",
    "email": "client@example.com"
  },
  "shop": { "id": 7 }
}
```

`counterparty` can be `null`. Do not trust optional fields for money-side decisions without checking local business rules.

## Receiver Workflow

1. Inspect the target service stack and find the existing webhook/router pattern.
2. Add a dedicated route such as `POST /webhooks/gigma/order-paid`.
3. Read the raw request body before JSON parsing. Signature verification must use the exact bytes/string received.
4. Require `ORDER_PAID_WEBHOOK_SECRET`; fail closed on missing/empty secret.
5. Verify timestamp freshness before expensive work. Use a 5 minute window unless the service has known clock drift; never accept very old requests.
6. Recompute HMAC over `timestamp + "." + raw_body` and compare with `X-Signature` using constant-time comparison.
7. Parse JSON only after signature passes.
8. Require event consistency: header `X-Webhook-Event`, body `event`, and event-id prefix must all match `order.paid`.
9. Atomically claim `X-Webhook-Event-Id` in a durable store with a unique constraint before side effects. Duplicate event id should return `200` or `204` without repeating the business action.
10. Return `2xx` only after the event is durably recorded or safely processed. Return `5xx` for temporary failures so ERP can retry.

Idempotency means the same payment event may arrive more than once; the receiver must treat the second copy as already handled.

## Minimal Pseudocode

```text
raw_body = request.raw_body
timestamp = header("X-Webhook-Timestamp")
signature = header("X-Signature")
secret = env("ORDER_PAID_WEBHOOK_SECRET")

reject 500 if secret is missing
reject 400 if timestamp/signature/event headers are missing
reject 401 if timestamp is stale
expected = "sha256=" + hmac_sha256(secret, timestamp + "." + raw_body)
reject 401 if !constant_time_equal(signature, expected)

payload = parse_json(raw_body)
reject 400 if payload.event != "order.paid"
reject 400 if payload.event_id != header("X-Webhook-Event-Id")

claimed = idempotency_store.try_insert_unique(payload.event_id, status="processing")
if !claimed:
  return 204

process_or_enqueue(payload)
idempotency_store.mark_done(payload.event_id)
return 204
```

`try_insert_unique` must be a single atomic operation backed by a unique key. Do not implement it as `exists()` followed by `insert()`: concurrent retries can both pass the check and process the same paid event twice.

## Node/Express Pattern

Use `express.raw()` for this route. Do not use `express.json()` before signature verification on the same route.

```js
import crypto from "node:crypto";
import express from "express";

const app = express();

app.post(
  "/webhooks/gigma/order-paid",
  express.raw({ type: "application/json", limit: "256kb" }),
  async (req, res) => {
    const secret = process.env.ORDER_PAID_WEBHOOK_SECRET;
    if (!secret) return res.sendStatus(500);

    const rawBody = req.body.toString("utf8");
    const timestamp = req.get("X-Webhook-Timestamp");
    const signature = req.get("X-Signature");
    const event = req.get("X-Webhook-Event");
    const eventId = req.get("X-Webhook-Event-Id");

    if (!timestamp || !signature || event !== "order.paid" || !eventId) {
      return res.sendStatus(400);
    }

    const ageMs = Math.abs(Date.now() - Number(timestamp) * 1000);
    if (!Number.isFinite(ageMs) || ageMs > 5 * 60 * 1000) {
      return res.sendStatus(401);
    }

    const expected =
      "sha256=" +
      crypto.createHmac("sha256", secret).update(`${timestamp}.${rawBody}`).digest("hex");

    if (!safeEqual(signature, expected)) return res.sendStatus(401);

    let payload;
    try {
      payload = JSON.parse(rawBody);
    } catch {
      return res.sendStatus(400);
    }

    if (payload.event !== "order.paid" || payload.event_id !== eventId) {
      return res.sendStatus(400);
    }

    // processIdempotently must claim eventId with one atomic unique insert
    // before side effects. Return 204 on duplicate.
    await processIdempotently(eventId, payload);
    return res.sendStatus(204);
  }
);

function safeEqual(a, b) {
  const aa = Buffer.from(a);
  const bb = Buffer.from(b);
  return aa.length === bb.length && crypto.timingSafeEqual(aa, bb);
}
```

## Laravel/PHP Pattern

Use `$request->getContent()` as raw body and `hash_equals()` for comparison. Put the route outside CSRF/browser middleware if it is a public webhook endpoint, and protect it with the signature instead of session auth.

```php
$secret = env('ORDER_PAID_WEBHOOK_SECRET');
$rawBody = $request->getContent();
$timestamp = (string) $request->header('X-Webhook-Timestamp', '');
$signature = (string) $request->header('X-Signature', '');
$event = (string) $request->header('X-Webhook-Event', '');
$eventId = (string) $request->header('X-Webhook-Event-Id', '');

if (! is_string($secret) || $secret === '') {
    abort(500);
}

if ($timestamp === '' || $signature === '' || $event !== 'order.paid' || $eventId === '') {
    abort(400);
}

if (! ctype_digit($timestamp) || abs(time() - (int) $timestamp) > 300) {
    abort(401);
}

$expected = 'sha256='.hash_hmac('sha256', $timestamp.'.'.$rawBody, $secret);

if (! hash_equals($expected, (string) $signature)) {
    abort(401);
}

try {
    $payload = json_decode($rawBody, true, 512, JSON_THROW_ON_ERROR);
} catch (\JsonException) {
    abort(400);
}

if (($payload['event'] ?? null) !== 'order.paid' || ($payload['event_id'] ?? null) !== $eventId) {
    abort(400);
}

// Claim $eventId with one atomic unique insert before side effects.
// On duplicate, return response()->noContent().
```

## Security Rules

- Do not require `Authorization` from ERP for this webhook. ERP signs the request; custom `Authorization` headers are intentionally blocked in webhook configuration.
- Do not log `ORDER_PAID_WEBHOOK_SECRET`, full `X-Signature`, full phone, full email, or raw payload in production logs.
- Mask identifiers in logs where practical: `event_id`, `order.id`, status, and short error reason are usually enough.
- Never process unsigned requests in a fallback mode.
- Do not accept `http://` webhook URLs for production tests; use HTTPS.
- Keep the endpoint narrow: only `order.paid`, only `POST`, small body limit.
- If the handler calls another paid/money side effect, make it idempotent too.

## ERP Setup Notes

In Gigma ERP, create a webhook for the Application:

```http
POST /api/applications/{application}/webhooks
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "event": "order.paid",
  "url": "https://your-service.example.com/webhooks/gigma/order-paid",
  "secret": "{same value as ORDER_PAID_WEBHOOK_SECRET}",
  "is_active": true
}
```

Secret rotation exists, but it returns a new secret that must be installed on the receiver. For low-risk rotation, either pause the webhook, rotate, update env, restart, then resend failed deliveries; or temporarily support old and new secrets with a short explicit expiry window. Remove the old secret immediately after the first successful delivery signed by the new secret; never leave dual-secret support permanent.

## Required Tests

For a production receiver, add focused tests:

- valid signed request returns `2xx` and records the event;
- invalid signature returns `401` and does not process;
- stale timestamp returns `401`;
- duplicate `event_id` returns `2xx` and does not repeat side effects;
- concurrent duplicate `event_id` requests cannot both run side effects;
- malformed JSON after a valid signature returns `400`;
- missing secret fails closed;
- body parser does not change the raw body before HMAC verification.
