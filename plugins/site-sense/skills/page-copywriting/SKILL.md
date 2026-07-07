---
name: page-copywriting
description: "Write website page copy for homepages, landing pages, service pages, product pages, pricing pages, comparison pages, and SEO landing pages using the product context, meaning map, page brief, proof, objections, and CTA. Use this skill whenever the user asks to write site copy, landing page copy, homepage copy, hero section, service page, product page, page sections, FAQ, CTA, or website text. Triggers on текст сайта, лендинг, написать страницу, homepage copy, hero, landing copy, CTA, блоки сайта, FAQ, продающий текст, текст услуги, продуктовая страница. Also triggers after meaning-positioning or seo-content-brief when the user needs finished page copy."
category: content
catalog_summary: "Writes website pages: hero, sections, proof, FAQ, CTA"
display_order: 7
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Page Copywriting

Напиши страницу сайта так, чтобы пользователь быстро понял, что это, зачем ему, почему верить и что делать дальше.

---

## When to use

- Нужно написать главную, лендинг, страницу услуги, продукта, pricing, comparison, SEO-page.
- Нужно собрать hero, блоки, benefits, proof, FAQ, CTA.
- Есть бриф, смысловая карта или SEO-бриф.
- Нужно переписать страницу с нуля по новой стратегии.
- Нужно сделать несколько вариантов hero или оффера.

## When NOT to use

- Если нет понимания аудитории и смысла, сначала используй `product-marketing-context` и `meaning-positioning`.
- Если страница должна ранжироваться, сначала используй `seo-content-brief`.
- Если нужно только проверить существующий текст, используй `conversion-copy-review`.
- Если нужно только вычитать русский, используй `russian-copy-polish`.

---

## Required inputs

- page type;
- аудитория;
- цель страницы;
- основной CTA;
- смысл/оффер;
- proof points;
- objections;
- SEO intent, если есть;
- tone of voice;
- ограничения по длине.

Если данных нет, создай черновик с допущениями и выдели места, где нужен proof.

---

## The framework: page narrative

### 1. Match

Первый экран должен подтвердить: «я попал туда, куда нужно». Что это, для кого, какой результат.

### 2. Problem

Покажи ситуацию и цену текущего способа. Без драматизации и клише.

### 3. Mechanism

Объясни, как продукт создаёт изменение.

### 4. Benefits

Покажи результаты пользователя, а не свойства продукта.

### 5. Proof

Кейсы, цифры, отзывы, логотипы, процесс, примеры.

### 6. Objections

Сними сомнения: цена, сложность, риски, внедрение, доверие, сравнение.

### 7. Action

Дай конкретный следующий шаг.

---

## Workflow

1. Определи тип страницы и её роль в воронке.
2. Выбери главный message из `meaning-positioning` или сформулируй его.
3. Напиши 3 варианта hero: clear, sharp, proof-led.
4. Выбери рекомендуемый hero.
5. Собери структуру блоков в логическом порядке.
6. Напиши текст каждого блока: headline, body, bullets, CTA.
7. Добавь proof blocks и FAQ.
8. Проверь, что CTA повторяется в нужных местах.
9. Добавь notes для дизайнера: какие визуалы, tables, screenshots, cards нужны.
10. Если есть SEO-бриф, соблюдай H1/H2 и must-answer вопросы.

---

## Failure patterns

- Hero красивый, но не объясняет продукт.
- Слишком много «мы», мало «вы/ваша задача».
- Benefits написаны как features.
- Нет proof рядом с сильными claims.
- CTA одинаково расплывчатый везде: «узнать больше».
- Страница не ведёт по логике, блоки можно перемешать без потери смысла.
- FAQ отвечает на вопросы компании, а не сомнения пользователя.
- Русский текст звучит как переведённый SaaS-сайт.

---

## Output format

```markdown
# Page copy

## Page brief recap
## Hero variants
## Recommended hero
## Page structure
## Full copy
### Section 1: Hero
### Section 2: Problem
### Section 3: Solution / mechanism
### Section 4: Benefits
### Section 5: How it works
### Section 6: Proof
### Section 7: Comparison / objections
### Section 8: FAQ
### Section 9: Final CTA
## Meta title and description, if SEO page
## Design notes
## Missing proof / validation notes
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `page-copy.md`
- Ready for next skill: yes/no
- Recommended next skill: `conversion-copy-review`
- Inputs passed forward:
  - page brief recap
  - selected hero
  - full copy by section
  - CTA placements
  - proof blocks
  - FAQ
  - design notes
  - missing proof / validation notes
- Assumptions to keep:
  - [список]
- Open questions:
  - [только критичные]
- Do not change without confirmation:
  - [chosen hero, claims awaiting proof, SEO H1/H2, CTA]
```

---

## Reference files

- `references/page-structure-library.md` — структуры разных типов страниц.
- `references/hero-formulas.md` — формулы hero.
- `references/faq-patterns.md` — какие FAQ нужны для конверсии.
