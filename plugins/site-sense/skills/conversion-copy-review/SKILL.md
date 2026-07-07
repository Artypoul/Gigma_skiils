---
name: conversion-copy-review
description: "Audit website copy for conversion, clarity, message hierarchy, offer strength, proof, objections, CTA, friction, and section order. Use this skill whenever the user asks to improve page copy, review a landing page, increase conversion, find weak messaging, rewrite for clarity, or diagnose why a page is not converting. Triggers on CRO, конверсия, аудит текста, проверь лендинг, слабый оффер, улучшить страницу, CTA, objections, proof, landing review. Also triggers when page copy exists but needs strategic critique before rewriting."
category: growth
catalog_summary: "Copy audit for clarity, conversion, proof, objections, CTA"
display_order: 8
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Conversion Copy Review

Проверь страницу на ясность и конверсию: понятно ли, кому это нужно, зачем, почему верить и что делать дальше.

---

## When to use

- Нужно оценить лендинг, главную или страницу услуги.
- Пользователь говорит, что страница не конвертит.
- Нужно найти слабые места в оффере, структуре, CTA, proof.
- Нужно дать приоритетные правки, а не просто «улучшить стиль».
- Нужно сравнить текущую страницу с новой смысловой картой.

## When NOT to use

- Если текста ещё нет, используй `page-copywriting`.
- Если проблема только в языке и стиле, используй `russian-copy-polish`.
- Если нет понимания аудитории, сначала используй `product-marketing-context`.
- Если задача техническое SEO, используй SEO-audit skill, если он есть.

---

## Required inputs

- текст страницы или URL content dump;
- цель страницы;
- аудитория;
- CTA;
- traffic source, если известен;
- конверсионные данные, если есть;
- ограничения: бренд, legal, SEO.

Если данных мало, оцени текст по универсальным критериям и пометь недостающие данные.

---

## The framework: 10 conversion checks

### 1. Message match

Страница соответствует ожиданию пользователя из рекламы, поиска, ссылки или меню.

### 2. Clarity

С первого экрана понятно: что это, для кого, что даёт.

### 3. Specificity

Есть конкретные результаты, сценарии, ограничения, цифры, примеры.

### 4. Relevance

Текст говорит о задачах аудитории, а не только о компании.

### 5. Differentiation

Понятно, почему выбрать это, а не альтернативу.

### 6. Proof

Сильные claims поддержаны доказательствами.

### 7. Objection handling

Страница заранее снимает риски, цену, сроки, сложность, доверие.

### 8. CTA

CTA конкретен, заметен и повторяется в логичных местах.

### 9. Friction

Меньше лишних шагов, лишних вопросов, непонятных формулировок.

### 10. Flow

Блоки ведут пользователя от понимания к доверию и действию.

---

## Workflow

1. Определи страницу, аудиторию, CTA и traffic source.
2. Сделай first-screen audit: что понятно за 5 секунд.
3. Проверь структуру: порядок блоков, логика, gaps.
4. Найди generic claims и слабые места.
5. Сопоставь claims с proof.
6. Найди objections, которые не закрыты.
7. Проверь CTA и формы.
8. Дай scorecard 1-5 по 10 критериям.
9. Составь prioritized fixes: P1, P2, P3.
10. Дай примеры переписанных блоков.

---

## Failure patterns

- Давать только общие советы без конкретных переписанных фрагментов.
- Критиковать стиль, игнорируя стратегию.
- Предлагать добавить больше текста вместо лучшей иерархии.
- Усиливать обещания без proof.
- Менять CTA без понимания intent.
- Исправлять H1, не проверив offer и message match.

---

## Output format

```markdown
# Conversion copy review

## Summary
## Scorecard
| Criterion | Score | Notes |
## First-screen diagnosis
## Message hierarchy issues
## Proof gaps
## Objections not handled
## CTA and friction issues
## Section-by-section notes
## Prioritized fixes
### P1
### P2
### P3
## Rewritten examples
## Test ideas
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `copy-review.md`
- Ready for next skill: yes/no
- Recommended next skill: `page-copywriting`
- Inputs passed forward:
  - scorecard
  - P1/P2/P3 fixes
  - proof gaps
  - CTA and friction issues
  - rewritten examples
  - test ideas
- Assumptions to keep:
  - [список]
- Open questions:
  - [что блокирует финал]
- Do not change without confirmation:
  - [valid claims, proven proof, legal/compliance text, SEO-critical headings]
```

Если замечания сводятся только к языковой полировке после уже внесённых copy-правок, затем передай результат в `russian-copy-polish`.

---

## Reference files

- `references/conversion-scorecard.md` — таблица оценки.
- `references/cta-checklist.md` — проверка CTA.
- `references/proof-gap-audit.md` — аудит claims и proof.
