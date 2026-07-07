---
name: information-architecture
description: "Design website information architecture: sitemap, page hierarchy, navigation, URL patterns, breadcrumbs, taxonomy, labeling, internal linking, and redirects. Use this skill whenever the user asks for structure of a website, sitemap, navigation, IA, URL map, page hierarchy, site sections, breadcrumbs, or content organization. Triggers on структура сайта, карта сайта, sitemap, IA, navigation, URL structure, перелинковка, taxonomy, categories, breadcrumbs, меню сайта, какие страницы нужны. Also triggers when content is being written without a structural plan."
category: strategy-and-discovery
catalog_summary: "Sitemap, page hierarchy, navigation, URLs, taxonomy, labels, internal links"
display_order: 4
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Information Architecture

Спроектируй структуру сайта так, чтобы пользователи находили нужное, поисковые системы понимали страницы, а тексты имели понятные места.

---

## When to use

- Нужно понять, какие страницы должны быть на сайте.
- Нужно сделать sitemap, URL map, навигацию, breadcrumbs.
- Сайт разрастается, и контент нужно организовать.
- Нужно подготовить структуру для дизайнера, разработчика или SEO.
- Нужно перестроить существующий сайт без потери URL и смысла.

## When NOT to use

- Для отдельной SEO-страницы используй `seo-content-brief`.
- Для написания текста используй `page-copywriting`.
- Для стратегии контента и topic clusters используй `content-strategy`.
- Для первичного позиционирования используй `meaning-positioning`.

---

## Required inputs

- тип сайта;
- аудитория и её задачи;
- бизнес-цели сайта;
- список существующих или планируемых страниц;
- SEO-приоритеты;
- важные конверсии;
- технические ограничения: CMS, языки, регионы, каталог, блог, docs;
- существующие URL и требования к редиректам, если сайт уже есть.

---

## The framework: 6 layers

### 1. Mental models

Как аудитория группирует информацию. Структура должна отражать пользовательские задачи, а не внутреннюю оргструктуру.

### 2. Sitemap

Иерархия страниц и типов страниц: homepage, sections, detail pages, blog, resources, docs, legal, landing pages.

### 3. URL patterns

Стабильные и читаемые правила для каждого типа страниц.

### 4. Navigation

Header, footer, sidebar, breadcrumbs, utility nav, contextual links.

### 5. Taxonomy

Категории, теги, фильтры, типы контента, metadata fields.

### 6. Labels

Названия пунктов меню, разделов и страниц языком аудитории.

---

## Workflow

1. Определи тип сайта: SaaS, услуги, e-commerce, docs, блог, hybrid, local business.
2. Выпиши задачи аудитории и бизнес-цели.
3. Составь page inventory: обязательные, SEO, доверие, конверсия, support.
4. Сгруппируй страницы по mental model аудитории.
5. Построй sitemap в ASCII и Mermaid.
6. Назначь URL patterns для каждого типа страниц.
7. Спроектируй header, footer, breadcrumbs, secondary nav.
8. Опиши taxonomy и правила labels.
9. Составь internal linking plan.
10. Для редизайна добавь redirect map.

---

## Failure patterns

- Структура повторяет отделы компании, а не задачи пользователя.
- Header содержит больше 7 основных пунктов.
- «Resources» становится мусорной корзиной для всего.
- URL меняются без причины и без 301 redirects.
- Категории пересекаются, теги разрастаются без правил.
- Важные страницы находятся глубже 3 кликов от главной.
- Breadcrumbs не совпадают с URL или логикой разделов.
- Нет внутренних ссылок на важные страницы.

---

## Output format

```markdown
# Information architecture

## Executive summary
## Audience mental models
## Page inventory
## Sitemap: ASCII
## Sitemap: Mermaid
## URL map
## Navigation specification
## Taxonomy and metadata
## Labeling rules
## Internal linking plan
## Redirect map, if redesign
## Implementation notes
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `information-architecture.md`
- Ready for next skill: yes/no
- Recommended next skill: `content-strategy`
- Inputs passed forward:
  - sitemap
  - page inventory
  - URL map
  - navigation spec
  - page goals
  - target audience per page
  - CTA per page
  - search intent candidates
  - internal linking plan
  - redirects, if redesign
- Assumptions to keep:
  - [список]
- Open questions:
  - [только критичные]
- Do not change without confirmation:
  - [URL patterns, preserved URLs, primary navigation, compliance pages]
```

Если контентный план уже существует или не нужен, после handoff переходи сразу к `seo-content-brief`.

---

## Reference files

- `references/ia-document-template.md` — шаблон итогового IA-документа.
- `references/url-pattern-library.md` — паттерны URL по типам страниц.
- `references/navigation-patterns.md` — header, footer, breadcrumbs, sidebar.
- `references/sitemap-mermaid.md` — Mermaid-шаблоны sitemap.
