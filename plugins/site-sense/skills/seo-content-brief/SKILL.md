---
name: seo-content-brief
description: "Create an SEO content brief for a webpage or article covering search intent, query set, title, meta description, H1/H2, entities, required sections, FAQ, schema, internal links, and conversion next step. Use this skill whenever the user asks for SEO brief, semantic brief, keyword-based page plan, article structure, search content brief, or on-page content requirements. Triggers on SEO-бриф, ТЗ для копирайтера, семантика, ключевые слова, интент, H1, title, meta description, FAQ, schema, internal links, контент под SEO. Also triggers before writing a page intended to rank in search."
category: seo-foundation
catalog_summary: "SEO brief: intent, structure, entities, metadata, FAQ, internal links"
display_order: 6
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# SEO Content Brief

Сделай SEO-бриф, который помогает написать страницу под интент, а не просто вставить ключевые слова.

---

## When to use

- Нужно ТЗ для копирайтера или SEO-страницы.
- Нужно определить структуру статьи или landing page по поисковому интенту.
- Пользователь дал ключи, запросы, competitors, SERP notes или тему.
- Нужно подготовить meta title, description, H1/H2, FAQ, schema, internal links.
- Нужно связать SEO-страницу с конверсией.

## When NOT to use

- Для общей контент-стратегии используй `content-strategy`.
- Для карты сайта и URL используй `information-architecture`.
- Для написания самого текста используй `page-copywriting` после брифа.
- Для технического SEO-аудита используй отдельный SEO-audit skill, если он есть в проекте.

---

## Required inputs

- тип страницы;
- тема или primary query;
- аудитория;
- search intent;
- бизнес-цель и CTA;
- продуктовая связь;
- вторичные запросы, если есть;
- конкуренты или SERP observations, если есть;
- ограничения: регион, язык, длина, тон, compliance.

Если keyword data нет, создай intent-first brief и пометь места, где нужна проверка данных.

---

## The framework: intent → answer → proof → next step

### Intent

Что человек хочет получить из поиска: информацию, выбор, сравнение, покупку, инструкцию, шаблон.

### Answer

Какие вопросы страница должна закрыть полностью и в каком порядке.

### Proof

Что делает страницу сильнее текущих результатов: примеры, данные, кейсы, screenshots, экспертность.

### Next step

Куда вести пользователя: product page, demo, calculator, template, consultation, related guide.

---

## Workflow

1. Определи primary intent: informational, commercial, transactional, navigational, local, implementation.
2. Сгруппируй запросы по подтемам и buyer stage.
3. Сформулируй angle страницы: почему эта страница будет лучше generic результата.
4. Создай metadata: title, description, H1.
5. Спроектируй H2/H3 структуру.
6. Добавь required answers, examples, proof, objections.
7. Определи FAQ и schema candidates.
8. Пропиши internal links: входящие и исходящие.
9. Укажи conversion next step.
10. Добавь checklist качества.

---

## Failure patterns

- Бриф перечисляет ключи, но не объясняет интент.
- H2 повторяют ключевые слова, а не вопросы пользователя.
- Нет связи с продуктом и дальнейшим действием.
- FAQ выдуман без реальных doubts.
- Title перегружен ключами.
- Страница пытается покрыть несколько несовместимых интентов.
- Нет internal links и proof requirements.

---

## Output format

```markdown
# SEO content brief

## Page summary
## Search intent
## Query and topic groups
## SERP expectations
## Page angle
## Metadata
## Recommended URL
## Outline: H1/H2/H3
## Must-answer questions
## Proof and examples needed
## Product tie-in
## FAQ
## Schema recommendations
## Internal linking plan
## Conversion path
## Copywriter checklist
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `seo-briefs.md`
- Ready for next skill: yes/no
- Recommended next skill: `page-copywriting`
- Inputs passed forward:
  - page type and URL
  - primary intent
  - query/topic groups
  - title, meta description, H1
  - H2/H3 outline
  - must-answer questions
  - proof and examples needed
  - FAQ
  - schema candidates
  - internal links
  - conversion next step
- Assumptions to keep:
  - [список]
- Open questions:
  - [данные, которые нужно проверить]
- Do not change without confirmation:
  - [target URL, primary intent, required H1/H2, regulated terms]
```

Не выдумывай keyword volume, KD, CPC, SERP features или позиции конкурентов без данных.

---

## Reference files

- `references/seo-brief-template.md` — заполняемый шаблон.
- `references/intent-types.md` — типы интентов и структура страницы.
- `references/onpage-checklist.md` — чек-лист on-page качества.
