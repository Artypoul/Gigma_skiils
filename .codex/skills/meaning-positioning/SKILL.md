---
name: meaning-positioning
description: "Find the core meanings, positioning, offer, sales angle, message hierarchy, objections, proof, and website narrative for a product or service. Use this skill whenever the user asks for смыслы, позиционирование, оффер, УТП, ценностное предложение, продающий лендинг, упаковка, message map, hero message, brand narrative, how to sell it on the site, or why customers should choose us. Triggers on смыслы сайта, оффер, УТП, value proposition, positioning, JTBD, why us, key message, narrative, message hierarchy, маркетинг, продажи, как продавать, продающий текст. Also triggers when copy sounds generic and needs sharper strategic meaning before rewriting."
category: strategy-and-discovery
catalog_summary: "Meanings, offer, positioning, message hierarchy, objections, proof"
display_order: 3
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Meaning Positioning

Найди смысловую основу сайта: что говорим, кому, почему это важно, чем отличаемся, почему нам верить и какой коммерческий угол действительно поможет продавать.

---

## When to use

- Пользователь просит «найти смыслы», «сделать оффер», «сформулировать УТП».
- Нужно понять, какой hero должен быть на сайте.
- Нужно понять, как продавать продукт на лендинге без пустых обещаний.
- Продукт есть, но текст звучит как у всех.
- Нужно сделать message hierarchy для сайта или лендинга.
- Нужно снять objections и объяснить отличие от альтернатив.

## When NOT to use

- Если нет базового контекста продукта и аудитории, сначала используй `product-marketing-context`.
- Если нужно построить карту сайта, используй `information-architecture`.
- Если нужно написать готовую страницу, используй `page-copywriting` после этого skill.
- Если нужно только отредактировать стиль, используй `russian-copy-polish`.

---

## Required inputs

- продукт/услуга;
- главный сегмент;
- задача или боль аудитории;
- текущие альтернативы;
- отличие от альтернатив;
- доказательства;
- какие claims нельзя обещать без подтверждения;
- желаемый CTA;
- ограничения по тону.

Если данные неполные, работай с допущениями и отмечай, что проверить.

---

## The framework: 6 meaning layers

### 1. Customer reality

Что человек уже переживает до встречи с продуктом. Не «боль» как абстракция, а конкретная ситуация.

### 2. Desired progress

Куда он хочет прийти. Что станет быстрее, безопаснее, проще, прибыльнее, спокойнее.

### 3. Enemy or friction

Что мешает: хаос, ручная работа, риск, неопределённость, дорогие подрядчики, сложные инструменты, отсутствие экспертизы.

### 4. Mechanism

Как именно продукт создаёт изменение. Это не список features, а объяснение причинно-следственной связи.

### 5. Difference

Почему это решение лучше альтернатив для этого сегмента и ситуации.

### 6. Proof

Почему claim можно считать правдой: кейсы, цифры, процесс, демонстрации, отзывы, примеры.

Отделяй:

- safe commercial claim;
- sharp but still defensible claim;
- risky claim that needs explicit validation.

---

## Workflow

1. Определи главный сегмент и его конкретную ситуацию.
2. Сформулируй JTBD: когда, хочу, чтобы.
3. Назови альтернативы и то, почему они недостаточны.
4. Составь список возможных claims и sales angles.
5. Для каждого claim найди proof или пометь как гипотезу.
6. Выбери главный message: самый важный, дифференцирующий и доказуемый.
7. Построй hierarchy: hero → supporting claims → benefits → proof → objections → CTA.
8. Создай 3 варианта позиционирования: safe, sharp, bold.
9. Для каждого варианта пометь уровень коммерческого риска.
10. Рекомендую один вариант и объясни почему.

---

## Failure patterns

- «Мы помогаем бизнесу расти» без сегмента, механизма и proof.
- УТП формулируется как список функций.
- Текст говорит о компании, а не о прогрессе клиента.
- Главное сообщение не отличает продукт от альтернатив.
- Hero обещает больше, чем можно доказать.
- Hero старается быть продающим, но продаёт выдуманный outcome.
- У разных блоков страницы разная логика и нет единой narrative line.
- Слишком много смыслов, нет приоритета.

---

## Output format

```markdown
# Meaning map

## Segment and situation
## JTBD
## Current alternatives
## Core friction
## Desired progress
## Mechanism of value
## Differentiation
## Proof map
## Objections and answers
## Message hierarchy
## Offer options
### Safe
### Sharp
### Bold
## Recommended positioning
## Hero variants
## Words to use / avoid
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `meaning-map.md`
- Ready for next skill: yes/no
- Recommended next skill: `information-architecture`
- Inputs passed forward:
  - recommended positioning
  - main offer and hero claim
  - message hierarchy
  - differentiation
  - proof map
  - objections and answers
  - words to use / avoid
  - CTA logic
- Assumptions to keep:
  - [список]
- Open questions:
  - [только критичные]
- Do not change without confirmation:
  - [locked offer, claims, proof-sensitive phrases]
```

---

## Reference files

- `references/meaning-map-template.md` — шаблон смысловой карты.
- `references/offer-patterns.md` — паттерны оффера для разных типов сайтов.
- `references/message-hierarchy.md` — как строить hierarchy от hero до CTA.
