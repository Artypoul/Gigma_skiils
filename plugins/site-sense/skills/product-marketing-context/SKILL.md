---
name: product-marketing-context
description: "Create a reusable product marketing context file covering product, audience, problem, JTBD, alternatives, value proposition, positioning, proof, objections, and voice of customer. Use this skill whenever the user asks to define the product context, ICP, audience, positioning foundation, website brief, or inputs before writing site copy. Triggers on ЦА, ICP, JTBD, продуктовый контекст, позиционирование, бриф сайта, вводные, кому продаём, проблема клиента, alternatives, product marketing. Also triggers before website structure or copy work when the context is missing."
category: strategy-and-discovery
catalog_summary: "Reusable product, audience, problem, alternatives, proof, and messaging context"
display_order: 2
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Product Marketing Context

Создай базовый контекст, на который будут опираться структура сайта, SEO и тексты.

---

## When to use

- Нужно собрать вводные перед сайтом, лендингом или текстами.
- Пользователь просит определить ЦА, ICP, сегменты, боли, JTBD, альтернативы.
- Нужно понять, что писать в hero и почему аудитории это важно.
- Сайт уже есть, но тексты звучат общо и непонятно.
- Нужно создать файл `.agents/product-marketing.md` или `product-marketing-context.md`.

## When NOT to use

- Если нужно только переписать готовый текст, используй `russian-copy-polish`.
- Если контекст уже есть и нужно сделать оффер, используй `meaning-positioning`.
- Если нужно спроектировать sitemap, используй `information-architecture`.
- Если нужно написать страницу, используй `page-copywriting`.

---

## Required inputs

Желательно получить:

- описание продукта или услуги;
- аудитория и сегменты;
- главная проблема;
- текущие альтернативы;
- конкуренты;
- proof: кейсы, цифры, отзывы, логотипы, опыт;
- бизнес-модель и CTA;
- география и язык;
- ограничения по бренду, регуляторике, продукту.

Если часть данных отсутствует, создай раздел `Assumptions` и отметь, что нужно проверить.

---

## The framework: 9 blocks

### 1. Product

Что это, какую категорию занимает, что делает, чего не делает.

### 2. Audience

Главный сегмент, вторичные сегменты, покупательская роль, контекст использования.

### 3. Trigger event

Что должно произойти, чтобы пользователь начал искать решение.

### 4. Job to Be Done

Какой прогресс пользователь хочет получить. Не демография, а задача.

### 5. Current alternatives

Чем пользователь решает проблему сейчас: конкурентами, ручной работой, Excel, подрядчиками, «ничего не делать».

### 6. Pain and cost of inaction

Что болит, как это проявляется, во что обходится бездействие.

### 7. Value proposition

Who → Why → What before → How → What after → Alternatives.

### 8. Differentiation and proof

Чем отличаемся и чем это можно доказать.

### 9. Messaging inventory

Главный claim, подзаголовки, benefit pillars, objections, CTA, слова клиента.

---

## Workflow

1. Проверь, есть ли существующий контекст в проекте.
2. Раздели аудитории на сегменты. Не смешивай всех в одну ЦА.
3. Для главного сегмента опиши ситуацию, триггер и JTBD.
4. Назови альтернативы и слабости текущего способа.
5. Сформулируй ценность через «до → как → после».
6. Запиши proof points отдельно от claims.
7. Составь message inventory для сайта.
8. Отметь рисковые гипотезы, которые нужно проверить интервью, аналитикой или продажами.
9. Сохрани результат как `product-marketing.md` или предложи вставить в `.agents/product-marketing.md`.

---

## Failure patterns

- «ЦА: все предприниматели» без сегментов и ситуации.
- Описание продукта вместо описания ценности для пользователя.
- «Уникальность: качество и сервис» без доказательств.
- Игнорирование альтернативы «ничего не менять».
- Обещания без proof.
- Смешивание желаний бизнеса и языка клиента.
- Начало с features, а не с проблемы и результата.

---

## Output format

```markdown
# Product marketing context

## Assumptions
## Product
## Audience
## Trigger events
## JTBD
## Pain and cost of inaction
## Alternatives
## Value proposition
## Differentiation
## Proof points
## Objections
## Voice of customer
## Messaging inventory
## Open questions
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `product-marketing.md`
- Ready for next skill: yes/no
- Recommended next skill: `meaning-positioning`
- Inputs passed forward:
  - product/category
  - primary segment and situation
  - JTBD and trigger event
  - alternatives
  - value proposition
  - differentiation
  - proof points and proof gaps
  - objections
  - CTA and tone
- Assumptions to keep:
  - [список]
- Open questions:
  - [только критичные]
- Do not change without confirmation:
  - [claims, compliance, audience, CTA]
```

---

## Reference files

- `references/context-template.md` — заполняемый шаблон.
- `references/segment-card.md` — карточка сегмента.
- `references/proof-inventory.md` — как отделять claims от доказательств.
