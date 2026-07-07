---
name: content-strategy
description: "Plan website and SEO content strategy: content pillars, topic clusters, buyer journey pages, editorial priorities, searchable and shareable content, and internal linking. Use this skill whenever the user asks what content to create, what pages or articles are needed, how to build topical authority, or how to plan a blog/resources section. Triggers on контент-стратегия, контент-план, блог, topic clusters, pillar pages, SEO content, editorial calendar, content gaps, buyer journey. Also triggers when site architecture needs content types and clusters before page writing."
category: content
catalog_summary: "Content pillars, topic clusters, buyer journey, editorial priorities"
display_order: 5
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Content Strategy

Спланируй контент, который приводит спрос, объясняет продукт, закрывает возражения и поддерживает структуру сайта.

---

## When to use

- Нужно понять, какие страницы, статьи, guides, templates или case studies создать.
- Нужно собрать SEO-кластеры и контентные pillars.
- Нужно связать сайт, блог и воронку.
- Нужно найти content gaps против конкурентов или ожиданий аудитории.
- Нужно построить editorial calendar.

## When NOT to use

- Для структуры навигации и URL используй `information-architecture`.
- Для SEO-брифа конкретной страницы используй `seo-content-brief`.
- Для написания текста используй `page-copywriting`.
- Для смысла и оффера используй `meaning-positioning`.

---

## Required inputs

- product marketing context;
- аудитория и buyer stages;
- цели контента: traffic, leads, trust, education, sales enablement, retention;
- существующий контент, если есть;
- конкуренты или темы рынка;
- ресурсы: кто пишет, как часто, форматы;
- SEO-данные, если есть: keywords, GSC, Ahrefs, Semrush, Search Console, site search.

---

## The framework: searchable, shareable, sellable

### Searchable

Контент, который ловит существующий спрос. Он отвечает на запрос, закрывает search intent и ведёт к следующему шагу.

### Shareable

Контент, который создаёт спрос: оригинальные идеи, исследования, сильные позиции, истории, сравнения, данные.

### Sellable

Контент, который помогает выбрать: use cases, comparisons, pricing explainers, case studies, objections, implementation guides.

### Supportive

Контент, который уменьшает трение: docs, onboarding, FAQ, tutorials, checklists, templates.

---

## Workflow

1. Определи 3-5 content pillars, которые связаны с продуктом и задачами аудитории.
2. Разложи темы по buyer journey: awareness, consideration, decision, implementation.
3. Раздели страницы на evergreen pages, blog posts, guides, templates, case studies, comparisons.
4. Найди quick wins: высокая релевантность, понятный интент, низкая сложность, близость к продукту.
5. Собери clusters: hub page + supporting pages.
6. Укажи internal links: hub ↔ spokes, blog → product, comparison → pricing/demo.
7. Приоритизируй по impact, effort, confidence.
8. Сформируй editorial roadmap на 4-12 недель.

---

## Failure patterns

- Контент выбирается по объёму ключей, а не по релевантности бизнесу.
- Блог оторван от продукта и не ведёт к конверсии.
- Все статьи awareness, нет decision/implementation контента.
- Нет внутренних ссылок на продуктовые страницы.
- Pillars слишком широкие или не связаны с тем, что продаём.
- Каждая статья пишется отдельно, без cluster logic.
- Нет обновления старого контента.

---

## Output format

```markdown
# Content strategy

## Goals
## Audience questions
## Content pillars
## Buyer journey map
## Topic clusters
## Page and content inventory
## Prioritized roadmap
## Internal linking strategy
## Measurement plan
## Open research tasks
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `content-plan.md`
- Ready for next skill: yes/no
- Recommended next skill: `seo-content-brief`
- Inputs passed forward:
  - content pillars
  - topic clusters
  - prioritized pages/articles
  - buyer stage per item
  - intent hypothesis
  - product tie-in
  - internal linking opportunities
  - measurement plan
- Assumptions to keep:
  - [список]
- Open questions:
  - [данные, которые нужно проверить]
- Do not change without confirmation:
  - [pillar names, strategic priorities, excluded topics]
```

Если нет инструментальных SEO-данных, не придумывай частотность и сложность. Помечай приоритет как hypothesis-based.

---

## Reference files

- `references/content-cluster-template.md` — шаблон кластера.
- `references/buyer-journey-map.md` — mapping awareness/consideration/decision/implementation.
- `references/editorial-roadmap.md` — план публикаций.
