---
name: russian-copy-polish
description: "Edit Russian website copy for clarity, natural rhythm, directness, credibility, UX readability, microcopy quality, and removal of bureaucratic language, generic AI phrasing, translation artifacts, and empty marketing clichés. Use this skill whenever the user asks to polish Russian copy, humanize text, remove нейрослоп, make text clearer, improve UX writing, edit website copy, or adapt copy for Russian-speaking users. Triggers on отредактируй, русский текст, убери канцелярит, нейрослоп, humanize ru, сделать живее, UX copy, микрокопирайтинг, вычитка, лендинг на русском. Also triggers as the final pass after page-copywriting."
category: content
catalog_summary: "Russian copy editing: clarity, rhythm, naturalness, UX, no clichés"
display_order: 9
license: MIT
metadata:
  version: 0.2.1
  language: ru
---
# Russian Copy Polish

Сделай русский текст ясным, живым, уверенным и пригодным для сайта. Убери канцелярит, нейрослоп и пустые маркетинговые формулы.

---

## When to use

- Нужно финально вычитать текст сайта.
- Текст звучит как перевод или AI-generated copy.
- Нужно упростить, сделать точнее, убрать канцелярит.
- Нужно улучшить UX-microcopy: кнопки, формы, ошибки, подсказки.
- Нужно сохранить смысл, но сделать стиль естественнее.

## When NOT to use

- Если нет стратегии и текст слаб по смыслу, сначала используй `meaning-positioning`.
- Если страница плохо конвертит, сначала используй `conversion-copy-review`.
- Если нужно написать страницу с нуля, используй `page-copywriting`.
- Если нужен SEO-бриф, используй `seo-content-brief`.

---

## Required inputs

- текст;
- аудитория;
- цель страницы или блока;
- желаемый тон;
- что нельзя менять;
- SEO-термины, которые нужно сохранить;
- юридические формулировки, если есть.

Если ограничений нет, редактируй на ясность и естественность, не меняя фактический смысл.

---

## The framework: 7 edits

### 1. Meaning preservation

Сохрани факты, claims, CTA, proof и продуктовые ограничения.

### 2. Plain Russian

Убери тяжёлые конструкции, существительные вместо глаголов, официальщину.

### 3. Concrete language

Заменяй общие слова на конкретные результаты, действия, примеры.

### 4. Rhythm

Чередуй короткие и средние предложения. Убирай длинные цепочки.

### 5. Trust

Не усиливай claims без proof. Лучше точнее, чем громче.

### 6. UX clarity

Кнопки, формы, ошибки и подсказки должны говорить, что произойдёт дальше.

### 7. No AI smell

Убери фразы, которые звучат как шаблон: «в современном мире», «инновационные решения», «широкий спектр», «индивидуальный подход», «выведите бизнес на новый уровень».

---

## Workflow

1. Определи цель текста: объяснить, убедить, направить, снять страх, обучить.
2. Сохрани все факты и обязательные термины.
3. Найди и замени канцелярит.
4. Найди общие claims и сделай их конкретнее или пометь как proof gap.
5. Упростить синтаксис.
6. Улучшить заголовки, CTA и микрокопию.
7. Проверь тон: уверенный, не кричащий, не официальный.
8. Выдай две версии, если нужно: «бережная редактура» и «смелее».

---

## Failure patterns

- Делать текст красивее, но менее точным.
- Добавлять новые обещания без основания.
- Убирать SEO-термины, которые нужны.
- Делать всё слишком разговорным для B2B/экспертного контекста.
- Переписывать CTA так, что непонятно, что будет после клика.
- Оставлять «мы являемся», «осуществляем», «позволяет производить».

---

## Output format

```markdown
# Russian copy polish

## Edited version

[Текст]

## What changed

- [Правка и причина]

## Risk notes

- [Где не хватает proof или фактов]

## Optional stronger version

[Если уместно]
```

Для длинных страниц редактируй по блокам:

```markdown
## Hero
## Problem
## Solution
## Benefits
## Proof
## FAQ
## CTA
```

---

## Handoff

В конце результата добавь:

```markdown
## Handoff

- Artifact produced: `final-copy.md`
- Ready for next skill: yes/no
- Recommended next skill: `website-strategy-orchestrator`
- Inputs passed forward:
  - edited final copy
  - what changed
  - risk notes
  - preserved SEO terms
  - preserved claims and CTA
- Assumptions to keep:
  - [список]
- Open questions:
  - [если остались]
- Do not change without confirmation:
  - [final URL, final CTA, approved claims, legal text]
```

Если это была standalone-редактура без полной цепочки сайта, на этом шаге можно завершить работу без следующего skill.

---

## Reference files

- `references/ru-style-guide.md` — правила русского стиля.
- `references/banned-phrases.md` — список слабых фраз.
- `references/ux-microcopy.md` — кнопки, формы, ошибки, подсказки.
