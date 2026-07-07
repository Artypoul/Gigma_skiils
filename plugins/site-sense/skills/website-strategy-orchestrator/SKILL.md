---
name: website-strategy-orchestrator
description: "Run the full website strategy workflow from product context to meaning map, information architecture, SEO briefs, page copy, conversion review, and final Russian polish. Use this skill whenever the user asks to create a website, landing page, site structure, messaging system, page copy, sitemap, or website brief from scratch. Triggers on сайт с нуля, лендинг, структура сайта, смыслы сайта, тексты сайта, сайт под ключ, homepage, landing, sitemap, IA, positioning, copy. Also triggers when the user asks for several website tasks at once and needs an ordered process."
category: cross-cutting
catalog_summary: "Full website workflow: context, meanings, IA, SEO, copy, review"
display_order: 1
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Website Strategy Orchestrator

Проведи проект сайта по цепочке: контекст → смыслы → структура → SEO → тексты → ревью → финальная редактура.

---

## When to use

- Пользователь просит «сделать сайт», «продумать сайт», «собрать лендинг», «создать структуру и тексты».
- Нужно не одно действие, а весь путь от вводных до готовой спецификации.
- Нужно связать маркетинг, SEO, UX-структуру и copywriting в один результат.
- Пользователь не знает, с чего начать.
- Есть сырой бизнес-контекст, но нет структуры, оффера и текстов.

## When NOT to use

- Нужен только финальный редакторский проход, используй `russian-copy-polish`.
- Нужна только карта сайта и URL, используй `information-architecture`.
- Нужен только SEO-бриф, используй `seo-content-brief`.
- Нужен только текст одной страницы при уже готовом контексте, используй `page-copywriting`.
- Нужен только аудит уже написанного текста, используй `conversion-copy-review`.

---

## Required inputs

Минимум:

- что за продукт или услуга;
- для кого сайт;
- цель сайта;
- тип сайта: лендинг, многостраничник, SaaS, услуги, e-commerce, docs, контентный проект;
- основной CTA.

Если данных не хватает, сначала проверь файлы проекта:

- `.agents/product-marketing.md`
- `.claude/product-marketing.md`
- `product-marketing.md`
- `product-marketing-context.md`
- `meaning-map.md`
- `brief.md`
- `site-brief.md`
- `seo-briefs.md`
- `page-copy.md`

Задай максимум 5 вопросов. Если пользователь просит не спрашивать, продолжай с явными допущениями.

---

## The framework: 8 artifacts

### 1. Product context

Фиксирует продукт, аудиторию, проблему, альтернативы, доказательства и ограничения. Это основа для всех последующих решений.

### 2. Meaning map

Собирает ключевые смыслы: почему аудитории это важно, что меняется после решения, чем продукт отличается, какие objections нужно снять.

### 3. Information architecture

Определяет страницы, URL, навигацию, taxonomy, breadcrumbs и внутренние ссылки.

### 4. Content and SEO plan

Показывает, какие страницы и материалы нужны для спроса, доверия, обучения и конверсии.

### 5. Page briefs

Переводит стратегию в задания для каждой страницы: аудитория, интент, CTA, структура, доказательства.

### 6. Page copy

Пишет страницы с ясной иерархией: H1, hero, problem, solution, benefits, proof, FAQ, CTA.

### 7. Quality pass

Проверяет конверсию, ясность, доказательства, русский язык, структуру и готовность к дизайну/разработке.

### 8. Final site spec

Собирает всё в один handoff-документ: strategy, sitemap, URL, SEO specs, copy, risks, launch checklist.

---

## Workflow

1. Определи тип задачи: сайт с нуля, редизайн, отдельная страница, SEO-кластер, редактура.
2. Выбери маршрут из `references/workflow-map.md`.
3. Собери или создай `product-marketing-context`, если нет достаточного контекста.
4. Запусти смысловую работу через `meaning-positioning`.
5. Спроектируй структуру через `information-architecture`, если есть больше одной страницы или нужна навигация/URL.
6. Для органического спроса запусти `content-strategy` и `seo-content-brief`.
7. Напиши страницы через `page-copywriting`.
8. Проверь страницы через `conversion-copy-review`.
9. Финализируй через `russian-copy-polish`.
10. Собери итоговый документ: стратегия, sitemap, URL, навигация, тексты, SEO, checklist.

---

## Agent execution contract

Работай по gate-логике. Не считай этап завершённым, если нет минимального артефакта.

| Gate | Минимум для перехода дальше |
|---|---|
| Context → Meaning | сегмент, JTBD/задача, alternatives, value proposition, CTA, proof/proof gaps |
| Meaning → IA | core message, differentiation, objections, proof map, hero direction |
| IA → Content/SEO | page inventory, sitemap, URL map, navigation, internal links |
| SEO → Copy | intent, H1/H2, metadata, must-answer questions, CTA, proof requirements |
| Copy → Review | полный текст страницы/блока, CTA, proof blocks, FAQ или notes почему FAQ не нужен |
| Review → Polish | P1/P2/P3 fixes или принятый черновик |
| Polish → Handoff | чистовой текст, risk notes, launch checklist |

Если gate не пройден, создай краткую версию нужного артефакта с разделом `Assumptions` и продолжай. Не оставляй цепочку оборванной.

---

## Failure patterns

- Писать тексты до понимания аудитории и оффера.
- Делать структуру по внутренним отделам компании, а не по задачам пользователя.
- Смешивать несколько сегментов в один общий текст.
- Подменять доказательства обещаниями.
- Строить SEO-страницы без интента и внутренней перелинковки.
- Использовать общие фразы: «индивидуальный подход», «комплексные решения», «эксперты своего дела».
- Давать только советы, а не готовые артефакты.
- Для одной страницы пропускать `product-marketing-context` и `meaning-positioning`, когда контекст отсутствует.

---

## Output format

Для полного проекта выдай:

```text
# Website strategy package

## 1. Допущения и входные данные
## 2. Product marketing context
## 3. Meaning map
## 4. Information architecture
## 5. Content and SEO plan
## 6. Page briefs
## 7. Page copy
## 8. Conversion review
## 9. Russian polish notes
## 10. Launch checklist
## 11. Open risks and validation tasks
```

Если пользователь просит папку/файлы, сохрани артефакты отдельно:

- `product-marketing.md`
- `meaning-map.md`
- `information-architecture.md`
- `content-plan.md`
- `seo-briefs.md`
- `page-copy.md`
- `copy-review.md`
- `final-site-spec.md`

---

## Handoff

`website-strategy-orchestrator` — диспетчер. Он должен собрать финальный пакет и не запускать сам себя как этап.

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `final-site-spec.md`
- Chain status: complete/partial
- Completed artifacts:
  - `product-marketing.md`
  - `meaning-map.md`
  - `information-architecture.md`
  - `content-plan.md`
  - `seo-briefs.md`
  - `page-copy.md`
  - `copy-review.md`
  - `final-copy.md`
- Remaining blockers:
  - [только реальные блокеры]
- Launch readiness: ready/not ready
- Do not change without confirmation:
  - [final URL, final CTA, approved claims, legal text]
```

---

## Reference files

- `references/workflow-map.md` — карта, какой skill запускать на каком этапе.
- `references/site-output-checklist.md` — финальная проверка перед передачей в дизайн/разработку.
- `references/question-limits.md` — как работать при нехватке данных.
- `references/chain-gates.md` — gate-проверки между этапами.
